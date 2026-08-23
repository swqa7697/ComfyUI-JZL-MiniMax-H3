"""JZL MiniMax — 漫剧资产管理节点（modal 配置 + 全局资产池 + 无线传输）。

一个节点替代原来的「24×LoadImage + 8×LoadAudio + 参考总线」子图：
- modal 弹窗动态管理 图片/视频/音频 槽位（数量可调，每项可选文件、类型、开关、自定义名）
- execute 时加载所有「启用」的资产 → 写入全局资产池 JZL_ASSET_POOL
- 输出「资产清单」（JSON 字符串，只含名字/类型/启用状态，不含 tensor）供调度器连线
- 调度器（SceneDispatcher/AudioDispatcher/VideoDispatcher）按资产名从全局池取 tensor

资产名格式：`图片1角色孙悟空` / `视频1分镜战斗参考` / `音频1角色孙悟空`
（前缀 + 序号 + 类型 + 自定义名）
"""

import os
import re
import json
import glob
import math
import shutil
import subprocess
import tempfile

import torch
import torchaudio
import folder_paths
import node_helpers
import comfy.model_management
import comfy.sample
import comfy.samplers
import comfy.utils
import comfy.nested_tensor
from PIL import Image, ImageOps

# 复用 nodes.py 100% 复刻官方的模块级辅助（编码/画布/帧数）
from .nodes import (
    CANVAS_MULTIPLE,
    REF_IMAGE_SHORT_EDGE,
    _empty_av_latent,
    _resize,
    adapt_canvas,
    temporal_shape,
    align_frame_count,
)

# ── 全局资产池（无线传输核心）──────────────────────────────
# key = 资产名（如「图片1角色孙悟空」），value = {"kind": "image"|"audio"|"video", "data": tensor}
JZL_ASSET_POOL = {}

# ── 生成总线池（生成管理器 → 视频保存分配 无线传输）────────
# key = 组序号（0..11），value = {"image": tensor, "audio": dict|None}
JZL_BUS_POOL = {}

# 类型下拉统一列表（图片/视频/音频共用）
ASSET_TYPES = ["角色", "场景", "道具", "分镜", "音效", "音乐", "其他"]

# 视频抽帧：24fps，最多抽 240 帧（超出均匀采样）
VIDEO_FPS = 24
MAX_VIDEO_FRAMES = 240

# 生成模式 → 官方节点映射
_MODE_T2VA = "纯文本生成音视频-T2VA"
_MODE_I2VA = "首帧图生成音视频-I2VA"
_MODE_L2VA = "尾帧图生成音视频-L2VA"
_MODE_FL2VA = "首尾帧生成音视频-FL2VA"
_MODE_VA2VA = "音视频生成音视频-VA2VA"
_MODE_REF2VA = "多参考生成音视频-REF2VA"

_IMAGE_TO_VIDEO_MODES = (_MODE_T2VA, _MODE_I2VA, _MODE_L2VA, _MODE_FL2VA)
_REF_TO_VIDEO_MODES = (_MODE_VA2VA, _MODE_REF2VA)


def _asset_settings_file():
    """资产配置持久化文件路径（存 ComfyUI user 目录）。"""
    try:
        base = folder_paths.get_user_directory()
    except Exception:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "jzl_assets.json")


