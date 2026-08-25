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
import time
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
from comfy_api.latest import io

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

# ── 调度槽位映射（槽位名「角色A」→ 资产名「图片1 角色 孙悟空」）────────
JZL_SLOT_MAP = {}

# 类型下拉统一列表（图片/视频/音频共用）
ASSET_TYPES = ["角色", "场景", "道具", "分镜", "音效", "音乐", "其他"]

# 视频抽帧：24fps，最多抽 240 帧（超出均匀采样）
VIDEO_FPS = 24
MAX_VIDEO_FRAMES = 240

# 画幅比例选项（与「海螺H3视频参数」/ 官方 ResolutionSelector 一致）
ASPECT_RATIO_OPTIONS = [
    "1:1 (Square)", "2:3 (Portrait Photo)", "3:2 (Photo)", "3:4 (Portrait Standard)",
    "4:5 (Portrait Tall)", "4:3 (Standard)", "5:4 (Landscape Tall)",
    "9:16 (Portrait Widescreen)", "16:9 (Widescreen)", "21:9 (Ultrawide)",
]
ASPECT_RATIOS = {
    "1:1 (Square)": (1, 1), "2:3 (Portrait Photo)": (2, 3), "3:2 (Photo)": (3, 2),
    "3:4 (Portrait Standard)": (3, 4), "4:5 (Portrait Tall)": (4, 5), "4:3 (Standard)": (4, 3),
    "5:4 (Landscape Tall)": (5, 4), "9:16 (Portrait Widescreen)": (9, 16),
    "16:9 (Widescreen)": (16, 9), "21:9 (Ultrawide)": (21, 9),
}


def _story_style_options():
    """故事风格选项列表（供 schema combo 使用）。"""
    try:
        from .presets.script import STORY_STYLES
        keys = list(STORY_STYLES.keys())
        if keys:
            return keys
    except Exception:
        pass
    return ["热血战斗"]


# ── ⑤采样解码 / 偏好设置 原生 widget 选项 ────────────────
SAMPLER_OPTIONS = ["res_multistep", "euler", "euler_ancestral", "dpmpp_2m", "dpmpp_2m_sde",
                   "dpmpp_sde", "ddim", "uni_pc", "lcm", "gradient_estimation"]
SCHEDULER_OPTIONS = ["simple", "normal", "karras", "exponential", "sgm_uniform", "beta", "ddim_uniform"]
SEED_MODE_OPTIONS = ["randomize", "fixed", "increment"]
DECODE_VIDEO_OPTIONS = ["XB-BOX - VAE解码（原版优化）", "VAE解码"]
DECODE_AUDIO_OPTIONS = ["VAE解码（音频）"]


def _preference_options():
    """镜头语言偏好选项（与 JZL_MiniMaxH3Preference / JZL_MiniMaxPreset 保持一致）。"""
    try:
        from .nodes_llama import JZL_MiniMaxH3Preference as _P, JZL_MiniMaxPreset as _Pr
        return (list(_P._SHOT_SIZES), list(_P._CAMERA_MOVES), list(_P._CUT_RHYTHMS),
                list(_P._TRANSITIONS), list(_P._CREATIVE_REQS), list(_P._DETAIL_LENGTHS),
                list(_Pr._MUSIC))
    except Exception:
        return (["随机组合"], ["随机组合"], ["随机"], ["随机"], ["无特别要求"],
                ["标准 (350-500字)"], ["禁止音乐 / No Music"])


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
        },
    },
    "assets": {"images": [], "videos": [], "audios": []},
    "enhance": {
        "story_decompose": True,
        "enabled": False,
        "llm_backend": "本地模型 [local]",
        "force_offload": False,
        "seed": 0,
        "seed_control": "randomize",
        "llm": {
            "model": "",
            "mmproj": "None",
            "chat_handler": "None",
            "backend": "llama-cpp-python",
            "n_ctx": 32768,
            "vram_limit": -1,
            "image_min_tokens": 0,
            "image_max_tokens": 0,
            "max_tokens": 8192,
            "top_k": 40,
            "top_p": 0.9,
            "min_p": 0.05,
            "typical_p": 1.0,
            "temperature": 0.6,
            "repeat_penalty": 1.05,
            "frequency_penalty": 0.0,
            "present_penalty": 0.0,
            "mirostat_mode": 0,
            "mirostat_eta": 0.1,
            "mirostat_tau": 5.0,
            "gpu_device": "auto",
        },
        "api": {
            "provider": "OpenAI 兼容 (OpenAI/DeepSeek/Qwen/GLM/Kimi/Ollama/vLLM/LM Studio)",
            "model": "",
            "api_key": "",
            "base_url": "",
            "temperature": 0.6,
            "max_tokens": 8192,
            "thinking": "disabled",
        },
        "preference": {
            "shot_size": "随机组合",
            "camera_move": "随机组合",
            "cut_rhythm": "随机",
            "transition": "随机",
            "music_style": "禁止音乐 / No Music",
            "creative_req": "无特别要求",
            "detail_length": "标准 (350-500字)",
            "custom": "",
        },
        "custom_prompt": "",
        "system_prompt": "",
        "inference_mode": "one by one",
        "max_frames": 24,
        "max_size": 256,
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
        "steps": 4,
        "cfg": 1.0,
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


def _merge_manager_settings(data):
    """节点配置与默认值合并（补齐缺失块），并做旧配置兼容迁移。"""
    merged = json.loads(json.dumps(MANAGER_DEFAULTS, ensure_ascii=False))
    if isinstance(data, dict):
        for k, v in data.items():
            if k in merged and isinstance(v, dict):
                merged[k].update(v)
    # 旧配置兼容：enhance.llm.model 为空时，从旧 models.llm_* 字段补齐（①生成模型管理时代的结构）
    llm = merged.get("enhance", {}).get("llm") or {}
    if not (llm.get("model") or "").strip():
        legacy = merged.get("models") or {}
        if legacy.get("llm_model"):
            llm["model"] = legacy.get("llm_model")
        if legacy.get("mmproj"):
            llm["mmproj"] = legacy.get("mmproj")
        if legacy.get("chat_handler"):
            llm["chat_handler"] = legacy.get("chat_handler")
        if legacy.get("n_ctx") is not None:
            llm["n_ctx"] = int(legacy.get("n_ctx"))
        if legacy.get("vram_limit") is not None:
            llm["vram_limit"] = int(legacy.get("vram_limit"))
    return merged


def _read_manager_settings():
    """读取全局短剧管理器配置（旧工作流/无节点配置时回退用）。"""
    try:
        with open(_manager_settings_file(), "r", encoding="utf-8") as f:
            return _merge_manager_settings(json.load(f))
    except Exception:
        return _merge_manager_settings({})


def _parse_node_manager_settings(raw):
    """节点独立配置：解析工作流内保存的 manager_settings JSON；空/非法回退全局配置。"""
    if raw and isinstance(raw, str) and raw.strip():
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and any(k in data for k in ("assets", "enhance", "sample_decode")):
                return _merge_manager_settings(data)
        except Exception:
            pass
    return _read_manager_settings()


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
    """按调度指令从全局资产池取 kind 类资产，返回 list[tensor]（≤limit）。

    槽位名（如「场景A」）先经 JZL_SLOT_MAP 解析为资产名（如「图片2 场景 森林」），
    再与资产池模糊匹配；槽位本身已是资产名时直接匹配。
    """
    out = []
    for slot in _parse_slots_local(raw):
        if len(out) >= limit:
            break
        name = _slot_name(slot)
        asset_name = JZL_SLOT_MAP.get(name, name)
        data = None
        for key, item in JZL_ASSET_POOL.items():
            if item.get("kind") != kind:
                continue
            if key == asset_name or _match_asset(asset_name, key):
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
    """从提示词里提取资产引用（「图片N…」「视频N…」「音频N…」格式），
    返回 list[str]，并把引用从文本移除（引用仅用于匹配参考素材，不进入模型文本）。

    前端富文本插入的是去空格资产名（如「图片1角色碗碗」），本函数按资产名前缀识别。
    """
    names = []
    cleaned = text or ""

    def _repl(m):
        names.append(m.group(0))
        return ""

    cleaned = re.sub(r'(?:图片|视频|音频)\d+[^\s@，。；,.、]*', _repl, cleaned)
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
                         ref_audios=None, ref_image_size="match", ref_scale=1.0):
    """复刻官方 MiniMaxH3ReferenceToVideo 编码（va2va / ref2va）。"""
    latent, frame_count = _empty_av_latent(width, height, length)

    ref_items = []   # tokenizer 呈现顺序
    ref_blocks = []  # DiT payload 顺序

    for img in (ref_images or []):
        if img is None:
            continue
        h, w = img.shape[1], img.shape[2]
        if ref_image_size == "match":
            scale = min(1.0, math.sqrt(ref_scale * (width * height) / (w * h)))
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
    steps = int(sample_decode.get("steps", 4) or 4)
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


