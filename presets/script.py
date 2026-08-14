"""
MiniMax-H3 剧本与镜头处理器 — System Prompt 零件库
====================================================
节点 JZL_MiniMax_ScriptProcessor 的后台零件库。

故事风格/镜头数量选项在此维护（fallback），正式设定词在 shed/ 目录。
"""

# ═══════════════════════════════════════════════════════════════
#  零件库 2: {Story_Style} — 故事风格
# ═══════════════════════════════════════════════════════════════

STORY_STYLES = {
    "热血战斗": (
        "风格要素: 高张力对抗, 力量碰撞, 速度感, 技能释放的视觉奇观。"
        "色调倾向: 高饱和暖色(红/橙/金), 强烈的明暗对比, 粒子特效密集。"
        "节奏: 快切镜头, 短爆发, 冲击力优先。"
        "角色关系: 正邪对决、师徒传承、同伴羁绊。"
    ),
    "悬疑推理": (
        "风格要素: 线索的视觉暗示, 人物微表情, 环境细节的慢慢揭示, 反转瞬间。"
        "色调倾向: 低饱和冷色(蓝灰/墨绿), 单一光源, 阴影中隐藏信息。"
        "节奏: 缓慢推进, 关键帧停留, 细节点放大。"
        "角色关系: 侦探与嫌疑人、目击者与追踪者。"
    ),
    "温馨日常": (
        "风格要素: 生活中的微小美好, 人与环境的和谐互动, 情感的自然流露。"
        "色调倾向: 暖中性色(奶油/淡木/薄荷绿/天空蓝), 柔和的漫反射光, 金色时刻。"
        "节奏: 舒缓从容, 给情感留白, 环境空镜穿插。"
        "角色关系: 家人、朋友、宠物、邻里。"
    ),
    "奇幻冒险": (
        "风格要素: 宏大世界观, 奇异生物, 魔法效果, 史诗级场景。"
        "色调倾向: 高饱和丰富色盘, 发光粒子, 魔法光芒, 异世界质感。"
        "节奏: 场景跳跃大, 奇观展示与角色反应交替。"
        "角色关系: 勇者与伙伴、冒险小队、跨种族联盟。"
    ),
    "科幻未来": (
        "风格要素: 高科技环境, 全息投影, 赛博格, 空间站/未来城市, AI 交互。"
        "色调倾向: 冷峻金属色(银/铬/深蓝), 霓虹点缀(青/品红), 全息扫描线。"
        "节奏: 科技细节展示, 人机交互, 未来感运镜。"
        "角色关系: 人类与AI、太空探索者、未来市民。"
    ),
    "古风武侠": (
        "风格要素: 中国古典意境, 轻功身法, 剑气内功, 山水场景。"
        "色调倾向: 水墨感(青绿/素白/墨色/朱砂), 留白构图, 飘落花瓣。"
        "节奏: 动静结合, 招式拆解, 意境空镜。"
        "角色关系: 侠客与江湖、师徒传承、正邪对立。"
    ),
    "都市情感": (
        "风格要素: 现代都市生活, 咖啡馆/办公室/街道, 情感细腻互动。"
        "色调倾向: 现实主义色彩, 自然窗光, 城市夜景的暖黄与冷蓝交织。"
        "节奏: 对话聚焦, 反应镜头, 环境氛围渲染。"
        "角色关系: 恋人、同事、老朋友、偶遇的陌生人。"
    ),
    "恐怖惊悚": (
        "风格要素: 心理恐惧, 未知威胁, 空间压迫感, 突如其来的惊吓。"
        "色调倾向: 极暗调, 去饱和, 单光源(手电/烛光), 诡异的色彩偏移。"
        "节奏: 缓慢累积→突然爆发, 荷兰角, 前景遮挡制造不安。"
        "角色关系: 受害者与未知存在、孤立无援的个体。"
    ),
}


# ═══════════════════════════════════════════════════════════════
#  零件库 3: {Shot_Count} — 故事长度选项
# ═══════════════════════════════════════════════════════════════

