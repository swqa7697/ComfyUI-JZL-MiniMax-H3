"""JZL MiniMax H3 节点实现。

Reference to Video (ref2va) — 100% 复刻官方 MiniMaxH3ReferenceToVideo，
并新增「参考值放大」选项（仅 match 模式，面积倍率）。

官方参考: comfy_extras/nodes_minimax_h3.py — MiniMaxH3ReferenceToVideo
"""

import math

import torch
import torchaudio

import nodes
import comfy.model_management
import comfy.nested_tensor
import comfy.utils
import node_helpers
from comfy_api.latest import io

CANVAS_MULTIPLE = 32
BASE_SHORT_EDGE = 768
MAX_PIXELS = 768 * 1344
REF_IMAGE_SHORT_EDGE = 2048
FPS = 24
AUDIO_LATENT_FPS = 40


def align_frame_count(n):
    while n % 17 != 5:
        n += 1
    return n


def video_latent_t(frame_count):
    return 2 if frame_count <= 5 else ((frame_count - 5) // 17) * 5 + 2


def temporal_shape(length):
    frame_count = align_frame_count(max(5, length))
    duration = frame_count / FPS
    return frame_count, video_latent_t(frame_count), round(duration * AUDIO_LATENT_FPS)


def adapt_canvas(width, height):
    """768-short-edge canvas with 768*1344 area cap, per-axis round to 32."""
    ratio = width / height
    if ratio >= 1.0:
        nom_w, nom_h = BASE_SHORT_EDGE * ratio, BASE_SHORT_EDGE
    else:
        nom_w, nom_h = BASE_SHORT_EDGE, BASE_SHORT_EDGE / ratio
    if nom_w * nom_h > MAX_PIXELS:
        s = math.sqrt(MAX_PIXELS / (nom_w * nom_h))
        nom_w, nom_h = nom_w * s, nom_h * s
    return (max(CANVAS_MULTIPLE, round(nom_w / CANVAS_MULTIPLE) * CANVAS_MULTIPLE),
            max(CANVAS_MULTIPLE, round(nom_h / CANVAS_MULTIPLE) * CANVAS_MULTIPLE))


def _resize(image, width, height, crop):
    # image [B, H, W, C] -> [B, height, width, 3]
    samples = image[..., :3].movedim(-1, 1)
    samples = comfy.utils.common_upscale(samples, width, height, "lanczos", crop)
    return samples.movedim(1, -1)


def _empty_av_latent(width, height, length, batch_size=1):
    frame_count, latent_t, audio_t = temporal_shape(length)
    video = torch.zeros([batch_size, 24, latent_t, height // 16, width // 16],
                        device=comfy.model_management.intermediate_device())
    audio = torch.zeros([batch_size, 32, 2, audio_t],
                        device=comfy.model_management.intermediate_device())
    return {"samples": comfy.nested_tensor.NestedTensor((video, audio))}, frame_count


class JZL_MiniMaxH3ReferenceToVideo(io.ComfyNode):
    """ref2va: prompt + reference images / videos / audio -> conditioning + AV latent.

    参考物按固定顺序进入呈现：图像 → 视频（每个视频音轨的 <Audio j> 标签紧挨在其
    <Video k> 之前）→ 独立音频。序号按类型从 1 计数，提示词中用 <Picture i> /
    <Video k> / <Audio j> 引用。
    """

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="JZL_MiniMaxH3ReferenceToVideo",
            description="<Picture i> / <Video k> / <Audio j> 参考条件编码（MiniMax H3 ref2va）。提示词中使用相同标签引用。",
            display_name="JZL - 🎬 MiniMax H3 参考编码",
            category="JZL/MiniMax",
            inputs=[
                io.Clip.Input("clip"),
                io.Vae.Input("vae"),
                io.Vae.Input("audio_vae"),
                io.String.Input("prompt", multiline=True, dynamic_prompts=True),
                io.Int.Input("width", default=1344, min=32, max=nodes.MAX_RESOLUTION, step=32),
                io.Int.Input("height", default=768, min=32, max=nodes.MAX_RESOLUTION, step=32),
                io.Int.Input("length", default=124, min=5, max=3600, step=17,
                    tooltip="24fps 帧数，吸附到模型 17k+5 网格（124 ≈ 5s，训练区间约 124-362）"),
                io.Combo.Input("ref_image_size", options=["match", "max"], default="match",
                    tooltip="参考图尺寸策略。match=按生成画布像素面积等比缩小；max=短边对齐 2048，身份保真度最高但更慢。参考 token 参与每个采样步，max 可能慢数倍。"),
                io.Float.Input("ref_scale", display_name="参考值放大", default=1.0, min=1.0, max=5.0, step=0.1,
                    tooltip="仅 match 模式生效。参考图最终像素面积 = 生成画布面积 × 倍率（面积倍率，非分辨率倍率）。1.0=不放大，2.0=面积×2。越大保真度越高、越慢。"),
                io.Autogrow.Input("ref_images", optional=True,
                    template=io.Autogrow.TemplatePrefix(
                        input=io.Image.Input("ref_image", tooltip="参考图（若大于 2048 短边会被缩小，从不放大）"),
                        prefix="ref_image_", min=0, max=9)),
                io.Autogrow.Input("ref_videos", optional=True,
                    template=io.Autogrow.TemplatePrefix(
                        input=io.Image.Input("ref_video", tooltip="24fps 参考视频帧（2-15s）"),
                        prefix="ref_video_", min=0, max=3)),
                io.Autogrow.Input("ref_video_audios", optional=True,
                    template=io.Autogrow.TemplatePrefix(
                        input=io.Audio.Input("ref_video_audio", tooltip="同序号参考视频的音轨"),
                        prefix="ref_video_audio_", min=0, max=3)),
                io.Autogrow.Input("ref_audios", optional=True,
                    template=io.Autogrow.TemplatePrefix(
                        input=io.Audio.Input("ref_audio", tooltip="独立参考音频"),
                        prefix="ref_audio_", min=0, max=3)),
            ],
            outputs=[io.Conditioning.Output(display_name="positive"), io.Latent.Output()],
        )

    @staticmethod
    def _encode_ref_audio(audio_vae, audio):
        waveform = audio["waveform"]  # [B, C, L]
        sr = audio["sample_rate"]
        vae_sr = getattr(audio_vae, "audio_sample_rate", 32000)
        if sr != vae_sr:
            waveform = torchaudio.functional.resample(waveform, sr, vae_sr)
        z = audio_vae.encode(waveform[:1].movedim(1, -1))  # [1, 32, 2, T]
        return z, z.shape[-1]

    @classmethod
    def execute(cls, clip, vae, audio_vae, prompt, width, height, length, ref_image_size="match",
                ref_scale=1.0, ref_images=None, ref_videos=None, ref_video_audios=None, ref_audios=None) -> io.NodeOutput:
        latent, frame_count = _empty_av_latent(width, height, length)

        ref_items = []   # for the tokenizer presentation, in request order
        ref_blocks = []  # for the DiT payload, same order

        for img in (ref_images or {}).values():
            if img is None:
                continue
            h, w = img.shape[1], img.shape[2]
            if ref_image_size == "match":
                # aspect-preserving scale (down only) to the generation's pixel area
                # JZL 扩展：面积倍率 ref_scale（默认 1.0 = 官方行为）
                scale = min(1.0, math.sqrt(ref_scale * (width * height) / (w * h)))
            else:
                scale = min(1.0, REF_IMAGE_SHORT_EDGE / min(w, h))
            tw = max(CANVAS_MULTIPLE, round(w * scale / CANVAS_MULTIPLE) * CANVAS_MULTIPLE)
            th = max(CANVAS_MULTIPLE, round(h * scale / CANVAS_MULTIPLE) * CANVAS_MULTIPLE)
            resized = _resize(img[:1], tw, th, "disabled")
            z = vae.encode(resized)
            ref_items.append({"type": "image", "data": resized})
            ref_blocks.append({"kind": "image", "latent_h": th // 16, "latent_w": tw // 16, "latent": z})

        ref_video_audios = ref_video_audios or {}
        for name, video_frames in (ref_videos or {}).items():
            if video_frames is None:
                continue
            # index-paired soundtrack: ref_video_audio_N belongs to ref_video_N
            soundtrack = ref_video_audios.get("ref_video_audio_" + name.rsplit("_", 1)[-1])
            vh, vw = video_frames.shape[1], video_frames.shape[2]
            cw, ch = adapt_canvas(vw, vh)
            if vw * vh < cw * ch:
                cw = max(CANVAS_MULTIPLE, round(vw / CANVAS_MULTIPLE) * CANVAS_MULTIPLE)
                ch = max(CANVAS_MULTIPLE, round(vh / CANVAS_MULTIPLE) * CANVAS_MULTIPLE)
            frames = _resize(video_frames, cw, ch, "disabled")
            if frames.shape[0] > frame_count:
                frames = frames[:frame_count]
            n = frames.shape[0]
            if n < 5:
                raise ValueError("MiniMax H3 reference videos need at least 5 frames (~0.2s at 24 fps)")
            while n % 17 != 5:
                n -= 1
            frames = frames[:n]
            z = vae.encode(frames)
            audio_latent, ref_audio_t = (None, 0)
            if soundtrack is not None:
                audio_latent, ref_audio_t = cls._encode_ref_audio(audio_vae, soundtrack)
                # the soundtrack gets its own <Audio j> label, emitted before <Video k>
                ref_items.append({"type": "audio"})
            # Qwen sees the video at 2 fps with timestamps
            sample_idx = list(range(0, frames.shape[0], FPS // 2))
            qwen_frames = frames[sample_idx]
            ref_items.append({"type": "video", "data": qwen_frames,
                              "timestamps": [i / 2.0 for i in range(len(sample_idx))]})
            ref_blocks.append({"kind": "video_audio" if ref_audio_t else "video",
                               "latent_t": z.shape[2], "latent_h": ch // 16, "latent_w": cw // 16,
                               "ref_audio_t": ref_audio_t, "latent": z, "audio_latent": audio_latent})

        for audio in (ref_audios or {}).values():
            if audio is None:
                continue
            audio_latent, ref_audio_t = cls._encode_ref_audio(audio_vae, audio)
            ref_items.append({"type": "audio"})
            ref_blocks.append({"kind": "audio", "ref_audio_t": ref_audio_t, "audio_latent": audio_latent})

        tokens = clip.tokenize(prompt, minimax_ref_items=ref_items)
        cond = clip.encode_from_tokens_scheduled(tokens)
        if ref_blocks:
            cond = node_helpers.conditioning_set_values(cond, {"minimax_refs": ref_blocks})
        return io.NodeOutput(cond, latent)