def _concat_images(images):
    """拼接多段视频帧 [T,H,W,C] → 单段 [sum(T),H,W,C]（跳过 None）。"""
    valid = [img for img in (images or []) if img is not None]
    if not valid:
        return None
    if len(valid) == 1:
        return valid[0]
    return torch.cat(valid, dim=0)


def _concat_audios(audios):
    """拼接多段音频 waveform [B,C,L] → [B,C,sum(L)]（跳过 None，统一采样率）。"""
    valid = [a for a in (audios or []) if a is not None and a.get("waveform") is not None]
    if not valid:
        return None
    if len(valid) == 1:
        return valid[0]
    sr = valid[0].get("sample_rate", 32000)
    waves = []
    for a in valid:
        w = a.get("waveform")
        a_sr = a.get("sample_rate", 32000)
        if a_sr != sr:
            w = torchaudio.functional.resample(w, a_sr, sr)
        waves.append(w)
    return {"waveform": torch.cat(waves, dim=-1), "sample_rate": sr}


def _resolve_gen_size(aspect_ratio, megapixels):
    """生成分辨率：官方 ResolutionSelector 公式（画幅×MP → sqrt → 对齐倍数固定 32）。"""
    ratio = ASPECT_RATIOS.get(aspect_ratio, (16, 9))
    mp = float(megapixels or 1.0)
    multiple = 32  # 对齐倍数底层锁定 32
    total = mp * 1024 * 1024
    scale = math.sqrt(total / (ratio[0] * ratio[1]))
    return (
        max(32, round(ratio[0] * scale / multiple) * multiple),
        max(32, round(ratio[1] * scale / multiple) * multiple),
    )


def _resolve_length(duration):
    """时长（秒）→ 24fps 帧数 → 对齐 17k+5。"""
    duration = float(duration or 8)
    return align_frame_count(max(5, round(duration * 24)))


def _resolve_seed(seed_mode, base_seed, index):
    if seed_mode == "fixed":
        return base_seed
    if seed_mode == "increment":
        return base_seed + index
    # 0xffffffffffffffff(2^64-1) 超出 C int64 上界会溢出；用 int64 最大值 2^63-1
    return torch.randint(0, 0x7fffffffffffffff, (1,)).item()


# ── ③提示词：资产介绍 / 启用判断 / 偏好 / LLM 调用 ─────────────

_IMAGE_SLOT_TYPES = ("角色", "场景", "道具", "分镜", "其他")


def _asset_type_for_slot(kind, typ):
    """资产类型 → 调度槽位类型（build_shot_prompt 对照表识别的类型）。

    「自定义」→「其他」：官方 material_table/slot_map 只识别 角色/场景/道具/分镜/视频/音频/音效/音乐/其他。
    """
    if kind == "image":
        if typ == "自定义":
            return "其他"
        return typ if typ in _IMAGE_SLOT_TYPES else "其他"
    if kind == "video":
        return "视频"
    if kind == "audio":
        return "音频"
    return None