SHOT_COUNT_OPTIONS = {
    "短篇 (4镜)": 4,
    "中篇 (6镜)": 6,
    "中篇 (9镜)": 9,
    "长篇 (12镜)": 12,
    "长篇 (16镜)": 16,
    "长篇 (20镜)": 20,
    "长篇 (24镜)": 24,
    "长篇 (30镜)": 30,
    "长篇 (36镜)": 36,
    "长篇 (42镜)": 42,
    "长篇 (48镜)": 48,
    "长篇 (56镜)": 56,
}


# ═══════════════════════════════════════════════════════════════
#  V2 融合骨架（剧本与镜头处理器专用）
#  占位符: {Mode_Instruction} {Story_Style} {Shot_Count}
#          {Decompose_Rules} {Reference_Intro} {H3_Shot_Rules} {User_Story}
# ═══════════════════════════════════════════════════════════════

SCRIPT_SKELETON_V2 = '''# Role: 顶级短视频编剧 & MiniMax H3 分镜提示词工程师
你是专业的短视频编剧和 MiniMax H3 视频提示词撰写专家。你的任务分两步：
第一步：把用户故事拆解为恰好 {Shot_Count} 个镜头（每镜 2-6 秒的独立视频片段）。
第二步：为每个镜头写出一条可直接送入 MiniMax H3 模型生成视频的提示词。

## 0. 任务模式
{Mode_Instruction}

## 1. 故事风格
{Story_Style}

## 2. 分镜数量铁律
必须恰好生成 {Shot_Count} 个镜头，不多不少。每个镜头都是独立的一段视频片段。

## 3. 拆解规则
{Decompose_Rules}

{Reference_Intro}
{H3_Shot_Rules}

## 用户故事：
{User_Story}'''


def _build_schedule_rules(lang, enable_scene, enable_props, enable_video, enable_audio):
    """根据 4 个调度开关生成约束文本（注入 H3_Shot_Rules 的 {Schedule_Rules} 占位符）。"""
    if lang == "zh":
        lines = ["### 4.5 调度开关约束（必须遵守）"]
        if enable_scene:
            lines.append("- 场景分类已启用：SCENE_INSTRUCTION 的 scene 字段填写本镜场景，提示词中用 <Picture 1> 引用背景图。")
        else:
            lines.append("- 场景分类已关闭：SCENE_INSTRUCTION 的 scene 字段留空字符串，提示词中不引用背景图、不写背景参考标签。")
        if enable_props:
            lines.append("- 道具分类已启用：SCENE_INSTRUCTION 的 props 字段填写本镜道具，提示词中可引用道具参考图。")
        else:
            lines.append("- 道具分类已关闭：SCENE_INSTRUCTION 的 props 字段填\"无\"，提示词中不引用道具参考图。")
        if enable_video:
            lines.append("- 视频调度已启用：每个镜头输出 ===VIDEO_INSTRUCTION=== 段，提示词中可写 <Video N> 引用参考视频。")
        else:
            lines.append("- 视频调度已关闭：不要输出 ===VIDEO_INSTRUCTION=== 段，提示词中禁止写 <Video N> 标签。")
        if enable_audio:
            lines.append("- 音频调度已启用：每个镜头输出 ===AUDIO_INSTRUCTION=== 段，提示词中可写 <Audio N> 引用参考音频。")
        else:
            lines.append("- 音频调度已关闭：不要输出 ===AUDIO_INSTRUCTION=== 段，提示词中禁止写 <Audio N> 标签。")
    else:
        lines = ["### 4.5 Scheduling Toggle Rules (MUST follow)"]
        if enable_scene:
            lines.append("- Scene classification ENABLED: fill the scene field in SCENE_INSTRUCTION; reference the background with <Picture 1> in the prompt.")
        else:
            lines.append("- Scene classification DISABLED: leave the scene field empty; do NOT reference any background image or background label.")
        if enable_props:
            lines.append("- Prop classification ENABLED: fill the props field in SCENE_INSTRUCTION; may reference prop images in the prompt.")
        else:
            lines.append("- Prop classification DISABLED: set props to \"none\"; do NOT reference prop images.")
        if enable_video:
            lines.append("- Video scheduling ENABLED: output ===VIDEO_INSTRUCTION=== per shot; may use <Video N> in the prompt.")
        else:
            lines.append("- Video scheduling DISABLED: do NOT output ===VIDEO_INSTRUCTION===; do NOT use <Video N> labels.")
        if enable_audio:
            lines.append("- Audio scheduling ENABLED: output ===AUDIO_INSTRUCTION=== per shot; may use <Audio N> in the prompt.")
        else:
            lines.append("- Audio scheduling DISABLED: do NOT output ===AUDIO_INSTRUCTION===; do NOT use <Audio N> labels.")
    return "\n".join(lines)


