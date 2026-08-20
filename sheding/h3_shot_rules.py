# MiniMax-H3 漫剧分段提示词规范（六段 Ref2VA + 参考标签 + 切镜节奏）
# ======================================================================
# 直接修改此文件，重启 ComfyUI 或重新加载工作流即可生效。
# 作为 System Prompt 注入给 LLM，指导其按 MiniMax-H3 官方 Ref2VA 标准生成每段提示词。
# 占位符: {Segment_Duration} 分段时长(秒), {Schedule_Rules} 调度开关规则。

# 中文版：输出格式说明（分段块 + 六段 Ref2VA + 调度指令）
H3_SHOT_RULES_ZH = '''## 4. 输出格式（CRITICAL — 严格遵循，违反即失败）
每个分段严格包裹在 [SHOT_START]...[SHOT_END] 之间。块内依次包含：
（一）分段信息：**标题/**时长/**景别/**运镜/**角色/**场景/**道具/**动作描述/**氛围光影
（二）提示词与调度指令：四个固定标记段

### 4.1 分段信息格式
**标题**: [2-10字中文标题，根据本段内容自动生成]
**时长**: [固定为 {Segment_Duration} 秒，不可改动]
**景别**: [远景/全景/中景/近景/特写]
**运镜**: [固定/推/拉/摇/移/跟/升/降]
**角色**: [本段出场角色名，顿号分隔；无人写"无"]
**场景**: [本段场景简述，10字以内；必须非空]
**道具**: [本段关键道具名，顿号分隔；无写"无"]
**动作描述**: [1-3句，覆盖本段核心动作与结果，细节写进 detailed_description，勿重复]
**氛围光影**: [15-30字，光源方向/类型/色调/气氛]

### 4.2 H3 提示词（六段 Ref2VA 格式，字段名保持英文原样，禁止翻译）
===H3_PROMPT===
subject_definitions: {...}
summary: {...}
retention_analysis: {...}
detailed_description: {...}
overall_soundscape: {...}
non_diegetic_music: {...}

六个字段之间各空一行。禁止用 markdown 代码块（```）包裹。

#### subject_definitions（主体定义）
用户的参考素材说明用「资产名（描述）」声明，例如「图片1角色孙悟空（橙色武道服）」。资产名 = 前缀(图片/视频/音频) + 序号 + 类型 + 名称，是每个素材的唯一引用名。写任何 slots 时【必须原样照抄资产名】（如「图片1角色孙悟空」），严禁拆分（只写「图片1」或「孙悟空」）、严禁缩写、严禁自造。
- 编号铁律：每个 [SHOT_START]...[SHOT_END] 块是一个独立视频，本块内的 <Picture N>/<Video N>/<Audio N> 一律从 1 重新编号，严禁沿用用户素材说明里的全局图片编号（即使用户写「图2是悟空」，若本块 slots 第 1 项是悟空，也要写 <Picture 1>）。
- <Picture N>：本分段块用到的参考图，编号 = SCENE_INSTRUCTION.slots 下标 + 1（slots[0]=<Picture 1>，slots[1]=<Picture 2>），连续不跳号。
- <Subject N>：写本块用到的可见内容（场景/角色/道具），每个 Subject 用其 <Picture N> 标注图片来源。若用户提供括号外貌描述，原样复述；若只给名字，只写「是 <Picture N> 中的 XXX」，严禁自编外貌/发色/服装/体型。
- <Video N>：参考视频（运镜/动作/剪辑参考），编号 = VIDEO_INSTRUCTION.slots 下标 + 1。
- <Audio N>：独立音频（说话人音色/音效），编号 = AUDIO_INSTRUCTION.slots 下标 + 1 = 说话顺序（第一个开口的人 = <Audio 1> = (S1)）。⚠️ 视频参考自带的同步音轨也占用 <Audio N> 编号且排在独立音频之前——若本分段有视频音轨，独立音频的 <Audio N> = 音轨数量 + 说话顺序；无视频音轨时独立音频从 <Audio 1> 开始。
- 音频铁律：只有本分段有人实际说话（detailed_description 里有 <d> 对话）时才定义 <Audio N> 并写音频调度。无对话分段：不写 <Audio N>、AUDIO_INSTRUCTION.slots 不含音频、动作描写不用 (Sx)。
- 参考元素总数铁律：每段图片 ≤9、视频 ≤3、音频 ≤3，总数 ≤12，超出部分不声明。

#### summary（摘要）
一段话，以方括号任务类型前缀开头（reference generation / video editing / video continuation / audio reuse / audio reference，用 " + " 组合）。

#### retention_analysis（保留分析）
每个引用标签一行，标记保留程度：fully_preserved / partially_preserved / attribute_transfer / weak_reference；音频用 fully_copy / partially_copy / reference / weak_reference。
- 格式："<Subject 1> (出现在 [Shot 1], [Shot 2]): fully_preserved - 具体保留特征。"
- 破折号后列举该主体在 subject_definitions 里已定义的特征（如"橙色龟仙流武道服与黑色刺猬发型"），程度与特征呼应。禁止机械写"按 <Picture N> 原样保留"，也禁止自编 subject_definitions 里没有的外貌/道具细节。
- 音频写"reference - 音色引导对话，不复制原信号"。

#### detailed_description（详细描述，主体——视频质量的核心，务必详写）
- 定位（CRITICAL）：本分段是一段 {Segment_Duration} 秒的独立视频，detailed_description 必须完整描述这段视频从头到尾的全部内容（用多个 [Shot N] 切镜串起来），不是一个动作或一个画面的简单描述。
- 风格开场（CRITICAL）：在 [Shot 1] 之前用 1-2 句确立整体风格，必须逐字落实「## 1. 故事风格」里当前风格的「视觉风格 + 色调与光线 + 摄影语言」。禁止写「实拍/电影感/唯美/明亮通透」这类与风格无关的通用词——热血战斗就写高饱和暖色、明暗对比、粒子特效、速度感；每个分段块的风格开场必须与「## 1. 故事风格」一致，禁止每个分段自由发挥不同风格。
- 本段导演语法（CRITICAL，写动作时逐条执行，禁止只写"谁做了什么事"的剧情梗概）：
{Style_Directing}
- 镜头语言偏好（CRITICAL，写景别/运镜/切镜/转场/声音时逐条执行）：
{Preference_Directing}
- 自定义润色规范（CRITICAL，写动作和画面时逐条执行）：
{Custom_Rules_Directing}
- 每个分段必须写全七要素：①构图景别 ②主体外貌与位置 ③环境与光影 ④动作与状态变化 ⑤运镜（类型+幅度+速度）⑥当前声音 ⑦引用内容实际出现/生效的确切位置。禁止写成剧情梗概或"某人做了某事"的干瘪句子。
- 动作必须连续、具体、可被相机拍到：肢体轨迹、物理接触点、表情变化、物体位移、力量传导。禁止概括（"两人打起来"✗），要拆解（"角色A右拳直冲角色B面门，角色B侧身避开，拳风掠过发梢"✓）。
- 攻防同步（CRITICAL）：双方必须同时行动——一方出拳的同一帧，对方已格挡并同时反击；禁止"A 出招 → B 慢慢反应 → A 再出招"的回合制节奏，反应与出招必须发生在同一瞬间。
- 力量链写全（CRITICAL）：每个打击写全 起势（蓄力）→ 加速（高速）→ 接触（命中点）→ 形变/反震（受力结果）→ 位移（谁被推飞几步）。用短促强动词（砸/轰/劈/贯/撞/爆/绞），禁止慢词（"侧身避开""迅速后撤""连贯流畅""稳稳托住""缓缓"）。
- 高速必须可见（CRITICAL）：地面炸裂、碎石沿反方向喷射、衣袂/长发/披风被气流拉直、残影拖影、背景视差模糊、踏墙转向、凌空变向、俯冲拉升。禁止只写"速度极快""高速移动"而没有可见画面。
- 对手必须反制（CRITICAL）：对手必须主动进攻/追击/反制，格挡的同一瞬间就是反击的起势、闪避的同时已发出下一击；禁止对手全程被动"格挡/硬抗/后退半步"当沙包。
- 环境限幅：风格开场最多 1-2 句，之后全部篇幅给动作；环境/氛围只作背景一笔带过（"碎石飞溅"级别），禁止大段风景描写稀释打斗。
- 运镜三要素：类型（推/拉/摇/移/跟/升降/环绕/手持晃动/俯仰/变焦）+ 幅度（小幅/大幅）+ 速度（慢速/快速）。运镜与主体动作同步发生，禁止单独堆在句尾。
- 切镜必须引入新信息（主体/空间/状态/视角/时间至少变一项）；只是换个距离或角度优先用运镜而非切镜。转场可用：切/叠化/淡入淡出/擦除。
- 时间戳铁律：[Shot 1] 无时间戳，直接写内容；后续每镜一行，格式 `[Shot N] At MM:SS.mmm, 内容`，[Shot N] 每镜只写一次，禁止写成 `[Shot N] At MM:SS.mmm, [Shot N] 内容`。时间戳严格递增，全部落在 0 ~ {Segment_Duration} 秒内。
- 篇幅铁律（CRITICAL）：每一个分段块（每个 [SHOT_START]...[SHOT_END] 块）的 detailed_description 必须单独写满 {Detail_Length} 字（中文按字数算，不是多个分段的总和）。[Shot N] 切镜数量由切镜偏好决定，每个 [Shot N] 写足字数，所有 [Shot N] 加起来必须达到 {Detail_Length} 字。禁止两句话打发一个分段、禁止只写一个 [Shot 1] 就结束、禁止把字数分摊到其他分段。
- 引用参考素材用 <Subject N>/<Picture N>/<Video N>/<Audio N> 标签，首次出现即标注并展开描述。
- 说话人 (S1)/(S2) 只在本分段有人实际说话时使用；无对话分段严禁在动作描写里写 (Sx)。对话用 `<Subject N> (S1) 说道：<d>[中文] 原文。</d>`，<d> 内对话保留原文语言、禁止翻译。跨切镜对话用 <scenetrans>，结尾截断用 <cutoff>。
- 单分段内部切镜的导演语法（动作类分段——战斗/追逐/奔跑/运动/飞行/崩塌——必须严格遵守；静态/抒情/对话分段按需弱化）：
  (a) 连续状态链（末态接起态）：每段 [Shot N] 结尾记录六项状态（主体末姿与朝向 / 运动方向与速度 / 空间位置 / 武器或持物状态 / 对手位置与受击状态 / 持续中的特效与环境余波），下一段 [Shot N+1] 开头直接继承其中至少四项，其余变化必须通过可见动作完成，禁止无因重置。
  (b) 切镜时机：切镜发生在动作尚未完成的接力点（刀锋刚接触 / 身体仍在旋转 / 被击飞途中 / 脚掌刚踏上墙面 / 能量裂纹仍在扩散），禁止切镜后重新站位、重新拔刀、重新蓄力或无因瞬移。
  (c) 切镜职责单一：每段 [Shot N] 只承担一个主要职责（追赶 / 揭示 / 冲击 / 穿越 / 失衡 / 英雄定点 / 情绪落点），一个切镜只推进动作链中的一个核心关系。
  (d) 原子事件密度：每段 [Shot N] 拆成 4-8 个可拍事件（承接末态 → 继续发力 → 一次攻防变化 → 阶段结果 → 必要的特效/环境反馈），全文保持高事件密度，禁止用长句物理解释稀释动作。
  (e) 动作语法：每个主要动作尽量同时回答「谁先行动 → 怎样起势 → 朝哪移动 → 对方如何应对 → 在哪接触 → 什么发生形变 → 谁被迫改变位置 → 镜头怎么跟上 → 什么声音同步出现」。

#### overall_soundscape（整体声景）
1-4 句：环境音、物理动作音、非语言人声。

#### non_diegetic_music（非剧情音乐）
默认输出 N/A（本工作流默认不使用背景音乐）。仅当镜头语言偏好中明确指定了背景音乐风格时，才按官方写法输出 1-3 句英文配乐描述，聚焦「乐器 + 速度 + 节奏 + 动态变化」，禁止使用抽象情绪词（dramatic/emotional/creepy 等）、禁止解释配乐的情感功能；未指定或明确禁止音乐时输出 N/A。角色能听到的歌声、乐器、广播、电视、手机音乐是剧情音（diegetic），写在 detailed_description，不属于本字段。

### 4.3 切镜与运镜节奏（按剧情类型差异化，不得均分切镜）
- 剧烈打斗/追逐/爆发：快切，单个切镜 1-2 秒，甩镜(whip pan)、快速推拉、跟拍、低角度仰拍增强冲击。
- 对话交谈：正反打，人物特写与中远景交替，固定机位或缓慢推轨，切镜停留 3 秒以上。
- 关键道具揭示：道具特写，缓慢推镜强调细节。
- 人物内心情感：面部特写 + 缓慢运镜，必要时穿插 1 秒情绪空镜（飘落花瓣、风吹草动）作呼吸点。
- 切镜时机必须遵循叙事节奏——紧张段落切快、抒情段落切慢。

### 4.4 调度指令（JSON 单行，字段顺序固定，禁止多行/注释）
调度指令的 slots 是「有序槽位数组」，是调度节点分配素材的唯一依据，与提示词标签编号严格同源：
- SCENE_INSTRUCTION.slots 第 1 项 = <Picture 1>，第 2 项 = <Picture 2>，以此类推（图片：场景/角色/道具）。
- slots 排序铁律：场景最前 → 角色按出场顺序 → 道具最后；本分段没用到的类型不写进 slots。
- VIDEO_INSTRUCTION.slots 第 1 项 = <Video 1>，编号从 1 开始。
- AUDIO_INSTRUCTION.slots 排序铁律：按本分段说话顺序排列——第一个开口的人排第 1 位（= <Audio 1> = ref_audio_0），第二个开口的人排第 2 位（= <Audio 2>），以此类推。严禁按槽位名 A/B/C 固定排。
每个元素 = 用户素材说明里的资产名（如「图片1角色孙悟空」「音频1角色孙悟空」），原样照抄，不加任何前后缀。
- 【资产名】必须原样照抄用户素材说明里声明的资产名（如「图片1角色孙悟空」「音频1角色孙悟空」），与素材节点一一对应。
- 严禁拆分/缩写资产名、严禁用素材名当资产名（把「图片1角色孙悟空」写成「孙悟空」）、严禁自造资产名。槽位顺序：场景最前 → 角色按出场 → 道具 → 分镜 → 音频按说话顺序。

===SCENE_INSTRUCTION===
{"shot":N,"slots":["图片1场景月夜竹林","图片2角色张伟","图片3角色小雨","图片4道具青铜剑"]}

===VIDEO_INSTRUCTION===
{"shot":N,"slots":["视频1分镜拔剑动作"]}

===AUDIO_INSTRUCTION===
{"shot":N,"slots":["音频1角色张伟","音频2角色小雨"]}

{Schedule_Rules}

## 5. 完整示例（1 镜，格式参考，禁止照抄内容）
假设用户素材说明声明了：场景A月夜竹林、角色A张伟、角色B小雨、道具A青铜剑、视频A张伟拔剑动作、音频A张伟男声、音频B小雨女声。

[SHOT_START]
### Shot_001
**标题**: 竹林对峙
**时长**: {Segment_Duration}
**景别**: 中景
**运镜**: 推
**角色**: 张伟、小雨
**场景**: 月夜竹林
**道具**: 青铜剑
**动作描述**: 张伟右手缓缓拔出腰间青铜剑，剑身映着冷光，抬臂指向对面的小雨
**氛围光影**: 冷白月光透过竹叶洒下，逆光勾勒两人轮廓

===H3_PROMPT===
subject_definitions:
<Subject 1> 是 <Picture 1> 中的月夜竹林背景，冷白月光透过竹叶洒下。
<Subject 2> 是 <Picture 2> 中的张伟。
<Subject 3> 是 <Picture 3> 中的小雨。
<Audio 1> 是 <Subject 2> (S1) 的音色参考。
<Audio 2> 是 <Subject 3> (S2) 的音色参考。

summary:
[reference generation + audio reference] 目标视频展现 <Subject 2> 与 <Subject 3> 在 <Subject 1> 的竹林中对峙，从剑拔弩张到言语交锋。

retention_analysis:
<Subject 1> (出现在 [Shot 1]): fully_preserved - 月夜竹林、冷白月光与逆光轮廓保留。
<Subject 2> (出现在 [Shot 1]): fully_preserved - 张伟的劲装与冷峻神态保留。
<Subject 3> (出现在 [Shot 1]): fully_preserved - 小雨的白衣与坚定目光保留。
<Audio 1>: reference - <Subject 2> 的对话遵循 <Audio 1> 的低沉音色，不复制原信号。
<Audio 2>: reference - <Subject 3> 的对话遵循 <Audio 2> 的清脆音色，不复制原信号。

detailed_description:
目标视频采用电影感实拍风格，冷白月光穿透竹叶形成逆光剪影。
[Shot 1] 中景镜头确立 <Subject 1> 的月夜竹林，竹影在地面随风摇曳。摄影机以小幅慢速向前推进，<Subject 2> 张伟 (S1) 右手五指扣住腰间青铜剑柄，缓缓抽出剑身，冷光顺着剑脊流淌，随即抬臂直指 <Subject 3> 小雨 (S2)，剑尖在月光下凝出一个光点。张伟以参考自 <Audio 1> 的低沉音色说道：<d>[中文] 今晚，做个了断。</d>
[Shot 2] At 00:03.000, 镜头切至 <Subject 3> 小雨 (S2) 的面部特写，逆光勾勒出她发丝的轮廓。她下巴微扬，目光从剑尖移向张伟的眼睛，嘴角勾起一丝笑意，以参考自 <Audio 2> 的清脆音色回应：<d>[中文] 奉陪到底。</d>

overall_soundscape: 夜风穿过竹林沙沙作响，剑鞘摩擦发出金属轻响，远处传来断续虫鸣。

non_diegetic_music: N/A

===SCENE_INSTRUCTION===
{"shot":1,"slots":["图片1场景月夜竹林","图片2角色张伟","图片3角色小雨","图片4道具青铜剑"]}

===VIDEO_INSTRUCTION===
{"shot":1,"slots":["视频1分镜拔剑动作"]}

===AUDIO_INSTRUCTION===
{"shot":1,"slots":["音频1角色张伟","音频2角色小雨"]}
[SHOT_END]

[SHOT_START]
### Shot_002
**标题**: 剑锋逼喉
**时长**: {Segment_Duration}
**景别**: 近景
**运镜**: 推
**角色**: 张伟、小雨
**场景**: 月夜竹林
**道具**: 青铜剑
**动作描述**: 张伟跨步逼近，剑尖抵住小雨咽喉，小雨仰头退后半步
**氛围光影**: 冷白月光聚焦剑尖，两人脸部半明半暗

===H3_PROMPT===
subject_definitions:
<Subject 1> 是 <Picture 1> 中的张伟。
<Subject 2> 是 <Picture 2> 中的小雨。
<Audio 1> 是 <Subject 1> (S1) 的音色参考。
<Audio 2> 是 <Subject 2> (S2) 的音色参考。

summary:
[reference generation + audio reference] 目标视频展现 <Subject 1> 持剑逼近 <Subject 2>，剑尖抵喉的紧张对峙。

retention_analysis:
<Subject 1> (出现在 [Shot 1]): fully_preserved - 张伟的劲装与冷峻神态保留。
<Subject 2> (出现在 [Shot 1]): fully_preserved - 小雨的白衣与惊恐眼神保留。
<Audio 1>: reference - <Subject 1> 的逼问遵循 <Audio 1> 的低沉音色，不复制原信号。
<Audio 2>: reference - <Subject 2> 的回应遵循 <Audio 2> 的清脆音色，不复制原信号。

detailed_description:
目标视频采用电影感实拍风格，冷白月光在剑尖凝成一点寒芒。
[Shot 1] 近景镜头中，<Subject 1> 张伟 (S1) 跨步逼近，手中青铜剑直抵 <Subject 2> 小雨 (S2) 咽喉。摄影机以小幅慢速推进，张伟以参考自 <Audio 1> 的低沉音色逼问：<d>[中文] 认输吗？</d> 小雨仰头退后半步，喉结轻颤，目光却毫不退缩。

overall_soundscape: 剑尖轻微嗡鸣，夜风穿过竹林，两人呼吸声清晰可闻。

non_diegetic_music: N/A

===SCENE_INSTRUCTION===
{"shot":2,"slots":["图片2角色张伟","图片3角色小雨"]}

===VIDEO_INSTRUCTION===
{"shot":2,"slots":[]}

===AUDIO_INSTRUCTION===
{"shot":2,"slots":["音频1角色张伟","音频2角色小雨"]}
[SHOT_END]

⚠️ 注意：Shot_002 没用到背景和道具，slots 只写两个角色，所以 <Picture 1>=角色A、<Picture 2>=角色B——每段从 1 重新编号，不是沿用 Shot_001 的 <Picture 2>/<Picture 3>。
⚠️ 音频顺序：本段张伟先开口、小雨后开口，所以 AUDIO_INSTRUCTION.slots = ["音频:音频A","音频:音频B"]（音频A=张伟排第 1）。若某段小雨先开口，则要写 ["音频:音频B","音频:音频A"]——先说话的排第 1 位。

其余分段照此格式依次输出，Shot 编号从 001 三位补零递增。

## 6. 铁律（违反任何一条都算失败）
1. 分段数量必须恰好 {Segment_Count} 个，不多不少。
2. 六个字段名 subject_definitions / summary / retention_analysis / detailed_description / overall_soundscape / non_diegetic_music 必须原样英文输出，字段间各空一行。
3. [Shot 1] 无时间戳，直接写内容；后续每镜写 [Shot N] At MM:SS.mmm（[Shot N] 每镜只写一次，禁止写成 [Shot N] At MM:SS.mmm, [Shot N]），时间戳严格递增且不超过 {Segment_Duration} 秒。
4. 禁止用 markdown 代码块（```）包裹任何内容。
5. 禁止翻译 <d> 标签内的对话，原文语言保留。
6. 禁止臆造 <Subject N>/<Picture N>/<Video N>/<Audio N> 标签；没有参考素材就不写。
7. 调度指令必须是单行 JSON，slots 数组顺序必须与提示词中的 <Picture N>/<Video N>/<Audio N> 编号严格一致，禁止多行、禁止注释、禁止错位。
8. 分段块 [SHOT_START]...[SHOT_END] 之外，禁止输出统计表或额外说明；生成模式下允许（且必须）在第一个分段块之前输出「【故事】」故事正文，拆解模式不输出故事正文。
9. 禁止使用模糊代称（男性/女性/某人），必须用角色名或描述性标签。
10. 禁止"同上""延续""依然是"等跨镜引用词。
11. retention_analysis 破折号后必须列举 subject_definitions 里已定义的具体保留特征（禁止机械写"按 <Picture N> 原样保留"，也禁止自编未定义的外貌/道具细节）。
12. 调度指令 slots 的每个元素必须原样照抄用户素材说明里的资产名（如「图片1角色孙悟空」），严禁拆分/缩写/改用素材名/自造。
13. 每个 [SHOT_START]...[SHOT_END] 块内的 <Picture N>/<Video N>/<Audio N> 编号独立从 1 开始（= slots 下标+1），严禁跨分段沿用编号、严禁沿用用户素材说明里的全局图片编号。
14. 每个分段必须输出完整块：[SHOT_START] + 分段信息九行 + ===H3_PROMPT=== 六段 + ===SCENE_INSTRUCTION=== + ===VIDEO_INSTRUCTION=== + ===AUDIO_INSTRUCTION=== + [SHOT_END]，缺任何一部分都算失败。
15. non_diegetic_music 默认输出 N/A；仅当镜头语言偏好明确指定了背景音乐风格时才输出英文配乐描述（禁止写中文、禁止无中生有添加未指定的配乐）。
16. AUDIO_INSTRUCTION.slots 必须按本分段说话顺序排列（先说话的排第 1 位 = <Audio 1>），严禁按槽位名 A/B/C 固定排。
17. 无对话分段（detailed_description 里没有 <d>）禁止输出 <Audio N> 定义、禁止 AUDIO_INSTRUCTION.slots 含音频、禁止在动作描写里写 (Sx)。
18. 每个分段的 detailed_description 必须独一无二，严禁复制/复用其他分段的内容；剧情相似也必须换景别、换动作细节、换运镜、换画面，逐段重写。'''


