"""JZL MiniMax — 节点注册入口（V1 经典 API）

采用 V1 的 NODE_CLASS_MAPPINGS 注册，兼容两种节点实现：
- V3 节点（io.ComfyNode，如参考编码）：执行层按类继承自动识别，Autogrow 照常生效
- V1 节点（经典 API，如漫剧调度四节点）：保留 **kwargs 动态端口与按名分类
"""

import os

from server import PromptServer
from aiohttp import web

from .nodes import JZL_MiniMaxH3ReferenceToVideo, JZL_MiniMaxH3ReferenceToVideo2, JZL_MiniMaxH3CondSync, JZL_MiniMaxH3ImageToVideoDual
from .nodes_hailuo_video import JZL_HailuoH3VideoParams, JZL_HailuoH3VideoParamsPro
from .nodes_list_dispatcher import JZL_ListDispatcher
from .story_nodes import (
    JZL_MiniMax_ShotFormatter,
    JZL_MiniMax_SceneDispatcher,
    JZL_MiniMax_VideoDispatcher,
    JZL_MiniMax_AudioDispatcher,
    JZL_MiniMax_SceneDispatcher2,
    JZL_MiniMax_VideoDispatcher2,
    JZL_MiniMax_AudioDispatcher2,
)
from .nodes_llama import (
    JZL_LlamaModelLoaderPro,
    JZL_MiniMax_ScriptProcessor,
    JZL_MiniMaxPreset,
    JZL_MiniMaxRef2vaPreset,
    JZL_MiniMaxH3Preference,
    JZL_MiniMaxAPISettings,
    _read_api_settings,
    _write_api_settings,
)
from .nodes_music import JZL_MiniMaxMusicCaption, JZL_MiniMaxMusicCaptionDuet
from .nodes_music_lyrics import JZL_MiniMaxMusicLyricsEditor
from .nodes_h3_editor import JZL_MiniMaxH3PromptEditor
from .nodes_ref_bus import JZL_MiniMaxH3RefBusOut, JZL_MiniMaxH3RefBusIn
from .nodes_ref2va_bus import JZL_MiniMaxH3Ref2vaBusOut, JZL_MiniMaxH3Ref2vaBusIn
from .nodes_prompt_enhancer import JZL_MiniMaxPromptEnhancer
from .nodes_asset_manager import (
    JZL_MiniMaxAssetManager,
    JZL_MiniMaxAssetManagerMini,
    JZL_MiniMaxVideoSaveDistributor,
    _read_asset_settings,
    _write_asset_settings,
    _read_manager_settings,
    _write_manager_settings,
    _resolve_asset_path,
    _load_last_script,
)

WEB_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "js")