def _read_asset_settings():
    """读取资产配置，无配置返回默认结构。"""
    try:
        with open(_asset_settings_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {"images": [], "videos": [], "audios": []}


def _write_asset_settings(data):
    """保存资产配置到磁盘。"""
    try:
        with open(_asset_settings_file(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


# ── 短剧管理器统一配置（模型/资产/文本增强/生成参数/采样解码） ──────
MANAGER_DEFAULTS = {
    "auto_save": True,
    "models": {
        "fl2va": {
            "model": "",
            "loras": [],  # [{"name": "", "strength": 1.0}, ...]
        },
        "ref2va": {
            "model": "",
            "loras": [],
        },
        "common": {
            "clip": "",
            "video_vae": "",
            "audio_vae": "",
            "accel_mode": "关闭",
        },
    },
    "assets": {"images": [], "videos": [], "audios": []},
    "enhance": {
        "enabled": False,
        "llm_backend": "本地模型 [local]",
        "preset_mode": "首尾帧生成音视频[中文]-FL2VA [ZH]",
        "duration": 8,
        "visual_style": "不指定 / Unspecified",
        "music": "禁止音乐 / No Music",
        "aspect": "16:9",
        "cuts": "不指定 / Unspecified",
        "preset_prompt": "",
        "custom_prompt": "",
        "system_prompt": "",
        "inference_mode": "one by one",
        "max_frames": 24,
        "max_size": 256,
        "seed": 0,
    },
    "gen_params": {
        "aspect_ratio": "16:9 (Widescreen)",
        "megapixels": 1.0,
        "multiple": 32,
        "duration": 8,
        "width": 0,
        "height": 0,
        "scale_factor": 1.0,
        "upscale_scale": 1.5,
    },
    "sample_decode": {
        "sampler": "res_multistep",
        "scheduler": "simple",
        "steps": 25,
        "cfg": 1.0,
        "shift_video": 12.0,
        "shift_audio": 3.0,
        "seed_mode": "randomize",
        "decode_video": "XB-BOX - VAE解码（原版优化）",
        "decode_audio": "VAE解码（音频）",
    },
}


def _list_models(category):
    """列出 models/<category>/MiniMax-H3 下的模型文件（相对路径，如 MiniMax-H3/xxx.safetensors）。"""
    try:
        files = folder_paths.get_filename_list(category)
        return [f for f in files if "minimax-h3" in f.lower() or "minimax_h3" in f.lower()]
    except Exception:
        return []


def _manager_settings_file():
    """短剧管理器配置持久化文件（存 ComfyUI user 目录）。"""
    try:
        base = folder_paths.get_user_directory()
    except Exception:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "jzl_manager.json")


def _read_manager_settings():
    """读取短剧管理器配置，与默认值合并补齐缺失块。"""
    merged = json.loads(json.dumps(MANAGER_DEFAULTS, ensure_ascii=False))
    try:
        with open(_manager_settings_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                for k, v in data.items():
                    if k in merged and isinstance(v, dict):
                        merged[k].update(v)
    except Exception:
        pass
    return merged


def _write_manager_settings(data):
    """保存短剧管理器配置到磁盘。"""
    try:
        with open(_manager_settings_file(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


# ── 生成核心：分段 / 编码 / 采样 / 解码 ──────────────────────

def _slot_name(slot):
    """调度槽位（如「角色A」/「角色:角色A」）→ 纯名字。"""
    if isinstance(slot, str) and ":" in slot:
        return slot.split(":", 1)[-1].strip()
    return str(slot).strip()


def _parse_slots_local(raw):
    """解析调度指令为 slots 数组（兼容 str JSON / list / dict）。"""
    for _ in range(3):
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                return []
        elif isinstance(raw, (list, tuple)):
            return raw if raw else []
        elif isinstance(raw, dict):
            return raw.get("slots", [])
        else:
            return []
    return []


def _parse_four_in_one(content):
    """解析分段四段格式，返回 (h3_prompt, scene, video, audio)。复刻分段处理中心。"""
    h3, scene, video, audio = "", "{}", "{}", "{}"
    for section in re.split(r'\n(?====)', content or ""):
        section = section.strip()
        if section.startswith("===H3_PROMPT==="):
            h3 = section[len("===H3_PROMPT==="):].strip()
        elif section.startswith("===SCENE_INSTRUCTION==="):
            scene = section[len("===SCENE_INSTRUCTION==="):].strip()
        elif section.startswith("===VIDEO_INSTRUCTION==="):
            video = section[len("===VIDEO_INSTRUCTION==="):].strip()
        elif section.startswith("===AUDIO_INSTRUCTION==="):
            audio = section[len("===AUDIO_INSTRUCTION==="):].strip()
    return h3, scene, video, audio


def _collect_slots(raw, kind, limit):
    """按调度指令从全局资产池取 kind 类资产，返回 list[tensor]（≤limit）。"""
    out = []
    for slot in _parse_slots_local(raw):
        if len(out) >= limit:
            break
        name = _slot_name(slot)
        data = None
        for key, item in JZL_ASSET_POOL.items():
            if item.get("kind") != kind:
                continue
            if key == name or _match_asset(name, key):
                data = item.get("data")
                break
        if data is not None:
            out.append(data)
    return out


def _match_asset(a, b):
    """资产名模糊匹配（去空格互相包含，或分词交集）。"""
    sa, sb = (a or "").strip().lower(), (b or "").strip().lower()
    if not sa or not sb:
        return False
    if sa in sb or sb in sa:
        return True
    # 去空格后互相包含（@引用无空格 vs 资产名带空格）
    na = re.sub(r'\s+', '', sa)
    nb = re.sub(r'\s+', '', sb)
    if na and nb and (na in nb or nb in na):
        return True
    ta = {t for t in re.split(r'[-\s_（(）):：,，、/]+', sa) if t}
    tb = {t for t in re.split(r'[-\s_（(）):：,，、/]+', sb) if t}
    return bool(ta & tb)


def _extract_mentions(text):
    """从提示词里提取 @资产名（前端插入的是去空格资产名，如 @图片1角色孙悟空），
    返回 list[str]，并把 @引用从文本移除。"""
    names = []
    cleaned = text or ""

    def _repl(m):
        name = m.group(1).strip("，。；,.、:：()（）[]【】")
        if name:
            names.append(name)
        return ""

    cleaned = re.sub(r'@(\S+)', _repl, cleaned)
    return names, cleaned


def _get_asset_by_name(name):
    """按名字从资产池精确/模糊取资产，返回 (kind, tensor)。"""
    if not JZL_ASSET_POOL or not name:
        return None, None
    if name in JZL_ASSET_POOL:
        item = JZL_ASSET_POOL[name]
        return item.get("kind"), item.get("data")
    for key, item in JZL_ASSET_POOL.items():
        if _match_asset(name, key):
            return item.get("kind"), item.get("data")
    return None, None


def _encode_image_to_video(clip, vae, prompt, width, height, length, first_frame=None, last_frame=None):
    """复刻官方 MiniMaxH3ImageToVideo 编码（t2va / i2va / l2va / fl2va）。"""
    latent, frame_count = _empty_av_latent(width, height, length)

    images = []
    keyframes = []
    if first_frame is not None:
        img = _resize(first_frame[:1], width, height, "disabled")
        images.append(img)
        keyframes.append({"resolved_frame_index": 0, "image": img})
    if last_frame is not None:
        img = _resize(last_frame[:1], width, height, "center")
        images.append(img)
        keyframes.append({"resolved_frame_index": frame_count - 1, "image": img})

    tokens = clip.tokenize(prompt, images=images)
    cond = clip.encode_from_tokens_scheduled(tokens)

    if keyframes:
        for kf in keyframes:
            kf["latent"] = vae.encode(kf.pop("image"))
        cond = node_helpers.conditioning_set_values(cond, {
            "minimax_keyframes": keyframes,
            "minimax_frame_count": frame_count,
        })
    return cond, latent


def _encode_ref_audio(audio_vae, audio):
    """复刻官方 ref 音频编码：waveform → 归一化 latent。"""
    waveform = audio["waveform"]  # [B, C, L]
    sr = audio["sample_rate"]
    vae_sr = getattr(audio_vae, "audio_sample_rate", 32000)
    if sr != vae_sr:
        waveform = torchaudio.functional.resample(waveform, sr, vae_sr)
    z = audio_vae.encode(waveform[:1].movedim(1, -1))  # [1, 32, 2, T]
    return z, z.shape[-1]


def _encode_ref_to_video(clip, vae, audio_vae, prompt, width, height, length,
                         ref_images=None, ref_videos=None, ref_video_audios=None,
                         ref_audios=None, ref_image_size="match"):
    """复刻官方 MiniMaxH3ReferenceToVideo 编码（va2va / ref2va）。"""
    latent, frame_count = _empty_av_latent(width, height, length)

    ref_items = []   # tokenizer 呈现顺序
    ref_blocks = []  # DiT payload 顺序

    for img in (ref_images or []):
        if img is None:
            continue
        h, w = img.shape[1], img.shape[2]
        if ref_image_size == "match":
            scale = min(1.0, math.sqrt((width * height) / (w * h)))
        else:
            scale = min(1.0, REF_IMAGE_SHORT_EDGE / min(w, h))
        tw = max(CANVAS_MULTIPLE, round(w * scale / CANVAS_MULTIPLE) * CANVAS_MULTIPLE)
        th = max(CANVAS_MULTIPLE, round(h * scale / CANVAS_MULTIPLE) * CANVAS_MULTIPLE)
        resized = _resize(img[:1], tw, th, "disabled")
        z = vae.encode(resized)
        ref_items.append({"type": "image", "data": resized})
        ref_blocks.append({"kind": "image", "latent_h": th // 16, "latent_w": tw // 16, "latent": z})

    ref_video_audios = ref_video_audios or []
    for idx, video_frames in enumerate(ref_videos or []):
        if video_frames is None:
            continue
        soundtrack = ref_video_audios[idx] if idx < len(ref_video_audios) else None
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
            continue  # 官方要求 ≥5 帧，不足则跳过该参考
        while n % 17 != 5:
            n -= 1
        frames = frames[:n]
        z = vae.encode(frames)
        audio_latent, ref_audio_t = (None, 0)
        if soundtrack is not None:
            audio_latent, ref_audio_t = _encode_ref_audio(audio_vae, soundtrack)
            ref_items.append({"type": "audio"})
        sample_idx = list(range(0, frames.shape[0], 12))  # FPS//2 = 12 (2fps)
        qwen_frames = frames[sample_idx]
        ref_items.append({"type": "video", "data": qwen_frames,
                          "timestamps": [i / 2.0 for i in range(len(sample_idx))]})
        ref_blocks.append({"kind": "video_audio" if ref_audio_t else "video",
                           "latent_t": z.shape[2], "latent_h": ch // 16, "latent_w": cw // 16,
                           "ref_audio_t": ref_audio_t, "latent": z, "audio_latent": audio_latent})

    for audio in (ref_audios or []):
        if audio is None:
            continue
        audio_latent, ref_audio_t = _encode_ref_audio(audio_vae, audio)
        ref_items.append({"type": "audio"})
        ref_blocks.append({"kind": "audio", "ref_audio_t": ref_audio_t, "audio_latent": audio_latent})

    tokens = clip.tokenize(prompt, minimax_ref_items=ref_items)
    cond = clip.encode_from_tokens_scheduled(tokens)
    if ref_blocks:
        cond = node_helpers.conditioning_set_values(cond, {"minimax_refs": ref_blocks})
    return cond, latent


def _sample_av(model, positive, latent, sample_decode, seed):
    """MiniMax H3 采样：NestedTensor(视频+音频) → 去噪 latent。"""
    steps = int(sample_decode.get("steps", 25) or 25)
    cfg = float(sample_decode.get("cfg", 1.0) or 1.0)
    sampler_name = sample_decode.get("sampler", "res_multistep") or "res_multistep"
    scheduler = sample_decode.get("scheduler", "simple") or "simple"

    latent_image = latent["samples"]
    negative = []  # 空 negative（cfg=1 时不参与；[] 可安全通过 convert_cond）
    noise = comfy.sample.prepare_noise(latent_image, seed, None)
    disable_pbar = not comfy.utils.PROGRESS_BAR_ENABLED
    samples = comfy.sample.sample(
        model, noise, steps, cfg, sampler_name, scheduler,
        positive, negative, latent_image,
        denoise=1.0, disable_pbar=disable_pbar, seed=seed,
    )
    return samples


def _decode_av(vae, audio_vae, samples):
    """NestedTensor latent → (IMAGE [T,H,W,C], AUDIO dict|None)。"""
    if getattr(samples, "is_nested", False):
        tensors = samples.tensors
        video_z = tensors[0]
        audio_z = tensors[1] if len(tensors) > 1 else None
    else:
        video_z = samples
        audio_z = None

    image = vae.decode(video_z)  # [B, T, H, W, C]
    if image.ndim == 5:
        image = image[0]  # [T, H, W, C]

    audio = None
    if audio_z is not None:
        waveform = audio_vae.first_stage_model.decode(audio_z)  # [B, 2, L]
        audio = {"waveform": waveform, "sample_rate": getattr(audio_vae, "audio_sample_rate", 32000)}
    return image, audio


def _resolve_gen_size(gen_params):
    """生成分辨率：优先用面板里手填的宽高，否则按画幅+MP 对齐 32 计算。"""
    w = int(gen_params.get("width", 0) or 0)
    h = int(gen_params.get("height", 0) or 0)
    if w >= 32 and h >= 32:
        return w, h
    ratio = {"16:9": (16, 9), "9:16": (9, 16), "4:3": (4, 3), "3:4": (3, 4),
             "1:1": (1, 1), "21:9": (21, 9), "4:5": (4, 5), "5:4": (5, 4)}.get(
        gen_params.get("aspect_ratio"), (16, 9))
    mp = float(gen_params.get("megapixels", 1.0) or 1.0)
    multiple = int(gen_params.get("multiple", 32) or 32) or 32
    total = mp * 1024 * 1024
    scale = math.sqrt(total / (ratio[0] * ratio[1]))
    return (
        max(32, round(ratio[0] * scale / multiple) * multiple),
        max(32, round(ratio[1] * scale / multiple) * multiple),
    )


def _resolve_length(gen_params):
    """时长（秒）→ 24fps 帧数 → 对齐 17k+5。"""
    duration = float(gen_params.get("duration", 8) or 8)
    return align_frame_count(max(5, round(duration * 24)))


def _resolve_seed(seed_mode, base_seed, index):
    if seed_mode == "fixed":
        return base_seed
    if seed_mode == "increment":
        return base_seed + index
    return torch.randint(0, 0xffffffffffffffff, (1,)).item()


def _load_assets_into_pool(assets):
    """把配置的资产加载进 JZL_ASSET_POOL，返回 (manifest, errors)。"""
    manifest, errors = [], []

    for i, item in enumerate(assets.get("images", []) or []):
        if not item.get("enabled", True):
            continue
        path = (item.get("path") or "").strip()
        if not path or not os.path.isfile(path):
            continue
        try:
            data = _load_image(path)
            name = _asset_name("image", i, item)
            JZL_ASSET_POOL[name] = {"kind": "image", "data": data}
            manifest.append({"name": name, "kind": "image", "type": item.get("type", "")})
        except Exception as e:
            errors.append(f"图片{i + 1}加载失败：{e}")

    for i, item in enumerate(assets.get("videos", []) or []):
        if not item.get("enabled", True):
            continue
        path = (item.get("path") or "").strip()
        if not path or not os.path.isfile(path):
            continue
        data, err = _load_video(path)
        name = _asset_name("video", i, item)
        if data is None:
            errors.append(f"视频{i + 1}加载失败：{err}")
            continue
        JZL_ASSET_POOL[name] = {"kind": "video", "data": data}
        manifest.append({"name": name, "kind": "video", "type": item.get("type", "")})

    for i, item in enumerate(assets.get("audios", []) or []):
        if not item.get("enabled", True):
            continue
        path = (item.get("path") or "").strip()
        if not path or not os.path.isfile(path):
            continue
        try:
            data = _load_audio(path)
            name = _asset_name("audio", i, item)
            JZL_ASSET_POOL[name] = {"kind": "audio", "data": data}
            manifest.append({"name": name, "kind": "audio", "type": item.get("type", "")})
        except Exception as e:
            errors.append(f"音频{i + 1}加载失败：{e}")

    return manifest, errors


def _asset_name(kind, index, item):
    """生成资产名：图片1 角色 孙悟空 / 视频1 主体 跳舞的美女 / 音频1 音色 孙悟空参考音色。"""
    prefix = {"image": "图片", "video": "视频", "audio": "音频"}.get(kind, "资产")
    typ = (item.get("type") or "").strip()
    name = (item.get("name") or "").strip()
    return " ".join(x for x in (f"{prefix}{index + 1}", typ, name) if x)


def _find_ffmpeg():
    """查找 ffmpeg 可执行文件：系统 PATH → imageio_ffmpeg。"""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _load_image(path):
    """加载图片 → IMAGE tensor [1, H, W, C]（RGB, 0-1）。"""
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)  # 处理 EXIF 旋转
    img = img.convert("RGB")
    import numpy as np
    arr = np.asarray(img, dtype=np.float32) / 255.0
    return torch.from_numpy(arr)[None]  # [1, H, W, C]


def _load_audio(path):
    """加载音频 → AUDIO dict {"waveform": [1, C, L], "sample_rate": int}。"""
    waveform, sample_rate = torchaudio.load(path)  # [C, L]
    return {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}


def _load_video(path):
    """加载视频 → IMAGE 序列 [T, H, W, C]（ffmpeg 抽帧，24fps，最多 240 帧）。"""
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        return None, "未找到 ffmpeg（请安装 imageio-ffmpeg）"

    tmp = tempfile.mkdtemp(prefix="jzl_video_")
    try:
        out_pattern = os.path.join(tmp, "f_%05d.png")
        # fps=24 抽帧，短边缩放到 768 控制内存
        cmd = [
            ffmpeg, "-loglevel", "error", "-i", path,
            "-vf", "fps=%d,scale='min(768,iw)':-2" % VIDEO_FPS,
            "-frames:v", str(MAX_VIDEO_FRAMES),
            out_pattern,
        ]
        subprocess.run(cmd, check=True, timeout=600)
        frames = sorted(glob.glob(os.path.join(tmp, "f_*.png")))
        if not frames:
            return None, "视频抽帧失败（无帧）"
        if len(frames) > MAX_VIDEO_FRAMES:
            # 均匀采样
            idx = torch.linspace(0, len(frames) - 1, MAX_VIDEO_FRAMES).long()
            frames = [frames[i] for i in idx.tolist()]
        tensors = [_load_image(f)[0] for f in frames]  # 每个 [H, W, C]
        return torch.stack(tensors), None  # [T, H, W, C]
    except Exception as e:
        return None, f"视频加载失败：{e}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class JZL_MiniMaxAssetManager:
    """MiniMax-H3生成管理器 — 生成模式切换 + 模型/资产/参数/采样解码配置，输出 BUS。

    融合原 1140 工作流核心链路：
    分段处理中心 → 列表分发(每段独立提示词) → 场景/视频/音频调度(从资产池按名取参考)
    → 官方 ImageToVideo / ReferenceToVideo 编码 → 采样 → VAE 解码(视频+音频)
    → 写入生成总线池 JZL_BUS_POOL，输出 BUS(JSON) 给「视频保存分配」节点。
    """

    GENERATION_MODES = [
        "纯文本生成音视频-T2VA",
        "首帧图生成音视频-I2VA",
        "尾帧图生成音视频-L2VA",
        "首尾帧生成音视频-FL2VA",
        "音视频生成音视频-VA2VA",
        "多参考生成音视频-REF2VA",
    ]

    @classmethod
    def INPUT_TYPES(cls):
        # 配置入口按钮由前端 JS 在节点表面添加（addDOMWidget，吸附顶端）
        return {
            "required": {
                "mode": (cls.GENERATION_MODES, {"default": "首尾帧生成音视频-FL2VA",
                    "tooltip": "生成模式切换：T2VA纯文本 / I2VA首帧 / L2VA尾帧 / FL2VA首尾帧 / VA2VA视频二创 / REF2VA多参考"}),
                "video_count": ("INT", {"default": 6, "min": 1, "max": 12, "step": 1,
                    "tooltip": "生成视频数量（分段数，最多 12 段）"}),
                "prompt_input": ("STRING", {"default": "", "multiline": True,
                    "placeholder": "输入故事/剧本提示词，可用 @ 引用已配置的图片/视频/音频…"}),
            },
            "optional": {
                "clip": ("CLIP",),
                "vae": ("VAE",),
                "audio_vae": ("VAE",),
                "model": ("MODEL",),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("生成总线", "资产清单")
    FUNCTION = "execute"
    CATEGORY = "JZL/MiniMax"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # 管理器配置（资产+模型+提示词+参数+偏好+保存）内容变化必须触发重跑
        try:
            with open(_manager_settings_file(), "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return "no-manager"

    def execute(self, mode, video_count, prompt_input,
                clip=None, vae=None, audio_vae=None, model=None):
        manager = _read_manager_settings()
        assets_cfg = manager.get("assets") or {}
        gen_params = manager.get("gen_params") or {}
        sample_decode = manager.get("sample_decode") or {}

        # 清空重建池，避免旧资产/总线残留
        JZL_ASSET_POOL.clear()
        JZL_BUS_POOL.clear()

        manifest, errors = _load_assets_into_pool(assets_cfg)

        width, height = _resolve_gen_size(gen_params)
        length = _resolve_length(gen_params)

        # 分段（融合分段处理中心）：按 [SHOT_START] 块切分
        shots = re.findall(r'\[SHOT_START\](.*?)\[SHOT_END\]', prompt_input or "", re.DOTALL)
        count = max(1, min(12, int(video_count)))

        can_generate = clip is not None and vae is not None and model is not None
        if mode in _REF_TO_VIDEO_MODES and audio_vae is None:
            can_generate = False

        base_seed = int(sample_decode.get("seed", 0) or 0)
        seed_mode = sample_decode.get("seed_mode", "randomize") or "randomize"

        bus_items = []
        for i in range(count):
            raw = shots[i].strip() if i < len(shots) else ""
            h3, scene, vid, aud = _parse_four_in_one(raw)
            if not h3:
                h3 = prompt_input.strip() if i == 0 and prompt_input else "[未找到H3提示词]"

            # @ 引用：从提示词提取 @资产名（移除标记），匹配为参考素材
            mention_names, h3 = _extract_mentions(h3)

            if not can_generate:
                bus_items.append({
                    "index": i, "mode": mode, "prompt": h3,
                    "has_image": False, "has_audio": False,
                    "error": "未连接 CLIP / VAE / model（REF2VA/VA2VA 还需 audio_vae），仅完成分段",
                })
                continue

            # 参考提取（融合场景/视频/音频调度2：从资产池按名匹配）
            ref_images = _collect_slots(scene, "image", 9)
            ref_videos = _collect_slots(vid, "video", 3)
            ref_audios = _collect_slots(aud, "audio", 3)

            # @ 引用补充参考
            for mname in mention_names:
                kind, data = _get_asset_by_name(mname)
                if data is None:
                    continue
                if kind == "image" and len(ref_images) < 9:
                    ref_images.append(data)
                elif kind == "video" and len(ref_videos) < 3:
                    ref_videos.append(data)
                elif kind == "audio" and len(ref_audios) < 3:
                    ref_audios.append(data)

            seed = _resolve_seed(seed_mode, base_seed, i)
            try:
                if mode in _IMAGE_TO_VIDEO_MODES:
                    first = last = None
                    if mode == _MODE_I2VA and ref_images:
                        first = ref_images[0]
                    elif mode == _MODE_L2VA and ref_images:
                        last = ref_images[0]
                    elif mode == _MODE_FL2VA:
                        if ref_images:
                            first = ref_images[0]
                        if len(ref_images) > 1:
                            last = ref_images[1]
                    positive, latent = _encode_image_to_video(clip, vae, h3, width, height, length, first, last)
                else:
                    if mode == _MODE_VA2VA:
                        # 视频二创：参考视频 + 按序配对的音轨（不传图、不传独立音频）
                        paired_audio = ref_audios[:len(ref_videos)]
                        positive, latent = _encode_ref_to_video(
                            clip, vae, audio_vae, h3, width, height, length,
                            ref_images=None, ref_videos=ref_videos,
                            ref_video_audios=paired_audio, ref_audios=None)
                    else:
                        positive, latent = _encode_ref_to_video(
                            clip, vae, audio_vae, h3, width, height, length,
                            ref_images=ref_images, ref_videos=ref_videos,
                            ref_video_audios=ref_audios[:len(ref_videos)], ref_audios=ref_audios)

                samples = _sample_av(model, positive, latent, sample_decode, seed)
                image, audio = _decode_av(vae, audio_vae, samples)

                JZL_BUS_POOL[i] = {"image": image, "audio": audio}
                bus_items.append({
                    "index": i, "mode": mode, "prompt": h3,
                    "has_image": True, "has_audio": audio is not None,
                    "frames": int(image.shape[0]) if image is not None else 0,
                })
            except Exception as e:
                errors.append(f"第{i + 1}段生成失败：{e}")
                bus_items.append({
                    "index": i, "mode": mode, "prompt": h3,
                    "has_image": False, "has_audio": False,
                    "error": f"生成失败：{e}",
                })

        bus = json.dumps({"groups": count, "items": bus_items, "errors": errors}, ensure_ascii=False)
        manifest_json = json.dumps({"assets": manifest, "errors": errors}, ensure_ascii=False)
        return (bus, manifest_json)


class JZL_MiniMaxVideoSaveDistributor:
    """视频保存分配 — 接收生成总线，拆成 ≤12 组「图像 + 音频」输出，每组接一个 Video Combine。

    与「MiniMax-H3生成管理器」通过无线总线（JZL_BUS_POOL）传输：
    生成管理器把每段生成的 (IMAGE, AUDIO) 写入总线池，本节点按组序号读出，
    输出 12 组端口：图像1/音频1 … 图像12/音频12。
    """

    MAX_GROUPS = 12

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "bus": ("STRING", {"forceInput": True,
                    "tooltip": "接「MiniMax-H3生成管理器」的「生成总线」输出"}),
            },
        }

    RETURN_TYPES = ("IMAGE", "AUDIO") * MAX_GROUPS
    RETURN_NAMES = tuple(
        name for i in range(MAX_GROUPS) for name in (f"图像{i + 1}", f"音频{i + 1}")
    )
    FUNCTION = "execute"
    CATEGORY = "JZL/MiniMax"

    @classmethod
    def VALIDATE_INPUTS(cls, bus):
        return True

    def execute(self, bus):
        groups = 0
        try:
            if bus:
                groups = int((json.loads(bus).get("groups") or 0) if isinstance(bus, str) else 0)
        except Exception:
            groups = 0

        out = []
        for i in range(self.MAX_GROUPS):
            item = JZL_BUS_POOL.get(i)
            if i < groups and item:
                image = item.get("image")
                audio = item.get("audio")
                out.append(image if image is not None else _empty_image())
                out.append(audio if audio is not None else _empty_audio())
            else:
                out.append(None)
                out.append(None)
        return tuple(out)


def _empty_image():
    """空占位图像（未生成时保证端口有值，避免下游崩溃）。"""
    return torch.zeros((1, 32, 32, 3), dtype=torch.float32)


def _empty_audio():
    """空占位音频。"""
    return {"waveform": torch.zeros((1, 2, 1), dtype=torch.float32), "sample_rate": 32000}
