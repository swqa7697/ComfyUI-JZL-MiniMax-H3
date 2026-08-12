"""JLZ MiniMax H3 — V3 注册入口。

本仓库使用 ComfyUI 新版 V3 节点机制（comfy_entrypoint / io.Schema），
与官方 comfy_extras/nodes_minimax_h3.py 相同的注册方式。
"""

from .nodes import JLZ_MiniMaxH3ReferenceToVideo
from comfy_api.latest import ComfyExtension


class JLZ_MiniMaxH3Extension(ComfyExtension):
    async def get_node_list(self):
        return [
            JLZ_MiniMaxH3ReferenceToVideo,
        ]


async def comfy_entrypoint() -> JLZ_MiniMaxH3Extension:
    return JLZ_MiniMaxH3Extension()