NODE_CLASS_MAPPINGS = {
    "JZL_MiniMaxH3ReferenceToVideo": JZL_MiniMaxH3ReferenceToVideo,
    "JZL_MiniMaxH3ReferenceToVideo2": JZL_MiniMaxH3ReferenceToVideo2,
    "JZL_MiniMaxH3CondSync": JZL_MiniMaxH3CondSync,
    "JZL_MiniMaxH3ImageToVideoDual": JZL_MiniMaxH3ImageToVideoDual,
    "JZL_HailuoH3VideoParams": JZL_HailuoH3VideoParams,
    "JZL_HailuoH3VideoParamsPro": JZL_HailuoH3VideoParamsPro,
    "JZL_ListDispatcher": JZL_ListDispatcher,
    "JZL_MiniMax_ShotFormatter": JZL_MiniMax_ShotFormatter,
    "JZL_MiniMax_SceneDispatcher": JZL_MiniMax_SceneDispatcher,
    "JZL_MiniMax_VideoDispatcher": JZL_MiniMax_VideoDispatcher,
    "JZL_MiniMax_AudioDispatcher": JZL_MiniMax_AudioDispatcher,
    "JZL_MiniMax_SceneDispatcher2": JZL_MiniMax_SceneDispatcher2,
    "JZL_MiniMax_VideoDispatcher2": JZL_MiniMax_VideoDispatcher2,
    "JZL_MiniMax_AudioDispatcher2": JZL_MiniMax_AudioDispatcher2,
    "JZL_LlamaModelLoaderPro": JZL_LlamaModelLoaderPro,
    "JZL_MiniMax_ScriptProcessor": JZL_MiniMax_ScriptProcessor,
    "JZL_MiniMaxPreset": JZL_MiniMaxPreset,
    "JZL_MiniMaxRef2vaPreset": JZL_MiniMaxRef2vaPreset,
    "JZL_MiniMaxH3Preference": JZL_MiniMaxH3Preference,
    "JZL_MiniMaxAPISettings": JZL_MiniMaxAPISettings,
    "JZL_MiniMaxMusicCaption": JZL_MiniMaxMusicCaption,
    "JZL_MiniMaxMusicCaptionDuet": JZL_MiniMaxMusicCaptionDuet,
    "JZL_MiniMaxMusicLyricsEditor": JZL_MiniMaxMusicLyricsEditor,
    "JZL_MiniMaxH3PromptEditor": JZL_MiniMaxH3PromptEditor,
    "JZL_MiniMaxH3RefBusOut": JZL_MiniMaxH3RefBusOut,
    "JZL_MiniMaxH3RefBusIn": JZL_MiniMaxH3RefBusIn,
    "JZL_MiniMaxH3Ref2vaBusOut": JZL_MiniMaxH3Ref2vaBusOut,
    "JZL_MiniMaxH3Ref2vaBusIn": JZL_MiniMaxH3Ref2vaBusIn,
    "JZL_MiniMaxPromptEnhancer": JZL_MiniMaxPromptEnhancer,
    "JZL_MiniMaxAssetManager": JZL_MiniMaxAssetManager,
    "JZL_MiniMaxAssetManagerMini": JZL_MiniMaxAssetManagerMini,
    "JZL_MiniMaxVideoSaveDistributor": JZL_MiniMaxVideoSaveDistributor,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "JZL_MiniMaxH3ReferenceToVideo": "JZL - 🎬 MiniMax H3 参考编码",
    "JZL_MiniMaxH3ReferenceToVideo2": "JZL - 🎬 MiniMax H3 参考编码2",
    "JZL_MiniMaxH3CondSync": "JZL - 🌊 海螺H3二采条件同步",
    "JZL_MiniMaxH3ImageToVideoDual": "JZL - 🎬 MiniMax H3 二采编码",
    "JZL_HailuoH3VideoParams": "JZL - 🌊 海螺H3视频参数",
    "JZL_HailuoH3VideoParamsPro": "JZL - 🌊 海螺H3视频参数Pro",
    "JZL_ListDispatcher": "JZL - 📋 列表分发",
    "JZL_MiniMax_ShotFormatter": "JZL - 📋 分段处理中心",
    "JZL_MiniMax_SceneDispatcher": "JZL - 🎯 场景元素调度",
    "JZL_MiniMax_VideoDispatcher": "JZL - 🎬 视频调度",
    "JZL_MiniMax_AudioDispatcher": "JZL - 🎧 音频调度",
    "JZL_MiniMax_SceneDispatcher2": "JZL - 🎯 场景元素调度2",
    "JZL_MiniMax_VideoDispatcher2": "JZL - 🎬 视频调度2",
    "JZL_MiniMax_AudioDispatcher2": "JZL - 🎧 音频调度2",
    "JZL_LlamaModelLoaderPro": "JZL - 🚀 模型加载Pro",
    "JZL_MiniMax_ScriptProcessor": "JZL - 🎬 剧本与镜头处理器",
    "JZL_MiniMaxPreset": "JZL - ✨ MiniMax-fl2va提示词预设",
    "JZL_MiniMaxRef2vaPreset": "JZL - ✨ MiniMax-ref2va提示词预设",
    "JZL_MiniMaxH3Preference": "JZL - 🎯 MiniMax H3 偏好设置",
    "JZL_MiniMaxAPISettings": "JZL - 🌐 LLM-API 设置",
    "JZL_MiniMaxMusicCaption": "JZL - 🎵 MiniMax Music3 提示词预设",
    "JZL_MiniMaxMusicCaptionDuet": "JZL - 🎵 MiniMax Music3 提示词预设（双人）",
    "JZL_MiniMaxMusicLyricsEditor": "JZL - 🎵 MiniMax Music3 歌词编辑",
    "JZL_MiniMaxH3PromptEditor": "JZL - 📝 MiniMax H3 手写提示词",
    "JZL_MiniMaxH3RefBusOut": "JZL - 🔗 MiniMax H3 参考总线（打包）",
    "JZL_MiniMaxH3RefBusIn": "JZL - 🔗 MiniMax H3 参考总线（解包）",
    "JZL_MiniMaxH3Ref2vaBusOut": "JZL - 🔗 MiniMax H3 ref2va参考总线（打包）",
    "JZL_MiniMaxH3Ref2vaBusIn": "JZL - 🔗 MiniMax H3 ref2va参考总线（解包）",
    "JZL_MiniMaxPromptEnhancer": "JZL - ✨ 提示词增强",
    "JZL_MiniMaxAssetManager": "JZL - 🤖 MiniMax-H3短剧导演台Pro",
    "JZL_MiniMaxAssetManagerMini": "JZL - 🤖 MiniMax-H3短剧导演台Mini",
    "JZL_MiniMaxVideoSaveDistributor": "JZL - 💾 视频保存分配",
}