def _build_asset_intro(assets_cfg):
    """从勾选素材生成三路 ref_intro（槽位格式）+ 槽位→资产名映射。

    返回 (ref_image_intro, ref_video_intro, ref_audio_intro, slot_to_asset)。
    槽位按类型独立从 A 编号（角色A/场景A/道具A/视频A/音频A…），
    资产名 = 图片N 类型 名称（与 JZL_ASSET_POOL key 一致）。
    """
    slot_to_asset = {}
    counters = {}
    out = {"image": [], "video": [], "audio": []}
    for kind, key in (("image", "images"), ("video", "videos"), ("audio", "audios")):
        for i, item in enumerate(assets_cfg.get(key) or []):
            if not item.get("enabled", True):
                continue
            typ = (item.get("type") or "").strip()
            name = (item.get("name") or "").strip()
            if not name:
                continue
            slot_type = _asset_type_for_slot(kind, typ)
            if not slot_type:
                continue
            # 编号：用户手选 26 字母（A-Z）；缺失/非法时按类型自动兜底编号（旧资产兼容）
            letter = (item.get("letter") or "").strip().upper()
            if not re.match(r'^[A-Z]$', letter):
                letter = chr(ord("A") + counters.get(slot_type, 0))
            slot = f"{slot_type}{letter}"
            # 同类同字母冲突兜底：已被占用则顺延下一个可用字母（旧配置/手动重复）
            while slot in slot_to_asset and letter < "Z":
                letter = chr(ord(letter) + 1)
                slot = f"{slot_type}{letter}"
            counters[slot_type] = counters.get(slot_type, 0) + 1
            asset_name = _asset_name(kind, i, item)
            slot_to_asset[slot] = asset_name
            desc = (item.get("description") or "").strip()
            # 槽位格式（官方解析）：角色A = 名称（描述）
            if desc:
                out[kind].append(f"{slot} = {name}（{desc}）")
            else:
                out[kind].append(f"{slot} = {name}")
    return (
        "\n".join(out["image"]),
        "\n".join(out["video"]),
        "\n".join(out["audio"]),
        slot_to_asset,
    )


def _detect_enables(story, assets_cfg):
    """按勾选素材类型 + 提示词 @引用 智能判断四个调度开关。"""
    enable_scene = enable_props = enable_video = enable_audio = False
    for item in (assets_cfg.get("images") or []):
        if item.get("enabled", True):
            t = (item.get("type") or "").strip()
            if t == "场景":
                enable_scene = True
            elif t == "道具":
                enable_props = True
    for item in (assets_cfg.get("videos") or []):
        if item.get("enabled", True):
            enable_video = True
    for item in (assets_cfg.get("audios") or []):
        if item.get("enabled", True):
            enable_audio = True
    # 提示词 @引用兜底（视频/音频类型无歧义；图片类型按场景/道具字样判断）
    text = story or ""
    if re.search(r'视频\d+', text):
        enable_video = True
    if re.search(r'音频\d+', text):
        enable_audio = True
    if re.search(r'图片\d+[^\s@，。；,.、]*场景', text):
        enable_scene = True
    if re.search(r'图片\d+[^\s@，。；,.、]*道具', text):
        enable_props = True
    return enable_scene, enable_props, enable_video, enable_audio


def _build_preference(enhance):
    """偏好设置（镜头语言）+ 自定义提示词 → preference 字符串。"""
    pref_cfg = enhance.get("preference") or {}
    parts = []
    try:
        from .nodes_llama import JZL_MiniMaxH3Preference
        parts.append(JZL_MiniMaxH3Preference().build(
            pref_cfg.get("shot_size", "随机组合"),
            pref_cfg.get("camera_move", "随机组合"),
            pref_cfg.get("cut_rhythm", "随机"),
            pref_cfg.get("transition", "随机"),
            pref_cfg.get("music_style", "禁止音乐 / No Music"),
            pref_cfg.get("creative_req", "无特别要求"),
            pref_cfg.get("detail_length", "标准 (350-500字)"),
            pref_cfg.get("custom", ""),
        )[0])
    except Exception:
        pass
    custom = (enhance.get("custom_prompt") or "").strip()
    if custom:
        parts.append(custom)
    return "\n".join(parts)


def _llm_local_config(enhance):
    """本地 LLM 模型配置（custom_config）+ 推理参数（parameters）。"""
    c = enhance.get("llm") or {}
    custom_config = {
        "model": (c.get("model") or "").strip(),
        "mmproj": c.get("mmproj") or "None",
        "chat_handler": c.get("chat_handler") or "None",
        "n_ctx": int(c.get("n_ctx", 32768)),
        "vram_limit": int(c.get("vram_limit", -1)),
        "image_min_tokens": int(c.get("image_min_tokens", 0)),
        "image_max_tokens": int(c.get("image_max_tokens", 0)),
        "backend": c.get("backend") or "llama-cpp-python",
        "gpu_device": c.get("gpu_device") or "auto",
    }
    parameters = {
        "max_tokens": int(c.get("max_tokens", 8192)),
        "top_k": int(c.get("top_k", 40)),
        "top_p": float(c.get("top_p", 0.9)),
        "min_p": float(c.get("min_p", 0.05)),
        "typical_p": float(c.get("typical_p", 1.0)),
        "temperature": float(c.get("temperature", 0.6)),
        "repeat_penalty": float(c.get("repeat_penalty", 1.05)),
        "frequency_penalty": float(c.get("frequency_penalty", 0.0)),
        "present_penalty": float(c.get("present_penalty", 0.0)),
        "mirostat_mode": int(c.get("mirostat_mode", 0)),
        "mirostat_eta": float(c.get("mirostat_eta", 0.1)),
        "mirostat_tau": float(c.get("mirostat_tau", 5.0)),
        "state_uid": -1,
    }
    return custom_config, parameters


