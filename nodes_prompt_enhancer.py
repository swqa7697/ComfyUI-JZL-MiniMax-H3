"""JZL MiniMax — 提示词增强节点（独立文件，专一设定）。

串联在「剧本与镜头处理器」与「分段处理中心」之间：
  剧本输出 ──► 提示词增强 ──► 增强后剧本 ──► 分段处理中心
              BUS ──────────► 提示词增强（读取模型/API/偏好/风格等参数）

职责单一：独立运行一次 LLM，把剧本输出里每个分段的 detailed_description
字段重写、扩写并替换回原位置；其余字段（subject_definitions / summary /
retention_analysis / overall_soundscape / non_diegetic_music / 调度指令）原样保留。
"""

import re

from .llama_backend import LLAMA_CPP_STORAGE
from .nodes_llama import JZL_MiniMax_ScriptProcessor
from .sheding.prompt_enhancer_rules import build_enhancer_prompt


class JZL_MiniMaxPromptEnhancer:
    """提示词增强 — 只润色 detailed_description，其余原样保留。"""

    _SEGMENT_INFO_KEYS = ["标题", "时长", "景别", "运镜", "角色", "场景", "道具", "动作描述", "氛围光影"]
    _SEGMENT_INFO_KEYS_EN = ["Title", "Duration", "Shot size", "Camera", "Characters", "Scene", "Props", "Action", "Atmosphere"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "script_text": ("STRING", {"multiline": True, "forceInput": True,
                    "tooltip": "从「剧本与镜头处理器」的「剧本输出」连线"}),
                "bus": ("JZL_H3_BUS", {"forceInput": True,
                    "tooltip": "从「剧本与镜头处理器」的 BUS 连线，传递模型/API/偏好/风格等参数"}),
                "force_offload": ("BOOLEAN", {"default": False, "label_on": "增强后卸载", "label_off": "不卸载",
                    "tooltip": "本地模型：增强完成后卸载。建议剧本处理器关闭卸载、本节点开启，等增强完成再卸载，省一次重复加载"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "step": 1, "control_after_generate": True,
                    "tooltip": "随机种子\n改 seed 可生成不同的润色结果；前端可选随机/递增/固定"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("增强后剧本",)
    FUNCTION = "enhance"
    CATEGORY = "JZL/MiniMax"

    @classmethod
    def IS_CHANGED(cls, seed=0, **kwargs):
        return seed

    # ── 解析工具 ──────────────────────────────────────────────

    @staticmethod
    def _split_blocks(text):
        """分离统计表前缀与 [SHOT_START]...[SHOT_END] 块。"""
        text = text or ""
        blocks = re.findall(r'\[SHOT_START\](.*?)\[SHOT_END\]', text, re.DOTALL)
        prefix = re.split(r'\[SHOT_START\]', text, maxsplit=1)[0]
        return prefix.rstrip(), [b.strip() for b in blocks]

    @staticmethod
    def _extract_field(h3_body, field_name):
        """提取 H3_PROMPT 六字段之一（按行首字段名定位，到下一字段行首结束）。"""
        m = re.search(rf'(?m)^{field_name}\s*:\s*', h3_body)
        if not m:
            return ""
        content_start = m.end()
        tail = h3_body[content_start:]
        next_m = re.search(r'(?m)^[a-z_]+\s*:\s*', tail)
        content_end = content_start + (next_m.start() if next_m else len(tail))
        return h3_body[content_start:content_end].strip()

    @classmethod
    def _extract_segment_info(cls, block):
        """提取分段信息九行（**标题** 等），返回 dict。"""
        info = {}
        for key in cls._SEGMENT_INFO_KEYS:
            m = re.search(rf'\*\*{key}\*\*\s*[：:]\s*(.*?)(?:\n|$)', block)
            info[key] = m.group(1).strip() if m else ""
        return info

    @staticmethod
    def _extract_dispatch(block):
        """提取三个调度指令段，供 LLM 对齐标签编号。"""
        parts = []
        for marker in ("===SCENE_INSTRUCTION===", "===VIDEO_INSTRUCTION===", "===AUDIO_INSTRUCTION==="):
            m = re.search(rf'{marker}\s*(.*?)(?====|\[SHOT_END\]|\Z)', block, re.DOTALL)
            if m:
                parts.append(f"{marker}\n{m.group(1).strip()}")
        return "\n".join(parts)

    # ── LLM 调用 ──────────────────────────────────────────────

    @staticmethod
    def _run_llm(bus, system_prompt, user_msg, force_offload=False, seed=0):
        """按 BUS 里的后端配置调用 LLM，返回生成文本。"""
        llm_backend = str(bus.get("llm_backend", "local"))
        api_config = bus.get("api_config")
        llama_model = bus.get("llama_model")
        parameters = bus.get("parameters")
        save_states = bus.get("save_states", False)

        if "api" in llm_backend and api_config:
            return JZL_MiniMax_ScriptProcessor._call_api(api_config, system_prompt, user_msg)
        if "local" in llm_backend and llama_model is not None:
            if not LLAMA_CPP_STORAGE.llm:
                LLAMA_CPP_STORAGE.load_model(llama_model)
            try:
                _params = parameters.copy() if parameters else {}
                _params.pop("present_penalty", None)
                _params.pop("state_uid", None)
                output = LLAMA_CPP_STORAGE.llm.create_chat_completion(
                    messages=[{"role": "system", "content": system_prompt},
                              {"role": "user", "content": user_msg}],
                    seed=seed, **_params)
                return output["choices"][0]["message"]["content"]
            except Exception as e:
                return f"[LLM 错误] {e}"
            finally:
                if force_offload:
                    LLAMA_CPP_STORAGE.clean()
                elif not save_states:
                    LLAMA_CPP_STORAGE.clean_state()
        return "[错误] BUS 缺少 llama_model 或 api_config"

    # ── 单块润色 ──────────────────────────────────────────────

    @classmethod
    def _build_user_msg(cls, lang, info, subject_defs, dispatch, original_dd):
        if lang == "en":
            labels = cls._SEGMENT_INFO_KEYS_EN
            head = "[Segment info]"
            tail = "Please output the rewritten detailed_description body."
        else:
            labels = cls._SEGMENT_INFO_KEYS
            head = "【本分段信息】"
            tail = "请输出重写后的 detailed_description 正文。"
        info_lines = "\n".join(f"{lab}: {info.get(k) or ''}" for lab, k in zip(labels, cls._SEGMENT_INFO_KEYS))
        return (
            f"{head}\n{info_lines}\n\n"
            f"【subject_definitions（标签编号以此为准）】\n{subject_defs or '- 无'}\n\n"
            f"【调度指令（标签编号以此为准）】\n{dispatch or '- 无'}\n\n"
            f"【原 detailed_description（在此基础润色）】\n{original_dd}\n\n"
            f"{tail}"
        )

    @classmethod
    def _enhance_block(cls, block, system_prompt, bus, lang, force_offload, seed):
        """润色单块的 detailed_description，返回新块；失败返回 None（调用方保留原块）。"""
        h3_m = re.search(r'(===H3_PROMPT===\n)(.*?)(?====|\Z)', block, re.DOTALL)
        if not h3_m:
            return None
        marker = h3_m.group(1)
        h3_body = h3_m.group(2)

        dd_m = re.search(r'(?m)^detailed_description\s*:\s*', h3_body)
        if not dd_m:
            return None
        content_start = dd_m.end()
        tail = h3_body[content_start:]
        next_m = re.search(r'(?m)^[a-z_]+\s*:\s*', tail)
        content_end = content_start + (next_m.start() if next_m else len(tail))
        original_dd = h3_body[content_start:content_end].strip()
        if not original_dd:
            return None

        subject_defs = cls._extract_field(h3_body, "subject_definitions")
        dispatch = cls._extract_dispatch(block)
        info = cls._extract_segment_info(block)
        user_msg = cls._build_user_msg(lang, info, subject_defs, dispatch, original_dd)

        new_dd = cls._run_llm(bus, system_prompt, user_msg, force_offload, seed)
        new_dd = (new_dd or "").strip()
        if not new_dd or new_dd.startswith(("[API", "[LLM", "[错误", "[读取")):
            return None  # LLM 失败，保留原块

        new_h3_body = h3_body[:content_start] + "\n" + new_dd + "\n" + h3_body[content_end:]
        return block[:h3_m.start()] + marker + new_h3_body + block[h3_m.end():]

    # ── 主执行 ────────────────────────────────────────────────

    def enhance(self, script_text, bus, force_offload, seed):
        if not isinstance(bus, dict):
            return ("[错误] 请从「剧本与镜头处理器」的 BUS 连线",)
        if not script_text or not script_text.strip():
            return ("[错误] 请从「剧本与镜头处理器」的「剧本输出」连线",)

        lang = bus.get("lang", "zh")
        story_style = bus.get("story_style", "")
        segment_duration = bus.get("segment_duration", 8)
        preference = bus.get("preference", "")
        custom_rules = bus.get("custom_rules", "")

        system_prompt = build_enhancer_prompt(lang, story_style, segment_duration, preference, custom_rules)

        prefix, blocks = self._split_blocks(script_text)
        if not blocks:
            return ("[错误] 剧本输出里没有找到 [SHOT_START]...[SHOT_END] 分段块",)

        enhanced_blocks = []
        failed = 0
        for block in blocks:
            new_block = self._enhance_block(block, system_prompt, bus, lang, force_offload, seed)
            if new_block is None:
                failed += 1
                enhanced_blocks.append(block)
            else:
                enhanced_blocks.append(new_block)

        # 统计表（前缀）原样保留 + 增强后的分段块
        parts = [prefix] if prefix else []
        parts += [f"[SHOT_START]\n{b}\n[SHOT_END]" for b in enhanced_blocks]
        result = "\n\n".join(parts)

        if failed:
            result += f"\n\n[⚠️ 提示词增强] {failed} 个分段润色失败，已保留原 detailed_description。"
        return (result,)
