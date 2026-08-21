"""JZL MiniMax — Llama 后端支撑（模型加载存储 + GPU 检测）

从 XB_ToolBox 的 nodes_llama.py 抽取，供「模型加载器 Pro」与「编剧链」独立使用，
不依赖 XB_ToolBox。两个包的 LLAMA_CPP_STORAGE 相互独立，互不干扰。
"""

import os
import gc

import torch

import folder_paths
import comfy.model_management as mm

try:
    from llama_cpp import Llama
    from llama_cpp.llama_chat_format import (
        Llava15ChatHandler, Llava16ChatHandler, MoondreamChatHandler,
        NanoLlavaChatHandler, Llama3VisionAlphaChatHandler, MiniCPMv26ChatHandler
    )
    _HAS_LLAMA_CPP = True
except Exception as _e:
    # 未安装 llama-cpp-python：本地 LLM 推理不可用，其余节点照常加载
    print(f"[JZL-llama] llama-cpp-python 未安装（本地模型不可用，在线 API 等其余节点正常）：{_e}")
    Llama = None
    Llava15ChatHandler = Llava16ChatHandler = MoondreamChatHandler = None
    NanoLlavaChatHandler = Llama3VisionAlphaChatHandler = MiniCPMv26ChatHandler = None
    _HAS_LLAMA_CPP = False

from .support_llama.gguf_layers import get_layer_count


# =============================================================================
# A卡 / N卡 检测工具
# =============================================================================

def is_rocm() -> bool:
    """检测是否为 AMD ROCm 环境"""
    try:
        return torch.cuda.is_available() and hasattr(torch.version, "hip") and torch.version.hip is not None
    except Exception:
        return False


def is_nvidia() -> bool:
    """检测是否为 NVIDIA CUDA 环境"""
    try:
        return torch.cuda.is_available() and not is_rocm()
    except Exception:
        return False


def get_gpu_name() -> str:
    """获取 GPU 名称"""
    try:
        if torch.cuda.is_available():
            return torch.cuda.get_device_name(0)
    except Exception:
        pass
    return "Unknown"


def get_vram_gb() -> float:
    """获取 GPU 显存大小 (GB)"""
    try:
        if torch.cuda.is_available():
            return torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
    except Exception:
        pass
    return 0.0


def get_amd_arch() -> str:
    """获取 AMD GPU 架构代号"""
    if not is_rocm():
        return ""
    try:
        raw = torch.cuda.get_device_properties(0).gcnArchName
        return raw.split(":")[0] if raw else "unknown"
    except Exception:
        return "unknown"


# AMD 架构显存效率系数: 某些AMD架构的GGML offload效率与N卡不同
_AMD_VRAM_FACTOR = {
    "gfx1201": 1.55,  # RDNA4
    "gfx1200": 1.55,
    "gfx1151": 1.50,  # RDNA3.5
    "gfx1150": 1.50,
    "gfx1103": 1.50,  # RDNA3
    "gfx1102": 1.50,
    "gfx1101": 1.50,
    "gfx1100": 1.50,
    "gfx1037": 1.65,  # RDNA2
    "gfx1036": 1.65,
    "gfx1035": 1.65,
    "gfx1034": 1.65,
    "gfx1032": 1.65,
    "gfx1031": 1.65,
    "gfx1030": 1.65,
    "gfx1012": 1.70,  # RDNA1
    "gfx1011": 1.70,
    "gfx1010": 1.70,
    "gfx942": 1.40,   # CDNA3 (MI300X)
    "gfx90a": 1.40,   # CDNA2
    "gfx908": 1.45,   # CDNA
    "gfx906": 1.70,   # Vega
}


def get_vram_factor() -> float:
    """获取当前 GPU 的显存系数"""
    if is_nvidia():
        return 1.55
    if is_rocm():
        arch = get_amd_arch()
        for k, v in _AMD_VRAM_FACTOR.items():
            if arch.startswith(k):
                return v
        return 1.60  # AMD 默认
    return 1.55  # CPU / fallback