# ── 后端端点（分段处理中心「重拍」文件选择器） ─────────────────

HAS_TKINTER = False
try:
    import tkinter as tk
    from tkinter import filedialog
    HAS_TKINTER = True
except ImportError:
    pass  # 静默放行，不要让整个节点加载失败


@PromptServer.instance.routes.post("/jzl/choose_txt_file")
async def choose_txt_file(request):
    """选择 TXT 文件, 默认打开 MiniMax 故事输出目录"""
    if not HAS_TKINTER:
        return web.json_response({"path": "", "error": "当前环境缺少弹窗依赖"})
    try:
        data = await request.json()
        default_dir = data.get("default_dir", "")
    except Exception:
        default_dir = ""

    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        if default_dir and os.path.isdir(default_dir):
            file_path = filedialog.askopenfilename(
                initialdir=default_dir,
                title="选择分段提示词文件",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
            )
        else:
            file_path = filedialog.askopenfilename(
                title="选择分段提示词文件",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
            )
        root.destroy()
        return web.json_response({"path": file_path})
    except Exception as e:
        return web.json_response({"path": "", "error": f"弹窗调用失败: {str(e)}"})


@PromptServer.instance.routes.post("/jzl/minimax_default_dir")
async def minimax_default_dir(request):
    """返回 MiniMax 默认输出目录路径"""
    try:
        import folder_paths
        default_dir = os.path.join(folder_paths.get_output_directory(), "jzl")
        if not os.path.isdir(default_dir):
            os.makedirs(default_dir, exist_ok=True)
        return web.json_response({"dir": default_dir})
    except Exception:
        return web.json_response({"dir": ""})


# ── 后端端点（API 设置弹窗读写，Key 不明文进工作流） ─────────────────

@PromptServer.instance.routes.get("/jzl/api_settings")
async def jzl_api_settings_get(request):
    """读取 API 设置（弹窗打开时回显当前配置）"""
    return web.json_response({"ok": True, "settings": _read_api_settings()})


