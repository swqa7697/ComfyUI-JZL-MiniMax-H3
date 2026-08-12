"""JLZ MiniMax — 节点注册入口（V1 经典 API）

采用 V1 的 NODE_CLASS_MAPPINGS 注册，兼容两种节点实现：
- V3 节点（io.ComfyNode，如参考编码）：执行层按类继承自动识别，Autogrow 照常生效
- V1 节点（经典 API，如漫剧调度四节点）：保留 **kwargs 动态端口与按名分类
"""

import os

from server import PromptServer
from aiohttp import web

from .nodes import JLZ_MiniMaxH3ReferenceToVideo
from .story_nodes import (
    JLZ_MiniMax_ShotFormatter,
    JLZ_MiniMax_SceneDispatcher,
    JLZ_MiniMax_VideoDispatcher,
    JLZ_MiniMax_AudioDispatcher,
)

WEB_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "js")

NODE_CLASS_MAPPINGS = {
    "JLZ_MiniMaxH3ReferenceToVideo": JLZ_MiniMaxH3ReferenceToVideo,
    "JLZ_MiniMax_ShotFormatter": JLZ_MiniMax_ShotFormatter,
    "JLZ_MiniMax_SceneDispatcher": JLZ_MiniMax_SceneDispatcher,
    "JLZ_MiniMax_VideoDispatcher": JLZ_MiniMax_VideoDispatcher,
    "JLZ_MiniMax_AudioDispatcher": JLZ_MiniMax_AudioDispatcher,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "JLZ_MiniMaxH3ReferenceToVideo": "JLZ - 🎬 MiniMax H3 参考编码",
    "JLZ_MiniMax_ShotFormatter": "JLZ - 📋 分镜处理中心",
    "JLZ_MiniMax_SceneDispatcher": "JLZ - 🎯 场景元素调度",
    "JLZ_MiniMax_VideoDispatcher": "JLZ - 🎬 视频调度",
    "JLZ_MiniMax_AudioDispatcher": "JLZ - 🎧 音频调度",
}


# ── 后端端点（分镜处理中心「重拍」文件选择器） ─────────────────

HAS_TKINTER = False
try:
    import tkinter as tk
    from tkinter import filedialog
    HAS_TKINTER = True
except ImportError:
    pass  # 静默放行，不要让整个节点加载失败


@PromptServer.instance.routes.post("/jlz/choose_txt_file")
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
                title="选择镜头提示词文件",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
            )
        else:
            file_path = filedialog.askopenfilename(
                title="选择镜头提示词文件",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
            )
        root.destroy()
        return web.json_response({"path": file_path})
    except Exception as e:
        return web.json_response({"path": "", "error": f"弹窗调用失败: {str(e)}"})


@PromptServer.instance.routes.post("/jlz/minimax_default_dir")
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