def _llm_chat(enhance, system_prompt, user_msg, seed):
    """按 enhance 配置调用 LLM（本地/API），返回生成文本。"""
    from .llama_backend import LLAMA_CPP_STORAGE
    from .nodes_llama import JZL_MiniMax_ScriptProcessor

    if "api" in str(enhance.get("llm_backend", "")):
        api_cfg = enhance.get("api") or {}
        return JZL_MiniMax_ScriptProcessor._call_api(
            json.dumps(api_cfg, ensure_ascii=False), system_prompt, user_msg)

    custom_config, parameters = _llm_local_config(enhance)
    if not custom_config["model"]:
        return "[错误] 未选择本地 LLM 模型（请在「文本增强设置」里配置）"
    if not LLAMA_CPP_STORAGE.llm or LLAMA_CPP_STORAGE.current_config != custom_config:
        print("[JZL-llama] 开始加载模型...")
        LLAMA_CPP_STORAGE.load_model(custom_config)
    try:
        _params = parameters.copy()
        _params.pop("present_penalty", None)
        _params.pop("state_uid", None)
        output = LLAMA_CPP_STORAGE.llm.create_chat_completion(
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_msg}],
            seed=seed, **_params)
        return output["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[LLM 错误] {e}"


def _llm_finish(enhance):
    """最后一个 LLM 步骤后：按 force_offload 决定是否卸载本地模型。"""
    if "api" in str(enhance.get("llm_backend", "")):
        return
    try:
        from .llama_backend import LLAMA_CPP_STORAGE
        if LLAMA_CPP_STORAGE.llm is None:
            return  # 本轮未加载本地模型，无需清理（避免无谓 soft_empty_cache）
        if enhance.get("force_offload", False):
            LLAMA_CPP_STORAGE.clean()
        else:
            LLAMA_CPP_STORAGE.clean_state()
    except Exception:
        pass


def _persist_seed_control(manager, enhance, seed_control, current_seed, used_seed):
    """control_after_generate：更新 seed 并写回全局（旧工作流回退），返回新 seed（None=不变）。"""
    if seed_control == "randomize":
        new_seed = int(used_seed)
    elif seed_control == "increment":
        new_seed = current_seed + 1
    else:
        return None
    if int(enhance.get("seed", 0) or 0) == new_seed:
        return None
    enhance["seed"] = new_seed
    manager["enhance"] = enhance
    try:
        _write_manager_settings(manager)
    except Exception:
        pass
    return new_seed


def _build_seed_ui(manager, enhance, seed_control, current_seed, used_seed):
    """构造 control_after_generate 的 ui 回传（前端据此更新本节点 manager_settings 里的 seed）。"""
    ret = _persist_seed_control(manager, enhance, seed_control, current_seed, used_seed)
    if ret is None:
        return None
    return {"seed_update": {"seed": ret, "seed_control": seed_control}}


def _enhance_bus(enhance):
    """构造给「提示词增强」节点复用的 BUS dict（本地/API 双后端）。"""
    is_api = "api" in str(enhance.get("llm_backend", ""))
    custom_config, parameters = _llm_local_config(enhance)
    return {
        "use_api": is_api,
        "save_states": False,
        "api_config": json.dumps(enhance.get("api") or {}, ensure_ascii=False) if is_api else None,
        "llama_model": custom_config if not is_api else None,
        "parameters": parameters if not is_api else None,
    }


def _run_script_processor(story, manager, video_count, story_style, story_name, duration, prompt_lang, seed,
                          ref_image_intro="", ref_video_intro="", ref_audio_intro="",
                          enable_scene=True, enable_props=True, enable_video=True, enable_audio=True,
                          mode="生成模式 (Generate)"):
    """剧本与镜头处理器：直接严格调用 JZL_MiniMax_ScriptProcessor.execute（100% 复刻官方逻辑/格式）。

    返回 (script_output, err)。script_output = 统计表 + [SHOT_START] 分段块（生成模式含「【故事】」正文块），
    与「JZL - 🎬 剧本与镜头处理器」节点「剧本输出」端口内容完全一致。
    """
    from .nodes_llama import JZL_MiniMax_ScriptProcessor
    from .presets.script import SEGMENT_COUNT_OPTIONS

    enhance = manager.get("enhance") or {}
    is_api = "api" in str(enhance.get("llm_backend", ""))
    custom_config, parameters = _llm_local_config(enhance)
    count = max(1, min(12, int(video_count or 6)))

    # 本地后端未选模型：直接给出友好错误（官方 ScriptProcessor 内部不校验空模型，会尝试加载而崩）
    if not is_api and not (custom_config.get("model") or "").strip():
        return story, "[错误] 未选择本地 LLM 模型（请在「文本增强设置」里配置）"

    # video_count → 最近的分段数标签（官方 ScriptProcessor 的分段数 combo 只有 4/6/9/12/16/20/24）
    seg_options = sorted(SEGMENT_COUNT_OPTIONS.values())
    seg = min(seg_options, key=lambda o: (abs(o - count), o))
    seg_label = next(k for k, v in SEGMENT_COUNT_OPTIONS.items() if v == seg)

    # 自定义规则：管理器「系统提示词」直接喂给官方 ScriptProcessor 的 custom_rule_path（支持纯文本）
    custom_rule_text = (enhance.get("system_prompt") or "").strip()
    # 强制卸载与「开启增强」联动：增强开启时拆解后不强制卸载（保留模型给增强用，等增强完再卸，省重复加载）
    enhance_enabled = bool(enhance.get("enabled", False))
    script_force_offload = bool(enhance.get("force_offload", False)) and not enhance_enabled

    print(f"[JZL-剧本] 直接调用 JZL_MiniMax_ScriptProcessor | 模式={mode} | 分段={seg_label} | "
          f"风格「{story_style}」 | 故事「{story_name or ''}」 | 后端={'API' if is_api else '本地'} | 增强={'开' if enhance_enabled else '关'}")
    script_output, _bus = JZL_MiniMax_ScriptProcessor().execute(
        mode=mode,
        story_name=(story_name or "").strip(),
        story_input=(story or "").strip(),
        story_style=story_style or "热血战斗",
        use_custom_rule=bool(custom_rule_text),
        segment_count=seg_label,
        segment_duration=max(4, min(15, int(duration or 8))),
        prompt_lang=prompt_lang or "中文 [ZH]",
        ref_image_intro=ref_image_intro,
        ref_video_intro=ref_video_intro,
        ref_audio_intro=ref_audio_intro,
        enable_scene=enable_scene, enable_props=enable_props,
        enable_video=enable_video, enable_audio=enable_audio,
        seed=seed,
        force_offload=script_force_offload,
        save_states=False,
        llm_backend=enhance.get("llm_backend") or "本地模型 [local]",
        llama_model=custom_config if not is_api else None,
        parameters=parameters if not is_api else None,
        api_config=json.dumps(enhance.get("api") or {}, ensure_ascii=False) if is_api else None,
        preference=_build_preference(enhance),
        custom_rule_path=custom_rule_text or None,
    )
    if script_output.startswith(("[错误]", "[API 错误]", "[API 配置错误]", "[LLM 错误]")):
        return story, script_output
    return script_output, None


def _run_prompt_enhancer(segmented_text, manager, duration, story_style, prompt_lang, seed):
    """提示词增强：对拆解剧本二次润色（润色每个分段的 detailed_description）。

    直接复用官方 JZL_MiniMaxPromptEnhancer 节点逻辑（sheding/prompt_enhancer_rules 的规范）。
    与第一次 LLM 拆解共享 seed/生成后控制；强制卸载由外部 _llm_finish 统一在增强后处理。
    偏好设置(preference)在此注入 → 增强器按偏好逐条落实（二次润色）。
    """
    from .nodes_prompt_enhancer import JZL_MiniMaxPromptEnhancer
    try:
        from .sheding.story_styles import STORY_STYLES
    except ImportError:
        STORY_STYLES = {}

    enhance = manager.get("enhance") or {}
    lang = "zh" if "ZH" in str(prompt_lang or "") else "en"
    duration = max(4, min(15, int(duration or 8)))

    # 注入完整故事风格文本（视觉风格/色调光线/摄影语言/核心导演语法），增强器按风格逐条落实
    style_name = (story_style or "热血战斗").strip()
    style_text = STORY_STYLES.get(style_name, style_name)

    bus = _enhance_bus(enhance)
    bus.update({
        "lang": lang,
        "story_style": style_text,
        "segment_duration": duration,
        "preference": _build_preference(enhance),
        "custom_rules": (enhance.get("system_prompt") or "").strip(),
    })
    print(f"[JZL-增强] 开启提示词增强 | 语言={lang} | 风格「{style_name}」 | 种子={seed}（与拆解共享）")
    try:
        result = JZL_MiniMaxPromptEnhancer().enhance(segmented_text, bus, False, seed)[0]
    except Exception as e:
        return segmented_text, f"提示词增强失败：{e}"
    if result.startswith("[错误]"):
        return segmented_text, result
    return result, None


def _run_pure_prompt_llm(prompt, manager, story_style, prompt_lang, seed, asset_intro_text=""):
    """纯提示词生成：只用 LLM 润色/扩写用户提示词，不做分段拆解、不生成视频。"""
    enhance = manager.get("enhance") or {}
    lang = "zh" if "ZH" in str(prompt_lang or "") else "en"
    style = (story_style or "热血战斗").strip()
    pref = _build_preference(enhance)
    custom = (enhance.get("custom_prompt") or "").strip()
    rules = (enhance.get("system_prompt") or "").strip()

    if lang == "zh":
        lines = [
            "你是一位专业的影视提示词编辑。请对用户输入的提示词进行润色与扩写，使其更适合生成高质量视频。",
            "",
            f"故事风格：{style}",
        ]
        if pref:
            lines.append(f"镜头语言偏好：\n{pref}")
        if asset_intro_text:
            lines.append(f"可用素材（提示词中的 @引用 必须原样保留，不得改名或替换）：\n{asset_intro_text}")
        if custom:
            lines.append(f"用户自定义增强指令：\n{custom}")
        if rules:
            lines.append(f"系统规则：\n{rules}")
        lines += [
            "",
            "处理要求：",
            "1. 完整保留用户输入的原始意图与关键信息：角色、场景、动作、台词、@引用、[SHOT_START]...[SHOT_END] 分段块结构等一律不变；",
            "2. 只做润色与扩写：把概括性描述改写成具体、可被镜头捕捉的可见动作，丰富画面细节与氛围；",
            "3. 不做分段拆解：若输入不含 [SHOT_START] 块，保持单一文本输出，不要新增任何分段块；若输入含分段块，保留每个块的结构，只润色块内提示词；",
            "4. 直接输出处理后的提示词正文，不要任何解释、前言或统计。",
        ]
    else:
        lines = [
            "You are a professional film prompt editor. Polish and expand the user's prompt to make it suitable for high-quality video generation.",
            "",
            f"Story style: {style}",
        ]
        if pref:
            lines.append(f"Directing preference:\n{pref}")
        if asset_intro_text:
            lines.append(f"Available assets (preserve all @-references verbatim, do not rename or replace):\n{asset_intro_text}")
        if custom:
            lines.append(f"User custom enhancement instructions:\n{custom}")
        if rules:
            lines.append(f"System rules:\n{rules}")
        lines += [
            "",
            "Requirements:",
            "1. Keep all key information intact: characters, scenes, actions, dialogue, @-references, and any [SHOT_START]...[SHOT_END] block structure;",
            "2. Only polish and expand: rewrite vague descriptions into concrete, camera-capturable visible actions; enrich visual detail and atmosphere;",
            "3. Do NOT decompose into segments: if the input has no [SHOT_START] blocks, keep it as a single text and do NOT add segment blocks; if it has blocks, preserve each block and only polish the inner prompts;",
            "4. Output only the processed prompt text, with no explanation, preamble, or statistics.",
        ]

    result = _llm_chat(enhance, "\n".join(lines), (prompt or "").strip(), seed)
    if result.startswith(("[API 错误]", "[API 配置错误]", "[LLM 错误]", "[错误]")):
        return prompt, result
    return result.strip(), None


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


class JZL_MiniMaxAssetManager(io.ComfyNode):
    """MiniMax-H3生成管理器 — 生成模式切换 + 模型/资产/参数/采样解码配置，输出 BUS。

    融合原 1140 工作流核心链路：
    分段处理中心 → 列表分发(每段独立提示词) → 场景/视频/音频调度(从资产池按名取参考)
    → 官方 ImageToVideo / ReferenceToVideo 编码 → 采样 → VAE 解码(视频+音频)
    → 写入生成总线池 JZL_BUS_POOL，输出 BUS(JSON) 给「视频保存分配」节点。

    V3 节点（io.ComfyNode）：配置入口按钮由前端 JS addDOMWidget 在节点表面添加。
    """

    @classmethod
    def define_schema(cls):
        story_styles = _story_style_options()
        return io.Schema(
            node_id="JZL_MiniMaxAssetManager",
            display_name="MiniMax-H3生成管理器",
            category="JZL/MiniMax",
            description="MiniMax-H3 生成管理器：分段 + 调度 + 编码 + 采样 + 解码一体化，输出生成总线。",
            inputs=[
                # 运行模式（顶层切换，等同「JZL - 🎬 剧本与镜头处理器」）
                io.Combo.Input("run_mode", options=["拆解故事模式", "故事扩展模式", "纯提示词生成"],
                    default="拆解故事模式", display_name="运行模式",
                    tooltip="拆解故事模式=按情节把故事拆解为N段（不创意扩展）；故事扩展模式=先扩写故事正文再拆解为N段；纯提示词生成=只用LLM处理提示词，经「已处理剧本」端口输出文本，不生成视频"),
                # 生成参数（原生 widget，与「海螺H3视频参数」一致）
                io.Combo.Input("aspect_ratio", options=ASPECT_RATIO_OPTIONS, default="16:9 (Widescreen)",
                    display_name="画幅比例", tooltip="画幅比例（分辨率按 MP×1024² 公式自动计算，对齐倍数固定 32）"),
                io.Float.Input("megapixels", display_name="百万像素 MP", default=1.0, min=0.1, max=16.0, step=0.1,
                    tooltip="总像素数（MP），画幅×MP 决定分辨率"),
                io.String.Input("display_info", display_name="分辨率 / 帧数", default="832x480 · 192帧",
                    multiline=False, advanced=True, socketless=True,
                    tooltip="只读显示：当前画幅/MP/时长计算出的分辨率与帧数（对齐倍数固定 32）"),
                io.Int.Input("duration", display_name="每段视频时长（秒）", default=8, min=4, max=15, step=1,
                    tooltip="每段视频时长（秒），等同「剧本与镜头处理器」的每段视频时长(秒)"),
                io.Float.Input("scale_factor", display_name="参考图放大", default=1.0, min=1.0, max=5.0, step=0.1,
                    tooltip="参考图放大系数"),
                io.Float.Input("upscale_scale", display_name="二采放大倍数", default=1.5, min=1.0, max=4.0, step=0.05,
                    tooltip="二采（Ref2va）放大倍数"),
                io.Int.Input("video_count", display_name="生成视频数量", default=6, min=1, max=12,
                    tooltip="生成视频数量（分段数，最多 12 段）"),
                io.Combo.Input("save_mode", options=["分段保存", "拼接保存"], default="分段保存",
                    display_name="视频保存模式",
                    tooltip="分段保存=按顺序批量输出每段图像/音频；拼接保存=全部生成后拼接成一段再输出"),
                # ③提示词：剧本处理器参数（主界面显示）
                io.Combo.Input("story_style", options=story_styles, default=story_styles[0],
                    display_name="故事风格", tooltip="故事风格（剧本处理器按此风格拆解与润色）"),
                io.String.Input("story_name", display_name="故事名称", default="",
                    tooltip="故事名称（用于保存命名 / 日志）"),
                io.Combo.Input("prompt_lang", options=["中文 [ZH]", "英文 [EN]"], default="中文 [ZH]",
                    display_name="提示词语言", tooltip="提示词语言"),
                io.Model.Input("model", display_name="主模型", optional=True, advanced=True),
                io.Clip.Input("clip", display_name="CLIP", optional=True, advanced=True),
                io.Vae.Input("vae", display_name="视觉VAE", optional=True, advanced=True),
                io.Vae.Input("audio_vae", display_name="音频VAE", optional=True, advanced=True),
                io.String.Input("prompt_input", display_name="外部提示词", multiline=True, force_input=True,
                    optional=True,
                    placeholder="连线后使用外部提示词（替代节点内编辑）…",
                    tooltip="可选：接外部 STRING 提示词替代节点内编辑；不接则用节点内编辑的提示词"),
                io.String.Input("internal_prompt", display_name="节点内提示词", multiline=True, advanced=True,
                    socketless=True,
                    tooltip="节点内编辑的提示词（prompt_input 未连线时使用）"),
                io.String.Input("manager_settings", display_name="节点配置", multiline=True, advanced=True,
                    socketless=True, default="",
                    tooltip="本节点独立保存的完整配置 JSON（资产/增强/采样解码），随工作流保存，节点间互不影响"),
            ],
            outputs=[
                io.Image.Output(display_name="图像", is_output_list=True),
                io.Audio.Output(display_name="音频", is_output_list=True),
                io.String.Output("script", display_name="已处理剧本",
                    tooltip="全部LLM处理后的剧本/提示词文本：纯提示词生成模式=LLM处理结果；其余模式=拆解+增强后的分段文本"),
            ],
        )

    @classmethod
    def fingerprint_inputs(cls, manager_settings="", **kwargs):
        # 等价于 V1 的 IS_CHANGED：本节点工作流内保存的配置变化必须触发重跑（节点间互不影响）。
        # 关键：LLM 或采样任一为 randomize 时每次都返回唯一指纹 → 节点必然重跑，
        # 保证「随机种子」每次生成不同结果（否则配置内容不变会命中缓存、生成被跳过）。
        try:
            cfg = _parse_node_manager_settings(manager_settings)
            enhance = cfg.get("enhance") or {}
            sample_decode = cfg.get("sample_decode") or {}
            llm_random = (enhance.get("seed_control") or "randomize") == "randomize"
            samp_random = (sample_decode.get("seed_mode") or "randomize") == "randomize"
            if llm_random or samp_random:
                return f"random@{time.time_ns()}"
            return str(cfg)
        except Exception:
            return "no-manager"

    @classmethod
    def execute(cls, run_mode="拆解故事模式", video_count=6, aspect_ratio="16:9 (Widescreen)",
                megapixels=1.0, duration=8, scale_factor=1.0, upscale_scale=1.5, display_info="",
                story_style="热血战斗", story_name="", prompt_lang="中文 [ZH]", save_mode="分段保存",
                prompt_input=None, internal_prompt=None, manager_settings="",
                clip=None, vae=None, audio_vae=None, model=None) -> io.NodeOutput:
        run_mode = (run_mode or "拆解故事模式").strip()
        pure_prompt = run_mode == "纯提示词生成"
        story_mode = "生成模式 (Generate)" if run_mode == "故事扩展模式" else "拆解模式 (Decompose)"

        # 节点独立配置：工作流内保存的 manager_settings 优先；空则回退全局（旧工作流兼容）
        manager = _parse_node_manager_settings(manager_settings)
        enhance = manager.get("enhance") or {}
        assets_cfg = manager.get("assets") or {}
        sample_decode = manager.get("sample_decode") or {}

        # 内部提示词防御：旧工作流可能把模型输出误连到 internal_prompt（非字符串）
        if not isinstance(internal_prompt, str):
            internal_prompt = ""

        # 提示词替代关系：外部提示词端口（prompt_input）连线后优先使用；否则用节点内编辑（internal_prompt）
        prompt_input = (prompt_input or "").strip()
        if not prompt_input:
            prompt_input = (internal_prompt or "").strip()

        # 随机种子（LLM 剧本/增强）+ 生成后控制（control_after_generate）
        seed_control = (enhance.get("seed_control") or "randomize").strip() or "randomize"
        current_seed = int(enhance.get("seed", 0) or 0)
        if seed_control == "randomize":
            llm_seed = int(torch.randint(0, 0x7fffffffffffffff, (1,)).item())
        else:
            llm_seed = current_seed
        _mode_hint = "（纯提示词生成：仅LLM处理→已处理剧本输出，不生成视频）" if pure_prompt else (
            "（拆解故事模式→生成）" if run_mode == "拆解故事模式" else "（故事扩展模式→生成）")
        print(f"[JZL-管理器] 运行模式={run_mode} | LLM种子={llm_seed}({seed_control}) | "
              f"采样种子模式={sample_decode.get('seed_mode', 'randomize')} | 共{max(1, min(12, int(video_count or 6)))}段{_mode_hint}")

        # 纯提示词生成：只用 LLM 处理提示词 → 「已处理剧本」端口输出文本，跳过拆解与生成
        if pure_prompt:
            if not prompt_input:
                _llm_finish(enhance)
                return io.NodeOutput([], [], "")
            ri, rv, ra, _ = _build_asset_intro(assets_cfg)
            processed, p_err = _run_pure_prompt_llm(
                prompt_input, manager, story_style, prompt_lang, llm_seed,
                "\n".join(x for x in (ri, rv, ra) if x))
            _llm_finish(enhance)
            _seed_ui = _build_seed_ui(manager, enhance, seed_control, current_seed, llm_seed)
            if p_err:
                print(f"[JZL-管理器] {p_err}")
            return io.NodeOutput([], [], processed, ui=_seed_ui)

        # 清空重建池，避免旧资产/总线残留
        JZL_ASSET_POOL.clear()
        JZL_BUS_POOL.clear()
        JZL_SLOT_MAP.clear()

        manifest, errors = _load_assets_into_pool(assets_cfg)

        width, height = _resolve_gen_size(aspect_ratio, megapixels)
        length = _resolve_length(duration)
        count = max(1, min(12, int(video_count)))


        # ── ③提示词：资产介绍 + 启用判断 + 槽位映射（供调度匹配）──
        ref_image_intro, ref_video_intro, ref_audio_intro, slot_to_asset = _build_asset_intro(assets_cfg)
        JZL_SLOT_MAP.update(slot_to_asset)
        enable_scene, enable_props, enable_video, enable_audio = _detect_enables(prompt_input, assets_cfg)

        # ① 故事拆解（剧本处理器）：故事 → 分段（输入已是分段文本时跳过）
        has_shots = bool(re.search(r'\[SHOT_START\]', prompt_input or ""))
        if enhance.get("story_decompose", True) and not has_shots and prompt_input:
            prompt_input, err = _run_script_processor(
                prompt_input, manager, count, story_style, story_name, duration, prompt_lang, llm_seed,
                ref_image_intro=ref_image_intro, ref_video_intro=ref_video_intro, ref_audio_intro=ref_audio_intro,
                enable_scene=enable_scene, enable_props=enable_props,
                enable_video=enable_video, enable_audio=enable_audio, mode=story_mode)
            if err:
                errors.append(err)

        # ② 提示词增强（润色 detailed_description）：开启增强时执行
        if enhance.get("enabled", False):
            prompt_input, err = _run_prompt_enhancer(prompt_input, manager, duration, story_style, prompt_lang, llm_seed)
            if err:
                errors.append(err)

        # 卸载本地 LLM（最后一个 LLM 步骤之后，按 force_offload）
        _llm_finish(enhance)

        # 生成后控制（control_after_generate）：随机/递增时把新 seed 写回配置，下次运行生效
        _seed_ui = _build_seed_ui(manager, enhance, seed_control, current_seed, llm_seed)

        # ── 分段（融合分段处理中心）：按 [SHOT_START] 块切分 ──
        shots = re.findall(r'\[SHOT_START\](.*?)\[SHOT_END\]', prompt_input or "", re.DOTALL)

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

            # 生成模式自动推断（不再手动选择）：
            #  有参考视频 → 多参考/二创（REF2VA 全传）；无视频但有图 → 图片到视频（1张=首帧，≥2张=首尾帧）；否则 → 纯文本
            mode = "多参考生成音视频-REF2VA"
            if not ref_videos:
                mode = "首尾帧生成音视频-FL2VA" if len(ref_images) > 1 else (
                    "首帧图生成音视频-I2VA" if ref_images else "纯文本生成音视频-T2VA")

            can_generate = clip is not None and vae is not None and model is not None
            if (ref_videos or ref_audios) and audio_vae is None:
                can_generate = False

            seed = _resolve_seed(seed_mode, base_seed, i)
            if not can_generate:
                need = "CLIP / VAE / model"
                if (ref_videos or ref_audios) and audio_vae is None:
                    need = "CLIP / VAE / model / audio_vae（本段含视频或音频参考）"
                bus_items.append({
                    "index": i, "mode": mode, "prompt": h3,
                    "has_image": False, "has_audio": False,
                    "error": f"未连接 {need}，仅完成分段",
                })
                continue

            try:
                if ref_videos:
                    # 多参考/二创：参考视频 + 独立音频 + 图片（如有）
                    positive, latent = _encode_ref_to_video(
                        clip, vae, audio_vae, h3, width, height, length,
                        ref_images=ref_images, ref_videos=ref_videos,
                        ref_video_audios=ref_audios[:len(ref_videos)], ref_audios=ref_audios,
                        ref_scale=scale_factor)
                else:
                    # 图片到视频 / 纯文本：1张=首帧，≥2张=首尾帧
                    first = ref_images[0] if ref_images else None
                    last = ref_images[1] if len(ref_images) > 1 else None
                    positive, latent = _encode_image_to_video(clip, vae, h3, width, height, length, first, last)

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

        # ── 输出：图像 + 音频（is_output_list=True，恒为列表） ──
        images, audios = [], []
        for i in range(count):
            item = JZL_BUS_POOL.get(i)
            if item:
                images.append(item.get("image"))
                audios.append(item.get("audio"))

        if errors:
            for e in errors:
                print(f"[JZL-管理器] {e}")

        if save_mode == "拼接保存":
            image = _concat_images(images)
            audio = _concat_audios(audios)
            if image is None:
                image = _empty_image()
            if audio is None:
                audio = _empty_audio()
            return io.NodeOutput([image], [audio], prompt_input, ui=_seed_ui)

        # 分段保存：按顺序输出每段（失败的段跳过，错误见日志）
        return io.NodeOutput(images, audios, prompt_input, ui=_seed_ui)


class JZL_MiniMaxVideoSaveDistributor(io.ComfyNode):
    """视频保存分配 — 接收生成总线，拆成 ≤12 组「图像 + 音频」输出，每组接一个 Video Combine。

    与「MiniMax-H3生成管理器」通过无线总线（JZL_BUS_POOL）传输：
    生成管理器把每段生成的 (IMAGE, AUDIO) 写入总线池，本节点按组序号读出，
    输出 12 组端口：图像1/音频1 … 图像12/音频12。
    """

    MAX_GROUPS = 12

    @classmethod
    def define_schema(cls):
        inputs = [
            io.String.Input("bus", display_name="生成总线",
                tooltip="接「MiniMax-H3生成管理器」的「生成总线」输出"),
        ]
        outputs = []
        for i in range(cls.MAX_GROUPS):
            outputs.append(io.Image.Output(display_name=f"图像{i + 1}"))
            outputs.append(io.Audio.Output(display_name=f"音频{i + 1}"))
        return io.Schema(
            node_id="JZL_MiniMaxVideoSaveDistributor",
            display_name="JZL - 💾 视频保存分配",
            category="JZL/MiniMax",
            description="接收生成总线，拆成 ≤12 组「图像+音频」输出，每组接一个 Video Combine。",
            inputs=inputs,
            outputs=outputs,
        )

    @classmethod
    def execute(cls, bus) -> io.NodeOutput:
        groups = 0
        try:
            if bus:
                groups = int((json.loads(bus).get("groups") or 0) if isinstance(bus, str) else 0)
        except Exception:
            groups = 0

        out = []
        for i in range(cls.MAX_GROUPS):
            item = JZL_BUS_POOL.get(i)
            if i < groups and item:
                image = item.get("image")
                audio = item.get("audio")
                out.append(image if image is not None else _empty_image())
                out.append(audio if audio is not None else _empty_audio())
            else:
                out.append(None)
                out.append(None)
        return io.NodeOutput(*out)


def _empty_image():
    """空占位图像（未生成时保证端口有值，避免下游崩溃）。"""
    return torch.zeros((1, 32, 32, 3), dtype=torch.float32)


def _empty_audio():
    """空占位音频。"""
    return {"waveform": torch.zeros((1, 2, 1), dtype=torch.float32), "sample_rate": 32000}