@PromptServer.instance.routes.post("/jzl/api_settings")
async def jzl_api_settings_post(request):
    """保存 API 设置到磁盘（存 ComfyUI user 目录，不进工作流）"""
    try:
        payload = await request.json()
        settings = _write_api_settings(payload if isinstance(payload, dict) else {})
        return web.json_response({"ok": True, "settings": settings})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=500)


# ── 后端端点（漫剧资产管理弹窗读写 + 文件选择 + 图片预览） ─────────────────
# 路径解析统一用 nodes_asset_manager._resolve_asset_path（预览路由与资产池加载共用）

@PromptServer.instance.routes.post("/jzl/upload_asset")
async def jzl_upload_asset(request):
    """浏览器文件上传（替代 tkinter 弹窗，云机/无桌面环境可用）。

    前端用 <input type=file> 选文件后，以 multipart 表单 POST 到此接口
    （字段：file + kind），按类型分别保存到 ComfyUI input/jzl/image、/video、
    /audio 三个文件夹，返回 input 相对路径（如 jzl/image/xxx.png）——与官方
    「加载图像」一致：素材统一导入 input 文件夹、按相对路径引用，工作流可移植。
    """
    try:
        post = await request.post()
        file = post.get("file")
        kind = (post.get("kind") or "image").strip()
        if kind not in {"image", "video", "audio"}:
            kind = "image"
        if not file or not getattr(file, "file", None):
            return web.json_response({"error": "未收到文件"}, status=400)
        filename = os.path.basename((file.filename or "").strip())
        if not filename:
            return web.json_response({"error": "文件名为空"}, status=400)
        ext = os.path.splitext(filename)[1].lower()
        allow = {
            "image": {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"},
            "video": {".mp4", ".mov", ".webm", ".avi", ".mkv"},
            "audio": {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".opus"},
        }.get(kind, set())
        if ext not in allow:
            return web.json_response({"error": f"{kind} 类型不支持扩展名 {ext}"}, status=400)
        import folder_paths
        # input/jzl 下按类型分三个英文文件夹：image / video / audio
        sub = os.path.join("jzl", kind)
        out_dir = os.path.join(folder_paths.get_input_directory(), sub)
        os.makedirs(out_dir, exist_ok=True)
        # 重名自动加 (N)，与官方 /upload/image 一致
        dest = os.path.join(out_dir, filename)
        i = 1
        split = os.path.splitext(filename)
        while os.path.exists(dest):
            filename = f"{split[0]} ({i}){split[1]}"
            dest = os.path.join(out_dir, filename)
            i += 1
        with open(dest, "wb") as f:
            f.write(file.file.read())
        # input 相对路径（官方 LoadImage 同款），统一正斜杠，跨平台可移植
        rel = os.path.join(sub, filename).replace("\\", "/")
        return web.json_response({
            "ok": True,
            "path": rel,
            "name": filename,
            "subfolder": sub,
            "type": "input",
        })
    except Exception as exc:
        return web.json_response({"error": f"上传失败：{exc}"}, status=500)


@PromptServer.instance.routes.get("/jzl/asset_preview")
async def jzl_asset_preview(request):
    """图片资产缩略图预览：返回长边 256 的 JPEG（仅允许图片扩展名）。"""
    path = (request.query.get("path") or "").strip()
    if not path:
        return web.json_response({"error": "缺少 path"}, status=400)
    ext = os.path.splitext(path)[1].lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}:
        return web.json_response({"error": "仅支持图片预览"}, status=400)
    path = _resolve_asset_path(path)
    if not path:
        return web.json_response({"error": "文件不存在"}, status=404)
    try:
        from PIL import Image, ImageOps
        import io
        img = Image.open(path)
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        img.thumbnail((256, 256), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        return web.Response(body=buf.getvalue(), content_type="image/jpeg")
    except Exception as exc:
        return web.json_response({"error": f"预览失败：{exc}"}, status=500)


@PromptServer.instance.routes.get("/jzl/asset_full")
async def jzl_asset_full(request):
    """图片资产原图：返回原图 PNG（无损，用于弹窗查看大图；超长边 4096 防内存爆）。"""
    path = (request.query.get("path") or "").strip()
    if not path:
        return web.json_response({"error": "缺少 path"}, status=400)
    ext = os.path.splitext(path)[1].lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}:
        return web.json_response({"error": "仅支持图片"}, status=400)
    path = _resolve_asset_path(path)
    if not path:
        return web.json_response({"error": "文件不存在"}, status=404)
    try:
        from PIL import Image, ImageOps
        import io
        img = Image.open(path)
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        if max(img.size) > 4096:
            img.thumbnail((4096, 4096), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return web.Response(body=buf.getvalue(), content_type="image/png")
    except Exception as exc:
        return web.json_response({"error": f"原图加载失败：{exc}"}, status=500)


@PromptServer.instance.routes.get("/jzl/audio_preview")
async def jzl_audio_preview(request):
    """音频资产试听：返回音频文件本体（支持 Range 请求，供 <audio> 播放/拖动）。"""
    path = (request.query.get("path") or "").strip()
    if not path:
        return web.json_response({"error": "缺少 path"}, status=400)
    ext = os.path.splitext(path)[1].lower()
    if ext not in {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".opus", ".wma"}:
        return web.json_response({"error": "仅支持音频预览"}, status=400)
    path = _resolve_asset_path(path)
    if not path:
        return web.json_response({"error": "文件不存在"}, status=404)
    try:
        return web.FileResponse(path)
    except Exception as exc:
        return web.json_response({"error": f"音频读取失败：{exc}"}, status=500)


@PromptServer.instance.routes.get("/jzl/manager")
async def jzl_manager_get(request):
    """读取短剧管理器统一配置 + MiniMax-H3 模型列表 + 本地 LLM 模型列表"""
    try:
        import folder_paths
        from .llama_backend import chat_handlers as _ch
        from .nodes_asset_manager import _list_models
        from .presets.script import STORY_STYLES as _story_styles
        all_llms = folder_paths.get_filename_list("LLM")
        llm_list = [f for f in all_llms if "mmproj" not in f.lower()]
        mmproj_list = ["None"] + [f for f in all_llms if "mmproj" in f.lower()]
        diff_models = _list_models("diffusion_models")
        clip_models = _list_models("clip")
        vae_models = _list_models("vae")
        lora_models = _list_models("loras")
        story_styles = list(_story_styles.keys())
        save_dir = os.path.join(folder_paths.get_output_directory(), "jzl")
        upscaler_models = folder_paths.get_filename_list("latent_upscale_models")
    except Exception:
        llm_list, mmproj_list, _ch = [], ["None"], ["None"]
        diff_models = clip_models = vae_models = lora_models = []
        story_styles = []
        save_dir = "output/jzl"
        upscaler_models = []
    return web.json_response({
        "ok": True,
        "settings": _read_manager_settings(),
        "llm_models": llm_list,
        "mmproj_models": mmproj_list,
        "chat_handlers": _ch,
        "diffusion_models": diff_models,
        "clip_models": clip_models,
        "vae_models": vae_models,
        "lora_models": lora_models,
        "story_styles": story_styles,
        "save_dir": save_dir,
        "upscaler_models": upscaler_models,
    })


@PromptServer.instance.routes.post("/jzl/manager")
async def jzl_manager_post(request):
    """保存短剧管理器统一配置到磁盘"""
    try:
        payload = await request.json()
        settings = payload if isinstance(payload, dict) else {}
        _write_manager_settings(settings)
        return web.json_response({"ok": True, "settings": settings})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=500)


