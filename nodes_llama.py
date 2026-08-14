"""JZL MiniMax — Llama 模型加载器 + 编剧链节点（V1 经典 API）

漫剧创作链的前半段：
  剧本编剧 → 分镜词生成器 → （story_nodes.py 的分镜处理中心/调度）

依赖 llama_backend.py 的 LLAMA_CPP_STORAGE，与 XB_ToolBox 完全解耦。
"""

import os
import re
import json
from datetime import datetime

import folder_paths

from .llama_backend import LLAMA_CPP_STORAGE, chat_handlers
from .support_llama.presets.minimax_t2va import MINIMAX_T2VA_EN, MINIMAX_T2VA_ZH
from .support_llama.presets.minimax_i2va import MINIMAX_I2VA_EN, MINIMAX_I2VA_ZH
from .support_llama.presets.minimax_fl2va import MINIMAX_FL2VA_EN, MINIMAX_FL2VA_ZH
from .support_llama.presets.minimax_l2va import MINIMAX_L2VA_EN, MINIMAX_L2VA_ZH
from .support_llama.presets.minimax_ref2va import MINIMAX_REF2VA_EN, MINIMAX_REF2VA_ZH


# ═══════════════════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════════════════

def _get_output_dir(story_name="", subfolder=""):
    try:
        base = folder_paths.get_output_directory()
    except Exception:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "output")
    safe_name = re.sub(r'[<>:"/\\|?*\s]', '_', (story_name or "untitled").strip())
    out_dir = os.path.join(base, "jzl", safe_name, subfolder)
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def _safe_path(output_dir, prefix, shot_num=None, ext="txt"):
    ts = datetime.now().strftime("%H%M%S")
    fn = f"{prefix}_{shot_num:03d}_{ts}.{ext}" if shot_num is not None else f"{prefix}_{ts}.{ext}"
    return os.path.join(output_dir, fn)


def _find_latest_version(base_dir):
    """找到最新版本文件夹(第NNN次分镜词), 返回路径和下一个编号"""
    if not os.path.isdir(base_dir):
        return os.path.join(base_dir, "第001次分镜词"), 1
    pat = re.compile(r'第(\d{3})次分镜词')
    versions = []
    for f in os.listdir(base_dir):
        m = pat.match(f)
        if m and os.path.isdir(os.path.join(base_dir, f)):
            versions.append((int(m.group(1)), f))
    if versions:
        versions.sort(reverse=True)
        return os.path.join(base_dir, versions[0][1]), versions[0][0] + 1
    return os.path.join(base_dir, "第001次分镜词"), 1


# ═══════════════════════════════════════════════════════════════
#  节点 1: Llama 模型加载器 Pro
# ═══════════════════════════════════════════════════════════════

class JZL_LlamaModelLoaderPro:
    """Llama 模型加载器 Pro — 合并模型选择与推理参数，支持折叠高级选项"""

    @classmethod
    def INPUT_TYPES(s):
        all_llms = folder_paths.get_filename_list("LLM")
        model_list = [f for f in all_llms if "mmproj" not in f.lower()]
        mmproj_list = ["None"] + [f for f in all_llms if "mmproj" in f.lower()]

        return {
            "required": {
                "model": (model_list,),
                "mmproj": (mmproj_list, {"default": "None"}),
                "chat_handler": (chat_handlers, {"default": "None"}),
                "advanced_settings": ("BOOLEAN", {
                    "default": False,
                    "label_on": "高级参数 ▾",
                    "label_off": "高级参数 ▸",
                    "tooltip": "开启后显示上下文长度、显存上限、图像token 及全部推理参数"
                }),
                "n_ctx": ("INT", {
                    "default": 16384,
                    "min": 1024, "max": 327680, "step": 128,
                    "tooltip": "上下文长度上限\n16384 确保完整加载设定词+故事+分镜输出"
                }),
                "vram_limit": ("INT", {
                    "default": -1,
                    "min": -1, "max": 1024, "step": 1,
                    "tooltip": "显存使用上限(GB), -1=不限制\n参考值, 实际可能略超"
                }),
                "image_min_tokens": ("INT", {"default": 0, "min": 0, "max": 4096, "step": 32}),
                "image_max_tokens": ("INT", {"default": 0, "min": 0, "max": 4096, "step": 32}),
                "max_tokens": ("INT", {"default": 6144, "min": 0, "max": 8192, "step": 1,
                    "tooltip": "生成 Token 上限\n6144 确保 6-8 镜分镜脚本不会截断"}),
                "top_k": ("INT", {"default": 40, "min": 0, "max": 1000, "step": 1,
                    "tooltip": "词汇库检索范围\n40 配合 0.60 温度，兼顾格式严谨与词汇多样"}),
                "top_p": ("FLOAT", {"default": 0.9, "min": 0.0, "max": 1.0, "step": 0.01}),
                "min_p": ("FLOAT", {"default": 0.05, "min": 0.0, "max": 1.0, "step": 0.01}),
                "typical_p": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "temperature": ("FLOAT", {"default": 0.6, "min": 0.0, "max": 2.0, "step": 0.01,
                    "tooltip": "温度\n0.60 确保 [SHOT_START] 格式严谨，减少幻觉"}),
                "repeat_penalty": ("FLOAT", {"default": 1.12, "min": 0.0, "max": 10.0, "step": 0.01,
                    "tooltip": "重复惩罚\n1.12 避免多镜分镜运镜描述句式复读"}),
                "frequency_penalty": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "present_penalty": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 2.0, "step": 0.01}),
                "mirostat_mode": ("INT", {"default": 0, "min": 0, "max": 2, "step": 1}),
                "mirostat_eta": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 1.0, "step": 0.01}),
                "mirostat_tau": ("FLOAT", {"default": 5.0, "min": 0.0, "max": 10.0, "step": 0.01}),
                "state_uid": ("INT", {
                    "default": -1, "min": -1, "max": 999999, "step": 1,
                    "tooltip": "使用特定 ID 保存对话状态 (-1 = 使用节点 unique_id)"
                }),
            }
        }

    RETURN_TYPES = ("LLAMACPPMODEL", "LLAMACPPARAMS")
    RETURN_NAMES = ("llama_model", "parameters")
    FUNCTION = "loadmodel"
    CATEGORY = "JZL/MiniMax"

    def loadmodel(self, model, mmproj, chat_handler, advanced_settings,
                  n_ctx, vram_limit, image_min_tokens, image_max_tokens,
                  max_tokens, top_k, top_p, min_p, typical_p,
                  temperature, repeat_penalty, frequency_penalty, present_penalty,
                  mirostat_mode, mirostat_eta, mirostat_tau, state_uid):
        custom_config = {
            "model": model,
            "mmproj": mmproj,
            "chat_handler": chat_handler,
            "n_ctx": n_ctx,
            "vram_limit": vram_limit,
            "image_min_tokens": image_min_tokens,
            "image_max_tokens": image_max_tokens
        }

        parameters = {
            "max_tokens": max_tokens,
            "top_k": top_k,
            "top_p": top_p,
            "min_p": min_p,
            "typical_p": typical_p,
            "temperature": temperature,
            "repeat_penalty": repeat_penalty,
            "frequency_penalty": frequency_penalty,
            "present_penalty": present_penalty,
            "mirostat_mode": mirostat_mode,
            "mirostat_eta": mirostat_eta,
            "mirostat_tau": mirostat_tau,
            "state_uid": state_uid,
        }

        if not LLAMA_CPP_STORAGE.llm or LLAMA_CPP_STORAGE.current_config != custom_config:
            print("[JZL-llama] 开始加载模型...")
            LLAMA_CPP_STORAGE.load_model(custom_config)

        return (custom_config, parameters)