def print_gpu_info():
    """打印 GPU 信息用于调试"""
    gpu_type = "ROCm (AMD)" if is_rocm() else ("CUDA (NVIDIA)" if is_nvidia() else "CPU")
    gpu_name = get_gpu_name()
    vram = get_vram_gb()
    arch = get_amd_arch() if is_rocm() else ""
    factor = get_vram_factor()
    arch_str = f", arch={arch}" if arch else ""
    print(f"[JZL-llama] GPU 检测: {gpu_type}, {gpu_name}, VRAM={vram:.1f}GB{arch_str}, factor={factor}")


# =============================================================================
# Chat Handler 导入 (兼容不同版本 llama-cpp-python)
# =============================================================================

try:
    from llama_cpp.llama_chat_format import MTMDChatHandler
    chat_handlers_extra = ["DeepSeek-OCR"]
    _MTMD = True
except Exception:
    _MTMD = False
    chat_handlers_extra = []

chat_handlers = ["None", "LLaVA-1.5", "LLaVA-1.6", "Moondream2", "nanoLLaVA", "llama3-Vision-Alpha", "MiniCPM-v2.6"]

try:
    from llama_cpp.llama_chat_format import Gemma3ChatHandler
    chat_handlers += ["Gemma3"]
except Exception:
    Gemma3ChatHandler = None

try:
    from llama_cpp.llama_chat_format import Gemma4ChatHandler
    chat_handlers += ["Gemma4"]
except Exception:
    Gemma4ChatHandler = None

try:
    from llama_cpp.llama_chat_format import Qwen25VLChatHandler
    chat_handlers += ["Qwen2.5-VL", "MinerU2.5-Pro"]
except Exception:
    Qwen25VLChatHandler = None

try:
    from llama_cpp.llama_chat_format import Qwen3VLChatHandler
    chat_handlers += ["Qwen3-VL", "Qwen3-VL-Thinking"]
except Exception:
    Qwen3VLChatHandler = None

try:
    from llama_cpp.llama_chat_format import Qwen35ChatHandler
    chat_handlers += ["Qwen3.5", "Qwen3.5-Thinking", "Qwen3.6", "Qwen3.6-Thinking"]
except Exception:
    Qwen35ChatHandler = None

try:
    from llama_cpp.llama_chat_format import (GLM46VChatHandler, LFM2VLChatHandler, GLM41VChatHandler)
    chat_handlers += ["GLM-4.6V", "GLM-4.6V-Thinking", "GLM-4.1V-Thinking", "LFM2-VL"]
except Exception:
    GLM46VChatHandler = None
    LFM2VLChatHandler = None
    GLM41VChatHandler = None

try:
    from llama_cpp.llama_chat_format import LFM25VLChatHandler
    chat_handlers += ["LFM2.5-VL"]
except Exception:
    LFM25VLChatHandler = None

try:
    from llama_cpp.llama_chat_format import GraniteDoclingChatHandler
    chat_handlers += ["Granite-Docling"]
except Exception:
    GraniteDoclingChatHandler = None

try:
    from llama_cpp.llama_chat_format import MiniCPMv45ChatHandler
    chat_handlers += ["MiniCPM-v4.5", "MiniCPM-v4.5-Thinking"]
except Exception:
    MiniCPMv45ChatHandler = None

try:
    from llama_cpp.llama_chat_format import MiniCPMv46ChatHandler
    chat_handlers += ["MiniCPM-v4.6", "MiniCPM-v4.6-Thinking"]
except Exception:
    MiniCPMv46ChatHandler = None

try:
    from llama_cpp.llama_chat_format import PaddleOCRChatHandler
    chat_handlers += ["PaddleOCR-VL-1.5"]
except Exception:
    PaddleOCRChatHandler = None