@PromptServer.instance.routes.get("/jzl/assets")
async def jzl_assets_get(request):
    """读取资产配置（弹窗打开时回显）"""
    return web.json_response({"ok": True, "settings": _read_asset_settings()})


@PromptServer.instance.routes.post("/jzl/assets")
async def jzl_assets_post(request):
    """保存资产配置到磁盘"""
    try:
        payload = await request.json()
        settings = payload if isinstance(payload, dict) else {}
        _write_asset_settings(settings)
        return web.json_response({"ok": True, "settings": settings})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=500)


@PromptServer.instance.routes.post("/jzl/export_assets")
async def jzl_export_assets(request):
    """把当前素材库导出为 output/jzl/素材库.txt（UTF-8，可读格式，供跨机器导入）。"""
    try:
        import folder_paths
        payload = await request.json()
        assets = payload.get("assets") if isinstance(payload, dict) else None
        if not isinstance(assets, dict):
            return web.json_response({"error": "缺少素材数据"}, status=400)
        out_dir = os.path.join(folder_paths.get_output_directory(), "jzl")
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, "素材库.txt")

        def _cl(v):
            return (str(v) if v is not None else "").replace("|", "／").strip()

        lines = [
            "# JZL 素材库（MiniMax-H3短剧导演台Pro）v1",
            "# 每行：类型 | 编号 | 名称 | 描述 | 路径 | 启用(1/0)",
            "",
        ]
        for key, label in (("images", "图片"), ("videos", "视频"), ("audios", "音频")):
            lines.append(f"## {label}")
            for item in assets.get(key) or []:
                if not isinstance(item, dict):
                    continue
                lines.append(f"{_cl(item.get('type'))} | {_cl(item.get('letter'))} | {_cl(item.get('name'))} | "
                             f"{_cl(item.get('description'))} | {_cl(item.get('path'))} | "
                             f"{'1' if item.get('enabled', True) else '0'}")
            lines.append("")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return web.json_response({"ok": True, "path": path})
    except Exception as exc:
        return web.json_response({"error": f"导出失败：{exc}"}, status=500)