def build_shot_prompt(
    user_story: str,
    mode: str = "拆解模式 (Decompose)",
    story_style: str = "热血战斗",
    shot_count_label: str = "短篇 (4镜)",
    lang: str = "zh",
    shot_duration: int = 8,
    ref_image_intro: str = "",
    ref_video_intro: str = "",
    ref_audio_intro: str = "",
    enable_scene: bool = True,
    enable_props: bool = True,
    enable_video: bool = True,
    enable_audio: bool = True,
) -> str:
    """剧本与镜头处理器 — 拼装一次成型的 System Prompt（融合拆解 + 六段 Ref2VA 规范）。

    lang: "zh" / "en"；shot_duration: 分镜时长(秒)，约束时间戳范围。
    """
    from ..sheding.mode_instructions import MODE_INSTRUCTIONS as _mi
    from ..sheding.story_styles import STORY_STYLES as _ss
    from ..sheding.decompose_rules import DECOMPOSE_RULES as _dr
    from ..sheding.h3_shot_rules import H3_SHOT_RULES_ZH, H3_SHOT_RULES_EN

    mode_instruction = _mi.get(mode, list(_mi.values())[0] if _mi else "")
    style = _ss.get(story_style, list(_ss.values())[0] if _ss else "")
    shot_count = SHOT_COUNT_OPTIONS.get(shot_count_label, 4)
    shot_duration = max(4, min(15, int(shot_duration or 8)))

    schedule_rules = _build_schedule_rules(lang, enable_scene, enable_props, enable_video, enable_audio)

    # 用 replace 而非 format：rules 文本内含 {视觉描述} 等示意大括号，不能走 format
    rules = (H3_SHOT_RULES_ZH if lang == "zh" else H3_SHOT_RULES_EN)
    rules = rules.replace("{Shot_Count}", str(shot_count))
    rules = rules.replace("{Shot_Duration}", str(shot_duration))
    rules = rules.replace("{Schedule_Rules}", schedule_rules)

    # 参考素材说明（可选）：让 LLM 知道有哪些参考素材、按编号规则写标签
    ref_parts = []
    if ref_image_intro and ref_image_intro.strip():
        ref_parts.append(f"- 参考图片：{ref_image_intro.strip()}")
    if ref_video_intro and ref_video_intro.strip():
        ref_parts.append(f"- 参考视频：{ref_video_intro.strip()}")
    if ref_audio_intro and ref_audio_intro.strip():
        ref_parts.append(f"- 参考音频：{ref_audio_intro.strip()}")
    if ref_parts:
        reference_intro = ("## 3.5 参考素材说明\n" + "\n".join(ref_parts) +
                           "\n\n按下面 4.2 的 subject_definitions 规则，在提示词中为实际用到的参考素材写 <Subject N>/<Picture N>/<Video N>/<Audio N> 标签。")
    else:
        reference_intro = ""

    return SCRIPT_SKELETON_V2.format(
        Mode_Instruction=mode_instruction.format(Shot_Count=shot_count),
        Story_Style=style,
        Shot_Count=shot_count,
        Decompose_Rules=_dr,
        Reference_Intro=reference_intro,
        H3_Shot_Rules=rules,
        User_Story=user_story,
    )
