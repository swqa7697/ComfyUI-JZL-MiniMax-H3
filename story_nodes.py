"""JZL MiniMax 一键漫剧创作 — 节点定义（V1 经典 API）

总线信号链: 剧本编剧 → 分镜词生成器 → 分镜处理中心
调度分支: 分镜处理中心 → 场景元素调度 / 视频调度 / 音频调度

本文件包含 4 个纯逻辑节点（不依赖 llama-cpp）：
  1. JZL_MiniMax_ShotFormatter    分镜处理中心
  2. JZL_MiniMax_SceneDispatcher  场景元素调度
  3. JZL_MiniMax_VideoDispatcher  视频调度
  4. JZL_MiniMax_AudioDispatcher  音频调度

输出目录: {ComfyUI output}/jzl/{story_name}/{子目录}/
"""

import os
import re
import json

import torch


# ═══════════════════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════════════════

class _FlexibleInputType(dict):
    """任意数量的指定类型输入槽（配合 JS 动态端口）"""
    def __init__(self, type_):
        self.type_ = type_

    def __getitem__(self, key):
        return (self.type_,)

    def __contains__(self, key):
        return True


def _get_output_dir(story_name="", subfolder=""):
    try:
        import folder_paths
        base = folder_paths.get_output_directory()
    except ImportError:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "output")
    safe_name = re.sub(r'[<>:"/\\|?*\s]', '_', (story_name or "untitled").strip())
    out_dir = os.path.join(base, "jzl", safe_name, subfolder)
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


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


def _parse_four_in_one(content):
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


# ═══════════════════════════════════════════════════════════════
#  节点 1: 分镜处理中心
# ═══════════════════════════════════════════════════════════════