def _parse_assets_text(text):
    """把素材库 txt 文本解析为 assets（图片/视频/音频三段）。"""
    assets = {"images": [], "videos": [], "audios": []}
    cur = None
    _map = {"图片": "images", "视频": "videos", "音频": "audios"}
    text = (text or "").lstrip("\ufeff")  # 容忍带 BOM 的文件
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("## "):
            cur = _map.get(line[3:].strip())
            continue
        if line.startswith("#"):
            continue
        if cur is None:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 6:
            continue
        typ, letter, name, desc, p, enabled = parts[:6]
        assets[cur].append({
            "type": typ, "letter": letter, "name": name,
            "description": desc, "path": p,
            "enabled": enabled == "1",
        })
    return assets


@PromptServer.instance.routes.post("/jzl/import_assets")
async def jzl_import_assets(request):
    """从上传的 txt 文本解析素材库并返回（无 text 时兼容读取默认导出文件）。"""
    try:
        import folder_paths
        payload = {}
        try:
            payload = await request.json() or {}
        except Exception:
            payload = {}
        text = payload.get("text") if isinstance(payload, dict) else None
        if text is None:
            # 兼容：无文本时读取默认导出文件
            path = os.path.join(folder_paths.get_output_directory(), "jzl", "素材库.txt")
            if not os.path.isfile(path):
                return web.json_response({"error": "output/jzl/素材库.txt 不存在"}, status=404)
            with open(path, "r", encoding="utf-8-sig") as f:
                text = f.read()
        assets = _parse_assets_text(text)
        return web.json_response({"ok": True, "assets": assets})
    except Exception as exc:
        return web.json_response({"error": f"导入失败：{exc}"}, status=500)