try:
    from llama_cpp.llama_chat_format import Qwen3ASRChatHandler
    chat_handlers += ["Qwen3-ASR"]
except Exception:
    Qwen3ASRChatHandler = None

try:
    from llama_cpp.llama_chat_format import Step3VLChatHandler
    chat_handlers += ["Step3-VL"]
except Exception:
    Step3VLChatHandler = None

chat_handlers += chat_handlers_extra

# 未装 llama-cpp-python 时，下拉只保留 None（本地模型不可选）
if not _HAS_LLAMA_CPP:
    chat_handlers = ["None"]


# =============================================================================
# AnyType / 存储类
# =============================================================================

class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False


class LLAMA_CPP_STORAGE:
    llm = None
    chat_handler = None
    current_config = None
    messages = {}
    sys_prompts = {}

    @classmethod
    def clean_state(cls, id=-1):
        if id == -1:
            cls.messages.clear()
            cls.sys_prompts.clear()
        else:
            cls.messages.pop(f"{id}", None)
            cls.sys_prompts.pop(f"{id}", None)

    @classmethod
    def clean(cls, all=False):
        try:
            cls.llm.close()
        except Exception:
            pass

        try:
            cls.chat_handler._exit_stack.close()
        except Exception:
            pass

        cls.llm = None
        cls.chat_handler = None
        cls.current_config = None
        if all:
            cls.clean_state()

        gc.collect()
        mm.soft_empty_cache()

    @classmethod
    def load_model(cls, config):
        if Llama is None:
            raise RuntimeError(
                "未安装 llama-cpp-python，无法加载本地模型。\n"
                "请按 requirements.txt 安装：N卡 https://github.com/JamePeng/llama-cpp-python/releases"
            )

        def get_chat_handler(chat_handler):
            match chat_handler:
                case "Qwen3.5" | "Qwen3.5-Thinking" | "Qwen3.6" | "Qwen3.6-Thinking":
                    return Qwen35ChatHandler
                case "Qwen3-VL" | "Qwen3-VL-Thinking":
                    return Qwen3VLChatHandler
                case "Qwen3-ASR":
                    return Qwen3ASRChatHandler
                case "Qwen2.5-VL" | "MinerU2.5-Pro":
                    return Qwen25VLChatHandler
                case "LLaVA-1.5":
                    return Llava15ChatHandler
                case "LLaVA-1.6":
                    return Llava16ChatHandler
                case "Moondream2":
                    return MoondreamChatHandler
                case "nanoLLaVA":
                    return NanoLlavaChatHandler
                case "llama3-Vision-Alpha":
                    return Llama3VisionAlphaChatHandler
                case "MiniCPM-v2.6":
                    return MiniCPMv26ChatHandler
                case "MiniCPM-v4.5" | "MiniCPM-v4.5-Thinking":
                    return MiniCPMv45ChatHandler
                case "MiniCPM-v4.6" | "MiniCPM-v4.6-Thinking":
                    return MiniCPMv46ChatHandler
                case "Gemma3":
                    return Gemma3ChatHandler
                case "Gemma4":
                    return Gemma4ChatHandler
                case "GLM-4.6V" | "GLM-4.6V-Thinking":
                    return GLM46VChatHandler
                case "GLM-4.1V-Thinking":
                    return GLM41VChatHandler
                case "LFM2-VL":
                    return LFM2VLChatHandler
                case "LFM2.5-VL":
                    return LFM25VLChatHandler
                case "Granite-Docling":
                    return GraniteDoclingChatHandler
                case "DeepSeek-OCR":
                    return MTMDChatHandler
                case "PaddleOCR-VL-1.5":
                    return PaddleOCRChatHandler
                case "Step3-VL":
                    return Step3VLChatHandler
                case "None":
                    return None
                case _:
                    raise ValueError(f'未知模型类型: "{chat_handler}"')

        cls.clean(all=True)
        cls.current_config = config.copy()
        model = config["model"]
        mmproj = config["mmproj"]
        chat_handler = config["chat_handler"]
        n_ctx = config["n_ctx"]
        vram_limit = config["vram_limit"]
        image_max_tokens = config["image_max_tokens"]
        image_min_tokens = config["image_min_tokens"]
        n_gpu_layers = -1

        model_path = os.path.join(folder_paths.models_dir, 'LLM', model)
        handler = get_chat_handler(chat_handler)

        # A卡/N卡统一的显存感知层数计算
        vram_factor = get_vram_factor()
        if vram_limit != -1:
            gguf_layers = get_layer_count(model_path) or 32
            gguf_size = os.path.getsize(model_path) * vram_factor / (1024 ** 3)
            gguf_layer_size = gguf_size / gguf_layers

        if mmproj and mmproj != "None":
            mmproj_path = os.path.join(folder_paths.models_dir, 'LLM', mmproj)
            if chat_handler == "None":
                raise ValueError('"chat_handler" 不能为 None! (加载了 mmproj 视觉模块)')

            if vram_limit != -1:
                mmproj_size = os.path.getsize(mmproj_path) * vram_factor / (1024 ** 3)
                n_gpu_layers = max(1, int((vram_limit - mmproj_size) / gguf_layer_size))

            print(f"[JZL-llama] 加载视觉模块: {mmproj}")

            think_mode = "Thinking" in chat_handler
            kwargs = {"clip_model_path": mmproj_path, "verbose": False}
            if chat_handler in ["Qwen3-VL", "Qwen3-VL-Thinking"]:
                kwargs["force_reasoning"] = think_mode
                kwargs["image_max_tokens"] = image_max_tokens
                kwargs["image_min_tokens"] = image_min_tokens
            elif chat_handler in ["MiniCPM-v4.5", "GLM-4.6V", "Qwen3.5"]:
                kwargs["enable_thinking"] = think_mode

            if _MTMD:
                kwargs["image_max_tokens"] = image_max_tokens
                kwargs["image_min_tokens"] = image_min_tokens

            try:
                cls.chat_handler = handler(**kwargs)
            except Exception as e:
                raise RuntimeError(
                    f"{e}\n请更新 llama-cpp-python 版本\n"
                    "N卡: https://github.com/JamePeng/llama-cpp-python/releases\n"
                    "A卡: 请使用 ROCm/HIP 编译的 llama-cpp-python"
                )

        else:
            if vram_limit != -1:
                n_gpu_layers = max(1, int(vram_limit / gguf_layer_size))
            if handler is not None:
                cls.chat_handler = handler(verbose=False)
            else:
                cls.chat_handler = None

        print(f"[JZL-llama] 加载模型: {model}")
        print(f"[JZL-llama] n_gpu_layers = {n_gpu_layers} (0=仅CPU, -1=全部GPU)")
        cls.llm = Llama(
            model_path,
            chat_handler=cls.chat_handler,
            n_gpu_layers=n_gpu_layers,
            n_ctx=n_ctx,
            verbose=False
        )


any_type = AnyType("*")

# 模型卸载钩子
if not hasattr(mm, "unload_all_models_backup"):
    mm.unload_all_models_backup = mm.unload_all_models

    def patched_unload_all_models(*args, **kwargs):
        LLAMA_CPP_STORAGE.clean(all=True)
        result = mm.unload_all_models_backup(*args, **kwargs)
        return result

    mm.unload_all_models = patched_unload_all_models
    print("[JZL-llama] 模型卸载钩子已注册!")

# LLM 模型文件夹注册
llm_extensions = ['.ckpt', '.pt', '.bin', '.pth', '.safetensors', '.gguf']
folder_paths.folder_names_and_paths["LLM"] = ([os.path.join(folder_paths.models_dir, "LLM")], llm_extensions)

# 打印 GPU 信息
print_gpu_info()