class JZL_MiniMax_ShotFormatter:
    """本地文件为主数据通道, 重拍模式直接读选中文件"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "reshoot_mode": ("BOOLEAN", {"default": False, "label_on": "重拍", "label_off": "正常"}),
            },
            "optional": {
                "bus": ("*", {"force_input": True}),
                "shot_text": ("*", {"force_input": True}),
                "_reshoot_path": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("H3提示词", "场景调度指令", "视频调度", "音频调度")
    OUTPUT_IS_LIST = (True, True, True, True)
    FUNCTION = "execute"
    CATEGORY = "JZL/MiniMax"

    @staticmethod
    def _parse_shots(text):
        return [{"raw": b.strip()} for b in re.findall(r'\[SHOT_START\](.*?)\[SHOT_END\]', text or "", re.DOTALL)]

    def execute(self, reshoot_mode, bus=None, shot_text=None, _reshoot_path=None):
        # ── 重拍: 只读选中的本地文件 ──
        if reshoot_mode and _reshoot_path and os.path.isfile(_reshoot_path):
            content = open(_reshoot_path, "r", encoding="utf-8").read()
            h, s, vid, aud = _parse_four_in_one(content)
            h3_list = [h or "[未找到H3提示词]"]
            scene_list = [s or "{}"]
            video_list = [vid or "{}"]
            audio_list = [aud or "{}"]
            return {"ui": {"text": h3_list}, "result": (h3_list, scene_list, video_list, audio_list)}

        # ── 正常模式: 优先从总线读取(无磁盘IO), 回退到磁盘 ──
        try:
            bus_data = json.loads(bus) if isinstance(bus, str) else (bus or {})
        except Exception:
            bus_data = {}

        h3_list = bus_data.get("h3_prompts", [])
        scene_list = bus_data.get("scene_infos", [])
        video_list = bus_data.get("video_infos", [])
        audio_list = bus_data.get("audio_infos", [])

        if not h3_list:
            # 磁盘回退
            story_name = bus_data.get("story_name", "")
            shots = self._parse_shots(shot_text)
            if not shots:
                return {"ui": {"text": [""]}, "result": ([""], ["{}"], ["{}"], ["{}"])}
            shot_count = len(shots)
            h3_list, scene_list, video_list, audio_list = [], [], [], []

            base_dir = _get_output_dir(story_name, "H3提示词")
            latest_dir, _ = _find_latest_version(base_dir)
            pattern = re.compile(r'(\d{3})镜头_.*\.txt')
            shot_files = {}
            if os.path.isdir(latest_dir):
                for f in sorted(os.listdir(latest_dir)):
                    m = pattern.match(f)
                    if m:
                        shot_files[int(m.group(1))] = os.path.join(latest_dir, f)

            for i in range(1, shot_count + 1):
                h3, scene, vid, aud = "[未找到H3提示词]", "{}", "{}", "{}"
                if i in shot_files:
                    content = open(shot_files[i], "r", encoding="utf-8").read()
                    h, s, vv, aa = _parse_four_in_one(content)
                    if h:
                        h3 = h
                    if s:
                        scene = s
                    if vv:
                        vid = vv
                    if aa:
                        aud = aa
                if scene == "{}" and i <= len(shots):
                    block = shots[i - 1]["raw"]
                    chars, bg, props, cam, act = "无", "", "无", "固定", ""
                    for pat_key, pat in [("chars", r'\*\*角色\*\*[：:]\s*(.+?)(?:\n|$)'),
                                         ("bg", r'\*\*场景\*\*[：:]\s*(.+?)(?:\n|$)'),
                                         ("props", r'\*\*道具\*\*[：:]\s*(.+?)(?:\n|$)'),
                                         ("cam", r'\*\*运镜\*\*[：:]\s*(.+?)(?:\n|$)'),
                                         ("act", r'\*\*动作描述\*\*[：:]\s*(.+?)(?:\n|$)')]:
                        m = re.search(pat, block)
                        if m:
                            locals()[pat_key] = m.group(1).strip()
                    scene = json.dumps({"shot": i, "characters": chars or "无", "scene": bg, "props": props or "无"}, ensure_ascii=False)
                    vid = json.dumps({"shot": i, "camera": cam or "固定", "action": act, "video_hint": ""}, ensure_ascii=False)
                    aud = json.dumps({"shot": i, "audio_hint": ""}, ensure_ascii=False)
                h3_list.append(h3)
                scene_list.append(scene)
                video_list.append(vid)
                audio_list.append(aud)

        # 对齐长度
        while len(scene_list) < len(h3_list):
            scene_list.append("{}")
        while len(video_list) < len(h3_list):
            video_list.append("{}")
        while len(audio_list) < len(h3_list):
            audio_list.append("{}")

        return {"ui": {"text": h3_list}, "result": (h3_list, scene_list, video_list, audio_list)}


# ═══════════════════════════════════════════════════════════════
#  节点 2: 场景元素调度（按上游节点名自动分类）
# ═══════════════════════════════════════════════════════════════

class JZL_MiniMax_SceneDispatcher:
    """动态 IMAGE 输入，根据上游节点名称自动分类 角色/背景/道具，分配到 9 个 ref_image 槽位。"""

    _KW_CHARACTER = ["角色", "人物", "主角", "反派", "配角"]
    _KW_BACKGROUND = ["背景", "场景", "环境", "bg"]
    _KW_PROP = ["道具", "物品", "武器", "prop"]

    @staticmethod
    def _classify(name):
        try:
            from .sheding.dispatcher_rules import KW_CHARACTER, KW_BACKGROUND, KW_PROP
        except ImportError:
            KW_CHARACTER = JZL_MiniMax_SceneDispatcher._KW_CHARACTER
            KW_BACKGROUND = JZL_MiniMax_SceneDispatcher._KW_BACKGROUND
            KW_PROP = JZL_MiniMax_SceneDispatcher._KW_PROP
        n = name.lower()
        for kw in KW_CHARACTER:
            if kw.lower() in n:
                return "character"
        for kw in KW_BACKGROUND:
            if kw.lower() in n:
                return "background"
        for kw in KW_PROP:
            if kw.lower() in n:
                return "prop"
        return "character"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"scene_instruction": ("*", {"force_input": True})}, "optional": _FlexibleInputType("IMAGE")}

    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE")
    RETURN_NAMES = ("ref_image_0", "ref_image_1", "ref_image_2", "ref_image_3", "ref_image_4", "ref_image_5", "ref_image_6", "ref_image_7", "ref_image_8")
    FUNCTION = "execute"
    CATEGORY = "JZL/MiniMax"

    def execute(self, scene_instruction, **kwargs):
        needed_chars, needed_bg, needed_props = [], "", []
        try:
            si = json.loads(scene_instruction) if isinstance(scene_instruction, str) else scene_instruction
            if isinstance(si, list) and si:
                s = si[0]
                needed_chars = [c.strip() for c in s.get("characters", "无").replace("、", ",").split(",") if c.strip() and c.strip() != "无"]
                needed_bg = s.get("scene", "").strip()
                needed_props = [p.strip() for p in s.get("props", "无").replace("、", ",").split(",") if p.strip() and p.strip() != "无"]
        except Exception:
            pass

        char_images, bg_images, prop_images = {}, {}, {}
        seen = {}
        for name, tensor in kwargs.items():
            if tensor is None or not isinstance(tensor, torch.Tensor):
                continue
            seen[name] = seen.get(name, -1) + 1
            uname = f"{name}_{seen[name]}" if seen[name] else name
            cat = self._classify(name)
            if cat == "character":
                char_images[uname] = tensor
            elif cat == "background":
                bg_images[uname] = tensor
            else:
                prop_images[uname] = tensor

        empty_img = torch.zeros((1, 64, 64, 3), dtype=torch.float32, device="cpu")
        for t in kwargs.values():
            if isinstance(t, torch.Tensor):
                empty_img = torch.zeros_like(t)
                break

        slots = [empty_img] * 9
        si = 0
        # 背景
        for name in bg_images:
            if si >= 9:
                break
            if not needed_bg or needed_bg in name or name in needed_bg:
                slots[si] = bg_images[name]
                si += 1
                break
        # 角色
        for cn in needed_chars:
            if si >= 9:
                break
            for name in char_images:
                if cn in name or name in cn:
                    slots[si] = char_images[name]
                    si += 1
                    break
        # 道具
        for pn in needed_props:
            if si >= 9:
                break
            for name in prop_images:
                if pn in name or name in pn:
                    slots[si] = prop_images[name]
                    si += 1
                    break
        return tuple(slots)


# ═══════════════════════════════════════════════════════════════
#  节点 3: 视频调度 (动态端口 + 配对音频)
# ═══════════════════════════════════════════════════════════════

class JZL_MiniMax_VideoDispatcher:
    """动态视频端口（IMAGE），接入视频后自动配对一个「上游名（音频）」音频端口。
    交叉输出 3 组 ref_video / ref_video_audio。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"va_instruction": ("*", {"force_input": True})}, "optional": _FlexibleInputType("IMAGE")}

    RETURN_TYPES = ("IMAGE", "*", "IMAGE", "*", "IMAGE", "*")
    RETURN_NAMES = ("ref_video_0", "ref_video_audio_0", "ref_video_1", "ref_video_audio_1", "ref_video_2", "ref_video_audio_2")
    FUNCTION = "execute"
    CATEGORY = "JZL/MiniMax"

    def execute(self, va_instruction, **kwargs):
        needed_action = ""
        try:
            vi = json.loads(va_instruction) if isinstance(va_instruction, str) else va_instruction
            if isinstance(vi, list) and vi:
                needed_action = vi[0].get("action", "").strip()
        except Exception:
            pass

        videos, video_audios = {}, {}
        seen = {}
        for name, value in kwargs.items():
            if value is None:
                continue
            seen[name] = seen.get(name, -1) + 1
            uname = f"{name}_{seen[name]}" if seen[name] else name
            if "（音频）" in name:
                video_audios[uname] = value
            elif isinstance(value, torch.Tensor):
                videos[uname] = value

        empty_img = torch.zeros((1, 64, 64, 3), dtype=torch.float32, device="cpu")
        for t in videos.values():
            if isinstance(t, torch.Tensor):
                empty_img = torch.zeros_like(t)
                break

        vid_slots = [empty_img] * 3
        va_slots = [None] * 3
        vi = 0
        for name in videos:
            if vi >= 3:
                break
            if not needed_action or any(kw in name for kw in needed_action.split() if kw):
                vid_slots[vi] = videos[name]
                vi += 1
        vai = 0
        for name in video_audios:
            if vai >= 3:
                break
            va_slots[vai] = video_audios[name]
            vai += 1
        # 交叉输出: ref_video_0, ref_video_audio_0, ref_video_1, ...
        return (vid_slots[0], va_slots[0], vid_slots[1], va_slots[1], vid_slots[2], va_slots[2])


# ═══════════════════════════════════════════════════════════════
#  节点 4: 音频调度 (动态)
# ═══════════════════════════════════════════════════════════════

class JZL_MiniMax_AudioDispatcher:
    """动态音频接入, 仅接受 AUDIO 类型, 最多 3 条 ref_audio"""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"va_instruction": ("*", {"force_input": True})}, "optional": _FlexibleInputType("AUDIO")}

    RETURN_TYPES = ("*", "*", "*")
    RETURN_NAMES = ("ref_audio_0", "ref_audio_1", "ref_audio_2")
    FUNCTION = "execute"
    CATEGORY = "JZL/MiniMax"

    def execute(self, va_instruction, **kwargs):
        audios = {}
        seen = {}
        for name, value in kwargs.items():
            if value is None:
                continue
            seen[name] = seen.get(name, -1) + 1
            audios[f"{name}_{seen[name]}" if seen[name] else name] = value

        slots = [None] * 3
        ai = 0
        for name in audios:
            if ai >= 3:
                break
            slots[ai] = audios[name]
            ai += 1
        return tuple(slots)
