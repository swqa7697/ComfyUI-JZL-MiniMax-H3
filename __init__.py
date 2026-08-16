"""JZL MiniMax — 节点注册入口（V1 经典 API）

采用 V1 的 NODE_CLASS_MAPPINGS 注册，兼容两种节点实现：
- V3 节点（io.ComfyNode，如参考编码）：执行层按类继承自动识别，Autogrow 照常生效
- V1 节点（经典 API，如漫剧调度四节点）：保留 **kwargs 动态端口与按名分类
"""

import os

from server import PromptServer
from aiohttp import web

from .nodes import JZL_MiniMaxH3ReferenceToVideo, JZL_MiniMaxH3ReferenceToVideo2
from .nodes_hailuo_video import JZL_HailuoH3VideoParams
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
from .nodes_ref_bus import JZL_MiniMaxH3RefBusOut, JZL_MiniMaxH3RefBusIn
from .nodes_prompt_enhancer import JZL_MiniMaxPromptEnhancer

WEB_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "js")

NODE_CLASS_MAPPINGS = {
    "JZL_MiniMaxH3ReferenceToVideo": JZL_MiniMaxH3ReferenceToVideo,
    "JZL_MiniMaxH3ReferenceToVideo2": JZL_MiniMaxH3ReferenceToVideo2,
    "JZL_HailuoH3VideoParams": JZL_HailuoH3VideoParams,
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
    "JZL_MiniMaxH3RefBusOut": JZL_MiniMaxH3RefBusOut,
    "JZL_MiniMaxH3RefBusIn": JZL_MiniMaxH3RefBusIn,
    "JZL_MiniMaxPromptEnhancer": JZL_MiniMaxPromptEnhancer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "JZL_MiniMaxH3ReferenceToVideo": "JZL - 🎬 MiniMax H3 参考编码",
    "JZL_MiniMaxH3ReferenceToVideo2": "JZL - 🎬 MiniMax H3 参考编码2",
    "JZL_HailuoH3VideoParams": "JZL - 🌊 海螺H3视频参数",
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
    "JZL_MiniMaxAPISettings": "JZL - 🌐 API 设置",
    "JZL_MiniMaxMusicCaption": "JZL - 🎵 MiniMax Music3 提示词预设",
    "JZL_MiniMaxMusicCaptionDuet": "JZL - 🎵 MiniMax Music3 提示词预设（双人）",
    "JZL_MiniMaxMusicLyricsEditor": "JZL - 🎵 MiniMax Music3 歌词编辑",
    "JZL_MiniMaxH3RefBusOut": "JZL - 🔗 MiniMax H3 参考总线（打包）",
    "JZL_MiniMaxH3RefBusIn": "JZL - 🔗 MiniMax H3 参考总线（解包）",
    "JZL_MiniMaxPromptEnhancer": "JZL - ✨ 提示词增强",
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