@PromptServer.instance.routes.post("/jzl/choose_asset_file")
async def choose_asset_file(request):
    """tkinter 文件选择器：按 kind(image/video/audio) 过滤文件类型"""
    if not HAS_TKINTER:
        return web.json_response({"path": "", "error": "当前环境缺少弹窗依赖"})
    try:
        data = await request.json()
        kind = data.get("kind", "image")
    except Exception:
        kind = "image"

    filetypes = {
        "image": [("图片", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"), ("所有文件", "*.*")],
        "video": [("视频", "*.mp4 *.mov *.webm *.avi *.mkv"), ("所有文件", "*.*")],
        "audio": [("音频", "*.wav *.mp3 *.flac *.ogg *.m4a"), ("所有文件", "*.*")],
    }.get(kind, [("所有文件", "*.*")])
    titles = {"image": "选择图片", "video": "选择视频", "audio": "选择音频"}

    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        file_path = filedialog.askopenfilename(title=titles.get(kind, "选择文件"), filetypes=filetypes)
        root.destroy()
        return web.json_response({"path": file_path})
    except Exception as e:
        return web.json_response({"path": "", "error": f"弹窗调用失败: {str(e)}"})


@PromptServer.instance.routes.post("/jzl/choose_directory")
async def choose_directory(request):
    """tkinter 目录选择器：只允许选择 ComfyUI/output 目录内的文件夹（用于 ffmpeg 落盘/合并输出位置）"""
    if not HAS_TKINTER:
        return web.json_response({"path": "", "error": "当前环境缺少弹窗依赖"})
    try:
        import folder_paths
        out_root = os.path.abspath(folder_paths.get_output_directory())
        initial = os.path.join(out_root, "jzl")
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        dir_path = filedialog.askdirectory(
            title="选择文件夹（仅限 ComfyUI/output 目录内）",
            initialdir=initial if os.path.isdir(initial) else out_root)
        root.destroy()
        if not dir_path:
            return web.json_response({"path": ""})
        ap = os.path.abspath(dir_path)
        if ap != out_root and not ap.startswith(out_root + os.sep):
            return web.json_response({"path": "", "error": "只能选择 ComfyUI/output 目录内的文件夹"})
        return web.json_response({"path": dir_path})
    except Exception as e:
        return web.json_response({"path": "", "error": f"弹窗调用失败: {str(e)}"})


@PromptServer.instance.routes.get("/jzl/usage_md")
async def jzl_usage_md(request):
    """返回使用说明文档内容（不依赖前端静态资源服务，读取扩展目录 docs/USAGE.md）"""
    try:
        p = os.path.join(os.path.dirname(__file__), "docs", "USAGE.md")
        with open(p, "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type="text/plain; charset=utf-8")
    except Exception as e:
        return web.Response(status=404, text=f"文档读取失败: {str(e)}")


@PromptServer.instance.routes.get("/jzl/reshoot/load")
async def jzl_reshoot_load(request):
    """重拍模式：读取最后一次 LLM 拆解/增强后的完整提示词（output/jzl/最近提示词.json）。

    返回 {story_name, script, shots[], shot_count, time}；无记录时 shots 为空。
    """
    data = _load_last_script() or {"story_name": "", "script": "", "shots": [], "shot_count": 0, "time": ""}
    return web.json_response(data)


@PromptServer.instance.routes.get("/jzl/usage_qr/{name}")
async def jzl_usage_qr(request):
    """返回 docs 目录下的收款二维码图片（OpenPose 式 FileResponse，不依赖前端静态服务）。

    用法：/jzl/usage_qr/DS01.png —— 只允许访问 docs 目录内的文件。
    """
    name = os.path.basename(request.match_info.get("name", ""))
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "docs"))
    full = os.path.abspath(os.path.join(base, name))
    if not full.startswith(base + os.sep) or not os.path.isfile(full):
        return web.json_response({"error": "Not found"}, status=404)
    ext = os.path.splitext(name)[1].lower()
    ctype = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
             "webp": "image/webp", "gif": "image/gif"}.get(ext, "application/octet-stream")
    return web.FileResponse(full, headers={"Content-Type": ctype})
