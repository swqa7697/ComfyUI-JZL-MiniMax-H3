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
import shutil
import subprocess
import tempfile

import torch
import torchaudio
import folder_paths
from PIL import Image, ImageOps

# ── 全局资产池（无线传输核心）──────────────────────────────
# key = 资产名（如「图片1角色孙悟空」），value = {"kind": "image"|"audio"|"video", "data": tensor}
JZL_ASSET_POOL = {}

# 类型下拉统一列表（图片/视频/音频共用）
ASSET_TYPES = ["角色", "场景", "道具", "分镜", "音效", "音乐", "其他"]

# 视频抽帧：24fps，最多抽 240 帧（超出均匀采样）
VIDEO_FPS = 24
MAX_VIDEO_FRAMES = 240


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


def _asset_name(kind, index, item):
    """生成资产名：图片1角色孙悟空 / 视频1分镜参考 / 音频1角色孙悟空。"""
    prefix = {"image": "图片", "video": "视频", "audio": "音频"}.get(kind, "资产")
    typ = (item.get("type") or "").strip()
    name = (item.get("name") or "").strip()
    return f"{prefix}{index + 1}{typ}{name}"


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
    """漫剧资产管理 — modal 选择图片/视频/音频，加载进全局资产池，输出清单。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "open_manager": ("BOOLEAN", {"default": False,
                    "label_on": "🗂️ 打开资产管理…", "label_off": "🗂️ 打开资产管理…",
                    "tooltip": "点击后弹窗配置资产：动态数量 + 每项(文件/类型/开关/名称)"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("资产清单",)
    FUNCTION = "execute"
    CATEGORY = "JZL/MiniMax"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # 资产配置内容变化必须触发重跑，否则全局池是旧的
        try:
            with open(_asset_settings_file(), "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return "no-assets"

    def execute(self, open_manager):
        settings = _read_asset_settings()
        # 清空重建全局池，避免旧资产残留
        JZL_ASSET_POOL.clear()

        manifest = []
        errors = []

        # 图片
        for i, item in enumerate(settings.get("images", []) or []):
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

        # 视频
        for i, item in enumerate(settings.get("videos", []) or []):
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

        # 音频
        for i, item in enumerate(settings.get("audios", []) or []):
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

        result = json.dumps({"assets": manifest, "errors": errors}, ensure_ascii=False)
        return (result,)