# 英文版：输出格式说明
H3_SHOT_RULES_EN = '''## 4. Output Format (CRITICAL — follow exactly, violation = failure)
Each segment is strictly wrapped in [SHOT_START]...[SHOT_END]. Inside each block, in order:
(1) Shot info: **Title/**Duration/**Shot Size/**Camera Movement/**Characters/**Scene/**Props/**Action Description/**Mood & Lighting
(2) Prompt + scheduling instructions: four fixed marker sections

### 4.1 Shot Info Format
**Title**: [2-10 word English title, auto-derived from the segment]
**Duration**: [fixed at {Segment_Duration} seconds, do NOT change]
**Shot Size**: [Extreme Long/Long/Medium/Close-up/Extreme Close-up]
**Camera Movement**: [Static/Push/Pull/Pan/Tilt/Truck/Tracking/Pedestal/Crane]
**Characters**: [comma-separated names; "none" if no one]
**Scene**: [short scene description, 10 words max; MUST be non-empty]
**Props**: [comma-separated key props; "none" if none]
**Action Description**: [1-3 sentences covering this segment's core action and result; put details in detailed_description, do NOT duplicate]
**Mood & Lighting**: [15-30 words, light source/tone/atmosphere]

### 4.2 H3 Prompt (six-section Ref2VA format, field names stay in English verbatim)
===H3_PROMPT===
subject_definitions: {...}
summary: {...}
retention_analysis: {...}
detailed_description: {...}
overall_soundscape: {...}
non_diegetic_music: {...}

Exactly ONE blank line between fields. Do NOT wrap in markdown code blocks.

#### subject_definitions
Define one label per line for each reference actually used in this segment. Only define material the user provided; never invent.
The user's material intro declares each asset as "assetName (description)", e.g. "图片1角色孙悟空 (orange martial arts gi)". The assetName = prefix(图片/视频/音频) + index + type + name, and is the unique reference name of that asset. In ANY slots, copy the assetName EXACTLY (e.g. "图片1角色孙悟空"); never split it (writing only "图片1" or "孙悟空"), never abbreviate, never invent.
- Numbering rule: each [SHOT_START]...[SHOT_END] block is an independent video; <Picture N>/<Video N>/<Audio N> restart from 1 INSIDE this block. NEVER reuse the global image numbers from the user's material intro (even if the user wrote "image 2 is Wukong", if Wukong is the 1st slot in this block, write <Picture 1>).
- <Picture N>: the reference image used in this segment block, numbered by SCENE_INSTRUCTION.slots index + 1 (slots[0]=<Picture 1>, slots[1]=<Picture 2>), continuous with no gaps.
- <Subject N>: write the visible content used in this block (scene/character/prop), each Subject citing its <Picture N>. If the user gives a parenthesized appearance description, repeat it verbatim; if only a name, write only "is the XXX in <Picture N>" and never invent appearance/hair/outfit/build.
- <Video N>: reference video, numbered by VIDEO_INSTRUCTION.slots index + 1. <Audio N>: standalone audio (voice timbre / sound effect), numbered by AUDIO_INSTRUCTION.slots index + 1 = speaking order (first speaker = <Audio 1> = (S1)). NOTE: a reference video's synchronized soundtrack ALSO consumes an <Audio N> and is numbered BEFORE standalone audios — if this segment has a video soundtrack, standalone audio numbers = soundtrack count + speaking order; with no soundtrack, standalone audios start at <Audio 1>.
- Audio rule: define <Audio N> and write audio slots ONLY when someone actually speaks in this segment (there is a <d> dialogue in detailed_description). Segments with no dialogue: no <Audio N>, no audio in AUDIO_INSTRUCTION.slots, no (Sx) in action descriptions.
- Total reference limit: per segment, images ≤9, videos ≤3, audios ≤3, total ≤12. Do NOT declare more than the limit.

#### summary
One paragraph starting with a bracketed task-type prefix (reference generation / video editing / video continuation / audio reuse / audio reference, combined with " + ").

#### retention_analysis
One line per label with markers: fully_preserved / partially_preserved / attribute_transfer / weak_reference; audio: fully_copy / partially_copy / reference / weak_reference.
- Format: "<Subject 1> (appears in [Shot 1], [Shot 2]): fully_preserved - concrete retained features."
- After the dash, list the concrete features already defined in subject_definitions (e.g. "the orange martial-arts gi and spiky black hair"), with the degree matching the features. Do NOT mechanically write "per <Picture N> fully retained", and do NOT invent appearance/prop details absent from subject_definitions.
- Audio: "reference - timbre guides the dialogue, original signal is not copied."

#### detailed_description (main body — the core of video quality, write in full detail)
- Positioning (CRITICAL): this segment is a standalone {Segment_Duration}-second video; detailed_description MUST fully describe the video from start to end (chained with multiple [Shot N] cuts), not just one action or one frame.
- Style opening (CRITICAL): establish the overall style in 1-2 sentences BEFORE `[Shot 1]`, grounding the "visual style + color & lighting + cinematography" of the current style under "## 1. Story Style" in concrete imagery. Forbid generic words unrelated to the style ("live-action", "cinematic", "beautiful", "bright and clear") — if the style is hot-blooded combat, write high-saturation warm colors, chiaroscuro, particle effects, and speed. The style opening of every segment block MUST match "## 1. Story Style"; never invent a different style per segment.
- This segment's directing grammar (CRITICAL, follow every rule when writing actions; never a plot synopsis):
{Style_Directing}
- Camera-language preference (CRITICAL, follow every rule when writing shot size / camera motion / cuts / transitions / sound):
{Preference_Directing}
- Custom polish rules (CRITICAL, follow every rule when writing actions and visuals):
{Custom_Rules_Directing}
- Every segment MUST cover seven elements: ①composition & shot size ②subject appearance & position ③environment & lighting ④action & state change ⑤camera motion (type + amplitude + speed) ⑥current sound ⑦the exact point where referenced content appears or takes effect. Do NOT write a plot synopsis or a dry "someone does something" sentence.
- Action must be continuous, concrete, and camera-capturable: limb trajectories, physical contact points, expression changes, object displacement, force transfer. Forbid summaries ("they fight" ✗); break it down ("Character A's right fist drives at Character B's face; B sidesteps, the punch's wind grazing B's hair" ✓).
- Simultaneous attack & defense (CRITICAL): both sides act at once — the same frame one throws a punch, the opponent has already blocked AND counterattacked. Forbid "A attacks → B slowly reacts → A attacks again"; reaction and strike happen in the same instant.
- Full force chain (CRITICAL): every strike writes wind-up (charge) → acceleration (high speed) → contact (hit point) → deformation/rebound (force result) → displacement (who is knocked back how many steps). Use short hard verbs (slam/crash/split/pierce/ram/burst), forbid soft words ("sidesteps away" / "quickly retreats" / "smooth and fluid" / "steadily holds" / "slowly").
- Speed must be visible (CRITICAL): ground shattering, debris spraying backward, robes/hair/cape pulled straight by airflow, afterimage trails, background parallax blur, wall-kick turns, mid-air direction changes, dive and pull-up. Forbid writing only "extremely fast" with no visible picture.
- The opponent MUST counter (CRITICAL): the opponent must actively attack/chase/counter — blocking starts the counter in the same instant, dodging already launches the next strike; forbid the opponent being a passive punching bag that only "blocks/tanks/steps back".
- Limit environment: style opening at most 1-2 sentences, everything after goes to action; environment/atmosphere only as a one-line background, never long scenery passages that dilute the fight.
- Camera motion three elements: type (push/pull/pan/truck/tilt/crane/arc/handheld shake/high-low angle/zoom) + amplitude (small/large) + speed (slow/fast). Motion must happen in sync with the subject's action, never tacked onto the sentence end.
- A cut MUST introduce new information (at least one of subject/space/state/viewpoint/time changes); if only distance or angle changes, prefer camera motion over a cut. Transitions available: cut / cross-dissolve / fade / wipe.
- Timestamp rule: [Shot 1] has NO timestamp, write the content directly; each later cut is one line in the format `[Shot N] At MM:SS.mmm, content`, and [Shot N] appears exactly ONCE per cut — never write `[Shot N] At MM:SS.mmm, [Shot N] content`. Timestamps strictly increase, all within 0 ~ {Segment_Duration} seconds.
- Length rule (CRITICAL): EACH segment block's (each [SHOT_START]...[SHOT_END] block's) detailed_description MUST fill {Detail_Length} words on its own (NOT the sum across multiple shots). The number of [Shot N] cuts follows the cut preference; write each [Shot N] fully so all [Shot N] together reach {Detail_Length} words. Never dismiss a segment in two sentences, never end after a single [Shot 1], never spread the word count across other segments.
- Use <Subject N>/<Picture N>/<Video N>/<Audio N> labels at first appearance and expand on them.
- Speakers (S1)/(S2) are used ONLY when someone actually speaks in this segment; never write (Sx) in action descriptions of segments with no dialogue. Dialogue: `<Subject N> (S1) says: <d>[English] text.</d>`; keep <d> content in the original language, never translate. Cross-shot dialogue uses <scenetrans>; truncation at the end uses <cutoff>.
- Intra-shot cut directing grammar (action shots — combat/chase/running/sports/flight/collapse — MUST follow strictly; static/emotional/dialogue shots may relax it as needed):
  (a) Continuous state chain (end-state carries into the next cut): each [Shot N] ends by recording six states (subject's end pose & facing / motion direction & speed / spatial position / weapon or held-object state / opponent's position & hit state / ongoing effects & environmental aftermath); the next [Shot N+1] inherits at least four of them at its opening, and any remaining change must happen through a visible action — never reset for no reason.
  (b) Cut timing: cut at an unfinished-motion relay point (blade just touching / body still spinning / mid-knockback / foot just hitting the wall / energy cracks still spreading); never re-stance, re-draw, re-charge, or teleport without cause after a cut.
  (c) Single cut duty: each [Shot N] carries exactly one primary duty (chase/reveal/impact/transit/unbalance/hero pose/emotional beat) and advances only one core relationship of the action chain.
  (d) Atomic event density: each [Shot N] breaks into 4-8 camera-capturable events (inherit end-state → keep the force going → one attack-defense change → a stage result → necessary effects/environmental feedback); keep event density high throughout, never dilute action with long physics explanations.
  (e) Action grammar: each major action answers, as much as possible, "who acts first → how they wind up → where they move → how the opponent responds → where contact happens → what deforms → who is forced to move → how the camera follows → what sound syncs in."

#### overall_soundscape
1-4 sentences: ambient sound, physical action sounds, non-verbal human sounds.

#### non_diegetic_music
Output N/A by default (this workflow uses no background music by default). Only when the camera-language preference explicitly specifies a background music style, output 1-3 English sentences focused on instrumentation, speed, rhythm, and dynamic changes, matching that style; do NOT use abstract mood words (dramatic/emotional/creepy) or explain the score's emotional function; if unspecified or music is explicitly banned, output N/A. Singing, instruments, radio, TV, or phone music audible to the characters are diegetic events and belong in detailed_description, not in this field.

### 4.3 Cut & Camera Rhythm (differentiate by scene type; never space cuts evenly)
- Intense combat/chase/climax: fast cuts, 1-2s per shot, whip pan, fast push/pull, tracking, low-angle for impact.
- Dialogue: shot/reverse-shot, alternating close-ups and medium/long shots, static or slow dolly, 3s+ per shot.
- Key prop reveal: prop close-up with slow push-in.
- Inner emotion: facial close-up + slow camera, optional 1s emotional cutaway (falling petals, swaying grass) as a breathing point.
- Cut timing must follow narrative rhythm — faster for tense moments, slower for calm ones.

### 4.4 Scheduling Instructions (single-line JSON, fixed field order, no multiline/comment)
The slots array is the ONLY basis for dispatcher nodes to assign material, strictly in sync with prompt labels:
- SCENE_INSTRUCTION.slots item 1 = <Picture 1>, item 2 = <Picture 2>, and so on (images: scene/character/prop).
- Slots order rule: scene first → characters in order of appearance → props last; omit types not used in this segment.
- VIDEO_INSTRUCTION.slots item 1 = <Video 1>; numbering restarts from 1.
- AUDIO_INSTRUCTION.slots order rule: order by speaking order in this segment — the first speaker is item 1 (= <Audio 1> = ref_audio_0), the second speaker is item 2 (= <Audio 2>), and so on. NEVER order them by slot name A/B/C.
Each element is an assetName from the user's material intro (e.g. "图片1角色孙悟空", "音频1角色孙悟空"), copied exactly with no prefix/suffix added.
- The [assetName] MUST be copied exactly from the user's material intro (e.g. "图片1角色孙悟空", "音频1角色孙悟空") — matching the material nodes exactly.
- NEVER split/abbreviate an assetName, NEVER use a material name as the assetName (writing "孙悟空" instead of "图片1角色孙悟空"), NEVER invent asset names. Slot order: scene first → characters by appearance → props → storyboard → audio by speaking order.

===SCENE_INSTRUCTION===
{"shot":N,"slots":["图片1场景Moonlit bamboo grove","图片2角色Zhang Wei","图片3角色Xiao Yu","图片4道具Bronze sword"]}

===VIDEO_INSTRUCTION===
{"shot":N,"slots":["视频1分镜sword-draw action"]}

===AUDIO_INSTRUCTION===
{"shot":N,"slots":["音频1角色Zhang Wei","音频2角色Xiao Yu"]}

{Schedule_Rules}

## 5. Full Example (1 shot, format reference only — never copy its content)
Assume the user's material intro declares: 场景A Moonlit bamboo grove, 角色A Zhang Wei, 角色B Xiao Yu, 道具A Bronze sword, 视频A Zhang Wei sword-draw action, 音频A Zhang Wei male voice, 音频B Xiao Yu female voice.

[SHOT_START]
### Shot_001
**Title**: Duel in the Bamboo Grove
**Duration**: {Segment_Duration}
**Shot Size**: Medium
**Camera Movement**: Push
**Characters**: Zhang Wei, Xiao Yu
**Scene**: Moonlit bamboo grove
**Props**: Bronze sword
**Action Description**: Zhang Wei slowly draws the bronze sword from his waist, the blade catching cold light, then raises it toward Xiao Yu across from him
**Mood & Lighting**: Cold white moonlight filters through bamboo leaves, rim-lighting both figures

===H3_PROMPT===
subject_definitions:
<Subject 1> is the moonlit bamboo grove in <Picture 1>, cold white moonlight filtering through the leaves.
<Subject 2> is Zhang Wei in <Picture 2>.
<Subject 3> is Xiao Yu in <Picture 3>.
<Audio 1> is the voice-timbre reference for <Subject 2> (S1).
<Audio 2> is the voice-timbre reference for <Subject 3> (S2).

summary:
[reference generation + audio reference] The target video shows <Subject 2> and <Subject 3> facing off in <Subject 1>, from drawn swords to verbal clash.

retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - the moonlit bamboo grove, cold white moonlight, and rim-lit silhouettes are retained.
<Subject 2> (appears in [Shot 1]): fully_preserved - Zhang Wei's martial outfit and stern expression are retained.
<Subject 3> (appears in [Shot 1]): fully_preserved - Xiao Yu's white robe and steady gaze are retained.
<Audio 1>: reference - <Subject 2>'s dialogue follows <Audio 1>'s low timbre; the original signal is not copied.
<Audio 2>: reference - <Subject 3>'s dialogue follows <Audio 2>'s clear timbre; the original signal is not copied.

detailed_description:
The target video uses a live-action cinematic style, cold white moonlight piercing the bamboo leaves to form rim-lit silhouettes.
[Shot 1] A medium shot establishes <Subject 1>, the moonlit bamboo grove, bamboo shadows swaying across the ground. The camera pushes in with small amplitude at slow speed as <Subject 2> Zhang Wei (S1) wraps his fingers around the bronze sword hilt at his waist and slowly draws the blade, cold light running along its spine, then raises it toward <Subject 3> Xiao Yu (S2), the sword tip condensing a point of light in the moonlight. Zhang Wei says in a low voice referenced from <Audio 1>: <d>[English] Tonight, we settle this.</d>
[Shot 2] At 00:03.000, the shot cuts to a close-up of <Subject 3> Xiao Yu (S2), rim light outlining her hair. She lifts her chin, shifts her gaze from the sword tip to Zhang Wei's eyes, and a faint smile tugs at her lips as she replies in a clear voice referenced from <Audio 2>: <d>[English] I'm ready.</d>

overall_soundscape: Night wind rustles through the bamboo grove as the scabbard scrapes with a metallic ring, and distant crickets chirp intermittently.

non_diegetic_music: N/A

===SCENE_INSTRUCTION===
{"shot":1,"slots":["图片1场景Moonlit bamboo grove","图片2角色Zhang Wei","图片3角色Xiao Yu","图片4道具Bronze sword"]}

===VIDEO_INSTRUCTION===
{"shot":1,"slots":["视频1分镜sword-draw action"]}

===AUDIO_INSTRUCTION===
{"shot":1,"slots":["音频1角色Zhang Wei","音频2角色Xiao Yu"]}
[SHOT_END]

[SHOT_START]
### Shot_002
**Title**: Sword at the Throat
**Duration**: {Segment_Duration}
**Shot Size**: Close-up
**Camera Movement**: Push
**Characters**: Zhang Wei, Xiao Yu
**Scene**: Moonlit bamboo grove
**Props**: Bronze sword
**Action Description**: Zhang Wei steps forward, the sword tip pressing against Xiao Yu's throat as she leans back half a step
**Mood & Lighting**: Cold white moonlight focuses on the sword tip, both faces half-lit

===H3_PROMPT===
subject_definitions:
<Subject 1> is Zhang Wei in <Picture 1>.
<Subject 2> is Xiao Yu in <Picture 2>.
<Audio 1> is the voice-timbre reference for <Subject 1> (S1).
<Audio 2> is the voice-timbre reference for <Subject 2> (S2).

summary:
[reference generation + audio reference] The target video shows <Subject 1> advancing with his sword against <Subject 2>'s throat in tense confrontation.

retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - Zhang Wei's martial outfit and stern expression are retained.
<Subject 2> (appears in [Shot 1]): fully_preserved - Xiao Yu's white robe and startled gaze are retained.
<Audio 1>: reference - <Subject 1>'s demand follows <Audio 1>'s low timbre; the original signal is not copied.
<Audio 2>: reference - <Subject 2>'s reply follows <Audio 2>'s clear timbre; the original signal is not copied.

detailed_description:
The target video uses a live-action cinematic style, cold white moonlight condensing to a point on the sword tip.
[Shot 1] In a close-up, <Subject 1> Zhang Wei (S1) steps forward, pressing the bronze sword against <Subject 2> Xiao Yu's (S2) throat. The camera pushes in with small amplitude at slow speed as Zhang Wei demands in a low voice referenced from <Audio 1>: <d>[English] Do you yield?</d> Xiao Yu leans back half a step, her throat trembling, yet her gaze never wavers.

overall_soundscape: A faint hum from the sword tip, night wind through the bamboo, both characters' breathing clearly audible.

non_diegetic_music: N/A

===SCENE_INSTRUCTION===
{"shot":2,"slots":["图片2角色Zhang Wei","图片3角色Xiao Yu"]}

===VIDEO_INSTRUCTION===
{"shot":2,"slots":[]}

===AUDIO_INSTRUCTION===
{"shot":2,"slots":["音频1角色Zhang Wei","音频2角色Xiao Yu"]}
[SHOT_END]

⚠️ Note: Shot_002 uses no background and no props, so slots list only the two characters, giving <Picture 1>=角色A and <Picture 2>=角色B — numbering restarts from 1 in every segment, it does NOT continue Shot_001's <Picture 2>/<Picture 3>.
⚠️ Audio order: in this segment Zhang Wei speaks first and Xiao Yu second, so AUDIO_INSTRUCTION.slots = ["音频:音频A","音频:音频B"] (音频A = Zhang Wei, first). If Xiao Yu spoke first in some segment, write ["音频:音频B","音频:音频A"] — the first speaker goes first.

Output the remaining shots in the same format, Shot numbers zero-padded to three digits (001, 002, ...).

## 6. Iron Rules (violating any one is a failure)
1. Exactly {Segment_Count} segments, no more, no less.
2. The six field names subject_definitions / summary / retention_analysis / detailed_description / overall_soundscape / non_diegetic_music must be output verbatim in English, one blank line between fields.
3. [Shot 1] has no timestamp, write the content directly; later cuts use [Shot N] At MM:SS.mmm ([Shot N] appears only once per cut, never write [Shot N] At MM:SS.mmm, [Shot N]) with strictly increasing timestamps, never exceeding {Segment_Duration} seconds.
4. Do NOT wrap anything in markdown code blocks (```).
5. Do NOT translate dialogue inside <d> tags; preserve the original language.
6. Do NOT invent <Subject N>/<Picture N>/<Video N>/<Audio N> labels; omit them if no reference material exists.
7. Scheduling instructions must be single-line JSON; the slots order must strictly match the <Picture N>/<Video N>/<Audio N> numbering in the prompt. No multiline, no comments, no misalignment.
8. Output nothing outside [SHOT_START]...[SHOT_END] except: in Generate mode you MUST output a 【故事】 story body before the first segment block; in Decompose mode output no story body, no statistics table, no extra notes.
9. Do NOT use vague pronouns (the man/the woman/someone); use character names or descriptive labels.
10. Do NOT use cross-shot references like "same as above" or "continues".
11. After the dash in retention_analysis you MUST list concrete retained features already defined in subject_definitions (do NOT mechanically write "per <Picture N> fully retained", and do NOT invent appearance/prop details absent from subject_definitions).
12. Every scheduling-instruction slot element MUST copy the assetName from the user's material intro exactly (e.g. "图片1角色孙悟空"); never split/abbreviate/substitute a material name/invent.
13. <Picture N>/<Video N>/<Audio N> numbering restarts from 1 inside EVERY [SHOT_START]...[SHOT_END] block (= slots index + 1). NEVER continue numbering across shots, and NEVER reuse the global image numbers from the user's material intro.
14. Every segment MUST output a complete block: [SHOT_START] + nine shot-info lines + ===H3_PROMPT=== six sections + ===SCENE_INSTRUCTION=== + ===VIDEO_INSTRUCTION=== + ===AUDIO_INSTRUCTION=== + [SHOT_END]. Missing any part is a failure.
15. non_diegetic_music is N/A by default; output English score description ONLY when the camera-language preference explicitly specifies a background music style (never write Chinese, never invent an unspecified score).
16. AUDIO_INSTRUCTION.slots MUST be ordered by speaking order in this segment (first speaker = item 1 = <Audio 1>); NEVER order by slot name A/B/C.
17. Segments with no dialogue (no <d> in detailed_description) MUST NOT output <Audio N> definitions, MUST NOT put audio in AUDIO_INSTRUCTION.slots, and MUST NOT write (Sx) in action descriptions.
18. Every segment's detailed_description MUST be unique; NEVER copy or reuse another segment's content. Even for similar plot points, change the shot size, action details, camera work, and imagery, and rewrite each segment from scratch.'''