# ═══════════════════════════════════════════════════════════════
#  节点 2: 剧本与镜头处理器 (剧本编剧 + 分镜词生成器 合一)
#  故事 → N 镜（每镜三合一：H3提示词 + 场景指令 + 音视频指令）
# ═══════════════════════════════════════════════════════════════

class JZL_MiniMax_ScriptProcessor:
    """剧本与镜头处理器 — 一次 LLM 调用：故事拆解 + 每镜 H3 提示词 + 调度指令。"""

    _FIELD_PATTERNS = [
        ("characters", r'\*\*角色\*\*[：:]\s*(.+?)(?:\n|$)'),
        ("scene", r'\*\*场景\*\*[：:]\s*(.+?)(?:\n|$)'),
        ("props", r'\*\*道具\*\*[：:]\s*(.+?)(?:\n|$)'),
        ("camera", r'\*\*运镜\*\*[：:]\s*(.+?)(?:\n|$)'),
        ("action", r'\*\*动作描述\*\*[：:]\s*(.+?)(?:\n|$)'),
    ]

    @classmethod
    def INPUT_TYPES(cls):
        from .presets.script import STORY_STYLES, SHOT_COUNT_OPTIONS
        try:
            from .sheding.story_styles import STORY_STYLES as _ss
        except ImportError:
            _ss = STORY_STYLES
        return {
            "required": {
                "llm_backend": (["local", "api"], {"default": "local"}),
                "mode": (["拆解模式 (Decompose)", "生成模式 (Generate)"], {"default": "拆解模式 (Decompose)"}),
                "story_style": (list(_ss.keys()), {"default": list(_ss.keys())[0] if _ss else "热血战斗"}),
                "story_name": ("STRING", {"default": "", "placeholder": "故事名称"}),
                "story_input": ("STRING", {"multiline": True, "default": ""}),
                "shot_length": (list(SHOT_COUNT_OPTIONS.keys()), {"default": list(SHOT_COUNT_OPTIONS.keys())[0] if SHOT_COUNT_OPTIONS else "短篇 (4镜)"}),
                "shot_duration": ("INT", {"default": 8, "min": 4, "max": 15, "step": 1,
                    "tooltip": "分镜时长(秒)，强制每个分镜视频长度。与「海螺H3视频参数」的时长联动"}),
                "prompt_lang": (["中文 [ZH]", "英文 [EN]"], {"default": "中文 [ZH]"}),
                "ref_image_intro": ("STRING", {"multiline": True, "default": "",
                    "placeholder": "参考图片介绍，例：图1主角特写，图2背景街道..."}),
                "ref_video_intro": ("STRING", {"multiline": True, "default": "",
                    "placeholder": "参考视频介绍，例：视频1运镜参考，视频2动作参考..."}),
                "ref_audio_intro": ("STRING", {"multiline": True, "default": "",
                    "placeholder": "参考音频介绍，例：音频1男主音色，音频2女主音色..."}),
                "advanced_settings": ("BOOLEAN", {
                    "default": False,
                    "label_on": "高级参数 ▾",
                    "label_off": "高级参数 ▸",
                    "tooltip": "开启后显示场景/道具/视频/音频调度开关"
                }),
                "enable_scene": ("BOOLEAN", {"default": True, "label_on": "启用场景", "label_off": "禁用场景",
                    "tooltip": "启用后统计表和分镜里才会输出场景分类调度指令"}),
                "enable_props": ("BOOLEAN", {"default": True, "label_on": "启用道具", "label_off": "禁用道具",
                    "tooltip": "启用后统计表和分镜里才会输出道具分类调度指令"}),
                "enable_video": ("BOOLEAN", {"default": True, "label_on": "启用视频", "label_off": "禁用视频",
                    "tooltip": "启用后分镜里才会输出参考视频调度指令"}),
                "enable_audio": ("BOOLEAN", {"default": True, "label_on": "启用音频", "label_off": "禁用音频",
                    "tooltip": "启用后分镜里才会输出参考音频调度指令"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "step": 1}),
                "force_offload": ("BOOLEAN", {"default": False}),
                "save_states": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "llama_model": ("LLAMACPPMODEL",),
                "parameters": ("LLAMACPPARAMS",),
                "api_response": ("*", {"force_input": True}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("参数总线", "剧本输出")
    FUNCTION = "execute"
    CATEGORY = "JZL/MiniMax"

    @classmethod
    def _parse_four_in_one(cls, content):
        """解析四段格式, 返回 (h3_prompt, scene_info, video_info, audio_info)"""
        h3, scene, video, audio = "", "{}", "{}", "{}"
        for section in re.split(r'\n(?====)', content):
            section = section.strip()
            if section.startswith("===H3_PROMPT==="):
                h3 = section[len("===H3_PROMPT===\n"):].strip()
            elif section.startswith("===SCENE_INSTRUCTION==="):
                scene = section[len("===SCENE_INSTRUCTION===\n"):].strip()
            elif section.startswith("===VIDEO_INSTRUCTION==="):
                video = section[len("===VIDEO_INSTRUCTION===\n"):].strip()
            elif section.startswith("===AUDIO_INSTRUCTION==="):
                audio = section[len("===AUDIO_INSTRUCTION===\n"):].strip()
        return h3, scene, video, audio

    @classmethod
    def _extract_scene_info(cls, shot, shot_num, enable_scene=True, enable_props=True):
        chars, scene, props = "无", "", "无"
        for key, pat in cls._FIELD_PATTERNS:
            m = re.search(pat, shot)
            if not m:
                continue
            val = m.group(1).strip()
            if key == "characters":
                chars = val
            elif key == "scene" and enable_scene:
                scene = val
            elif key == "props" and enable_props:
                props = val
        return json.dumps({"shot": shot_num, "characters": chars or "无", "scene": scene, "props": props or "无"}, ensure_ascii=False)

    @classmethod
    def _extract_video_info(cls, shot, shot_num):
        camera, action = "固定", ""
        for key, pat in cls._FIELD_PATTERNS:
            m = re.search(pat, shot)
            if not m:
                continue
            val = m.group(1).strip()
            if key == "camera":
                camera = val
            elif key == "action":
                action = val
        return json.dumps({"shot": shot_num, "camera": camera or "固定", "action": action, "video_hint": ""}, ensure_ascii=False)

    @classmethod
    def _extract_audio_info(cls, shot, shot_num):
        return json.dumps({"shot": shot_num, "audio_hint": ""}, ensure_ascii=False)

    @classmethod
    def _build_stat_table(cls, scene_list, shot_count):
        chars, scenes, props = [], [], []
        for s in scene_list:
            try:
                d = json.loads(s) if isinstance(s, str) else (s or {})
            except Exception:
                d = {}
            for c in str(d.get("characters", "")).replace("、", ",").split(","):
                c = c.strip()
                if c and c != "无" and c not in chars:
                    chars.append(c)
            sc = str(d.get("scene", "")).strip()
            if sc and sc not in scenes:
                scenes.append(sc)
            for p in str(d.get("props", "")).replace("、", ",").split(","):
                p = p.strip()
                if p and p != "无" and p not in props:
                    props.append(p)
        lines = ["[Statistical table]"]
        lines.append(f"角色共{len(chars)}个：{'、'.join(chars) if chars else '无'}")
        lines.append(f"场景共{len(scenes)}个：{'、'.join(scenes) if scenes else '无'}")
        lines.append(f"道具共{len(props)}个：{'、'.join(props) if props else '无'}")
        lines.append(f"分镜共{shot_count}个")
        return "\n".join(lines)

    def execute(self, mode, story_name, story_input, story_style, shot_length,
                shot_duration, prompt_lang, ref_image_intro, ref_video_intro, ref_audio_intro,
                advanced_settings, enable_scene, enable_props, enable_video, enable_audio,
                seed, force_offload, save_states,
                llm_backend="local", llama_model=None, parameters=None, api_response=None):
        from .presets.script import build_shot_prompt, SHOT_COUNT_OPTIONS

        bus = json.dumps({"story_name": story_name, "api_response": api_response, "has_llama": llama_model is not None}, ensure_ascii=False)
        if not story_input or not story_input.strip():
            return (bus, "[错误] 请输入故事内容")

        lang = "zh" if "ZH" in prompt_lang else "en"
        system_prompt = build_shot_prompt(
            user_story=story_input.strip(), mode=mode, story_style=story_style,
            shot_count_label=shot_length, lang=lang, shot_duration=shot_duration,
            ref_image_intro=ref_image_intro, ref_video_intro=ref_video_intro, ref_audio_intro=ref_audio_intro,
            enable_scene=enable_scene, enable_props=enable_props,
            enable_video=enable_video, enable_audio=enable_audio,
        )
        shot_count = SHOT_COUNT_OPTIONS.get(shot_length, 4)
        user_msg = f"请生成恰好 {shot_count} 个镜头，每个镜头固定 {shot_duration} 秒，输出 [SHOT_START]...[SHOT_END] 完整块（分镜信息 + 六段提示词 + 调度指令）。"

        if llm_backend == "api" and api_response:
            result = api_response
        elif llm_backend == "local" and llama_model is not None:
            if not LLAMA_CPP_STORAGE.llm:
                LLAMA_CPP_STORAGE.load_model(llama_model)
            try:
                _params = parameters.copy() if parameters else {}
                _params.pop("present_penalty", None)
                _params.pop("state_uid", None)
                output = LLAMA_CPP_STORAGE.llm.create_chat_completion(
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_msg}],
                    seed=seed, **_params)
                result = output["choices"][0]["message"]["content"]
            except Exception as e:
                result = f"[LLM 错误] {e}"
            finally:
                if force_offload:
                    LLAMA_CPP_STORAGE.clean()
                elif not save_states:
                    LLAMA_CPP_STORAGE.clean_state()
        else:
            return (bus, "[错误] 请连接 llama_model 或 api_response")

        # 解析 N 镜 → 四段（H3提示词 / 场景 / 视频 / 音频），保存 TXT
        shots = re.findall(r'\[SHOT_START\](.*?)\[SHOT_END\]', result or "", re.DOTALL)
        shots = [s.strip() for s in shots]
        h3_list, scene_list, video_list, audio_list = [], [], [], []
        if shots:
            base_dir = _get_output_dir(story_name, "H3提示词")
            _, next_ver = _find_latest_version(base_dir)
            ver_dir = os.path.join(base_dir, f"第{next_ver:03d}次分镜词")
            os.makedirs(ver_dir, exist_ok=True)
            for i, shot in enumerate(shots):
                shot_num = i + 1
                h3_text, scene_info, video_info, audio_info = self._parse_four_in_one(shot)
                if not h3_text:
                    h3_text = f"[解析失败] 第{shot_num}镜缺少 ===H3_PROMPT==="
                if scene_info == "{}":
                    scene_info = self._extract_scene_info(shot, shot_num, enable_scene, enable_props)
                if video_info == "{}":
                    video_info = self._extract_video_info(shot, shot_num)
                if audio_info == "{}":
                    audio_info = self._extract_audio_info(shot, shot_num)
                h3_list.append(h3_text)
                scene_list.append(scene_info)
                video_list.append(video_info)
                audio_list.append(audio_info)

                ts = datetime.now().strftime("%H%M%S")
                txt_path = os.path.join(ver_dir, f"{shot_num:03d}镜头_{ts}.txt")
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(f"===H3_PROMPT===\n{h3_text}\n")
                    f.write(f"===SCENE_INSTRUCTION===\n{scene_info}\n")
                    f.write(f"===VIDEO_INSTRUCTION===\n{video_info}\n")
                    f.write(f"===AUDIO_INSTRUCTION===\n{audio_info}\n")

        # 统计表由节点计算，保证准确（方便用户准备素材）
        stat_table = self._build_stat_table(scene_list, len(shots))

        bus_data = {"story_name": story_name, "api_response": api_response, "has_llama": llama_model is not None}
        bus_data["h3_prompts"] = h3_list
        bus_data["scene_infos"] = scene_list
        bus_data["video_infos"] = video_list
        bus_data["audio_infos"] = audio_list
        bus_data["stat_table"] = stat_table
        new_bus = json.dumps(bus_data, ensure_ascii=False)

        # 剧本输出：统计表 + 分镜原文（LLM 出错时直接透出错误信息）
        script_output = (stat_table + "\n\n" + result) if shots else result

        # 保存剧本（含统计表）
        prefix = "生成故事拆解" if "生成" in mode else "原始故事拆解"
        with open(_safe_path(_get_output_dir(story_name, "故事拆解"), prefix), "w", encoding="utf-8") as f:
            f.write(script_output)

        return (new_bus, script_output)


class JZL_MiniMaxPreset:
    """MiniMax H3 提示词预设 — T2VA/I2VA/FL2VA/L2VA + 动态参数注入"""

    _STYLES = [
        "不指定 / Unspecified",
        # 🎬 电影感
        "电影感 / Cinematic", "实拍 / Live-action",
        "复古胶片 / Vintage film", "黑白电影 / Black & White",
        "纪录片 / Documentary",
        # 📷 商业摄影
        "极简广告 / Minimalist commercial",
        "微距摄影 / Macro photography",
        "航拍 / Aerial drone",
        # 🎨 动画
        "二维动画 / 2D-animated", "三维CG / 3D CG",
        "日系二次元 / Anime", "美式漫画 / American Comic",
        "皮克斯3D / Pixar-style 3D", "定格动画 / Stop-motion",
        "手绘发光 / Hand-drawn glow", "像素艺术 / Pixel art",
        # 🚀 科幻前卫
        "赛博朋克 / Cyberpunk", "蒸汽朋克 / Steampunk",
        "故障艺术 / Glitch art",
        # 🧶 特殊材质
        "羊毛毡 / Wool felt", "折纸 / Origami",
        # 🖌️ 美术
        "水彩 / Watercolor", "粘土动画 / Claymation",
        "水墨 / Ink wash", "油画 / Oil painting",
        "纸艺拼贴 / Paper collage", "剪纸 / Paper cutout",
        "铅笔素描 / Pencil sketch", "浮世绘 / Ukiyo-e",
        # 🏮 中国风
        "敦煌壁画 / Dunhuang Murals",
        "青花瓷 / Blue-white Porcelain",
        "工笔画 / Gongbi Painting",
        "皮影戏 / Shadow Puppetry",
        "中国风插画 / Chinese Illustration",
        "年画 / New Year Painting",
        # 🧵 手工布艺
        "布艺 / Fabric Art",
        "蜡笔画 / Crayon drawing",
        "哥特萝莉 / Gothic Lolita",
    ]

    _STYLE_HINTS = {
        "电影感 / Cinematic": "cinematic lighting with shallow depth of field, film grain, and professional color grading",
        "实拍 / Live-action": "photorealistic live-action footage with natural lighting and authentic set design",
        "复古胶片 / Vintage film": "vintage film stock with warm color grading, subtle grain, and nostalgic atmosphere",
        "黑白电影 / Black & White": "high-contrast black-and-white cinematography with dramatic shadows",
        "纪录片 / Documentary": "observational documentary style with natural handheld camera work and candid framing",
        "极简广告 / Minimalist commercial": "clean minimalist product cinematography with smooth dolly moves, soft even lighting, and uncluttered compositions",
        "微距摄影 / Macro photography": "extreme close-up macro lens with razor-thin depth of field, revealing fine textures and details",
        "航拍 / Aerial drone": "sweeping aerial drone shots with wide vistas, slow majestic reveals, and expansive landscape views",
        "二维动画 / 2D-animated": "traditional 2D hand-drawn animation with expressive line art and fluid character motion",
        "三维CG / 3D CG": "high-quality 3D rendering with realistic materials, global illumination, and smooth animation",
        "日系二次元 / Anime": "Japanese anime cel-shading with vibrant saturated colors, clean linework, and expressive character designs",
        "美式漫画 / American Comic": "American comic book style with bold black ink outlines, halftone dot shading, and dynamic compositions",
        "皮克斯3D / Pixar-style 3D": "Pixar-quality 3D with smooth curved surfaces, rich vibrant colors, expressive character animation, and polished lighting",
        "定格动画 / Stop-motion": "GLOBAL MATERIAL OVERRIDE — the entire visual world is a stop-motion animation. Characters are handcrafted puppets with visible material textures, moving with tactile frame-by-frame stutter. Environments are miniature physical sets with real fabrics, painted backdrops, and practical lighting. EVERYTHING is a physical model under a camera.",
        "手绘发光 / Hand-drawn glow": "GLOBAL MATERIAL OVERRIDE — the entire visual world is rough hand-drawn line art on dark paper. Characters and environments are sketched with glowing neon-colored outlines that flicker and pulse organically. Light trails follow movement like afterimages. The world itself is a living drawing, every line redrawn in real-time.",
        "像素艺术 / Pixel art": "GLOBAL MATERIAL OVERRIDE — the entire visual world is built from visible pixel blocks. Characters, environments, water, fire, smoke, sky — EVERYTHING is composed of crisp square pixels with a limited retro color palette. Motion is frame-by-frame at low FPS with deliberate pixel-level changes. Particles are individual pixel dots. The pixel grid IS the universe.",
        "赛博朋克 / Cyberpunk": "high-contrast neon-lit cyberpunk cityscape with rain-slicked streets, holographic displays, and chrome cybernetics",
        "蒸汽朋克 / Steampunk": "intricate brass machinery and Victorian-era steam technology with copper pipes, gears, and sepia tones",
        "故障艺术 / Glitch art": "digital glitch distortion with RGB color channel split, scan lines, data corruption artifacts, and VHS noise",
        "羊毛毡 / Wool felt": "GLOBAL MATERIAL OVERRIDE — the entire visual world is handcrafted from fuzzy wool felt. Characters have soft felt textile bodies with visible fiber textures and stitched seams. Wind ripples through felt grass, felt water flows with fiber movement, felt clouds drift across a felt sky. Environments are sewn felt dioramas. DO NOT place felt toys in a real scene — everything IS felt.",
        "折纸 / Origami": "GLOBAL MATERIAL OVERRIDE — the entire universe is constructed from folded paper. Characters are origami figures with sharp clean creases and geometric folded anatomy. Paper birds flap creased wings, paper water ripples in folded layers, paper fire crackles as curling sheets. The world itself is paper — all matter is folded, creased, and crisp.",
        "水彩 / Watercolor": "GLOBAL MATERIAL OVERRIDE — the entire visual world is a 2D watercolor painting on paper. Characters are NOT real people — their bodies are translucent color washes, their faces are soft pigment blooms on wet paper, their edges dissolve into the paper grain. Hair is bleeding pigment streaks, skin is the white of paper with tinted wash. Rain falls as pigment droplets, light diffuses through layered washes. NO realistic skin, NO 3D — only wet pigment on paper.",
        "粘土动画 / Claymation": "GLOBAL MATERIAL OVERRIDE — the entire visual world is hand-sculpted clay. Characters are NOT real people — their bodies are clay with rounded tactile surfaces, visible fingerprints, and tool marks. Hair is sculpted clay strands, skin is smooth plasticine, clothing is pressed clay sheets. Clay water splashes in sculpted droplets, clay smoke rolls in malleable puffs. NO real skin — only clay shaped by human hands.",
        "水墨 / Ink wash": "GLOBAL MATERIAL OVERRIDE — the entire visual world is a 2D ink wash painting on xuan rice paper. Characters are NOT real people — their bodies are fluid black brushstrokes, their faces are ink lines on paper, their clothing is graded ink washes. Hair flows as sweeping brushstrokes, skin tone is the white of the paper itself with ink shading. Water splashes as flying ink drops, wind leaves brushstroke trails, mist is spreading ink on wet paper. NO realistic skin, NO realistic fabric, NO 3D — only ink and paper.",
        "油画 / Oil painting": "GLOBAL MATERIAL OVERRIDE — the entire visual world is a 2D oil painting on canvas. Characters are NOT real people — their bodies are thick oil paint applied with palette knives, their faces are built from layered brushstrokes, their clothing is impasto pigment. Hair is swept paint, skin is blended oil color on canvas, eyes are precise brush dabs. Water ripples in heavy oil strokes, fire is palette-knife texture, clouds are smeared white paint. NO realistic skin, NO real fabric, NO 3D — only oil paint on canvas.",
        "纸艺拼贴 / Paper collage": "GLOBAL MATERIAL OVERRIDE — the entire visual world is layered torn paper. Characters are NOT real people — their bodies are cut from textured paper with torn edges, their faces are printed paper fragments, their clothing is different paper types (newsprint, craft, tissue). Paper birds flap torn-edge wings, paper water ripples in layered sheets. NO real skin — only paper.",
        "剪纸 / Paper cutout": "GLOBAL MATERIAL OVERRIDE — the entire visual world is Chinese paper cutout art. Characters are NOT real people — their bodies are intricate red paper silhouettes cut with symmetrical patterns, moving with articulated paper joints. Shadows cast dramatic shapes through the paper lattice. NO real skin — only cut paper.",
        "铅笔素描 / Pencil sketch": "GLOBAL MATERIAL OVERRIDE — the entire visual world is a 2D graphite pencil drawing on textured paper. Characters are NOT real people — their bodies are graphite lines, hatching, and cross-hatching on paper. Faces are sketched pencil marks, hair is sweeping graphite strokes, skin tone is the white of paper with varying pencil pressure. Motion is lines erasing and redrawing. Eraser marks leave ghost trails. NO real skin, NO 3D — only pencil on paper.",
        "浮世绘 / Ukiyo-e": "GLOBAL MATERIAL OVERRIDE — the entire visual world is a 2D Japanese ukiyo-e woodblock print. Characters are NOT real people — their bodies are flat color areas with bold black outlines printed on washi paper. Faces are printed woodblock features, hair is carved-line black ink, clothing is flat color blocks. NO real skin, NO 3D — only woodblock ink on paper.",
        "敦煌壁画 / Dunhuang Murals": "GLOBAL MATERIAL OVERRIDE — the entire visual world is a 2D animated Dunhuang cave mural on a fresco wall. Characters are NOT real people — their bodies are mineral pigment paintings (ochre, turquoise, lapis lazuli) with weathered fresco cracks. Flying deities trail faded pigment ribbons. NO real skin, NO 3D — only ancient mural pigment on plaster.",
        "青花瓷 / Blue-white Porcelain": "GLOBAL MATERIAL OVERRIDE — the entire universe is living 3D blue-and-white porcelain. Characters are NOT real people — their bodies are white-glazed porcelain with cobalt-blue hand-painted patterns flowing across their skin as features and clothing. Porcelain birds take flight with clicking ceramic wings, porcelain water flows as liquid glaze, porcelain trees bloom with cobalt flowers. NO real skin — only glazed ceramic.",
        "工笔画 / Gongbi Painting": "GLOBAL MATERIAL OVERRIDE — the entire visual world is a 2D gongbi painting on flat silk. Characters are NOT real people — their bodies are ultra-fine brush outlines filled with flat mineral color washes on silk. Every hair and petal is individually painted. Silk fibers visible beneath the pigment. NO real skin, NO 3D — only brush and silk.",
        "皮影戏 / Shadow Puppetry": "GLOBAL MATERIAL OVERRIDE — the entire visual world is a 2D shadow puppet theater on a translucent screen. Characters are NOT real people — their bodies are intricately carved leather silhouettes with articulated joints, illuminated by warm amber backlighting. NO real skin, NO 3D — only leather shadows on a screen.",
        "中国风插画 / Chinese Illustration": "modern Chinese illustration blending traditional ink aesthetics with contemporary digital art, featuring elegant flowing lines, poetic composition, and dreamlike color harmony",
        "年画 / New Year Painting": "GLOBAL MATERIAL OVERRIDE — the entire visual world is a 2D vibrant Chinese folk New Year woodblock print. Characters are NOT real people — their bodies are bold primary color blocks with thick black outlines on flat printed paper. Door gods step out of frames and walk, carp leap as printed patterns. NO real skin, NO 3D — only folk print on paper.",
        "布艺 / Fabric Art": "GLOBAL MATERIAL OVERRIDE — the entire visual world is constructed from sewn fabric and textiles. Characters are NOT real people — they are cloth dolls with stitched seams, button eyes, embroidered facial features, yarn hair, and patchwork clothing. Environments are quilted fabric landscapes: grass is green felt, water is flowing blue silk, clouds are tufted cotton, trees are embroidered tapestry. Every surface shows visible thread, stitching, and fabric grain. NO realistic skin, NO real materials — only fabric and thread.",
        "蜡笔画 / Crayon drawing": "GLOBAL MATERIAL OVERRIDE — the entire visual world is a 2D wax crayon drawing on textured paper. Characters are NOT real people — their bodies are waxy crayon strokes on paper with the paper grain visible through the wax. Bright colors have the distinctive grainy, slightly uneven crayon texture. Lines are thick and waxy with visible stroke direction. Paper texture shows through all color areas. NO 3D depth, NO CG, NO realistic skin — only crayon on paper.",
        "哥特萝莉 / Gothic Lolita": "Gothic Lolita fashion and atmosphere — NOT a material override but a costume and world style. Characters wear elaborate dark Victorian-inspired Lolita clothing: lace-trimmed black dresses, ruffled petticoats, corsets, platform boots, ornate headpieces with ribbons and roses. Architecture is moody Gothic with pointed arches, stained glass, wrought iron. Dramatic chiaroscuro lighting with deep shadows. Color palette: black, deep purple, burgundy, ivory, silver accents. Atmosphere is darkly romantic and theatrical.",
    }

    _MUSIC = [
        "禁止音乐 / No Music",
        "不指定 / Unspecified",
        # 🎹 器乐
        "钢琴 / Piano", "管弦乐 / Orchestral",
        "原声吉他 / Acoustic",
        # 🎛️ 电子
        "电子 / Electronic", "氛围 / Ambient",
        "合成器浪潮 / Synthwave", "芯片音乐 / Chiptune",
        "Lo-fi / Lo-fi",
        # 🎞️ 叙事
        "史诗 / Epic", "悬疑 / Suspense",
        "浪漫弦乐 / Romantic Strings",
        # 🥁 节奏
        "摇滚 / Rock", "爵士 / Jazz",
        "嘻哈 / Hip-Hop", "放克 / Funk",
        # ⛪ 人声
        "纯人声合唱 / Acapella Choir",
        # 🔇 极简
        "极简拟音 / Minimalist Foley",
        # 🏮 中国风
        "国风民乐 / Chinese Folk",
        "戏曲 / Chinese Opera",
        "古琴 / Guqin",
    ]

    _MUSIC_HINTS = {
        "禁止音乐 / No Music": "ABSOLUTELY NO background music of any kind. non_diegetic_music MUST be \"N/A\". Do not add any score, melody, or rhythm.",
        "钢琴 / Piano": "a solo piano piece at a slow to moderate tempo, with sparse delicate notes and natural reverb",
        "管弦乐 / Orchestral": "a majestic full orchestral arrangement with swelling strings and warm brass, maintaining a steady high-energy rhythm throughout",
        "原声吉他 / Acoustic": "an acoustic guitar piece with gentle fingerpicking patterns and warm natural wood resonance",
        "电子 / Electronic": "an electronic track with layered synthesizers, digital beats, and atmospheric pads",
        "氛围 / Ambient": "a minimal ambient soundscape with long sustained tones, subtle textures, and no distinct rhythm",
        "合成器浪潮 / Synthwave": "a pulsing Synthwave instrumental track with heavy analog bass, retro drum machines, neon-soaked pads, and a driving steady rhythm, no vocals, starting abruptly at full energy with zero intro",
        "芯片音乐 / Chiptune": "a retro 8-bit instrumental chiptune track with square-wave melodies, simple waveforms, and nostalgic video game sound",
        "Lo-fi / Lo-fi": "a lo-fi instrumental beat with vinyl crackle, mellow chords, soft drum loops, and a relaxed downtempo groove",
        "史诗 / Epic": "an epic cinematic instrumental score with powerful brass, thundering percussion, soaring choir, and dramatic steady intensity, starting abruptly at full energy without any intro or build-up",
        "悬疑 / Suspense": "a tense suspense instrumental score with low-frequency drones, sudden dissonant stabs, creeping tension, and unsettling silence",
        "浪漫弦乐 / Romantic Strings": "a romantic instrumental string arrangement with lush violins, gentle cello, harp glissandos, and a tender sustained atmosphere",
        "摇滚 / Rock": "an instrumental-only rock track with electric guitar riffs, driving drums, bass groove, and energetic dynamics, STRICTLY NO VOCALS, starting at full power with zero intro",
        "爵士 / Jazz": "an instrumental jazz piece with walking bass, brushed drums, improvisational piano or saxophone, smoky club atmosphere, no vocals",
        "嘻哈 / Hip-Hop": "an instrumental hip-hop beat with heavy 808 bass, crisp trap snares, hi-hat rolls, and a grooving rhythmic flow, STRICTLY NO VOCALS, dropping in at full energy with no intro",
        "放克 / Funk": "an instrumental funk groove with a bouncy slap bassline, tight rhythm guitar, brass stabs, and an infectious syncopated rhythm, no vocals, kicking in immediately at full groove",
        "纯人声合唱 / Acapella Choir": "a pure acapella choir with layered vocal harmonies and no instruments, evoking sacred, ethereal, or haunting atmosphere",
        "极简拟音 / Minimalist Foley": "minimalist foley and ambient silence — only crisp physical sound effects like subtle clicks, soft whooshes, and spatial emptiness, with no melodic music at all",
        "国风民乐 / Chinese Folk": "a traditional Chinese folk piece with guzheng, erhu, dizi bamboo flute, pipa, and flowing pentatonic melodies evoking ancient landscapes",
        "戏曲 / Chinese Opera": "a stylized Chinese opera piece with clanging gongs, wooden clappers, piercing erhu, and dramatic vocal delivery in traditional theatrical style",
        "古琴 / Guqin": "a solo guqin piece with deep resonant plucked silk strings, slow meditative pace, profound stillness, and subtle harmonic overtones",
    }

    _ASPECTS = [
        "16:9", "9:16", "4:3", "3:4", "1:1", "21:9", "4:5", "5:4",
    ]

    _ASPECT_HINTS = {
        "16:9": "standard widescreen — use wide establishing shots, horizontal subject placement, cinematic scope",
        "9:16": "vertical portrait — center subjects vertically, stack elements top-to-bottom, leave breathing room above and below",
        "4:3": "classic Academy ratio — balanced framed composition, suited for dialogue and character-focused shots",
        "3:4": "tall portrait — vertical emphasis, subjects fill the frame from top to bottom, dramatic low/high angles",
        "1:1": "square format — symmetrical center-weighted composition, subjects centered in frame",
        "21:9": "ultrawide cinematic — emphasize sweeping horizontal space, panoramic landscapes, subjects placed off-center with vast negative space",
        "4:5": "portrait tall — slightly taller than 3:4, ideal for social media portrait, subjects framed with vertical breathing room",
        "5:4": "landscape tall — slightly taller than standard, balanced composition with modest horizontal emphasis",
    }

    _CUTS = [
        "不指定 / Unspecified",
        "不切镜 / Single Shot",
        "1 次切镜 / 1 Cut",
        "2 次切镜 / 2 Cuts",
        "3 次切镜 / 3 Cuts",
        "4 次切镜 / 4 Cuts",
        "5 次切镜 / 5 Cuts",
        "6 次切镜 / 6 Cuts",
        "7 次切镜 / 7 Cuts",
        "8 次切镜 / 8 Cuts",
        "9 次切镜 / 9 Cuts",
    ]

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "预设模式": ([
                    "纯文本生成音视频[英文]-T2VA [EN]", "纯文本生成音视频[中文]-T2VA [ZH]",
                    "首帧图生成音视频[英文]-I2VA [EN]", "首帧图生成音视频[中文]-I2VA [ZH]",
                    "首尾帧生成音视频[英文]-FL2VA [EN]", "首尾帧生成音视频[中文]-FL2VA [ZH]",
                    "尾帧图生成音视频[英文]-L2VA [EN]", "尾帧图生成音视频[中文]-L2VA [ZH]",
                ],),
                "视频时长": ("INT", {"default": 8, "min": 4, "max": 15, "step": 1,
                    "tooltip": "视频时长 (秒), MiniMax H3 支持 4–15 秒"}),
                "视觉风格": (s._STYLES, {"default": "不指定 / Unspecified"}),
                "音乐风格": (s._MUSIC, {"default": "禁止音乐 / No Music"}),
                "画面比例": (s._ASPECTS, {"default": "16:9"}),
                "切镜次数": (s._CUTS, {"default": "不指定 / Unspecified"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("system_prompt",)
    FUNCTION = "build"
    CATEGORY = "JZL/MiniMax"

    def build(self, 预设模式, 视频时长, 视觉风格, 音乐风格, 画面比例, 切镜次数):
        preset = 预设模式
        duration = 视频时长
        style = 视觉风格
        music = 音乐风格
        aspect = 画面比例
        cuts = 切镜次数
        match preset:
            case "纯文本生成音视频[英文]-T2VA [EN]":   base = MINIMAX_T2VA_EN
            case "纯文本生成音视频[中文]-T2VA [ZH]":   base = MINIMAX_T2VA_ZH
            case "首帧图生成音视频[英文]-I2VA [EN]":   base = MINIMAX_I2VA_EN
            case "首帧图生成音视频[中文]-I2VA [ZH]":   base = MINIMAX_I2VA_ZH
            case "首尾帧生成音视频[英文]-FL2VA [EN]":   base = MINIMAX_FL2VA_EN
            case "首尾帧生成音视频[中文]-FL2VA [ZH]":   base = MINIMAX_FL2VA_ZH
            case "尾帧图生成音视频[英文]-L2VA [EN]":   base = MINIMAX_L2VA_EN
            case "尾帧图生成音视频[中文]-L2VA [ZH]":   base = MINIMAX_L2VA_ZH
            case _: raise ValueError(f'未知预设: "{preset}"')

        is_zh = "[ZH]" in preset
        params = []

        if is_zh:
            params.append("## 目标视频参数（必须严格遵守）")
            params.append(f"- 视频时长：正好 {duration} 秒（镜头切分和时间戳必须精确落在此范围内，最后一个镜头必须在第{duration}秒前结束）")
            if "不指定" not in style:
                en_name = style.split(" / ")[0]
                zh_name = style.split(" / ")[-1]
                hint = self._STYLE_HINTS.get(style, "")
                params.append(f"- 视觉风格：{zh_name} ({en_name}) — {hint}")
                params.append(f"  ⚠️ [Shot 1] 必须以 \"{en_name}\" 开头，然后立即用1-2句话详细描述{zh_name}在画面中的具体视觉呈现——材质、光影、色彩、动作特征。严禁只写风格名称就跳到下一句！必须写出该风格\"长什么样\"。")
                params.append(f"  正确示例: \"[Shot 1] 粘土动画，画面中的角色呈现手工泥塑的圆润质感，表面可见细微指痕和工具刮痕，动作带有定格动画特有的逐帧卡顿节奏...\"")
                params.append(f"  错误示例: \"[Shot 1] 粘土动画，中全景镜头...\"（只写了名称，没有视觉描述）")
            if "不指定" not in music:
                zh_name = music.split(" / ")[-1]
                hint = self._MUSIC_HINTS.get(music, "")
                params.append(f"- 背景音乐风格：{zh_name} — {hint}")
                if "禁止音乐" in music:
                    params.append(f"  ⚠️ 整个视频不得出现任何背景音乐。non_diegetic_music 必须严格输出 \"N/A\"。")
            if "不指定" not in cuts:
                if "不切镜" in cuts:
                    params.append(f"- 切镜：固定镜头，不切镜。整段视频只有 [Shot 1] 一个镜头。仅通过运镜（摇摄、俯仰、横移、变焦、跟拍、推拉）改变视角。严禁输出 [Shot N] 时间戳。")
                else:
                    n = int(cuts.split(" ")[0])
                    max_ok = max(1, duration // 2)
                    if n > max_ok:
                        params.append(f"- ⚠️ 切镜次数 {n} 对于 {duration} 秒视频过多（合理上限 {max_ok} 次）。请根据实际可用时长自行削减到合理范围，保证每个镜头至少 2 秒。")
                    params.append(f"- 切镜：正好 {n} 次（共 {n+1} 个镜头）。所有镜头必须在 {duration} 秒内完成。切镜时机遵循叙事节奏——紧张段落切快、抒情段落切慢，不可均分。每次切镜必须以 [Shot N] At MM:SS.mmm 开头，时间戳严格递增。")
            hint = self._ASPECT_HINTS.get(aspect, "")
            params.append(f"- 画面比例：{aspect} — {hint}")
            params.append(f"  所有镜头构图、主体位置、留白空间必须匹配 {aspect} 比例。")
        else:
            params.append("## Target Video Parameters (MUST follow exactly)")
            params.append(f"- Duration: exactly {duration} seconds (all shot timestamps MUST fall within this range; the final shot must end before the {duration}-second mark)")
            if "Unspecified" not in style:
                en_name = style.split(" / ")[0]
                hint = self._STYLE_HINTS.get(style, "")
                params.append(f"- Visual style: {en_name} — {hint}")
                params.append(f"  ⚠️ [Shot 1] MUST begin with \"{en_name}\" and immediately elaborate with 1-2 sentences of concrete visual description — textures, lighting, colors, motion characteristics that define this style. Do NOT just name the style and move on. Show what the style actually looks like.")
                params.append(f"  Correct: \"[Shot 1] Claymation, the characters have the rounded tactile quality of hand-sculpted clay with visible fingerprints and tool marks, their movements carrying the distinctive frame-by-frame stutter of stop-motion...\"")
                params.append(f"  Wrong: \"[Shot 1] Claymation, a medium-wide shot...\" (name only, no visual description)")
            if "Unspecified" not in music:
                en_name = music.split(" / ")[0]
                hint = self._MUSIC_HINTS.get(music, "")
                params.append(f"- Background music style: {en_name} — {hint}")
                if "No Music" in music:
                    params.append(f"  ⚠️ The video must have absolutely no background music. non_diegetic_music MUST be \"N/A\".")
            if "Unspecified" not in cuts:
                if "Single Shot" in cuts:
                    params.append(f"- Cuts: Single continuous shot — NO cuts. The entire video is only [Shot 1]. Use camera movement only (pan, tilt, truck, zoom, tracking, push/pull) to change viewpoint. Do NOT output any [Shot N] timestamps.")
                else:
                    n = int(cuts.split(" ")[0])
                    max_ok = max(1, duration // 2)
                    if n > max_ok:
                        params.append(f"- ⚠️ {n} cuts is excessive for a {duration}-second video (reasonable max: {max_ok}). Reduce to a feasible number, ensuring at least 2 seconds per shot.")
                    params.append(f"- Cuts: exactly {n} cut(s) (meaning {n+1} total shots). All shots must fit within {duration} seconds. Cut timing must follow narrative rhythm — faster cuts for tense/action moments, longer holds for calm/emotional moments. Do NOT space cuts evenly. Every cut MUST begin with [Shot N] At MM:SS.mmm with strictly increasing timestamps.")
            hint = self._ASPECT_HINTS.get(aspect, "")
            params.append(f"- Aspect ratio: {aspect} — {hint}")
            params.append(f"  All shot compositions, subject placement, and negative space must be framed for {aspect}.")
        params.append("")
        param_block = "\n".join(params)

        marker = "## "
        idx = base.find(marker)
        if idx > 0:
            result = base[:idx].rstrip() + "\n\n" + param_block + base[idx:]
        else:
            result = param_block + "\n" + base

        return (result,)


class JZL_MiniMaxRef2vaPreset:
    """MiniMax H3 Ref2VA 全引用模式专用 — 多模态参考 + 风格策略"""

    _STYLES = [
        "保持统一风格 / Consistent Style",
        "多种风格混搭 / Mixed Styles",
        "多种风格转换 / Style Transformation",
    ]

    _STYLE_HINTS = {
        "保持统一风格 / Consistent Style": "STRICT STYLE CONSISTENCY — all characters, environments, and visual elements must share the exact same visual style derived from the reference images. Every frame must look like it belongs to a single unified visual universe. No character should look like they came from a different artwork.",
        "多种风格混搭 / Mixed Styles": "STYLE MIXING — different characters or elements may retain their distinct visual styles from their respective references. Examples: a live-action person interacting with a 2D-animated character; two pixel-art characters walking through a photorealistic background; a clay figure next to an origami figure. CRITICAL: each reference element must remain visually STABLE — a real person must stay real, an anime character must stay anime, clay must stay clay throughout the video. The challenge is making them coexist naturally in the same space.",
        "多种风格转换 / Style Transformation": "STYLE TRANSFORMATION — the ENTIRE frame undergoes a smooth, visible transition from one visual style to another over the course of the video. Examples: live-action gradually becomes 2D-animated; claymation transforms into origami; watercolor washes over a realistic scene. ALL shapes, proportions, and spatial relationships must be preserved during the transformation — only the rendering style changes. The transformation must be smooth and continuous, not an abrupt switch.",
    }

    _CUTS = JZL_MiniMaxPreset._CUTS
    _MUSIC = JZL_MiniMaxPreset._MUSIC
    _MUSIC_HINTS = JZL_MiniMaxPreset._MUSIC_HINTS
    _ASPECTS = JZL_MiniMaxPreset._ASPECTS
    _ASPECT_HINTS = JZL_MiniMaxPreset._ASPECT_HINTS

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "预设模式": ([
                    "多参考生成音视频[英文]-Ref2VA [EN]",
                    "多参考生成音视频[中文]-Ref2VA [ZH]",
                ],),
                "参考图片介绍": ("STRING", {"default": "", "multiline": True,
                    "placeholder": "输入参考图片描述，例：图一男主角特写，图二女主角全身，图三背景街道..."}),
                "参考视频介绍": ("STRING", {"default": "", "multiline": True,
                    "placeholder": "输入参考视频描述，例：视频一运镜参考，视频二角色动作参考..."}),
                "参考音频介绍": ("STRING", {"default": "", "multiline": True,
                    "placeholder": "输入参考音频描述，例：音频一男主音色参考，音频二女主音色参考..."}),
                "视频时长": ("INT", {"default": 8, "min": 4, "max": 15, "step": 1,
                    "tooltip": "视频时长 (秒), MiniMax H3 支持 4–15 秒"}),
                "视觉风格": (s._STYLES, {"default": "保持统一风格 / Consistent Style"}),
                "音乐风格": (s._MUSIC, {"default": "禁止音乐 / No Music"}),
                "画面比例": (s._ASPECTS, {"default": "16:9"}),
                "切镜次数": (s._CUTS, {"default": "不指定 / Unspecified"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("system_prompt",)
    FUNCTION = "build"
    CATEGORY = "JZL/MiniMax"

    def build(self, 预设模式, 参考图片介绍, 参考视频介绍, 参考音频介绍, 视频时长, 视觉风格, 音乐风格, 画面比例, 切镜次数):
        preset = 预设模式
        imgs = 参考图片介绍
        vids = 参考视频介绍
        auds = 参考音频介绍
        duration = 视频时长
        style = 视觉风格
        music = 音乐风格
        aspect = 画面比例
        cuts = 切镜次数

        match preset:
            case "多参考生成音视频[英文]-Ref2VA [EN]":   base = MINIMAX_REF2VA_EN
            case "多参考生成音视频[中文]-Ref2VA [ZH]":   base = MINIMAX_REF2VA_ZH
            case _: raise ValueError(f'未知预设: "{preset}"')

        is_zh = "[ZH]" in preset
        params = []

        # ── 参考素材注入 ──
        if is_zh:
            params.append("## 目标视频参数（必须严格遵守）")
            if imgs.strip():
                params.append(f"- 参考图片说明：{imgs.strip()}")
            if vids.strip():
                params.append(f"- 参考视频说明：{vids.strip()}")
            if auds.strip():
                params.append(f"- 参考音频说明：{auds.strip()}")
            params.append(f"- 视频时长：正好 {duration} 秒（镜头切分和时间戳必须精确落在此范围内，最后一个镜头必须在第{duration}秒前结束）")
            hint = self._STYLE_HINTS.get(style, "")
            params.append(f"- 视觉风格策略：{style.split('/')[-1].strip()} ({style.split('/')[0].strip()}) — {hint}")
            if "不指定" not in music:
                zh_name = music.split(" / ")[-1]
                hint_m = self._MUSIC_HINTS.get(music, "")
                params.append(f"- 背景音乐风格：{zh_name} — {hint_m}")
                if "禁止音乐" in music:
                    params.append(f"  ⚠️ 整个视频不得出现任何背景音乐。non_diegetic_music 必须严格输出 \"N/A\"。")
            if "不指定" not in cuts:
                if "不切镜" in cuts:
                    params.append(f"- 切镜：固定镜头，不切镜。整段视频只有 [Shot 1] 一个镜头。仅通过运镜改变视角。严禁输出 [Shot N] 时间戳。")
                else:
                    n = int(cuts.split(" ")[0])
                    max_ok = max(1, duration // 2)
                    if n > max_ok:
                        params.append(f"- ⚠️ 切镜次数 {n} 对于 {duration} 秒视频过多（合理上限 {max_ok} 次）。请自行削减。")
                    params.append(f"- 切镜：正好 {n} 次（共 {n+1} 个镜头）。切镜时机遵循叙事节奏，不可均分。每次切镜必须以 [Shot N] At MM:SS.mmm 开头。")
            hint_a = self._ASPECT_HINTS.get(aspect, "")
            params.append(f"- 画面比例：{aspect} — {hint_a}")
            params.append(f"  所有镜头构图、主体位置、留白空间必须匹配 {aspect} 比例。")
        else:
            params.append("## Target Video Parameters (MUST follow exactly)")
            if imgs.strip():
                params.append(f"- Reference image notes: {imgs.strip()}")
            if vids.strip():
                params.append(f"- Reference video notes: {vids.strip()}")
            if auds.strip():
                params.append(f"- Reference audio notes: {auds.strip()}")
            params.append(f"- Duration: exactly {duration} seconds (all shot timestamps MUST fit within this range; the final shot must end before the {duration}-second mark)")
            hint = self._STYLE_HINTS.get(style, "")
            params.append(f"- Visual style strategy: {style.split('/')[0].strip()} — {hint}")
            if "Unspecified" not in music:
                en_name = music.split(" / ")[0]
                hint_m = self._MUSIC_HINTS.get(music, "")
                params.append(f"- Background music style: {en_name} — {hint_m}")
                if "No Music" in music:
                    params.append(f"  ⚠️ The video must have absolutely no background music. non_diegetic_music MUST be \"N/A\".")
            if "Unspecified" not in cuts:
                if "Single Shot" in cuts:
                    params.append(f"- Cuts: Single continuous shot — NO cuts. Only [Shot 1]. Use camera movement only.")
                else:
                    n = int(cuts.split(" ")[0])
                    max_ok = max(1, duration // 2)
                    if n > max_ok:
                        params.append(f"- ⚠️ {n} cuts is excessive for a {duration}-second video (reasonable max: {max_ok}). Reduce.")
                    params.append(f"- Cuts: exactly {n} cut(s) (meaning {n+1} total shots). Cut timing follows narrative rhythm — do NOT space evenly. Every cut MUST begin with [Shot N] At MM:SS.mmm.")
            hint_a = self._ASPECT_HINTS.get(aspect, "")
            params.append(f"- Aspect ratio: {aspect} — {hint_a}")
            params.append(f"  All shot compositions must be framed for {aspect}.")
        params.append("")
        param_block = "\n".join(params)

        marker = "## "
        idx = base.find(marker)
        if idx > 0:
            result = base[:idx].rstrip() + "\n\n" + param_block + base[idx:]
        else:
            result = param_block + "\n" + base

        return (result,)
