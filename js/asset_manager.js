/**
 * JZL MiniMax — 漫剧短剧管理器（第一版）
 * ============================================================
 * 参照「短剧管理器」网页原型，融合 JZL MiniMax H3 节点真实参数：
 *   ① 生成模型管理（本地 LLM 模型加载）
 *   ② 参考资源管理（图片/视频/音频资产池）
 *   ③ 提示词管理（提示词增强 + LLM 后端）
 *   ④ 生成参数管理（海螺H3视频参数）
 *   ⑤ 生成偏好管理（镜头语言偏好）
 *   ⑥ 视频保存管理（输出目录 + 命名规则）
 * 配置统一持久化到 jzl_manager.json（ComfyUI user 目录）。
 */

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const NODE_TYPE = "JZL_MiniMaxAssetManager";
const MANAGER_ENDPOINT = "/jzl/manager";
const UPLOAD_ENDPOINT = "/jzl/upload_asset";
const ASSET_PREVIEW_ENDPOINT = "/jzl/asset_preview";
const AUDIO_PREVIEW_ENDPOINT = "/jzl/audio_preview";

// ── 下拉选项（与后端节点保持一致的选项列表） ─────────────────────
const OPTIONS = {
    llmBackend: ["本地模型 [local]", "在线API [api]"],
    providers: [
        "OpenAI 兼容 (OpenAI/DeepSeek/Qwen/GLM/Kimi/Ollama/vLLM/LM Studio)",
        "Anthropic",
        "Google Gemini",
    ],
    shotSize: ["根据剧情", "随机组合", "远景为主", "全景为主", "中景为主", "近景为主", "特写为主"],
    cameraMove: ["根据剧情", "随机组合", "固定机位", "推拉", "摇移", "俯仰", "升降", "环绕", "跟拍", "手持晃动", "旋转", "一镜到底"],
    cutRhythm: ["根据剧情", "随机组合", "一镜到底", "2~5镜", "5~9镜", "9~13镜", "13~18镜"],
    transition: ["随机", "硬切", "叠化", "淡入淡出", "擦除"],
    music: [
        "禁止音乐 / No Music", "不指定 / Unspecified",
        "史诗战争 / Epic Orchestral", "动作追逐 / Action Chase",
        "紧张悬疑 / Tense Suspense", "恐怖惊悚 / Horror Atmosphere",
        "温馨治愈 / Warm & Gentle", "浪漫爱情 / Romantic Strings",
        "悲伤抒情 / Melancholic", "轻松喜剧 / Light Comedy",
        "古风武侠 / Chinese Wuxia", "科幻未来 / Sci-fi Electronic",
        "神秘探索 / Mysterious Adventure", "史诗悲剧 / Tragic Epic",
    ],
    creativeReq: ["无特别要求", "节奏紧凑", "舒缓留白", "情感细腻", "明快轻松", "多反转结局", "开放式结局", "强冲突"],
    detailLength: ["标准 (350-500字)", "精简 (200-350字)", "详细 (500-800字)", "超详细 (800-1200字)"],
    style: [
        "不指定 / Unspecified", "电影感 / Cinematic", "实拍 / Live-action",
        "复古胶片 / Vintage film", "黑白电影 / Black & White", "纪录片 / Documentary",
        "极简广告 / Minimalist commercial", "微距摄影 / Macro photography", "航拍 / Aerial drone",
        "二维动画 / 2D-animated", "三维CG / 3D CG", "日系二次元 / Anime",
        "美式漫画 / American Comic", "皮克斯3D / Pixar-style 3D", "定格动画 / Stop-motion",
        "手绘发光 / Hand-drawn glow", "像素艺术 / Pixel art", "赛博朋克 / Cyberpunk",
        "蒸汽朋克 / Steampunk", "故障艺术 / Glitch art", "羊毛毡 / Wool felt",
        "折纸 / Origami", "水彩 / Watercolor", "粘土动画 / Claymation",
        "水墨 / Ink wash", "油画 / Oil painting", "纸艺拼贴 / Paper collage",
        "剪纸 / Paper cutout", "铅笔素描 / Pencil sketch", "浮世绘 / Ukiyo-e",
        "敦煌壁画 / Dunhuang Murals", "青花瓷 / Blue-white Porcelain", "工笔画 / Gongbi Painting",
        "皮影戏 / Shadow Puppetry", "中国风插画 / Chinese Illustration", "年画 / New Year Painting",
        "布艺 / Fabric Art", "蜡笔画 / Crayon drawing", "哥特萝莉 / Gothic Lolita",
    ],
    aspectRatio: [
        "1:1 (Square)", "2:3 (Portrait Photo)", "3:2 (Photo)", "3:4 (Portrait Standard)",
        "4:5 (Portrait Tall)", "4:3 (Standard)", "5:4 (Landscape Tall)",
        "9:16 (Portrait Widescreen)", "16:9 (Widescreen)", "21:9 (Ultrawide)",
    ],
    assetTypes: ["角色", "场景", "道具", "分镜", "音效", "音乐", "其他"],
    presetModes: [
        "纯文本生成音视频[英文]-T2VA [EN]", "纯文本生成音视频[中文]-T2VA [ZH]",
        "首帧图生成音视频[英文]-I2VA [EN]", "首帧图生成音视频[中文]-I2VA [ZH]",
        "首尾帧生成音视频[英文]-FL2VA [EN]", "首尾帧生成音视频[中文]-FL2VA [ZH]",
        "尾帧图生成音视频[英文]-L2VA [EN]", "尾帧图生成音视频[中文]-L2VA [ZH]",
    ],
    aspectShort: ["16:9", "9:16", "4:3", "3:4", "1:1", "21:9", "4:5", "5:4"],
    cuts: ["不指定 / Unspecified", "不切镜 / Single Shot", "1 次切镜 / 1 Cut", "2 次切镜 / 2 Cuts", "3 次切镜 / 3 Cuts", "4 次切镜 / 4 Cuts", "5 次切镜 / 5 Cuts", "6 次切镜 / 6 Cuts", "7 次切镜 / 7 Cuts", "8 次切镜 / 8 Cuts", "9 次切镜 / 9 Cuts"],
    inferenceModes: ["one by one", "images", "video"],
    samplers: ["res_multistep", "res_multistep_cfg_pp", "res_multistep_ancestral", "res_multistep_ancestral_cfg_pp",
        "euler", "euler_cfg_pp", "euler_ancestral", "euler_ancestral_cfg_pp",
        "heun", "heunpp2", "exp_heun_2_x0", "exp_heun_2_x0_sde",
        "dpm_2", "dpm_2_ancestral", "lms", "dpm_fast", "dpm_adaptive",
        "dpmpp_2s_ancestral", "dpmpp_2s_ancestral_cfg_pp", "dpmpp_sde", "dpmpp_sde_gpu",
        "dpmpp_2m", "dpmpp_2m_cfg_pp", "dpmpp_2m_sde", "dpmpp_2m_sde_gpu",
        "dpmpp_2m_sde_heun", "dpmpp_2m_sde_heun_gpu", "dpmpp_3m_sde", "dpmpp_3m_sde_gpu",
        "ddpm", "lcm", "ipndm", "ipndm_v", "deis",
        "gradient_estimation", "gradient_estimation_cfg_pp", "er_sde", "seeds_2", "seeds_3",
        "sa_solver", "sa_solver_pece", "ddim", "uni_pc", "uni_pc_bh2"],
    schedulers: ["simple", "sgm_uniform", "karras", "exponential", "ddim_uniform", "beta", "normal", "linear_quadratic", "kl_optimal"],
    seedModes: ["randomize", "fixed", "increment"],
    decodeCleanup: ["卸载显存模型", "不做清理"],
};

const PANELS = {
    assets: { label: "📁 参考素材管理" },
    prompt: { label: "📝 剧本拆解配置" },
    preference: { label: "🎭 采样解码设置" },
    preference_settings: { label: "🎯 镜头参数预设" },
    prompt_elements: { label: "➕ 常用提示词元素" },
    align: { label: "🎯 参考元素切换" },
    save_settings: { label: "💾 视频保存设置" },
    help: { label: "📖 节点使用说明" },
};

// 节点表面按钮定义（前端 addWidget 添加）
const PANEL_BUTTONS = [
    { widget: "btn_assets", label: "📁 参考素材管理", panel: "assets" },
    { widget: "btn_prompt", label: "📝 剧本拆解配置", panel: "prompt" },
    { widget: "btn_pref", label: "🎭 采样解码设置", panel: "preference" },
    { widget: "btn_save", label: "💾 视频保存设置", panel: "save_settings" },
    { widget: "btn_elements", label: "➕ 常用提示词元素", panel: "prompt_elements" },
    { widget: "btn_preference", label: "🎯 镜头参数预设", panel: "preference_settings" },
    { widget: "btn_align", label: "🎯 参考元素切换", panel: "align" },
    { widget: "btn_help", label: "📖 节点使用说明", panel: "help" },
];

const KIND_LABEL = { image: "图片", video: "视频", audio: "音频" };
// 每种资产类型不同的分类选项
const ASSET_TYPES_BY_KIND = {
    image: ["角色", "场景", "道具", "自定义"],
    video: ["主体", "运镜", "特效", "其他"],
    audio: ["音色", "音效", "配乐", "念白", "其他"],
};
const ASSET_TYPES = ASSET_TYPES_BY_KIND.image;
// 资产类型 → 调度槽位类型（与后端 _asset_type_for_slot 一致；「自定义」→「其他」官方识别）
function slotTypeOf(kind, type) {
    if (kind === "image") return { "角色": "角色", "场景": "场景", "道具": "道具", "自定义": "其他", "分镜": "分镜", "其他": "其他" }[type] || "其他";
    return kind === "video" ? "视频" : "音频";
}

let modal = null;

// ── V3 widget 值读写 ──────────────────────────────────────
// V3 combo widget 的 callback 是空函数，直接赋值 value 才会同步 _state.value（序列化/执行都读它）
function readWidgetValue(w) {
    return w ? (w._state?.value ?? w.value) : undefined;
}
function setWidgetValue(w, val) {
    if (!w) return;
    w.value = val;
    if (w._state) w._state.value = val;
    w._node?.setDirtyCanvas?.(true, true);
}

// ── @ 引用素材（按节点独立缓存） ─────────────────────────────
let mentionMenu = null;
let mentionState = null;  // { editable, start, end }
let promptCaretPos = null;  // 记忆的光标偏移（null=末尾），供资产显示窗点击插入定位
function notifyAssetsChanged(node) {
    if (!node) return;
    loadManager(node).then((data) => {
        cacheAssets(node, data.settings);
        try { node.__jzlRefresh?.(); } catch (_) {}
    }).catch(() => {});
}

const KIND_PREFIX = { image: "图片", video: "视频", audio: "音频" };
const KIND_ICON = { image: "🖼️", video: "🎬", audio: "🎧" };

// @资产 富文本着色：图片按类型（角色/场景/道具/自定义）分色，视频/音频各一色
const ASSET_COLORS = {
    image: { "角色": "#4da3ff", "场景": "#5ecf8a", "道具": "#ffb84d", "自定义": "#ffd166", "分镜": "#ffd166", "其他": "#9aa7b8" },
    video: "#c792ea",
    audio: "#ff8fa3",
};
function assetColor(item) {
    if (item.kind === "image") return ASSET_COLORS.image[item.type] || ASSET_COLORS.image["其他"];
    return ASSET_COLORS[item.kind] || "#9aa7b8";
}

// contenteditable 光标辅助
function caretOffset(editable) {
    // 与 getPromptText 一致：token 按 dataset.jzlName（资产名）计长，
    // 避免「显示简称/底层全名」两种视图不一致导致 @ 检测定位错误
    const sel = window.getSelection();
    if (!sel || !sel.rangeCount || !editable.contains(sel.anchorNode)) return getPromptText(editable).length;
    const range = sel.getRangeAt(0);
    const pre = document.createRange();
    pre.selectNodeContents(editable);
    pre.setEnd(range.endContainer, range.endOffset);
    const tmp = document.createElement("div");
    tmp.appendChild(pre.cloneContents());
    return getPromptText(tmp).length;
}
function getPromptText(editable) {
    // 精确纯文本：普通文本拼接；资产 token 输出其全名(dataset.jzlAsset)；<br>/块级转 \n
    let out = "";
    const visit = (node) => {
        for (const child of node.childNodes) {
            if (child.nodeType === 3) {
                out += child.textContent;
            } else if (child.nodeType === 1) {
                if (child.classList?.contains("jzl-asset-token")) {
                    out += child.dataset.jzlName || child.dataset.jzlAsset || "";
                } else if (child.tagName === "BR") {
                    out += "\n";
                } else if (child.tagName === "DIV" || child.tagName === "P") {
                    visit(child); out += "\n";
                } else {
                    visit(child);
                }
            }
        }
    };
    visit(editable);
    return out;
}

function insertSpanAtCaret(editable, span) {
    const sel = window.getSelection();
    if (sel && sel.rangeCount && editable.contains(sel.anchorNode)) {
        const range = sel.getRangeAt(0);
        range.deleteContents();
        range.insertNode(span);
        range.setStartAfter(span);
        range.collapse(true);
        sel.removeAllRanges();
        sel.addRange(range);
    } else {
        editable.appendChild(span);
        const r = document.createRange();
        r.selectNodeContents(editable);
        r.collapse(false);
        sel?.removeAllRanges();
        sel?.addRange(r);
    }
}
function setCaretToOffset(editable, offset) {
    // 与 caretOffset/getPromptText 保持一致：资产 token 整体按 dataset.jzlName（资产名）长度计。
    // 否则光标定位会错位 → 点击资产窗插入跑到错误位置。
    const sel = window.getSelection();
    const range = document.createRange();
    let remaining = offset;
    let found = false;
    const walk = (parent) => {
        for (const child of Array.from(parent.childNodes)) {
            if (found) return;
            if (child.nodeType === 3) {
                const len = child.textContent.length;
                if (remaining <= len) {
                    range.setStart(child, remaining);
                    range.collapse(true);
                    found = true;
                    return;
                }
                remaining -= len;
            } else if (child.nodeType === 1) {
                if (child.classList && child.classList.contains("jzl-asset-token")) {
                    const len = (child.dataset.jzlName || child.dataset.jzlAsset || "").length;
                    if (remaining <= len) {
                        range.setStartAfter(child);
                        range.collapse(true);
                        found = true;
                        return;
                    }
                    remaining -= len;
                } else if (child.tagName === "BR") {
                    if (remaining <= 1) {
                        range.setStartAfter(child);
                        range.collapse(true);
                        found = true;
                        return;
                    }
                    remaining -= 1;
                } else if (child.tagName === "DIV" || child.tagName === "P") {
                    walk(child);
                    if (found) return;
                    // 块级元素末尾按 1 个换行计（与 getPromptText 一致）
                    if (remaining <= 0) {
                        range.setStartAfter(child);
                        range.collapse(true);
                        found = true;
                        return;
                    }
                    remaining -= 1;
                } else {
                    walk(child);
                    if (found) return;
                }
            }
        }
    };
    walk(editable);
    if (found) {
        sel.removeAllRanges();
        sel.addRange(range);
        return range;
    }
    range.selectNodeContents(editable);
    range.collapse(false);
    sel.removeAllRanges();
    sel.addRange(range);
    return range;
}

function assetFullName(kind, index, item) {
    return [KIND_PREFIX[kind] + (index + 1), item?.type, item?.name].filter(Boolean).join(" ");
}

function cacheAssets(node, settings) {
    if (node) node.__jzlAssets = (settings?.assets) || { images: [], videos: [], audios: [] };
}

// 槽位（类型+字母）分配：与后端 _build_asset_intro 完全一致
// 手选字母（A-Z）优先；缺失/非法按类型自动从 A 起顺延；同类同字母冲突顺延下一字母
function buildSlotMap(assets) {
    const map = {};
    const counters = {};
    const used = {};
    const kinds = [["image", "images"], ["video", "videos"], ["audio", "audios"]];
    for (const [kind, key] of kinds) {
        (assets?.[key] || []).forEach((item, i) => {
            if (item?.enabled === false) return;
            const name = (item?.name || "").trim();
            if (!name) return;
            const st = slotTypeOf(kind, item?.type || "");
            if (!st) return;
            let letter = (item?.letter || "").trim().toUpperCase();
            if (!/^[A-Z]$/.test(letter)) letter = String.fromCharCode(65 + (counters[st] || 0));
            let slot = st + letter;
            while (used[slot] && letter < "Z") {
                letter = String.fromCharCode(letter.charCodeAt(0) + 1);
                slot = st + letter;
            }
            used[slot] = true;
            counters[st] = (counters[st] || 0) + 1;
            map[`${kind}:${i}`] = slot;
        });
    }
    return map;
}

function collectMentionItems(node) {
    const kindMap = { images: "image", videos: "video", audios: "audio" };
    const cache = node?.__jzlAssets || { images: [], videos: [], audios: [] };
    const slotMap = buildSlotMap(cache);
    const items = [];
    for (const kindKey of ["images", "videos", "audios"]) {
        const kind = kindMap[kindKey];
        let displayIndex = 0;  // 显示连续编号（跳过空槽位，避免跳号：音频1、音频3）
        (cache[kindKey] || []).forEach((item, idx) => {
            if (item?.enabled === false) return;
            if (!(item?.path || "").trim()) return;  // 空槽口（未上传素材）不显示在主界面
            const name = assetFullName(kind, displayIndex, item);  // 全名（图片1 角色 碗碗）
            displayIndex++;
            if (!name) return;
            const cleanName = (item?.name || "").trim();  // 资产自定义名（严格匹配用，一字不差）
            const slot = slotMap[`${kind}:${idx}`] || "";
            items.push({
                name,                    // 全名（带空格）→ 后端匹配用
                token: name.replace(/\s+/g, ""),  // 去空格全名（后端提取用）
                display: cleanName || name.replace(/\s+/g, ""),  // 简称（输入框显示）
                matchName: cleanName,     // 严格匹配名：提示词里精确出现该名字 → 着色/对齐（第3/5点）
                slot,                     // 槽位（类型+字母，如「角色A」，与后端 _build_asset_intro 一致）
                slotLabel: (slot ? slot + cleanName : (cleanName || name.replace(/\s+/g, ""))),  // 显示文本（角色A兔子）
                kind, type: item?.type || "", path: item?.path || "",
                description: item?.description || "",  // 详细描述（hover 用）
            });
        });
    }
    return items;
}

function closeMentionMenu() {
    if (mentionMenu) { mentionMenu.remove(); mentionMenu = null; }
    mentionState = null;
}

function openMentionMenu(editable, start, end, query, node) {
    const q = (query || "").toLowerCase();
    const all = collectMentionItems(node);
    // 过滤：@角色 → 只显示类型=角色；@孙悟空 → 只显示名称含"孙悟空"
    const items = all.filter((it) => {
        if (!q) return true;
        return it.type.toLowerCase().includes(q) || it.name.toLowerCase().includes(q);
    });
    if (!items.length) { closeMentionMenu(); return; }

    closeMentionMenu();
    mentionState = { editable, start, end };

    // 定位到光标后面（而非输入框底部）：取当前光标 range 的矩形
    let rect = editable.getBoundingClientRect();
    try {
        const sel = window.getSelection();
        if (sel && sel.rangeCount) {
            const r = sel.getRangeAt(0).cloneRange();
            r.collapse(true);
            if (editable.contains(r.startContainer)) {
                const cr = r.getBoundingClientRect();
                if (cr.width > 0 || cr.height > 0) rect = cr;
            }
        }
    } catch (_) {}
    const menu = document.createElement("div");
    menu.style.cssText = "position:fixed;z-index:10001;background:#1e1e1e;border:1px solid #444;border-radius:8px;max-height:340px;max-width:460px;overflow-y:auto;box-shadow:0 8px 20px rgba(0,0,0,0.5);padding:8px;";
    menu.style.left = rect.left + "px";
    menu.style.top = (rect.bottom + 4) + "px";

    // 自动列数：根据数量整理宫格
    const cols = items.length <= 3 ? items.length : Math.min(5, Math.max(3, Math.ceil(Math.sqrt(items.length))));
    const grid = document.createElement("div");
    grid.style.cssText = `display:grid;grid-template-columns:repeat(${cols},74px);gap:8px;`;

    for (const item of items) {
        const cell = document.createElement("div");
        cell.style.cssText = "display:flex;flex-direction:column;align-items:center;gap:3px;cursor:pointer;border-radius:6px;padding:4px;border:1px solid transparent;";

        const thumb = document.createElement("div");
        thumb.style.cssText = "width:64px;height:64px;border-radius:5px;border:1px solid #444;background:#111;display:flex;align-items:center;justify-content:center;overflow:hidden;font-size:26px;";
        if (item.kind === "image") {
            const img = document.createElement("img");
            img.style.cssText = "width:100%;height:100%;object-fit:cover;";
            img.src = item.path ? `${ASSET_PREVIEW_ENDPOINT}?path=${encodeURIComponent(item.path)}` : "/extensions/ComfyUI-JZL-MiniMax-H3/icon.png";
            img.onerror = () => { img.src = "/extensions/ComfyUI-JZL-MiniMax-H3/icon.png"; };
            thumb.appendChild(img);
        } else {
            thumb.textContent = item.kind === "video" ? "🎬" : "🎧";
        }

        const typeTag = document.createElement("span");
        typeTag.style.cssText = "font-size:10px;color:#8ab8dd;line-height:1;";
        typeTag.textContent = item.type || KIND_LABEL[item.kind] || "";

        const label = document.createElement("span");
        label.style.cssText = "font-size:11px;color:#ddd;line-height:1.2;max-width:70px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-align:center;";
        label.textContent = item.slotLabel || item.name;

        cell.append(thumb, typeTag, label);
        cell.addEventListener("mousedown", (e) => { e.preventDefault(); e.stopPropagation(); });
        cell.addEventListener("click", () => chooseMention(item));
        cell.addEventListener("mouseenter", () => { cell.style.border = "1px solid #5b9bd5"; cell.style.background = "#2a2a2a"; });
        cell.addEventListener("mouseleave", () => { cell.style.border = "1px solid transparent"; cell.style.background = "transparent"; });
        grid.appendChild(cell);
    }

    menu.appendChild(grid);
    document.body.appendChild(menu);
    mentionMenu = menu;

    const dismiss = (e) => {
        if (!menu.contains(e.target)) closeMentionMenu();
    };
    setTimeout(() => document.addEventListener("mousedown", dismiss, { once: true }), 0);
}

function chooseMention(item) {
    if (!mentionState) return;
    const { editable, start, end } = mentionState;
    const token = item.token;  // 去空格全名（后端匹配用）
    closeMentionMenu();
    editable.focus();
    // 删除 @…到光标，替换为锁死着色 span（整体不可编辑，只能整体删除）
    const sRange = setCaretToOffset(editable, start);
    const eRange = setCaretToOffset(editable, end);
    sRange.setEnd(eRange.endContainer, eRange.endOffset);
    sRange.deleteContents();
    const span = makeAssetToken(token, item);
    sRange.insertNode(span);
    const caretRange = document.createRange();
    caretRange.setStartAfter(span);
    caretRange.collapse(true);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(caretRange);
    const nameLen = (item.matchName || item.display || token).length;
    promptCaretPos = start + nameLen;
    editable.dispatchEvent(new Event("input", { bubbles: true }));
    editable.dispatchEvent(new Event("change"));
    // @ 添加素材 → 自动激活「显示引用」并保存
    const _n = editable.__node;
    if (_n) { _n.__jzlAlignMode = "ref"; _n.__updateAlignStatus?.(); saveAlignMode(_n, "ref"); }
}

function makeAssetToken(token, item) {
    const span = document.createElement("span");
    span.dataset.jzlAsset = token;  // 全名（去空格），后端匹配用（旧工作流兼容）
    span.dataset.jzlName = (item.matchName || item.display || item.name || "").trim();  // 资产名 → 纯文本输出（清洗类型+编号）
    span.dataset.jzlKind = item.kind || "";
    span.contentEditable = "false";
    span.className = "jzl-asset-token";
    span.title = item.slot ? `${item.slot} ${item.name || token}` : (item.name || token);  // hover 显示槽位+全名
    // 图片：内嵌缩略图；视频/音频：CSS 伪元素图标（不占用文本）
    if (item.kind === "image") {
        const img = document.createElement("img");
        img.className = "jzl-asset-thumb";
        img.src = item.path ? `${ASSET_PREVIEW_ENDPOINT}?path=${encodeURIComponent(item.path)}` : "/extensions/ComfyUI-JZL-MiniMax-H3/icon.png";
        img.onerror = () => { img.src = "/extensions/ComfyUI-JZL-MiniMax-H3/icon.png"; };
        span.appendChild(img);
    }
    const text = document.createElement("span");
    text.textContent = item.slotLabel || item.display || token;  // 显示：类型+字母+名称（如「角色A兔子」）
    text.style.color = assetColor(item);
    span.appendChild(text);
    return span;
}

function findAssetByToken(token, node) {
    const t = (token || "").replace(/\s+/g, "").toLowerCase();
    if (!t) return null;
    const items = collectMentionItems(node);
    return items.find(it => it.token.toLowerCase() === t)
        || items.find(it => {
            const n = it.token.toLowerCase();
            return n && (n.includes(t) || t.includes(n));
        });
}

function renderPromptFromText(promptBox, text, node) {
    // 把纯文本里的「资产名」重新渲染成「缩略图 + 彩色文字」锁死 token：
    // 1) 严格一字不差匹配资产自定义名（最长优先，避免部分重叠）
    // 2) 旧工作流遗留的 图片N… 全名 token 兜底（自动迁移为纯文本）
    promptBox.innerHTML = "";
    const source = text || "";
    const items = collectMentionItems(node)
        .filter((it) => (it.matchName || "").length)
        .sort((a, b) => b.matchName.length - a.matchName.length);
    const legacyRe = /(?:图片|视频|音频)\d+[^\s@，。；,.、]*/g;
    let last = 0;
    let i = 0;
    while (i < source.length) {
        // 1) 严格资产名匹配（一字不差）
        let hit = null;
        for (const it of items) {
            if (source.startsWith(it.matchName, i)) { hit = it; break; }
        }
        if (hit) {
            if (i > last) promptBox.appendChild(document.createTextNode(source.slice(last, i)));
            promptBox.appendChild(makeAssetToken(hit.token, hit));
            i += hit.matchName.length;
            last = i;
            continue;
        }
        // 2) 旧工作流遗留全名 token（图片N 类型 名称）
        legacyRe.lastIndex = i;
        const m = legacyRe.exec(source);
        if (m && m.index === i) {
            if (i > last) promptBox.appendChild(document.createTextNode(source.slice(last, i)));
            const item = findAssetByToken(m[0], node);
            if (item) {
                promptBox.appendChild(makeAssetToken(m[0], item));
            } else {
                promptBox.appendChild(document.createTextNode(m[0]));
            }
            i += m[0].length;
            last = i;
            continue;
        }
        i++;
    }
    if (last < source.length) promptBox.appendChild(document.createTextNode(source.slice(last)));
}

// 参考元素切换（双向）：正向=纯文本按素材名一字不差对齐成 @token；逆向=已有 @token 时清洗成纯文本（只保留名称）
function toggleAlignPrompt(node) {
    const box = node?.__promptBox;
    if (!box) return;
    const ip = (node.widgets || []).find((w) => w.name === "internal_prompt");
    // 切换方向由当前模式（__jzlAlignMode）决定，而不是由「有无 @token」决定：
    // 空文本/无素材时也始终能双向切换（避免空框永远无 token → 卡在正向切不回纯文本）
    if (node.__jzlAlignMode === "text") {
        // 正向：纯文本 → 按素材名一字不差对齐成 @token
        renderPromptFromText(box, getPromptText(box), node);
        if (ip) setWidgetValue(ip, getPromptText(box));
        box.dispatchEvent(new Event("input", { bubbles: true }));
        node.setDirtyCanvas?.(true, true);
        node.__jzlAlignMode = "ref";
        node.__updateAlignStatus?.();
        saveAlignMode(node, "ref");
        notify("✅ 已切换为显示引用（按素材名一字不差着色）", "success");
    } else {
        // 逆向：@素材 → 纯文本（getPromptText 只输出名称，自动清洗类型+编号）
        const text = getPromptText(box);
        box.innerHTML = "";
        box.appendChild(document.createTextNode(text));
        if (ip) setWidgetValue(ip, text);
        box.dispatchEvent(new Event("input", { bubbles: true }));
        node.setDirtyCanvas?.(true, true);
        node.__jzlAlignMode = "text";
        node.__updateAlignStatus?.();
        saveAlignMode(node, "text");
        notify("✅ 已切换为纯文本（只保留素材名称）", "success");
    }
}

function saveAlignMode(node, mode) {
    // 把「参考元素切换」状态写入 manager_settings（随工作流保存，刷新不丢失）
    const msW = (node?.widgets || []).find((w) => w.name === "manager_settings");
    if (!msW) return;
    const raw = readWidgetValue(msW);
    let s = {};
    try { s = raw ? JSON.parse(raw) : {}; } catch (_) {}
    s.align_mode = mode;
    setWidgetValue(msW, JSON.stringify(s));
}

function insertAssetToken(editable, item) {
    // 在内部编辑窗口（contenteditable）光标处插入「缩略图 + 彩色」锁死 token（资产显示窗点击）
    if (!editable) return;
    const token = item.token;  // 去空格全名（后端匹配用）
    const span = makeAssetToken(token, item);
    editable.focus();
    // 用记忆的光标位置插入（点击资产窗时实时 selection 会丢失，导致 token 跑到开头）
    const offset = (typeof promptCaretPos === "number") ? promptCaretPos : getPromptText(editable).length;
    const range = setCaretToOffset(editable, offset);
    range.insertNode(span);
    const caretRange = document.createRange();
    caretRange.setStartAfter(span);
    caretRange.collapse(true);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(caretRange);
    const nameLen = (item.matchName || item.display || token).length;
    promptCaretPos = offset + nameLen;
    editable.dispatchEvent(new Event("input", { bubbles: true }));
    editable.dispatchEvent(new Event("change"));
    // 点击添加素材 → 自动激活「显示引用」并保存
    const _n = editable.__node;
    if (_n) { _n.__jzlAlignMode = "ref"; _n.__updateAlignStatus?.(); saveAlignMode(_n, "ref"); }
}

function renderAssetWindow(windowBox, textarea, node) {
    windowBox.innerHTML = "";
    const items = collectMentionItems(node);
    if (!items.length) {
        windowBox.append(el("div", "font-size:11px;color:#777;padding:4px;", "（暂无素材，到「引用资产设置」添加）"));
        windowBox.style.height = "30px";
        windowBox.__onResize?.();
        return;
    }
    // 自动换行宫格：始终显示全部素材，多行时窗口与节点自动增高（按节点宽度自动换行，不遮挡）
    const grid = document.createElement("div");
    grid.style.cssText = "display:flex;flex-wrap:wrap;gap:6px;padding:3px;align-content:flex-start;";
    for (const item of items) {
        const cell = document.createElement("div");
        cell.style.cssText = "flex:0 0 78px;width:78px;cursor:pointer;border-radius:6px;overflow:hidden;border:1px solid #333;background:#111;";
        cell.title = [item.name, item.description].filter(Boolean).join("\n");  // hover 显示完整内容
        // 缩略图（图片）或图标（视频/音频）
        const thumb = document.createElement("div");
        thumb.style.cssText = "width:78px;height:52px;display:flex;align-items:center;justify-content:center;overflow:hidden;font-size:24px;background:#000;";
        if (item.kind === "image") {
            const img = document.createElement("img");
            img.style.cssText = "width:100%;height:100%;object-fit:cover;";
            img.src = item.path ? `${ASSET_PREVIEW_ENDPOINT}?path=${encodeURIComponent(item.path)}` : "";
            img.onerror = () => { img.remove(); };
            thumb.appendChild(img);
        } else {
            thumb.textContent = item.kind === "video" ? "🎬" : "🎧";
        }
        // 名称标签（类型 + 自定义名）——字号 11px 可显示约 7 个字（如「角色A小白兔」），超长省略号
        const label = document.createElement("div");
        label.style.cssText = "width:100%;height:22px;line-height:22px;font-size:11px;color:#cdd8e2;background:rgba(10,20,30,.7);text-align:center;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding:0 3px;box-sizing:border-box;";
        label.textContent = item.slotLabel || item.display || "";
        cell.append(thumb, label);
        cell.addEventListener("mousedown", (e) => e.stopPropagation());
        cell.addEventListener("click", () => insertAssetToken(textarea, item));
        grid.appendChild(cell);
    }
    windowBox.appendChild(grid);
    // 高度自适应内容（多行换行时增高），并通知节点调整整体高度；
    // 用 scrollHeight 取完整内容高度（含 overflow:hidden 可能遮挡的多行），保证素材不被吞
    const h = Math.max(grid.scrollHeight || grid.offsetHeight, 30);
    windowBox.style.height = h + "px";
    windowBox.__onResize?.();
}

function notify(msg, type = "success") {
    try {
        if (app?.ui?.toast) { app.ui.toast.add({ text: msg, type }); return; }
    } catch (_) {}
    console.log(`[JZL Asset] ${msg}`);
}

async function loadLists() {
    // 模型/风格等列表仍从后端拉（仅列表，不含节点配置）
    try {
        const resp = await api.fetchApi(MANAGER_ENDPOINT);
        const data = await resp.json().catch(() => ({}));
        return {
            llm_models: data?.llm_models || [],
            mmproj_models: data?.mmproj_models || ["None"],
            chat_handlers: data?.chat_handlers || ["None"],
            diffusion_models: data?.diffusion_models || [],
            clip_models: data?.clip_models || [],
            vae_models: data?.vae_models || [],
            lora_models: data?.lora_models || [],
            story_styles: data?.story_styles || [],
            save_dir: data?.save_dir || "",
            upscaler_models: data?.upscaler_models || [],
        };
    } catch (_) {
        return { llm_models: [], mmproj_models: ["None"], chat_handlers: ["None"], story_styles: [], save_dir: "", upscaler_models: [] };
    }
}

async function loadManager(node) {
    // 节点独立配置：优先读工作流内保存的 manager_settings；空则全新默认（不继承其他节点/全局）。
    // 先 await loadLists 再读 widget：configure 在 onNodeCreated 之后才恢复 manager_settings 值，
    // 若在 await 前读取会拿到空值 → 刷新后资产窗/提示词着色丢失（第4点修复）。
    const lists = await loadLists();
    const w = node?.widgets?.find((x) => x.name === "manager_settings");
    const raw = w ? readWidgetValue(w) : "";
    let settings = null;
    if (raw && typeof raw === "string" && raw.trim()) {
        try { const s = JSON.parse(raw); if (s && typeof s === "object") settings = s; } catch (_) {}
    }
    return { settings: settings || defaultSettings(), ...lists };
}

async function saveManager(node, value) {
    const w = node?.widgets?.find((x) => x.name === "manager_settings");
    if (w) setWidgetValue(w, JSON.stringify(value));
    try { node?.__jzlUpdateInfo?.(); } catch (_) {}  // 保存后实时同步节点「实时显示」
    return value;
}

async function chooseFile(kind) {
    // 浏览器原生文件选择 + multipart 上传到后端（与官方「加载图像」一致）。
    // 云机/无桌面环境也完全可用：文件从用户浏览器直传服务器，不依赖 tkinter 弹窗。
    const accept = { image: "image/*", video: "video/*", audio: "audio/*" }[kind] || "";
    const input = document.createElement("input");
    input.type = "file";
    input.accept = accept;
    input.style.display = "none";
    const done = (p) => { if (input.parentNode) input.parentNode.removeChild(input); return p; };
    const chosen = new Promise((resolve) => {
        input.addEventListener("change", async () => {
            const file = input.files && input.files[0];
            if (!file) { resolve(null); return; }
            const fd = new FormData();
            fd.append("file", file);
            fd.append("kind", kind);
            try {
                const resp = await api.fetchApi(UPLOAD_ENDPOINT, { method: "POST", body: fd });
                const data = await resp.json().catch(() => ({}));
                if (data?.path) { resolve(data.path); return; }
                notify(data?.error || "上传失败", "error");
                resolve(null);
            } catch (_) {
                notify("上传失败", "error");
                resolve(null);
            }
        });
        // 用户在文件对话框点「取消」时正常结束并清理 input（现代浏览器均支持 cancel 事件）
        input.addEventListener("cancel", () => resolve(null));
    });
    document.body.appendChild(input);
    input.click();
    return done(await chosen);
}

function el(tag, css, text) {
    const e = document.createElement(tag);
    if (css) e.style.cssText = css;
    if (text !== undefined) e.textContent = text;
    return e;
}

function makeSectionTitle(text) {
    return el("div", "margin:14px 0 4px;font-size:14px;font-weight:600;color:var(--fg-color,#eee);border-bottom:1px solid var(--border-color,#444);padding-bottom:4px;", text);
}

function makeCountRow(labelText, kind, value, onChange) {
    const row = el("div", "display:flex;align-items:center;gap:6px;");
    row.append(el("span", "font-size:12px;color:var(--fg-color,#ddd);white-space:nowrap;", labelText));
    const dec = el("button", "width:26px;height:26px;background:var(--comfy-input-bg,#2a2a2a);color:var(--fg-color,#ddd);border:1px solid var(--border-color,#555);border-radius:5px;font-size:12px;line-height:1;cursor:pointer;", "◀");
    dec.title = "减少数量";
    const inp = el("input", "width:44px;text-align:center;background:var(--comfy-input-bg,#1d1d1d);color:var(--fg-color,#ddd);border:1px solid var(--border-color,#444);border-radius:4px;padding:4px 0;font-size:13px;");
    inp.type = "number";
    inp.min = "0";
    inp.max = "64";
    inp.step = "1";
    inp.value = value;
    inp.className = "jzl-count-input";
    const inc = el("button", "width:26px;height:26px;background:var(--comfy-input-bg,#2a2a2a);color:var(--fg-color,#ddd);border:1px solid var(--border-color,#555);border-radius:5px;font-size:12px;line-height:1;cursor:pointer;", "▶");
    inc.title = "增加数量";
    const apply = (n) => {
        n = Math.max(0, Math.min(64, Math.floor(n)));
        inp.value = n;
        onChange(n);
    };
    dec.addEventListener("click", () => apply((parseInt(inp.value, 10) || 0) - 1));
    inc.addEventListener("click", () => apply((parseInt(inp.value, 10) || 0) + 1));
    inp.addEventListener("change", () => apply(parseInt(inp.value, 10) || 0));
    row.append(dec, inp, inc);
    return row;
}

function showFullImage(path) {
    // 弹窗显示原图（非缩略图）
    const overlay = el("div", "position:fixed;inset:0;background:rgba(0,0,0,0.92);z-index:10002;display:flex;align-items:center;justify-content:center;cursor:zoom-out;");
    const img = document.createElement("img");
    img.src = api.apiURL(`/jzl/asset_full?path=${encodeURIComponent(path)}`);
    img.style.cssText = "max-width:94vw;max-height:94vh;object-fit:contain;border-radius:4px;box-shadow:0 10px 40px rgba(0,0,0,0.6);";
    img.onerror = () => { img.remove(); overlay.append(el("div", "color:#999;font-size:14px;", "原图加载失败")); };
    overlay.appendChild(img);
    overlay.addEventListener("click", () => overlay.remove());
    document.body.appendChild(overlay);
}

function makeAssetCard(kind, index, item, list, onEdit, onDelete, isLast, refreshAll) {
    const refreshAllFn = refreshAll || (() => {});
    const row = el("div", "display:flex;align-items:center;gap:8px;margin:5px 0;padding:6px 8px;background:var(--comfy-menu-bg,#232323);border:1px solid var(--border-color,#3a3a3a);border-radius:6px;");

    // 顺序：启用开关 → 类型（先选）→ 编号（字母 A-Z）→ 槽位标签（角色A）
    const chk = el("input", "width:18px;height:18px;accent-color:#2d9d6f;cursor:pointer;");
    chk.type = "checkbox";
    chk.checked = item.enabled !== false;
    chk.title = "启用/禁用该素材";
    chk.addEventListener("change", () => { item.enabled = chk.checked; onEdit(); refreshAllFn(); });

    // 类型下拉（放前面，先选类型）
    const typeSel = el("select", "flex:0 0 62px;background:var(--comfy-input-bg,#1d1d1d);color:var(--fg-color,#ddd);border:1px solid var(--border-color,#444);border-radius:4px;padding:5px 2px;font-size:12px;");
    for (const t of (ASSET_TYPES_BY_KIND[kind] || ASSET_TYPES)) {
        const o = el("option", "", t);
        if (t === item.type) o.selected = true;
        typeSel.append(o);
    }

    // 字母编号（A-Z）：同一类型已被其他素材占用的字母隐藏，防止同类同编号
    const letterSel = el("select", "width:42px;background:var(--comfy-input-bg,#1d1d1d);color:var(--fg-color,#ddd);border:1px solid var(--border-color,#444);border-radius:4px;padding:4px 1px;font-size:12px;text-align:center;cursor:pointer;");
    letterSel.title = "编号（26 字母 A-Z，同一类型内唯一）";
    const usedLetters = () => {
        const used = new Set();
        (list || []).forEach((it, idx) => {
            if (idx === index) return;
            if (it?.enabled === false) return;
            if ((it?.type || "") === (item.type || "")) {
                const L = (it?.letter || "").toUpperCase();
                if (L) used.add(L);
            }
        });
        return used;
    };
    const renderLetters = () => {
        const used = usedLetters();
        letterSel.innerHTML = "";
        // 空白项「—」= 未指定编号（生成时后端按类型自动分配 A/B/C…）；新增默认空白，不占编号、不顶掉前面的
        const blank = el("option", "", "—");
        blank.value = "";
        blank.title = "未指定编号（生成时按类型自动分配）";
        if (!(item.letter || "").trim()) blank.selected = true;
        letterSel.append(blank);
        // 26 字母全部显示；已被同类其他素材占用的置灰禁用（可见但不可选），切换/换编号后实时刷新
        const cur = (item.letter || "").trim().toUpperCase();
        for (let i = 0; i < 26; i++) {
            const L = String.fromCharCode(65 + i);
            const o = el("option", "", L);
            if (L === cur) o.selected = true;
            if (used.has(L) && L !== cur) o.disabled = true;
            letterSel.append(o);
        }
    };
    const slotTag = el("span", "font-size:11px;color:#ffd166;white-space:nowrap;flex:0 0 auto;min-width:42px;text-align:center;font-weight:600;", "");
    const renderSlot = () => {
        const st = slotTypeOf(kind, item?.type || "");
        const L = (item?.letter || "").trim().toUpperCase();
        const tag = L || "?";
        slotTag.textContent = `${st}${tag}`;
        slotTag.title = `调度槽位：${st}${tag}（未指定编号时生成自动分配；ref 描述与调度 slots 用）`;
    };
    typeSel.addEventListener("change", () => { item.type = typeSel.value; renderLetters(); renderSlot(); onEdit(); refreshAllFn(); });
    letterSel.addEventListener("change", () => { item.letter = letterSel.value; renderSlot(); onEdit(); refreshAllFn(); });
    renderLetters();
    renderSlot();

    row.append(chk, typeSel, letterSel, slotTag);

    // 缩略图：图片预览；音频空槽黑底🎧 / 已选蓝底+试听；视频黑底图标
    const thumb = el("div", "flex:0 0 44px;width:44px;height:44px;border-radius:5px;border:1px solid var(--border-color,#444);background:#000;display:flex;align-items:center;justify-content:center;overflow:hidden;font-size:18px;");
    let imgEl = null;
    let refreshAudio = null;  // 音频试听刷新（kind==="audio" 时赋值）
    const refreshThumb = () => {
        if (kind !== "image" || !imgEl) return;
        const p = (item.path || "").trim();
        if (p) {
            imgEl.src = api.apiURL(`/jzl/asset_preview?path=${encodeURIComponent(p)}`);
            imgEl.style.display = "";
        } else {
            imgEl.style.display = "none";  // 空槽口纯黑
        }
    };
    if (kind === "image") {
        imgEl = el("img", "width:100%;height:100%;object-fit:cover;");
        imgEl.alt = "";
        imgEl.onerror = () => { imgEl.style.display = "none"; };
        thumb.append(imgEl);
        thumb.title = "点击查看原图";
        thumb.style.cursor = "pointer";
        thumb.addEventListener("click", () => {
            const p = (item.path || "").trim();
            if (p) showFullImage(p);
        });
    } else if (kind === "audio") {
        // 音频：空槽黑底🎧；已选蓝底 + ▶/⏸ 试听
        const playBtn = el("button", "width:100%;height:100%;border:none;background:transparent;color:#fff;font-size:16px;cursor:pointer;line-height:1;padding:0;", "🎧");
        thumb.appendChild(playBtn);
        refreshAudio = () => {
            const p = (item.path || "").trim();
            if (p) {
                thumb.style.background = "#2d5a88";  // 蓝色：已选
                playBtn.textContent = "▶";
                playBtn.title = "试听（点击播放/暂停）";
            } else {
                thumb.style.background = "#000";     // 黑色：空槽
                playBtn.textContent = "🎧";
                playBtn.title = "空槽位（未选择音频）";
            }
        };
        let audioEl = null;
        playBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            const p = (item.path || "").trim();
            if (!p) return;
            if (audioEl && !audioEl.paused) {
                audioEl.pause();
                playBtn.textContent = "▶";
                return;
            }
            if (!audioEl) {
                audioEl = new Audio();
                audioEl.src = api.apiURL(`${AUDIO_PREVIEW_ENDPOINT}?path=${encodeURIComponent(p)}`);
                audioEl.onended = () => { playBtn.textContent = "▶"; };
                audioEl.onerror = () => { playBtn.textContent = "▶"; };
            }
            audioEl.play().then(() => { playBtn.textContent = "⏸"; }).catch(() => { playBtn.textContent = "▶"; });
        });
        thumb.title = "音频试听";
        refreshAudio();
    } else {
        thumb.textContent = "🎬";
        thumb.style.background = "#000";
    }
    row.append(thumb);

    // 名称输入
    const nameInp = el("input", "flex:0 0 26%;width:0;background:var(--comfy-input-bg,#1d1d1d);color:var(--fg-color,#ddd);border:1px solid var(--border-color,#444);border-radius:4px;padding:6px;font-size:12px;");
    nameInp.type = "text";
    nameInp.placeholder = "名称（如：孙悟空）";
    nameInp.value = item.name || "";
    nameInp.addEventListener("change", () => { item.name = nameInp.value.trim(); onEdit(); });

    // 详细描述输入（路径只由「上传素材」按钮设置，不再显示路径输入框）
    const descInp = el("input", "flex:1 1 120px;width:0;background:var(--comfy-input-bg,#1d1d1d);color:var(--fg-color,#ccc);border:1px solid var(--border-color,#444);border-radius:4px;padding:6px;font-size:11px;");
    descInp.type = "text";
    descInp.placeholder = "详细描述（如：黑色刺猬头、橙色龟仙流武道服…）";
    descInp.value = item.description || "";
    descInp.addEventListener("change", () => { item.description = descInp.value.trim(); onEdit(); });

    const pickBtn = el("button", "flex:0 0 auto;background:#2a4a6a;color:#cfe3f7;border:1px solid #5b9bd5;border-radius:4px;padding:6px 8px;font-size:12px;cursor:pointer;", "上传素材");
    pickBtn.title = "选择文件";
    pickBtn.addEventListener("click", async () => {
        const p = await chooseFile(kind);
        if (p) { item.path = p; refreshThumb(); if (refreshAudio) refreshAudio(); onEdit(); }
    });

    row.append(nameInp, descInp, pickBtn);

    // 删除按钮：仅最后一个槽位显示（防止中间删除导致顺序错乱）
    if (isLast) {
        const delBtn = el("button", "flex:0 0 auto;background:transparent;color:#e08a8a;border:1px solid #844;border-radius:4px;padding:6px 8px;font-size:12px;cursor:pointer;", "删除槽位");
        delBtn.title = "删除此槽位（只允许删除最后一个）";
        delBtn.addEventListener("click", onDelete);
        row.append(delBtn);
    }

    refreshThumb();
    return row;
}

function renderAssetSection(c, kind, list, title) {
    const fireEdit = () => c.dispatchEvent(new Event("change", { bubbles: true }));
    c.append(makeSectionTitle(title));
    const box = el("div", "");
    // 拖拽排序：拖动某张卡片放到另一张上即「交换位置」（同一类型内调整顺序）
    let dragFrom = -1;
    const wireDrag = (card, i) => {
        card.draggable = true;
        card.style.cursor = "grab";
        card.addEventListener("dragstart", (e) => {
            dragFrom = i;
            try { e.dataTransfer.effectAllowed = "move"; e.dataTransfer.setData("text/plain", String(i)); } catch (_) {}
        });
        card.addEventListener("dragover", (e) => {
            e.preventDefault();
            try { e.dataTransfer.dropEffect = "move"; } catch (_) {}
        });
        card.addEventListener("drop", (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (dragFrom >= 0 && dragFrom !== i && list[dragFrom] && list[i]) {
                const tmp = list[dragFrom];
                list[dragFrom] = list[i];
                list[i] = tmp;
                dragFrom = -1;
                renderList();
                fireEdit();
            }
            dragFrom = -1;
        });
        card.addEventListener("dragend", () => { dragFrom = -1; });
    };
    const renderList = () => {
        box.innerHTML = "";
        list.forEach((item, i) => {
            const isLast = i === list.length - 1;
            const card = makeAssetCard(kind, i, item, list, fireEdit, () => {
                list.splice(i, 1);
                renderList();
                fireEdit();
            }, isLast, renderList);
            wireDrag(card, i);
            box.append(card);
        });
        const addBtn = el("button", "margin-top:4px;width:100%;padding:6px;background:#2a3a4a;color:#9fc3e8;border:1px dashed #5b9bd5;border-radius:6px;font-size:12px;cursor:pointer;", `+ 添加${KIND_LABEL[kind]}`);
        addBtn.addEventListener("click", () => {
            list.push({ type: (ASSET_TYPES_BY_KIND[kind] || ASSET_TYPES)[0], name: "", path: "", enabled: true, letter: "" });
            renderList();
            fireEdit();
        });
        box.appendChild(addBtn);
    };
    renderList();
    c.append(box);
}

function openModal(node, panelId) {
    if (modal) { modal.overlay?.querySelector?.("input,button,select")?.focus?.(); return; }

    loadManager(node).then((data) => {
        buildModal(node, data, panelId);
    }).catch((e) => {
        notify("读取管理器配置失败：" + e.message, "error");
        buildModal(node, { settings: null, llm_models: [], mmproj_models: ["None"], chat_handlers: ["None"] }, panelId);
    });
}

function ensureManagerStyle() {
    if (document.getElementById("jzl-asset-style")) return;
    const st = el("style", "");
    st.id = "jzl-asset-style";
    st.textContent = [
        ".jzl-count-input::-webkit-inner-spin-button,",
        ".jzl-count-input::-webkit-outer-spin-button{-webkit-appearance:none;margin:0}",
        ".jzl-count-input{-moz-appearance:textfield;appearance:textfield}",
        // 弹窗原生控件（对齐 ComfyUI 输入框主题）
        ".jzl-input{box-sizing:border-box;background:var(--comfy-input-bg,#2a2a2a);color:var(--fg-color,#ddd);border:1px solid var(--border-color,#444);border-radius:4px;padding:6px 10px;font-size:13px;outline:none;}",
        ".jzl-input:hover{background:var(--comfy-input-bg-hover,#3a3a3a);}",
        ".jzl-input:focus{border-color:#5b9bd5;}",
        ".jzl-input option{background:var(--comfy-menu-bg,#2a2a2a);}",
        "[contenteditable][data-placeholder]:empty:before{content:attr(data-placeholder);color:#666;font-size:12px;}",
        "[contenteditable]:focus{outline:none;border-color:#5b9bd5;}",
        ".jzl-asset-token{display:inline-flex;align-items:center;gap:2px;padding:0 3px;margin:0 1px;border-radius:3px;background:#2f3540;user-select:none;cursor:default;vertical-align:middle;}",
        ".jzl-asset-token .jzl-asset-thumb{display:inline-block;width:20px;height:20px;object-fit:cover;border-radius:3px;border:1px solid #555;vertical-align:middle;}",
        ".jzl-asset-token[data-jzl-kind='video']::before{content:'🎬';font-size:12px;}",
        ".jzl-asset-token[data-jzl-kind='audio']::before{content:'🎧';font-size:12px;}",
        // 弹窗内勾选框统一 18px 橙色（素材库卡片用内联样式绿色覆盖，不受影响）
        ".jzl-modal input[type='checkbox']{width:18px;height:18px;accent-color:#f59e0b;cursor:pointer;}",
    ].join("\n");
    document.head.append(st);
}

// ── ➕ 提示词元素（融合 JZL_MiniMaxH3PromptEditor 手写提示词全套模板）──
const H3_EXAMPLE_TEXT = `[SHOT_START]

===H3_PROMPT===
subject_definitions:
<Subject 1> 是 <Picture 1> 中的龟仙屋，临海沙滩上的粉色两层小屋，红色尖顶屋顶，墙面印有 KAME HOUSE 字样，四周棕榈树环绕，面朝蔚蓝大海。
<Subject 2> 是 <Picture 2> 中的孙悟空，标志性的黑色刺猬头爆炸发型，身穿橙色龟仙流武道服，蓝色腰带，深蓝色内衣和护腕，脚穿蓝红相间武道靴，有一条棕色的猴子尾巴。

summary:
[reference generation + audio reference] 目标视频展现 <Subject 2> 与 <Subject 3> 在 <Subject 1> 的龟仙屋前收拾行囊、并肩启程前往武道会的场景。

retention_analysis:
<Subject 1> (出现在 [Shot 1], [Shot 2], [Shot 3]): fully_preserved - 粉色两层小屋、红色尖顶、KAME HOUSE 字样、棕榈树环绕。

detailed_description:

正午阳光从海面方向斜照，暖金色调铺满整座沙滩，写实电影级 3D 渲染风格，高饱和暖色主导，画面充满热血少年出发前的昂扬张力。

[Shot 1] 全景镜头确立 <Subject 1> 的龟仙屋全貌，粉色两层小屋的红色尖顶在暖阳下泛着微光，墙面 "KAME HOUSE" 字样清晰可辨。<Subject 2> 孙悟空蹲在门廊前，把最后一件橙色武道服用力塞进行囊，随即直起身，黑色刺猬头在海风里微微晃动。他转头望向门框方向，以参考自 <Audio 1> 的年轻音色说道：<d>[中文] 我收拾好了。</d>
overall_soundscape: 海风呼啸掠过棕榈叶，海浪拍打沙滩的哗啦声，行囊布料摩擦的沙沙声。

non_diegetic_music: N/A

===SCENE_INSTRUCTION===
{"slots":["场景:场景A","角色:角色A","角色:角色D"]}

===AUDIO_INSTRUCTION===
{"slots":["音频:音频A","音频:音频D"]}
[SHOT_END]`;

// [按钮标签, 插入内容, 是否末尾换行]
const H3_TAGS = [
    ["1. 示例文本", H3_EXAMPLE_TEXT, true],
    ["2. 段落开头", "[SHOT_START]\n===H3_PROMPT===", true],
    ["3. 段落结尾", "[SHOT_END]", true],
    ["4. 主体描述", "subject_definitions:\n<Subject 1> 是 <Picture 1> 中的**，***。\n<Subject 2> 是 <Picture 2> 中的**，***。\n<Subject 3> 是 <Picture 3> 中的**，***。", true],
    ["5. 视频摘要", "summary:\n[reference generation] 目标视频展现 ***。", true],
    ["6. 详细描述", "detailed_description:\n目标视频采用***风格，***。", true],
    ["7. 新建分镜", "[Shot 1] ", false],
    ["8. 整体声效", "overall_soundscape: 海浪拍打沙滩的哗啦声，棕榈叶沙沙作响，远处海鸥鸣叫。", true],
    ["9. 背景音效", "non_diegetic_music: N/A", true],
    ["10. 参考图片调用", '===SCENE_INSTRUCTION===\n{"slots":["场景:场景A","角色:角色A","道具:道具A"]}', true],
    ["11. 参考视频调用", '===VIDEO_INSTRUCTION===\n{"slots":["视频:视频A","视频:视频B"]}', true],
    ["12. 参考音频调用", '===AUDIO_INSTRUCTION===\n{"slots":["音频:音频A","音频:音频B"]}', true],
];

function closePromptElements() {
    document.getElementById("jzl-prompt-elements")?.remove();
    if (window.__jzlElEsc) {
        window.removeEventListener("keydown", window.__jzlElEsc);
        window.__jzlElEsc = null;
    }
}

function insertPromptElement(editable, text, trailing) {
    // 在内部编辑窗口（contenteditable）光标处插入提示词元素模板（自动另起一行）
    if (!editable) return;
    editable.focus();
    const sel = window.getSelection();
    let range = null;
    if (sel && sel.rangeCount) {
        const r0 = sel.getRangeAt(0);
        if (editable.contains(r0.startContainer)) range = r0;
    }
    if (!range) {
        range = document.createRange();
        range.selectNodeContents(editable);
        range.collapse(false);
    }
    const tmp = document.createElement("div");
    const pr = document.createRange();
    pr.selectNodeContents(editable);
    pr.setEnd(range.startContainer, range.startOffset);
    tmp.appendChild(pr.cloneContents());
    const prefix = getPromptText(tmp);
    let insert = "";
    if (prefix && !prefix.endsWith("\n")) insert += "\n";
    insert += text;
    if (trailing) insert += "\n";
    const tn = document.createTextNode(insert);
    range.deleteContents();
    range.insertNode(tn);
    const caret = document.createRange();
    caret.setStartAfter(tn);
    caret.collapse(true);
    sel.removeAllRanges();
    sel.addRange(caret);
    editable.dispatchEvent(new Event("input", { bubbles: true }));
    editable.dispatchEvent(new Event("change"));
}

// ── 原生提示词 textarea：@ 素材菜单（悬浮窗定位在光标后面）──
function getPromptTextarea(w) {
    if (!w) return null;
    if (w.element?.tagName === "TEXTAREA") return w.element;
    if (w.element?.querySelector) {
        const ta = w.element.querySelector("textarea");
        if (ta) return ta;
    }
    if (w.inputEl?.tagName === "TEXTAREA") return w.inputEl;
    return null;
}

function setupInternalPrompt(node, box, ipWidget) {
    // 提示词来源只有节点内编辑框（外部提示词端口已删除）：输入同步到 internal_prompt
    const syncInternal = () => {
        if (ipWidget) setWidgetValue(ipWidget, getPromptText(box));
    };
    box.addEventListener("input", () => {
        syncInternal();
        const offset = caretOffset(box);
        promptCaretPos = offset;  // 记忆光标位置，供资产窗点击插入
        const before = getPromptText(box).slice(0, offset);
        const m = before.match(/@([^@\s]*)$/);
        if (m) openMentionMenu(box, offset - m[0].length, offset, m[1], node);
        else closeMentionMenu();
    });
    box.addEventListener("keyup", () => { promptCaretPos = caretOffset(box); });
    box.addEventListener("click", () => { promptCaretPos = caretOffset(box); });
    box.addEventListener("change", syncInternal);
    // 粘贴：阻止 ComfyUI 画布把剪贴板里的「节点 JSON」粘贴到画布，只插入纯文本到提示词
    box.addEventListener("paste", (e) => {
        e.stopPropagation();
        e.preventDefault();
        const text = (e.clipboardData || window.clipboardData)?.getData("text/plain") || "";
        if (!text) return;
        const sel = window.getSelection();
        let range = null;
        if (sel && sel.rangeCount) {
            const r0 = sel.getRangeAt(0);
            if (box.contains(r0.startContainer)) range = r0;
        }
        if (!range) {
            range = document.createRange();
            range.selectNodeContents(box);
            range.collapse(false);
        }
        const frag = document.createDocumentFragment();
        String(text).replace(/\r\n/g, "\n").split("\n").forEach((line, idx) => {
            if (idx > 0) frag.appendChild(document.createElement("br"));
            frag.appendChild(document.createTextNode(line));
        });
        range.deleteContents();
        range.insertNode(frag);
        range.collapse(false);
        sel.removeAllRanges();
        sel.addRange(range);
        box.dispatchEvent(new Event("input", { bubbles: true }));
        box.dispatchEvent(new Event("change"));
    });
    box.addEventListener("blur", () => setTimeout(closeMentionMenu, 150));
    // internal_prompt 是内部存储字段：拒绝接线（幽灵防护）
    const origCC = node.onConnectionsChange;
    node.onConnectionsChange = function (type, index, connected, link_info) {
        const r = origCC?.apply(this, arguments);
        if (type === 1 && this.inputs && this.inputs[index]) {
            const inp = this.inputs[index];
            if (inp.name === "internal_prompt" && connected) {
                try {
                    const lid = link_info?.id != null ? link_info.id : (typeof link_info === "number" ? link_info : null);
                    inp.link = null;
                    inp.socketless = true;
                    if (lid != null && this.graph && this.graph.links) {
                        const l = this.graph.links[lid];
                        if (l) {
                            const origin = this.graph.getNodeById(l.origin_id);
                            if (origin && origin.outputs && origin.outputs[l.origin_slot] && Array.isArray(origin.outputs[l.origin_slot].links)) {
                                const ol = origin.outputs[l.origin_slot].links;
                                const idx = ol.indexOf(lid);
                                if (idx >= 0) ol.splice(idx, 1);
                            }
                            delete this.graph.links[lid];
                        }
                    }
                    this.setDirtyCanvas?.(true, true);
                } catch (_) {}
            }
        }
        return r;
    };
    syncInternal();
}

function caretCoords(ta) {
    // 用镜像 div 精确计算 textarea 光标位置（@ 菜单定位在光标后面）
    const pos = ta.selectionStart ?? ta.value.length;
    const mirror = document.createElement("div");
    const cs = getComputedStyle(ta);
    mirror.style.cssText = `position:fixed;left:-10000px;top:0;visibility:hidden;white-space:pre-wrap;word-break:break-word;` +
        `font-size:${cs.fontSize};font-family:${cs.fontFamily};line-height:${cs.lineHeight};` +
        `width:${ta.clientWidth}px;box-sizing:border-box;` +
        `padding-top:${cs.paddingTop};padding-right:${cs.paddingRight};padding-bottom:${cs.paddingBottom};padding-left:${cs.paddingLeft};` +
        `border:${cs.borderWidth} ${cs.borderStyle} ${cs.borderColor};`;
    mirror.textContent = ta.value.slice(0, pos);
    const mark = document.createElement("span");
    mark.textContent = "\u200b";
    mirror.appendChild(mark);
    document.body.appendChild(mirror);
    const mr = mark.getBoundingClientRect();
    const mm = mirror.getBoundingClientRect();
    const tr = ta.getBoundingClientRect();
    document.body.removeChild(mirror);
    return { x: tr.left + (mr.left - mm.left), y: tr.top + (mr.top - mm.top) };
}

function openMentionMenuAtCaret(node, ta, start, end, query) {
    const q = (query || "").toLowerCase();
    const items = collectMentionItems(node).filter((it) => {
        if (!q) return true;
        return it.type.toLowerCase().includes(q) || it.name.toLowerCase().includes(q);
    });
    if (!items.length) { closeMentionMenu(); return; }
    closeMentionMenu();
    mentionState = { ta, start, end, mode: "textarea" };

    const pos = caretCoords(ta);
    const menu = document.createElement("div");
    menu.style.cssText = "position:fixed;z-index:10001;background:#1e1e1e;border:1px solid #444;border-radius:8px;max-height:340px;max-width:460px;overflow-y:auto;box-shadow:0 8px 20px rgba(0,0,0,0.5);padding:8px;";
    menu.style.left = pos.x + "px";
    menu.style.top = (pos.y + 6) + "px";

    const cols = items.length <= 3 ? items.length : Math.min(5, Math.max(3, Math.ceil(Math.sqrt(items.length))));
    const grid = document.createElement("div");
    grid.style.cssText = `display:grid;grid-template-columns:repeat(${cols},74px);gap:8px;`;
    for (const item of items) {
        const cell = document.createElement("div");
        cell.style.cssText = "display:flex;flex-direction:column;align-items:center;gap:3px;cursor:pointer;border-radius:6px;padding:4px;border:1px solid transparent;";
        const thumb = document.createElement("div");
        thumb.style.cssText = "width:64px;height:64px;border-radius:5px;border:1px solid #444;background:#111;display:flex;align-items:center;justify-content:center;overflow:hidden;font-size:26px;";
        if (item.kind === "image") {
            const img = document.createElement("img");
            img.style.cssText = "width:100%;height:100%;object-fit:cover;";
            img.src = item.path ? `${ASSET_PREVIEW_ENDPOINT}?path=${encodeURIComponent(item.path)}` : "";
            img.onerror = () => { img.src = "/extensions/ComfyUI-JZL-MiniMax-H3/icon.png"; };
            thumb.appendChild(img);
        } else {
            thumb.textContent = item.kind === "video" ? "🎬" : "🎧";
        }
        const typeTag = document.createElement("span");
        typeTag.style.cssText = "font-size:10px;color:#8ab8dd;line-height:1;";
        typeTag.textContent = item.type || KIND_LABEL[item.kind] || "";
        const label = document.createElement("span");
        label.style.cssText = "font-size:11px;color:#ddd;line-height:1.2;max-width:70px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-align:center;";
        label.textContent = item.slotLabel || item.name;
        cell.append(thumb, typeTag, label);
        cell.addEventListener("mousedown", (e) => { e.preventDefault(); e.stopPropagation(); });
        cell.addEventListener("click", () => chooseMentionText(ta, item));
        cell.addEventListener("mouseenter", () => { cell.style.border = "1px solid #5b9bd5"; cell.style.background = "#2a2a2a"; });
        cell.addEventListener("mouseleave", () => { cell.style.border = "1px solid transparent"; cell.style.background = "transparent"; });
        grid.appendChild(cell);
    }
    menu.appendChild(grid);
    document.body.appendChild(menu);
    mentionMenu = menu;
}

function chooseMentionText(ta, item) {
    if (!mentionState || mentionState.mode !== "textarea") return;
    const { start, end } = mentionState;
    closeMentionMenu();
    const token = item.token;
    const text = ta.value;
    const next = text.slice(0, start) + token + " " + text.slice(end);
    ta.value = next;
    const pos = start + token.length + 1;
    try { ta.focus(); ta.setSelectionRange(pos, pos); } catch (_) {}
    ta.dispatchEvent(new Event("input", { bubbles: true }));
    ta.dispatchEvent(new Event("change"));
}

function showPromptElements(self) {
    const box = self?.__promptBox;
    if (!box) return;
    closePromptElements();
    const overlay = document.createElement("div");
    overlay.id = "jzl-prompt-elements";
    overlay.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:99999;display:flex;align-items:center;justify-content:center;";
    overlay.addEventListener("mousedown", (e) => { if (e.target === overlay) closePromptElements(); });
    const panel = document.createElement("div");
    panel.style.cssText = "background:#1b1b1f;border:1px solid #444;border-radius:10px;padding:14px;max-width:640px;width:92%;max-height:80vh;overflow-y:auto;box-shadow:0 10px 40px rgba(0,0,0,.6);";
    const title = document.createElement("div");
    title.textContent = "➕ 提示词元素（插入到提示词光标处，自动另起一行）";
    title.style.cssText = "color:#eee;font-size:14px;font-weight:600;margin-bottom:10px;";
    panel.appendChild(title);
    const grid = document.createElement("div");
    grid.style.cssText = "display:grid;grid-template-columns:repeat(3,1fr);gap:6px;";
    for (const [label, tag, trailing] of H3_TAGS) {
        const b = document.createElement("button");
        b.textContent = label;
        b.style.cssText = "padding:7px 6px;border:1px solid #555;border-radius:6px;background:#2a2a2e;color:#eee;cursor:pointer;font-size:12px;line-height:1;";
        b.addEventListener("mouseenter", () => { b.style.background = "#3a3a40"; });
        b.addEventListener("mouseleave", () => { b.style.background = "#2a2a2e"; });
        b.addEventListener("click", () => { insertPromptElement(box, tag, trailing); closePromptElements(); });
        grid.appendChild(b);
    }
    panel.appendChild(grid);
    overlay.appendChild(panel);
    document.body.appendChild(overlay);
    window.__jzlElEsc = (e) => { if (e.key === "Escape") closePromptElements(); };
    window.addEventListener("keydown", window.__jzlElEsc);
}

// ── 表单控件 ──────────────────────────────────────────────
function field(labelText, control) {
    // 原生感：无卡片背景，标签 + 控件对齐（对齐官方设置面板）
    const g = el("div", "display:flex;align-items:center;gap:12px;margin-bottom:10px;");
    const lab = el("label", "flex:0 0 160px;font-size:13px;color:var(--descrip-text,#999);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;", labelText);
    control.style.flex = "1 1 0";
    control.style.minWidth = "0";
    // 复选框/开关是 label 包裹，不加输入框样式；真正的输入控件才有 .jzl-input（等宽由 flex 保证）
    if (control.tagName === "INPUT" || control.tagName === "SELECT" || control.tagName === "TEXTAREA") {
        control.classList.add("jzl-input");
    }
    g.append(lab, control);
    return g;
}

function selectControl(options, value, onChange) {
    const s = el("select", "flex:1 1 0;min-width:0;");
    s.className = "jzl-input";
    for (const o of options) {
        const op = el("option", "", o);
        if (o === value) op.selected = true;
        s.append(op);
    }
    s.addEventListener("change", () => onChange(s.value));
    return s;
}

function textControl(value, placeholder, onChange) {
    const i = el("input", "flex:1 1 0;min-width:0;");
    i.className = "jzl-input";
    i.type = "text";
    i.value = value || "";
    if (placeholder) i.placeholder = placeholder;
    i.addEventListener("change", () => onChange(i.value.trim()));
    return i;
}

function passwordControl(value, placeholder, onChange) {
    // 密码型输入：明文不显示（API Key 等敏感字段）
    const i = el("input", "flex:1 1 0;min-width:0;");
    i.className = "jzl-input";
    i.type = "password";
    i.value = value || "";
    if (placeholder) i.placeholder = placeholder;
    i.addEventListener("change", () => onChange(i.value.trim()));
    return i;
}

function numberControl(value, opts, onChange) {
    const i = el("input", "flex:1 1 0;min-width:0;");
    i.className = "jzl-input";
    i.type = "number";
    i.value = value;
    if (opts) { i.min = opts.min; i.max = opts.max; i.step = opts.step; }
    i.addEventListener("change", () => onChange(parseFloat(i.value) || 0));
    return i;
}

function checkboxControl(value, labelText, onChange) {
    const w = el("label", "display:flex;align-items:center;gap:10px;cursor:pointer;font-size:13px;color:var(--fg-color,#ddd);");
    const c = el("input", "width:18px;height:18px;accent-color:#f59e0b;cursor:pointer;");
    c.type = "checkbox";
    c.checked = !!value;
    c.addEventListener("change", () => onChange(c.checked));
    w.append(c, el("span", "", labelText));
    return w;
}

// control_after_generate（生成后控制）：随机/固定/增加/减少
const SEED_CONTROL_KEYS = ["randomize", "fixed", "increment", "decrement"];
const SEED_CONTROL_LABEL = { randomize: "随机", fixed: "固定", increment: "增加", decrement: "减少" };

function seedControlRow(p, fieldKey = "seed", modeKey = "seed_control", labelText = "种子") {
    // 原生感：标签 + 数字输入 + control_after_generate 按钮（点击循环 随机/固定/增加/减少）
    const g = el("div", "display:flex;align-items:center;gap:12px;margin-bottom:10px;");
    const lab = el("label", "flex:0 0 160px;font-size:13px;color:var(--descrip-text,#999);white-space:nowrap;", labelText);
    const i = el("input", "flex:1;min-width:0;");
    i.type = "number";
    i.value = p[fieldKey] ?? 0;
    i.min = 0; i.max = 0xffffffffffffffff; i.step = 1;
    i.className = "jzl-input";
    i.addEventListener("change", () => { p[fieldKey] = Math.round(parseFloat(i.value) || 0); });
    const ctrl = el("button", "flex:1 1 0;min-width:0;background:#b45309;color:#fff;border:1px solid #d97706;border-radius:4px;padding:6px 10px;font-size:12px;cursor:pointer;white-space:nowrap;text-align:center;");
    const curKey = () => (SEED_CONTROL_LABEL[p[modeKey]] ? p[modeKey] : "randomize");
    const render = () => {
        ctrl.textContent = "🔁 " + SEED_CONTROL_LABEL[curKey()];
        ctrl.title = "生成后控制（control_after_generate）：随机=每次运行自动换新种子；固定=锁定当前值；递增=每次运行+1。点击切换";
    };
    ctrl.addEventListener("click", () => {
        const next = SEED_CONTROL_KEYS[(SEED_CONTROL_KEYS.indexOf(curKey()) + 1) % SEED_CONTROL_KEYS.length];
        p[modeKey] = next;
        render();
        g.dispatchEvent(new Event("change", { bubbles: true }));  // 触发面板自动保存
    });
    render();
    g.append(lab, i, ctrl);
    return g;
}

function defaultSettings() {
    return {
        auto_save: true,
        align_mode: "text",
        models: {
            fl2va: { model: "", loras: [] },
            ref2va: { model: "", loras: [] },
            common: { clip: "", video_vae: "", audio_vae: "" },
        },
        assets: { images: [], videos: [], audios: [] },
        enhance: {
            story_decompose: true,
            enabled: false,
            llm_backend: "本地模型 [local]",
            force_offload: false,
            seed: 0, seed_control: "randomize",
            llm: {
                model: "", mmproj: "None", chat_handler: "None",
                backend: "llama-cpp-python", n_ctx: 32768, vram_limit: -1,
                image_min_tokens: 0, image_max_tokens: 0, max_tokens: 8192,
                top_k: 40, top_p: 0.9, min_p: 0.05, typical_p: 1.0,
                temperature: 0.6, repeat_penalty: 1.05, frequency_penalty: 0.0,
                present_penalty: 0.0, mirostat_mode: 0, mirostat_eta: 0.1,
                mirostat_tau: 5.0, gpu_device: "auto",
            },
            api: {
                provider: "OpenAI 兼容 (OpenAI/DeepSeek/Qwen/GLM/Kimi/Ollama/vLLM/LM Studio)",
                model: "deepseek-v4-flash", api_key: "", base_url: "https://api.deepseek.com/v1",
                temperature: 0.6, max_tokens: 8192, thinking: "disabled",
            },
            preference: {
                shot_size: "随机组合", camera_move: "随机组合", cut_rhythm: "随机",
                transition: "随机", music_style: "禁止音乐 / No Music",
                creative_req: "无特别要求", detail_length: "标准 (350-500字)", custom: "",
            },
            custom_prompt: "", system_prompt: "",
            inference_mode: "one by one", max_frames: 24, max_size: 256,
        },
        gen_params: {
            aspect_ratio: "16:9 (Widescreen)", megapixels: 1.0, multiple: 32, duration: 8,
            width: 0, height: 0, scale_factor: 1.0, upscale_scale: 1.5,
        },
        sample_decode: {
            sampler: "res_multistep", scheduler: "simple", steps: 4, cfg: 1.0,
            seed: 0, seed_mode: "randomize",
            decode_video: "XB-BOX - VAE解码（原版优化）", decode_cleanup: "卸载显存模型",
            second: {
                enabled: false,
                upscaler_model: "minimax_h3_latent_upscaler_3d_fp32.pth",
                device: "cuda", precision: "fp32",
                sampler: "euler", scheduler: "simple", steps: 3, denoise: 0.3,
                sigmas_mode: "scheduler",
                custom_sigmas: "0.8500, 0.6316, 0.3158, 0.0000",
            },
        },
    };
}

// ── 配置面板 ──────────────────────────────────────────────
// 槽位类型顺序（与后端 _build_asset_intro 的 _SLOT_TYPE_ORDER 一致）
const REF_SLOT_ORDER = { "角色": 0, "场景": 1, "道具": 2, "分镜": 3, "其他": 4, "视频": 0, "音频": 0 };

// 按勾选素材生成只读的三路描述文本（供 LLM 拆解/增强使用，与后端 _build_asset_intro 完全一致）
function buildRefIntro(assets) {
    const out = { image: [], video: [], audio: [] };
    const slotMap = buildSlotMap(assets || {});
    const collect = (kind, key, pool) => {
        ((assets?.[key]) || []).forEach((item, i) => {
            if (item?.enabled === false) return;
            const name = (item?.name || "").trim();
            if (!name) return;
            const st = slotTypeOf(kind, item?.type || "");
            const slot = slotMap[`${kind}:${i}`] || st;
            const desc = (item?.description || "").trim();
            pool.push({ order: REF_SLOT_ORDER[st] ?? 9, L: slot.slice(st.length), text: `${slot} = ${name}${desc ? `（${desc}）` : ""}` });
        });
    };
    collect("image", "images", out.image);
    collect("video", "videos", out.video);
    collect("audio", "audios", out.audio);
    const fmt = (arr) => arr.slice().sort((a, b) => a.order - b.order || a.L.localeCompare(b.L)).map((x) => x.text).join("\n");
    return { image: fmt(out.image), video: fmt(out.video), audio: fmt(out.audio) };
}

function renderAssetsTools(c, s, build) {
    c.append(makeSectionTitle("素材库导入导出"));
    const row = el("div", "display:flex;align-items:center;gap:8px;margin:0 0 4px;");
    const exp = el("button", "flex:1 1 0;background:#2a4a6a;color:#cfe3f7;border:1px solid #5b9bd5;border-radius:4px;padding:7px 10px;font-size:12px;cursor:pointer;white-space:nowrap;", "⬆️ 导出素材库");
    const imp = el("button", "flex:1 1 0;background:#3a5a2a;color:#d7f0c8;border:1px solid #6b9b5b;border-radius:4px;padding:7px 10px;font-size:12px;cursor:pointer;white-space:nowrap;", "⬇️ 导入素材库");
    const status = el("div", "font-size:11px;color:#9fd6a4;margin:0 0 10px;min-height:14px;white-space:pre-wrap;", "");
    const say = (msg, isErr) => {
        status.textContent = msg;
        status.style.color = isErr ? "#e08a8a" : "#9fd6a4";
        try { notify(msg, isErr ? "error" : "success"); } catch (_) {}
    };
    exp.title = "把当前已添加的素材保存为 output/jzl/素材库.txt";
    imp.title = "选择素材库 txt 文件并载入（覆盖当前列表）";
    exp.addEventListener("click", async () => {
        exp.disabled = true; say("正在导出…");
        try {
            const resp = await api.fetchApi("/jzl/export_assets", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ assets: s.assets || { images: [], videos: [], audios: [] } }),
            });
            const data = await resp.json().catch(() => ({}));
            if (data?.ok) say("✅ 已导出：output/jzl/素材库.txt");
            else say(`❌ ${data?.error || ("导出失败（HTTP " + resp.status + "）——请确认已重启 ComfyUI 且新版已部署")}`, true);
            console.log("[JZL 素材库] export resp", resp.status, data);
        } catch (e) { say(`❌ 导出失败：${(e && e.message) || e}`, true); console.error(e); }
        exp.disabled = false;
    });
    imp.addEventListener("click", () => {
        if (!document.__jzlImportInput) {
            const inp = document.createElement("input");
            inp.type = "file";
            inp.accept = ".txt,text/plain";
            inp.style.display = "none";
            document.body.appendChild(inp);
            document.__jzlImportInput = inp;
        }
        const inp = document.__jzlImportInput;
        inp.value = "";
        inp.onchange = async () => {
            const file = inp.files && inp.files[0];
            if (!file) return;
            imp.disabled = true; say(`正在导入 ${file.name}…`);
            try {
                const text = await new Promise((resolve, reject) => {
                    const r = new FileReader();
                    r.onload = () => resolve(r.result || "");
                    r.onerror = () => reject(r.error);
                    r.readAsText(file, "utf-8");
                });
                const resp = await api.fetchApi("/jzl/import_assets", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ text }),
                });
                const data = await resp.json().catch(() => ({}));
                if (data?.ok && data.assets) {
                    s.assets = data.assets;
                    build?.();
                    c.dispatchEvent(new Event("change", { bubbles: true }));  // 触发自动保存
                    const n = (data.assets.images || []).length + (data.assets.videos || []).length + (data.assets.audios || []).length;
                    say(`✅ 已从 ${file.name} 导入 ${n} 个素材并保存`);
                } else {
                    say(`❌ ${data?.error || ("导入失败（HTTP " + resp.status + "）")}`, true);
                }
                console.log("[JZL 素材库] import resp", resp.status, data);
            } catch (e) { say(`❌ 导入失败：${(e && e.message) || e}`, true); console.error(e); }
            imp.disabled = false;
        };
        inp.click();
    });
    row.append(exp, imp);
    c.append(row, status);
}

function renderAssetsPanel(c, s, mode) {
    const assets = s.assets;
    // 素材引用提示（生成路径由引用内容自动推断）
    c.append(el("div", "background:#2b3a4a;border:1px solid #5b9bd5;border-radius:6px;padding:8px 12px;margin-bottom:8px;font-size:12px;color:#cfe3f7;", `素材引用上限：图片 ≤9 / 视频 ≤3 / 音频 ≤3（生成路径按引用内容自动推断：有视频→多参考，≥2图→首尾帧，1图→首帧，无→纯文本）`));

    renderAssetSection(c, "image", assets.images, "🖼️ 图片");
    renderAssetSection(c, "video", assets.videos, "🎬 视频");
    renderAssetSection(c, "audio", assets.audios, "🎧 音频");

    // 底部：只读的「传给 LLM 的素材描述」（按勾选素材自动生成，顺序：角色→场景→道具→自定义，字母 A/B/C）
    c.append(makeSectionTitle("📄 传给 LLM 的素材描述（只读，按勾选自动生成）"));
    const mkRef = (label, getVal) => {
        const row = el("div", "display:flex;align-items:flex-start;gap:10px;margin-bottom:8px;");
        const lab = el("div", "flex:0 0 72px;font-size:12px;color:var(--descrip-text,#999);padding-top:6px;", label);
        const ta = el("textarea", "flex:1;min-width:0;resize:vertical;background:var(--comfy-input-bg,#1d1d1d);color:var(--fg-color,#ccc);border:1px solid var(--border-color,#444);border-radius:4px;padding:6px;font-size:11px;line-height:1.5;");
        ta.readOnly = true;
        const set = () => { const v = getVal(); ta.value = v; ta.rows = Math.max(2, Math.min(8, v.split("\n").length)); };
        set();
        row.append(lab, ta);
        return { row, set };
    };
    const ri = mkRef("图片描述", () => buildRefIntro(s.assets).image);
    const rv = mkRef("视频描述", () => buildRefIntro(s.assets).video);
    const ra = mkRef("音频描述", () => buildRefIntro(s.assets).audio);
    c.append(ri.row, rv.row, ra.row);
    // 素材变化（change 冒泡到 c）时刷新只读描述；委托模式避免重建时重复/失效监听
    c.__jzlRefIntroRefresh = () => { ri.set(); rv.set(); ra.set(); };
    if (!c.__jzlRefIntroBound) {
        c.__jzlRefIntroBound = true;
        c.addEventListener("change", () => { try { c.__jzlRefIntroRefresh?.(); } catch (_) {} });
    }
}

function renderAutoSave(c, s) {
    // 自动保存已移至弹窗底部，与「取消/保存」按钮同行（见 buildModal footer）
}

function renderPromptPanel(c, s, d, node) {
    const p = s.enhance;
    renderAutoSave(c, s);

    // ── 输出语言（最顶优先选择；读写 manager_settings.enhance.prompt_lang，随工作流保存）──
    c.append(makeSectionTitle("输出语言"));
    c.append(field("输出语言", selectControl(["中文 [ZH]", "英文 [EN]"], p.prompt_lang || "中文 [ZH]", v => { p.prompt_lang = v; })));

    // ── 开关 ──
    c.append(makeSectionTitle("开关"));
    c.append(field("故事拆解", checkboxControl(p.story_decompose !== false, "把故事通过 LLM 拆解为分段提示词", v => { p.story_decompose = v; })));
    c.append(field("开启增强", checkboxControl(p.enabled === true, "拆解后对每个分段的详细描述再做润色", v => { p.enabled = v; })));
    c.append(field("强制卸载", checkboxControl(p.force_offload === true, "LLM 用完即卸载（增强开启时等增强后再卸）", v => { p.force_offload = v; })));

    // ── LLM 后端（方形勾选单选：本地 / 在线API，切换只显示对应设置区块；样式与「故事拆解」一致）──
    c.append(makeSectionTitle("LLM 后端"));
    const backendRow = el("div", "display:flex;align-items:center;gap:16px;min-width:0;");
    const backendCbs = [];
    const mkBackendCb = (val, label) => {
        const lab = el("label", "display:flex;align-items:center;gap:6px;font-size:13px;color:var(--descrip-text,#999);cursor:pointer;");
        const c = el("input", "width:18px;height:18px;accent-color:#f59e0b;cursor:pointer;");
        c.type = "checkbox";
        c.checked = (String(p.llm_backend || "").includes("api") ? "在线API [api]" : "本地模型 [local]") === val;
        c.addEventListener("change", () => {
            if (c.checked) {
                p.llm_backend = val;
                backendCbs.forEach((x) => { if (x !== c) x.checked = false; });
                syncBackend();
            } else if (backendCbs.every((x) => !x.checked)) {
                c.checked = true;  // 保持至少一个选中
            }
        });
        lab.append(c, el("span", "", label));
        backendRow.append(lab);
        backendCbs.push(c);
        return c;
    };
    c.append(field("LLM后端", backendRow));

    // ── 本地 LLM 模型 ──
    const localBox = el("div", "");
    localBox.append(makeSectionTitle("本地 LLM 模型"));
    const llm = p.llm || (p.llm = {});
    const llmModels = (d?.llm_models && d.llm_models.length) ? d.llm_models : ["（未找到本地 LLM 模型）"];
    const mmprojModels = (d?.mmproj_models && d.mmproj_models.length) ? d.mmproj_models : ["None"];
    const chatHandlers = (d?.chat_handlers && d.chat_handlers.length) ? d.chat_handlers : ["None"];
    // 关键修复：下拉默认显示第一个模型，但 llm.model 仍为空 → 之前点保存会存成空串触发「未选择本地 LLM 模型」。
    // 打开面板时把「所见即所得」同步进存储：不切换直接保存也会持久化当前显示的模型。
    if (!llm.model && llmModels.length && !llmModels[0].startsWith("（")) llm.model = llmModels[0];
    localBox.append(field("模型", selectControl(llmModels, llm.model || llmModels[0], v => { llm.model = v; })));
    localBox.append(field("视觉模块 mmproj", selectControl(mmprojModels, llm.mmproj || "None", v => { llm.mmproj = v; })));
    localBox.append(field("Chat Handler", selectControl(chatHandlers, llm.chat_handler || "None", v => { llm.chat_handler = v; })));
    localBox.append(field("推理后端", selectControl(["llama-cpp-python", "llama-server"], llm.backend || "llama-cpp-python", v => { llm.backend = v; })));
    localBox.append(field("上下文长度 n_ctx", numberControl(llm.n_ctx ?? 32768, { min: 1024, max: 262144, step: 128 }, v => { llm.n_ctx = Math.round(v); })));
    localBox.append(field("显存上限 vram_limit (GB)", numberControl(llm.vram_limit ?? -1, { min: -1, max: 1024, step: 1 }, v => { llm.vram_limit = Math.round(v); })));
    localBox.append(field("图像最小 tokens", numberControl(llm.image_min_tokens ?? 0, { min: 0, max: 4096, step: 32 }, v => { llm.image_min_tokens = Math.round(v); })));
    localBox.append(field("图像最大 tokens", numberControl(llm.image_max_tokens ?? 0, { min: 0, max: 4096, step: 32 }, v => { llm.image_max_tokens = Math.round(v); })));
    localBox.append(field("max_tokens", numberControl(llm.max_tokens ?? 8192, { min: 0, max: 262144, step: 1 }, v => { llm.max_tokens = Math.round(v); })));
    localBox.append(field("top_k", numberControl(llm.top_k ?? 40, { min: 0, max: 1000, step: 1 }, v => { llm.top_k = Math.round(v); })));
    localBox.append(field("top_p", numberControl(llm.top_p ?? 0.9, { min: 0, max: 1, step: 0.01 }, v => { llm.top_p = v; })));
    localBox.append(field("min_p", numberControl(llm.min_p ?? 0.05, { min: 0, max: 1, step: 0.01 }, v => { llm.min_p = v; })));
    localBox.append(field("typical_p", numberControl(llm.typical_p ?? 1.0, { min: 0, max: 1, step: 0.01 }, v => { llm.typical_p = v; })));
    localBox.append(field("temperature", numberControl(llm.temperature ?? 0.6, { min: 0, max: 2, step: 0.01 }, v => { llm.temperature = v; })));
    localBox.append(field("repeat_penalty", numberControl(llm.repeat_penalty ?? 1.05, { min: 0, max: 10, step: 0.01 }, v => { llm.repeat_penalty = v; })));
    localBox.append(field("frequency_penalty", numberControl(llm.frequency_penalty ?? 0.0, { min: 0, max: 1, step: 0.01 }, v => { llm.frequency_penalty = v; })));
    localBox.append(field("present_penalty", numberControl(llm.present_penalty ?? 0.0, { min: 0, max: 2, step: 0.01 }, v => { llm.present_penalty = v; })));
    localBox.append(field("mirostat_mode", numberControl(llm.mirostat_mode ?? 0, { min: 0, max: 2, step: 1 }, v => { llm.mirostat_mode = Math.round(v); })));
    localBox.append(field("mirostat_eta", numberControl(llm.mirostat_eta ?? 0.1, { min: 0, max: 1, step: 0.01 }, v => { llm.mirostat_eta = v; })));
    localBox.append(field("mirostat_tau", numberControl(llm.mirostat_tau ?? 5.0, { min: 0, max: 10, step: 0.01 }, v => { llm.mirostat_tau = v; })));
    localBox.append(field("GPU 设备", selectControl(["auto", "0", "1", "2", "3"], llm.gpu_device || "auto", v => { llm.gpu_device = v; })));
    c.append(localBox);

    // ── 在线 API ──
    const apiBox = el("div", "");
    apiBox.append(makeSectionTitle("在线 API"));
    const api = p.api || (p.api = {});
    apiBox.append(field("服务商", selectControl(OPTIONS.providers, api.provider || OPTIONS.providers[0], v => { api.provider = v; })));
    apiBox.append(field("模型", textControl(api.model || "deepseek-v4-flash", "deepseek-v4-flash…", v => { api.model = v; })));
    apiBox.append(field("API Key", passwordControl(api.api_key || "", "sk-…（已隐藏）", v => { api.api_key = v; })));
    apiBox.append(field("Base URL", textControl(api.base_url || "https://api.deepseek.com/v1", "https://api.deepseek.com/v1", v => { api.base_url = v; })));
    apiBox.append(field("temperature", numberControl(api.temperature ?? 0.6, { min: 0, max: 2, step: 0.01 }, v => { api.temperature = v; })));
    apiBox.append(field("max_tokens", numberControl(api.max_tokens ?? 8192, { min: 1, max: 262144, step: 1 }, v => { api.max_tokens = Math.round(v); })));
    apiBox.append(field("thinking", selectControl(["disabled", "enabled"], api.thinking || "disabled", v => { api.thinking = v; })));
    c.append(apiBox);

    const syncBackend = () => {
        const isApi = String(p.llm_backend || "").includes("api");
        localBox.style.display = isApi ? "none" : "block";
        apiBox.style.display = isApi ? "block" : "none";
    };
    mkBackendCb("本地模型 [local]", "本地模型");
    mkBackendCb("在线API [api]", "在线API");
    syncBackend();

    // ── 随机种子（剧本处理器与提示词增强共享，含生成后控制） ──
    c.append(makeSectionTitle("随机种子"));
    c.append(seedControlRow(p));

    // ── 指令推理 ──
    c.append(makeSectionTitle("指令推理"));
    c.append(field("自定义提示词", textControl(p.custom_prompt || "", "选填：自定义增强指令…", v => { p.custom_prompt = v; })));
    c.append(field("系统提示词", textControl(p.system_prompt || "", "选填…", v => { p.system_prompt = v; })));
    c.append(field("推理模式", selectControl(OPTIONS.inferenceModes, p.inference_mode || OPTIONS.inferenceModes[0], v => { p.inference_mode = v; })));
    c.append(field("最大帧数", numberControl(p.max_frames ?? 24, { min: 2, max: 1024, step: 1 }, v => { p.max_frames = Math.round(v); })));
    c.append(field("最大尺寸", numberControl(p.max_size ?? 256, { min: 128, max: 16384, step: 64 }, v => { p.max_size = Math.round(v); })));
}

function renderPreferenceSettingsPanel(c, s) {
    const p = s.enhance.preference || (s.enhance.preference = {});
    renderAutoSave(c, s);
    c.append(field("景别偏好", selectControl(OPTIONS.shotSize, p.shot_size || OPTIONS.shotSize[0], v => { p.shot_size = v; })));
    c.append(field("运镜偏好", selectControl(OPTIONS.cameraMove, p.camera_move || OPTIONS.cameraMove[0], v => { p.camera_move = v; })));
    c.append(field("切镜节奏", selectControl(OPTIONS.cutRhythm, p.cut_rhythm || OPTIONS.cutRhythm[0], v => { p.cut_rhythm = v; })));
    c.append(field("转场偏好", selectControl(OPTIONS.transition, p.transition || OPTIONS.transition[0], v => { p.transition = v; })));
    c.append(field("音乐风格", selectControl(OPTIONS.music, p.music_style || OPTIONS.music[0], v => { p.music_style = v; })));
    c.append(field("创作要求", selectControl(OPTIONS.creativeReq, p.creative_req || OPTIONS.creativeReq[0], v => { p.creative_req = v; })));
    c.append(field("详细描述字数", selectControl(OPTIONS.detailLength, p.detail_length || OPTIONS.detailLength[0], v => { p.detail_length = v; })));
    c.append(field("自定义镜头语言", textControl(p.custom || "", "选填。自由描述镜头要求…", v => { p.custom = v; })));
}

function renderPrefPanel(c, s, d) {
    const p = s.sample_decode;
    const sec = p.second || (p.second = {});
    renderAutoSave(c, s);

    // ── 采样（一采）──
    c.append(makeSectionTitle("采样"));
    c.append(field("K采样器", selectControl(OPTIONS.samplers, p.sampler || OPTIONS.samplers[0], v => { p.sampler = v; })));
    c.append(field("调度器", selectControl(OPTIONS.schedulers, p.scheduler || OPTIONS.schedulers[0], v => { p.scheduler = v; })));
    c.append(field("采样步数", numberControl(p.steps ?? 4, { min: 1, max: 200, step: 1 }, v => { p.steps = Math.round(v); })));
    c.append(field("降噪系数", numberControl(p.denoise ?? 1.0, { min: 0, max: 1, step: 0.05 }, v => { p.denoise = v; })));
    c.append(seedControlRow(p, "seed", "seed_mode", "随机种子"));

    // ── 二次采样（开关 + 设置；不折叠，设置项始终显示；种子与一采共享）──
    c.append(makeSectionTitle("二次采样"));
    c.append(field("启用二次采样", checkboxControl(!!sec.enabled,
        "一采后➡️分离latent➡️ 视频latent放大➡️合并latent➡️二次采样",
        v => { sec.enabled = v; })));
    const upModels = (d?.upscaler_models && d.upscaler_models.length) ? d.upscaler_models : ["minimax_h3_latent_upscaler_3d_fp32.pth"];
    c.append(field("latent放大模型选择", selectControl(upModels, sec.upscaler_model || upModels[0], v => { sec.upscaler_model = v; })));
    c.append(field("运行设备", selectControl(["cuda", "rocm", "cpu"], sec.device || "cuda", v => { sec.device = v; })));
    c.append(field("精度", selectControl(["fp32", "fp16", "bf16"], sec.precision || "fp32", v => { sec.precision = v; })));

    // ── Sigmas 模式（单选：调度器 / 自定义）──
    // 调度器=用 调度器+采样步数+降噪系数 生成 sigmas 二采；自定义=直接用下方输入的自定义 sigmas 序列（对齐 1190 ManualSigmas）
    const sigModeRow = el("div", "display:flex;align-items:center;gap:16px;min-width:0;");
    const mkSigRadio = (val, label) => {
        const lab = el("label", "display:flex;align-items:center;gap:5px;font-size:13px;color:var(--descrip-text,#999);cursor:pointer;");
        const r = el("input", "accent-color:#f59e0b;cursor:pointer;");
        r.type = "radio"; r.name = "jzl_second_sigmas"; r.value = val;
        r.checked = (sec.sigmas_mode || "scheduler") === val;
        r.addEventListener("change", () => { if (r.checked) { sec.sigmas_mode = val; syncSigMode(); } });
        lab.append(r, el("span", "", label));
        sigModeRow.append(lab);
        return r;
    };
    c.append(field("Sigmas模式", sigModeRow));
    c.append(field("K采样器", selectControl(OPTIONS.samplers, sec.sampler || "euler", v => { sec.sampler = v; })));
    const fScheduler = field("调度器", selectControl(OPTIONS.schedulers, sec.scheduler || "simple", v => { sec.scheduler = v; }));
    const fSteps = field("采样步数", numberControl(sec.steps ?? 3, { min: 1, max: 200, step: 1 }, v => { sec.steps = Math.round(v); }));
    const fDenoise = field("降噪系数", numberControl(sec.denoise ?? 0.3, { min: 0, max: 1, step: 0.05 }, v => { sec.denoise = v; }));
    const fCustom = field("自定义Sigmas", textControl(sec.custom_sigmas || "0.8500, 0.6316, 0.3158, 0.0000", "0.8500, 0.6316, 0.3158, 0.0000", v => { sec.custom_sigmas = v; }));
    c.append(fScheduler, fSteps, fDenoise, fCustom);
    const syncSigMode = () => {
        const custom = (sec.sigmas_mode || "scheduler") === "custom";
        // 注意：field 容器是 flex 布局，恢复显示必须显式设回 "flex"（设 "" 会移除 display 声明，
        // 回落到块级布局，导致标签/控件错位、控件变窄贴边）
        fScheduler.style.display = custom ? "none" : "flex";
        fSteps.style.display = custom ? "none" : "flex";
        fDenoise.style.display = custom ? "none" : "flex";
        fCustom.style.display = custom ? "flex" : "none";
    };
    mkSigRadio("scheduler", "调度器");
    mkSigRadio("custom", "自定义");
    syncSigMode();

    // ── 解码 ──
    c.append(makeSectionTitle("解码"));
    // 视频解码固定 XB-BOX 优化版（=原版+显存清理，与 1146 一致）；清理选项完整保留
    c.append(field("视频解码", el("div", "font-size:13px;color:var(--fg-color,#ddd);padding:6px 10px;background:var(--comfy-input-bg,#2a2a2a);border:1px solid var(--border-color,#444);border-radius:4px;", "XB-BOX - VAE解码（原版优化）")));
    c.append(field("解码前清理", selectControl(OPTIONS.decodeCleanup, p.decode_cleanup || OPTIONS.decodeCleanup[0], v => { p.decode_cleanup = v; })));
    c.append(field("音频解码", el("div", "font-size:13px;color:var(--fg-color,#ddd);padding:6px 10px;background:var(--comfy-input-bg,#2a2a2a);border:1px solid var(--border-color,#444);border-radius:4px;", "VAE解码（音频）")));
}

// ── 💾 视频保存设置面板（读写隐藏 schema widget） ─────────────────
// 节点表面的「保存模式」已移入本面板；新增「分段视频自动保存 / 分段视频自动合并」+ 路径。
// 这些值直接写入隐藏 widget（save_mode/auto_save/auto_save_path/auto_merge/auto_merge_path），
// 随工作流序列化，execute 直接读取，不经过 manager_settings。
function renderSaveSettingsPanel(c, node, d) {
    const w = (name) => (node?.widgets || []).find((x) => x.name === name);
    const saveModeW = w("save_mode");
    const autoSaveW = w("auto_save");
    const autoMergeW = w("auto_merge");
    const autoMergeDelW = w("auto_merge_delete");
    const val = (ww, dflt) => (ww ? readWidgetValue(ww) : undefined) ?? dflt;
    // 保存/合并位置固定为运行中 ComfyUI 的 output/jzl（运行时可推导，不写死盘符，不可修改，只读显示）
    const saveDir = (d && d.save_dir) || "output/jzl";
    const locRow = (label) => {
        const row = el("div", "display:flex;align-items:center;gap:8px;font-size:12px;color:var(--descrip-text,#999);margin:0 0 6px 172px;line-height:1.6;");
        row.append(el("span", "white-space:nowrap;color:var(--fg-color,#ccc);", label));
        row.append(el("code", "font-family:monospace;background:var(--comfy-input-bg,#2a2a2a);border:1px solid var(--border-color,#444);border-radius:4px;padding:3px 8px;color:#9fd6a4;user-select:all;", saveDir));
        return row;
    };

    // 保存设置（原有下游 VHS 保存逻辑，已移入面板）
    c.append(makeSectionTitle("保存设置"));
    c.append(field("保存模式", selectControl(["分段保存", "拼接保存"], val(saveModeW, "分段保存"),
        (v) => { if (saveModeW) setWidgetValue(saveModeW, v); })));
    c.append(el("div", "font-size:12px;color:var(--descrip-text,#999);margin:-4px 0 6px 172px;line-height:1.6;",
        "分段保存=按顺序批量输出每段图像/音频（接「视频保存分配→VHS」）；拼接保存=全部生成后拼接成一段再输出。此选项只影响下游 VHS 保存方式，保留原有逻辑。"));

    // 分段视频自动保存（ffmpeg 逐段落盘，位置固定 output/jzl）
    c.append(makeSectionTitle("ffmpeg 逐段落盘"));
    const asRow = field("分段视频自动保存", checkboxControl(!!val(autoSaveW, false),
        "每段跑完立刻用 ffmpeg 落盘 mp4（不依赖下游 VHS）",
        (v) => { if (autoSaveW) setWidgetValue(autoSaveW, v); sync(); }));
    const asLoc = locRow("保存位置：");
    c.append(asRow, asLoc);

    // 分段视频自动合并（合并输出位置固定 output/jzl）
    c.append(makeSectionTitle("分段视频自动合并"));
    const amRow = field("分段视频自动合并", checkboxControl(!!val(autoMergeW, false),
        "把落盘的 mp4 按顺序拼接为完整一个视频（无论保存模式；未开自动保存时内部临时落盘）",
        (v) => { if (autoMergeW) setWidgetValue(autoMergeW, v); sync(); }));
    const amDelRow = field("合并后删除分段视频", checkboxControl(!!val(autoMergeDelW, false),
        "合并完成后删除各分段 mp4（仅保留合并结果；未开自动保存时的临时分段本就会清理）",
        (v) => { if (autoMergeDelW) setWidgetValue(autoMergeDelW, v); }));
    const amLoc = locRow("合并输出位置：");
    c.append(amRow, amLoc, amDelRow);

    const sync = () => {
        const as = !!val(autoSaveW, false);
        const am = !!val(autoMergeW, false);
        asLoc.style.display = as ? "" : "none";
        amLoc.style.display = am ? "" : "none";
        amDelRow.style.display = am ? "" : "none";
    };
    sync();
}

// ── 📖 节点使用说明面板 ────────────────────────────────
// 使用说明内置回退 HTML（OpenPose 式内嵌：后端 /jzl/usage_md 不可用时也能显示；完整文档见 docs/USAGE.md）
const USAGE_FALLBACK_HTML = `
<div style="font-size:13px;line-height:1.8;color:var(--fg-color,#ddd);">
<h3 style="margin:0 0 8px;font-size:16px;font-weight:700;color:var(--fg-color,#eee);border-bottom:1px solid var(--border-color,#444);padding-bottom:4px;">MiniMax-H3 生成管理器 · 使用说明</h3>
<p style="margin:6px 0;">一个节点完成 <b>剧本分段 → 参考调度 → 编码 → 采样 → 解码</b> 全流程，输出生成总线，无缝对接「视频保存分配」与 VHS 保存，亦支持 ffmpeg 逐段落盘 / 自动合并。</p>
<h4 style="margin:10px 0 4px;color:var(--fg-color,#eee);">一、快速上手</h4>
<ol style="padding-left:20px;margin:4px 0;">
<li>添加节点：JZL/MiniMax → <code>JZL - 🤖 MiniMax-H3短剧生成管理器</code></li>
<li>接好模型输入：主模型 / CLIP / 视觉VAE / 音频VAE（含视频或音频参考时必须接音频VAE）</li>
<li>在节点表面 📝 提示词 框输入故事 / 剧本（可用 @ 引用素材）</li>
<li>点「📁 参考素材管理」上传并配置素材（图片 / 视频 / 音频）</li>
<li>设置「视频数量」（1~48）、画幅、时长等参数后运行</li>
</ol>
<p style="margin:4px 0;">提示：不接模型也能运行——只做剧本分段 + 调度，不做采样解码。</p>
<h4 style="margin:10px 0 4px;color:var(--fg-color,#eee);">二、运行模式</h4>
<ul style="padding-left:20px;margin:4px 0;">
<li><b>故事拆解模式</b>：按情节拆解为 N 段（不创意扩展）</li>
<li><b>故事扩展模式</b>：先扩写故事正文，再拆解为 N 段</li>
<li><b>穿透生成模式</b>：跳过 LLM 拆解与增强，直接用提示词生成</li>
<li><b>仅提示词输出</b>：只用 LLM 处理提示词经「已处理剧本」输出文本，不生成视频</li>
</ul>
<h4 style="margin:10px 0 4px;color:var(--fg-color,#eee);">三、素材与参考调度</h4>
<ul style="padding-left:20px;margin:4px 0;">
<li>引用上限：图片 ≤9 / 视频 ≤3 / 音频 ≤3，总参考 ≤12（官方上限）</li>
<li>提示词中用 @素材名 引用，或由调度指令（类型:槽位名）自动匹配</li>
<li>生成路径按引用自动推断：有视频→多参考(REF2VA)；否则按参考图数量选首尾帧/首帧/纯文本</li>
</ul>
<h4 style="margin:10px 0 4px;color:var(--fg-color,#eee);">四、界面按钮（4×2）</h4>
<p style="margin:4px 0;">📁 参考素材管理 ｜ 📝 剧本拆解配置 ｜ 🎭 采样解码设置 ｜ 🎯 镜头参数预设 ｜ ➕ 常用提示词元素 ｜ 🎯 参考元素切换 ｜ 💾 视频保存设置 ｜ 📖 节点使用说明</p>
<ul style="padding-left:20px;margin:4px 0;">
<li><b>保存模式</b>：分段保存（逐段输出接 VHS）/ 拼接保存（合并为一段再输出）——仅影响下游 VHS</li>
<li><b>分段视频自动保存</b>：每段跑完立即用 ffmpeg 落盘 mp4 到指定目录，不依赖下游 VHS</li>
<li><b>分段视频自动合并</b>：把落盘的各段 mp4 按顺序拼接为完整一个视频（无论保存模式）</li>
</ul>
<h4 style="margin:10px 0 4px;color:var(--fg-color,#eee);">五、采样与解码</h4>
<ul style="padding-left:20px;margin:4px 0;">
<li>采样：res_multistep / euler 等 K 采样器；可调 步数 / CFG / 降噪 / 种子</li>
<li>解码：视频 XB-BOX - VAE解码（原版优化）；音频 VAE解码（音频）</li>
<li>逐段顺序生成：每段「采样→解码→写入总线→（可选落盘）」完成后才进入下一段</li>
</ul>
<h4 style="margin:10px 0 4px;color:var(--fg-color,#eee);">六、输出</h4>
<ul style="padding-left:20px;margin:4px 0;">
<li><b>图像</b> IMAGE 列表：每段视频帧（分段保存）或拼接后一段（拼接保存）</li>
<li><b>音频</b> AUDIO 列表：每段音频（与图像一一对应）</li>
<li><b>已处理剧本</b> STRING：全部 LLM 处理后的剧本文本</li>
<li>配合「JZL - 💾 视频保存分配」把「生成总线」接上，每组接一个 VHS Video Combine 逐段保存 mp4</li>
</ul>
<h4 style="margin:10px 0 4px;color:var(--fg-color,#eee);">七、常见问题</h4>
<ul style="padding-left:20px;margin:4px 0;">
<li>没有生成视频？检查 CLIP/VAE/model 是否接好；含视频或音频参考还需接 audio_vae</li>
<li>视频数量改了没生效？确认剧本拆解配置已保存（固定种子时）</li>
<li>想跑一段存一段？在「💾 视频保存设置」勾选「分段视频自动保存」并填路径</li>
</ul>
</div>
`;

function renderHelpPanel(c) {
    const box = el("div", "font-size:13px;line-height:1.7;color:var(--fg-color,#ddd);");
    c.append(box);
    api.fetchApi("/jzl/usage_md")
        .then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.text(); })
        .then((md) => { box.innerHTML = mdToHtml(md); })
        .catch(() => { box.innerHTML = USAGE_FALLBACK_HTML; });  // API 不可用时显示内置说明

    // 底部：支持与打赏 + 其他仓库 + 联系交流
    const qrWrap = el("div", "margin-top:18px;border-top:1px solid var(--border-color,#444);padding-top:14px;");
    qrWrap.append(el("div", "font-size:13px;font-weight:600;color:var(--fg-color,#eee);margin-bottom:10px;", "💰 支持与打赏"));
    qrWrap.append(el("div", "font-size:15px;font-weight:700;color:#f5a623;margin-bottom:12px;line-height:1.8;white-space:pre-line;",
        "本项目使用付费 AI 工具进行开发、调试和测试维护。\n如果这个工具对你有用，帮助到了你，欢迎打赏支持，你的支持将加速开发进度。"));
    const qrRow = el("div", "display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap;");
    const qrFiles = [["DS01.png", "微信"], ["DS02.png", "支付宝"]];
    qrFiles.forEach(([f, label]) => {
        const cell = el("div", "flex:1;min-width:200px;text-align:center;");
        const img = el("img", "width:180px;height:180px;object-fit:contain;background:#fff;border:1px solid var(--border-color,#444);border-radius:8px;");
        img.alt = label;
        img.src = api.apiURL(`/jzl/usage_qr/${f}`);
        img.onerror = () => { img.style.display = "none"; };
        const ph = el("div", "font-size:13px;font-weight:600;color:var(--fg-color,#ddd);margin-top:6px;", label);
        cell.append(img, ph);
        qrRow.append(cell);
    });
    qrWrap.append(qrRow);

    // 我的 ComfyUI 节点仓库
    qrWrap.append(el("div", "font-size:13px;font-weight:600;color:var(--fg-color,#eee);margin:16px 0 6px;", "我的 ComfyUI 节点仓库"));
    const repoRow = el("div", "display:flex;gap:10px;flex-wrap:wrap;");
    const mkRepo = (label, url) => {
        const a = el("a", "display:inline-block;background:#2a4a6a;color:#cfe3f7;border:1px solid #5b9bd5;border-radius:6px;padding:7px 14px;font-size:12px;text-decoration:none;cursor:pointer;", label);
        a.href = url; a.target = "_blank"; a.rel = "noopener noreferrer";
        a.addEventListener("mousedown", (e) => e.stopPropagation());
        return a;
    };
    repoRow.append(
        mkRepo("🧰 小白工具箱（XB_ToolBox）", "https://github.com/wjluoxiao/XB_ToolBox"),
        mkRepo("🎬 ComfyUI-JZL-MiniMax-H3", "https://github.com/wjluoxiao/ComfyUI-JZL-MiniMax-H3"),
    );
    qrWrap.append(repoRow);

    // 模型与工作流下载
    qrWrap.append(el("div", "font-size:13px;font-weight:600;color:var(--fg-color,#eee);margin:16px 0 6px;", "模型与工作流下载"));
    const dlRow = el("div", "display:flex;gap:10px;flex-wrap:wrap;");
    dlRow.append(
        mkRepo("🟢机制罗的模型总仓库", "https://pan.quark.cn/s/6ec0a5f56d08"),
        mkRepo("🟢机制罗的工作流仓库", "https://pan.quark.cn/s/65b5abcb7879"),
    );
    qrWrap.append(dlRow);

    // 联系与交流
    qrWrap.append(el("div", "font-size:13px;font-weight:600;color:var(--fg-color,#eee);margin:16px 0 6px;", "📮 联系与交流"));
    const bili = mkRepo("B站主页：space.bilibili.com/302329373", "https://space.bilibili.com/302329373");
    bili.style.background = "#2a3a5a";
    qrWrap.append(bili);
    const qqRow = el("div", "display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:var(--descrip-text,#999);line-height:1.8;margin-top:4px;");
    qqRow.append(el("span", "", "⚡️充电股东群：136812541"));
    qqRow.append(el("span", "", "🤖QQ交流群1：231033995"));
    qqRow.append(el("span", "", "🤖QQ交流群2：56798547"));
    qrWrap.append(qqRow);
    c.append(qrWrap);
}

// 轻量 Markdown → HTML（标题/列表/代码块/加粗/行内代码/链接，够用即可）
function mdToHtml(md) {
    const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    const inline = (s) => {
        let out = esc(s);
        out = out.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
        out = out.replace(/`([^`]+)`/g, "<code style='background:var(--comfy-input-bg,#222);padding:1px 4px;border-radius:3px;'>$1</code>");
        out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
        return out;
    };
    const lines = md.replace(/\r\n/g, "\n").split("\n");
    let html = "";
    let inCode = false;
    let codeBuf = [];
    let inUl = false;
    const closeUl = () => { if (inUl) { html += "</ul>\n"; inUl = false; } };
    for (const raw of lines) {
        const t = raw.trim();
        if (t.startsWith("```")) {
            if (inCode) { html += "<pre style='background:var(--comfy-input-bg,#1d1d1d);padding:10px;border-radius:6px;overflow-x:auto;font-size:12px;line-height:1.5;'>" + esc(codeBuf.join("\n")) + "</pre>\n"; codeBuf = []; inCode = false; }
            else { closeUl(); inCode = true; }
            continue;
        }
        if (inCode) { codeBuf.push(raw); continue; }
        if (!t) { closeUl(); continue; }
        if (/^#{1,6}\s/.test(t)) {
            closeUl();
            const lvl = t.match(/^#+/)[0].length;
            html += `<h${lvl} style="margin:14px 0 6px;font-size:${lvl === 1 ? 18 : 15}px;font-weight:700;color:var(--fg-color,#eee);border-bottom:1px solid var(--border-color,#444);padding-bottom:3px;">${inline(t.replace(/^#+\s*/, ""))}</h${lvl}>\n`;
            continue;
        }
        if (/^[-*]\s/.test(t)) {
            if (!inUl) { html += "<ul style='padding-left:20px;'>\n"; inUl = true; }
            html += `<li style="margin:3px 0;">${inline(t.replace(/^[-*]\s*/, ""))}</li>\n`;
            continue;
        }
        closeUl();
        html += `<p style="margin:6px 0;">${inline(t)}</p>\n`;
    }
    if (inCode) html += "<pre style='background:var(--comfy-input-bg,#1d1d1d);padding:10px;border-radius:6px;overflow-x:auto;font-size:12px;line-height:1.5;'>" + esc(codeBuf.join("\n")) + "</pre>\n";
    closeUl();
    return html;
}

function buildModal(node, data, panelId) {
    ensureManagerStyle();
    const settings = (data && data.settings) ? data.settings : defaultSettings();
    const d = data || { llm_models: [], mmproj_models: ["None"], chat_handlers: ["None"] };
    const title = (PANELS[panelId] && PANELS[panelId].label) || "🎬 JZL - 🤖 MiniMax-H3短剧生成管理器";

    const overlay = el("div", "position:fixed;inset:0;background:rgba(0,0,0,0.78);z-index:9999;display:flex;align-items:center;justify-content:center;");
    const dialog = el("section", "background:#1c1c1e;border:1px solid #333;border-radius:8px;width:820px;max-height:90vh;display:flex;flex-direction:column;box-shadow:0 20px 40px rgba(0,0,0,0.6);");
    dialog.className = "jzl-modal";
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.setAttribute("aria-label", title);

    // 头部
    const header = el("div", "padding:20px;border-bottom:1px solid var(--border-color,#444);");
    header.append(el("div", "font-size:18px;font-weight:700;color:var(--fg-color,#eee);", title));
    header.append(el("div", "font-size:12px;color:var(--descrip-text,#999);margin-top:5px;", "根据本地环境配置参数，保存后重新执行节点生效。"));
    dialog.append(header);

    // 单面板内容
    const panelBox = el("div", "padding:16px 20px;overflow-y:auto;flex:1;min-height:280px;");
    switch (panelId) {
        case "assets": {
            const buildAssets = () => {
                panelBox.innerHTML = "";
                renderAutoSave(panelBox, settings);
                renderAssetsTools(panelBox, settings, buildAssets);
                renderAssetsPanel(panelBox, settings, d.mode);
            };
            buildAssets();
            break;
        }
        case "prompt": renderPromptPanel(panelBox, settings, d, node); break;
        case "preference": renderPrefPanel(panelBox, settings, d); break;
        case "preference_settings": renderPreferenceSettingsPanel(panelBox, settings); break;
        case "save_settings": renderSaveSettingsPanel(panelBox, node, d); break;
        case "help": renderHelpPanel(panelBox); break;
        default: renderAutoSave(panelBox, settings);
    }
    dialog.append(panelBox);

    // 底部
    const error = el("div", "color:#e55;font-size:12px;margin:0 20px;min-height:16px;");
    const footer = el("div", "padding:15px 20px;border-top:1px solid var(--border-color,#444);display:flex;justify-content:flex-end;gap:10px;background:#18181a;border-bottom-left-radius:8px;border-bottom-right-radius:8px;");
    const cancelBtn = el("button", "background:transparent;border:1px solid var(--border-color,#555);color:#fff;border-radius:4px;padding:8px 20px;font-size:14px;cursor:pointer;", "取消");
    const saveBtn = el("button", "background:#2d5a88;color:#fff;border:none;border-radius:4px;padding:8px 20px;font-size:14px;font-weight:600;cursor:pointer;", "💾 保存");
    // 自动保存：统一移到弹窗底部，与「取消/保存」同行并靠左（样式与其他勾选框一致）
    const autoSaveRow = el("label", "display:flex;align-items:center;gap:6px;font-size:13px;color:var(--descrip-text,#999);cursor:pointer;margin-right:auto;");
    const autoSaveCb = el("input", "width:18px;height:18px;accent-color:#f59e0b;cursor:pointer;");
    autoSaveCb.type = "checkbox";
    autoSaveCb.checked = settings.auto_save !== false;
    autoSaveCb.addEventListener("change", () => { settings.auto_save = autoSaveCb.checked; });
    autoSaveRow.append(autoSaveCb, el("span", "", "自动保存"));
    footer.append(autoSaveRow, cancelBtn, saveBtn);
    dialog.append(error, footer);
    if (panelId === "help") { saveBtn.style.display = "none"; autoSaveRow.style.display = "none"; }  // 使用说明面板无需保存/自动保存

    overlay.append(dialog);
    document.body.append(overlay);

    const close = () => { overlay.remove(); modal = null; };

    // 保存
    let autoSaveTimer = null;
    const doSave = async (silent, refreshAssets=false) => {
        try {
            await saveManager(node, settings);
            if (!silent) notify("配置已保存，重新执行节点生效");
            // 只有「引用资产设置」面板才需要实时刷新资产窗/提示词着色，其余面板只存不刷（避免卡顿）
            if (refreshAssets) notifyAssetsChanged(node);
            return true;
        } catch (e) {
            error.textContent = "保存失败：" + e.message;
            return false;
        }
    };
    saveBtn.addEventListener("click", async () => {
        saveBtn.disabled = true;
        saveBtn.textContent = "保存中…";
        const ok = await doSave(false, panelId === "assets");
        if (ok) close();
        else { saveBtn.disabled = false; saveBtn.textContent = "💾 保存"; }
    });

    // 自动保存：任何控件 change 后 1200ms 防抖保存（降低频繁整包 POST 的卡顿）
    panelBox.addEventListener("change", () => {
        if (settings.auto_save !== false) {
            clearTimeout(autoSaveTimer);
            autoSaveTimer = setTimeout(() => doSave(true, panelId === "assets"), 1200);
        }
    });

    cancelBtn.addEventListener("click", close);
    overlay.addEventListener("mousedown", (e) => { if (e.target === overlay) close(); });

    modal = { overlay, dialog, close, __data: settings };
}

app.registerExtension({
    name: "JZL.MiniMaxAssetManager",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData?.name !== NODE_TYPE) return;
        const orig = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = orig?.apply(this, arguments);
            const self = this;

            // 1. 隐藏内部存储 widget（internal_prompt）与旧 mode
            const vcWidget = (self.widgets || []).find((w) => w.name === "video_count");
            const ipWidget = (self.widgets || []).find((w) => w.name === "internal_prompt");
            const hiddenNames = new Set(["mode", "internal_prompt", "manager_settings",
                "save_mode", "auto_save", "auto_save_path", "auto_merge", "auto_merge_path", "auto_merge_delete"]);
            for (const w of self.widgets || []) {
                if (!w) continue;
                const nm = w.name || "";
                if (nm === "jzl_manager") continue;  // DOM widget 保留
                if (!hiddenNames.has(nm) && !nm.startsWith("btn_")) continue;
                w.hidden = true;
                if (!w.options) w.options = {};
                w.options.hidden = true;
                // 关键：无条件强制布局高度为 0（原生 widget 没有 computeSize，必须无条件赋值）
                w.computeSize = () => [0, -4];
            }

            // 2. 单个 DOM widget：按钮区 + 生成参数(节点表面) + 视频数量 + 加速模式 + 提示词输入
            ensureManagerStyle();
            const container = document.createElement("div");
            container.style.cssText = "width:100%;height:100%;display:flex;flex-direction:column;gap:6px;padding:8px;box-sizing:border-box;overflow:hidden;";

            // 按钮区（4×2）
            const btnGrid = document.createElement("div");
            btnGrid.style.cssText = "display:grid;grid-template-columns:repeat(4,1fr);grid-auto-rows:30px;gap:6px;";
            for (const b of PANEL_BUTTONS) {
                const btn = document.createElement("button");
                btn.textContent = b.label;
                btn.style.cssText = [
                    "width:100%;", "height:30px;", "box-sizing:border-box;",
                    "display:flex;", "align-items:center;", "justify-content:center;",
                    "border-radius:6px;", "border:2px solid #5b9bd5;",
                    "background:#3a3a3a;", "color:#eee;", "font-size:12px;",
                    "cursor:pointer;", "white-space:nowrap;", "overflow:hidden;", "text-overflow:ellipsis;",
                ].join("");
                if (b.widget === "btn_align") { btn.dataset.alignBtn = "1"; self.__btnAlign = btn; }
                btn.addEventListener("mousedown", (e) => e.stopPropagation());
                btn.addEventListener("mouseenter", () => { if (btn.dataset.alignBtn) self.__alignBtnBg?.(true); else btn.style.background = "#4a4a4a"; });
                btn.addEventListener("mouseleave", () => { if (btn.dataset.alignBtn) self.__alignBtnBg?.(false); else btn.style.background = "#3a3a3a"; });
                btn.addEventListener("click", () => {
                    if (b.panel === "prompt_elements") { showPromptElements(self); return; }
                    if (b.panel === "align") { toggleAlignPrompt(self); return; }
                    openModal(self, b.panel);
                });
                btnGrid.appendChild(btn);
            }
            container.appendChild(btnGrid);

            // 生成信息状态行（实时显示，纯只读；值用绿色高亮；参数保存后自动同步）
            const _jzlValColor = "#9fd6a4";  // 结果值高亮色（区别于标签）
            const infoRow = el("div", "font-size:11px;color:#c9a86a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-height:14px;", "");
            infoRow.title = "当前生成配置（LLM语言/后端/增强 + 一采步数/二采/采样种子），只读显示";
            infoRow.addEventListener("mousedown", (e) => e.stopPropagation());
            container.appendChild(infoRow);
            const _jzlVal = (x) => `<span style="color:${_jzlValColor}">${x}</span>`;
            const updateInfo = () => {
                try {
                    const msW = (self.widgets || []).find((x) => x.name === "manager_settings");
                    let s = {};
                    if (msW) { try { s = JSON.parse(readWidgetValue(msW) || "{}"); } catch (_) {} }
                    const enh = s.enhance || {};
                    const sd = s.sample_decode || {};
                    const sec = sd.second || {};
                    const lang = String(enh.prompt_lang || "中文 [ZH]");
                    const langShort = lang.includes("EN") ? "英文[EN]" : "中文[ZH]";
                    const mode = String(enh.llm_backend || "").includes("api") ? "API" : "本地";
                    const enhOn = enh.enabled ? "开启" : "关闭";
                    const steps = sd.steps ?? 4;
                    const secOn = sec.enabled ? "开启" : "关闭";
                    const seed = sd.seed ?? 0;
                    infoRow.innerHTML = `LLM语言：${_jzlVal(langShort)} 丨 LLM模式：${_jzlVal(mode)} 丨 文本增强：${_jzlVal(enhOn)} 丨 一采步数：${_jzlVal(steps)} 丨 二采功能：${_jzlVal(secOn)} 丨 随机种：${_jzlVal(seed)}`;
                } catch (_) {}
            };
            self.__jzlUpdateInfo = updateInfo;  // 设置面板保存后由 saveManager 触发刷新

            // 提示词：内部编辑窗口（DOM 富文本 @ 着色），唯一提示词来源（外部提示词端口已删除）
            const promptLabel = el("div", "font-size:12px;color:#bbb;", "📝 提示词（用 @ 引用素材）");
            const alignStatus = el("span", "font-size:11px;margin-left:8px;", "");
            promptLabel.appendChild(alignStatus);
            container.appendChild(promptLabel);
            const promptBox = document.createElement("div");
            promptBox.contentEditable = "true";
            promptBox.spellcheck = false;
            promptBox.dataset.placeholder = "输入故事/剧本提示词，用 @ 引用素材…";
            promptBox.innerText = ipWidget?.value ?? "";
            promptBox.style.cssText = "width:100%;flex:1 1 auto;min-height:60px;box-sizing:border-box;background:#2a2a2a;color:#ddd;border:1px solid #444;border-radius:4px;padding:6px 8px;font-size:12px;overflow-y:auto;white-space:pre-wrap;word-break:break-word;";
            promptBox.addEventListener("mousedown", (e) => e.stopPropagation());
            container.appendChild(promptBox);
            self.__promptBox = promptBox;
            promptBox.__node = self;
            setupInternalPrompt(self, promptBox, ipWidget);

            // 参考元素切换状态（纯文本/显示引用）：默认「纯文本」（关闭）；只由「🎯 参考元素切换」按钮手动切换，
            // 资产变化（新增/修改素材）时保持当前模式、不自动切换。
            self.__jzlAlignMode = "text";
            const alignBtnBg = (hover) => {
                const b = self.__btnAlign;
                if (!b) return;
                const ref = self.__jzlAlignMode !== "text";
                b.style.background = ref ? (hover ? "#e8930c" : "#d97706") : (hover ? "#4a4a4a" : "#3a3a3a");
                b.style.borderColor = ref ? "#f59e0b" : "#5b9bd5";
            };
            const updateAlignStatus = () => {
                if (alignStatus) {
                    const ref = self.__jzlAlignMode !== "text";
                    alignStatus.textContent = `参考元素：${ref ? "显示引用" : "纯文本"}`;
                    alignStatus.style.color = ref ? "#5ecf8a" : "#bbb";
                    alignStatus.title = "由「🎯 参考元素切换」手动控制；已随工作流保存，刷新不丢失";
                }
                alignBtnBg(false);
            };
            self.__updateAlignStatus = updateAlignStatus;
            self.__alignBtnBg = alignBtnBg;
            updateAlignStatus();

            // Bug 1 修复：V3 的 migrateWidgetsValues 在加载时会按 schema 重排 widgets_values，
            // 但 addDOMWidget 生成的 jzl_manager 混在 widgets 数组里（schema 无此项）导致索引错位，
            // internal_prompt 会拿到 jzl_manager 的空值 → 刷新/重载后提示词丢失。
            // 这里在 configure 前后备份并回填 internal_prompt 值（按保存顺序的 widgets 下标取原始值）。
            const baseConfigure = self.configure.bind(self);
            self.configure = function (info) {
                let rawIP, rawMS;
                if (info && Array.isArray(info.widgets_values)) {
                    const ipIdx = (self.widgets || []).findIndex((w) => w.name === "internal_prompt");
                    if (ipIdx >= 0 && ipIdx < info.widgets_values.length) rawIP = info.widgets_values[ipIdx];
                    const msIdx = (self.widgets || []).findIndex((w) => w.name === "manager_settings");
                    if (msIdx >= 0 && msIdx < info.widgets_values.length) rawMS = info.widgets_values[msIdx];
                }
                const r = baseConfigure(info);
                if (rawMS !== undefined && rawMS !== null) {
                    const ms = (self.widgets || []).find((w) => w.name === "manager_settings");
                    if (ms) { ms._state.value = rawMS; ms.value = rawMS; }
                }
                if (rawIP !== undefined && rawIP !== null) {
                    const ip = (self.widgets || []).find((w) => w.name === "internal_prompt");
                    if (ip) {
                        ip._state.value = rawIP;
                        ip.value = rawIP;
                    }
                    const box = self.__promptBox;
                    if (box && rawIP && !getPromptText(box)) {
                        renderPromptFromText(box, String(rawIP), self);
                        if (ipWidget) setWidgetValue(ipWidget, String(rawIP));
                    }
                }
                // configure 可能重建端口 → 兜底清理幽灵接口（内部存储字段无端口）
                setTimeout(killGhost, 0);
                // 工作流加载后按真实 DOM 重算尺寸 + 锁定最小宽度（防版本差异导致的漂移）
                setTimeout(() => { try { lockMinWidth(); refreshSize?.(); } catch (_) {} }, 120);
                return r;
            };

            // 清理内部存储字段的幽灵接口（socketless 内部字段不应渲染端口；旧工作流残留连线也会渲染幽灵口）。
            // 覆盖：internal_prompt / prompt_input(旧) / display_info / manager_settings，widget 值保留供 execute 取值。
            // 多次重试覆盖工作流加载时序（链接在节点 configure 之后才连上）。
            const killGhost = () => {
                try {
                    for (const nm of ["internal_prompt", "prompt_input", "display_info", "manager_settings"]) {
                        const inp = (self.inputs || []).find((i) => i.name === nm);
                        if (!inp) continue;
                        // 1. 断开残留连线（旧工作流曾把「字符串A」接到 internal_prompt）
                        if (inp.link != null) {
                            const linkId = inp.link;
                            inp.link = null;
                            const g = self.graph;
                            if (g && g.links && g.links[linkId]) {
                                const link = g.links[linkId];
                                const origin = g.getNodeById(link.origin_id);
                                if (origin && origin.outputs && origin.outputs[link.origin_slot] && Array.isArray(origin.outputs[link.origin_slot].links)) {
                                    const ol = origin.outputs[link.origin_slot].links;
                                    const idx = ol.indexOf(linkId);
                                    if (idx >= 0) ol.splice(idx, 1);
                                }
                                delete g.links[linkId];
                            }
                            console.log(`[JZL-管理器] 已清理 ${nm} 幽灵连线`);
                        }
                        // 2. 彻底移除端口（内部存储字段，无端口；widget 值保留供 execute 取值）
                        const idx = self.inputs.indexOf(inp);
                        if (idx >= 0) {
                            self.inputs.splice(idx, 1);
                            (self.inputs || []).forEach((i, k) => { i.slot = k; });
                        }
                    }
                    self.setDirtyCanvas?.(true, true);
                } catch (_) {}
            };
            self.__jzlKillGhost = killGhost;
            [0, 150, 500, 1200].forEach((d) => setTimeout(killGhost, d));

            // 资产显示窗（缩略图墙，点击插入 @引用；自动换行，多行时节点同步增高）
            const windowTitle = el("div", "font-size:12px;color:#bbb;margin-top:2px;", "📁 资产显示窗（点击插入）");
            const windowBox = el("div", "min-height:30px;overflow:hidden;flex:0 0 auto;");
            const resizeNodeForContent = () => {
                requestAnimationFrame(() => {
                    try {
                        // scrollHeight 取完整内容高度（含多行），避免 overflow 把多行素材吞掉
                        const assetsH = windowBox.scrollHeight || windowBox.offsetHeight || 30;
                        const btnRows = Math.ceil(PANEL_BUTTONS.length / 4);
                        const minDom = btnRows * 40 + 10 + 16 + 72 + 22 + assetsH + 20;  // 按钮N行 + gap + 信息行 + 提示词min + 资产窗标题 + padding
                        const y = (self.widgets || []).find((w) => w.name === "jzl_manager")?.y;
                        const need = (Number.isFinite(y) ? y : 220) + minDom;
                        if (self.size && need > (self.size[1] || 0) + 1) {
                            self.setSize([self.size[0], need]);
                            self.setDirtyCanvas?.(true, true);
                            // 节点增高后 DOM 重排延迟 → 二次增高确保多行素材全部可见
                            setTimeout(() => {
                                self.setSize?.([self.size[0], need]);
                                self.setDirtyCanvas?.(true, true);
                            }, 80);
                        }
                    } catch (_) {}
                });
            };
            windowBox.__onResize = resizeNodeForContent;
            container.appendChild(windowTitle);
            container.appendChild(windowBox);

            // 缓存资产名并渲染资产显示窗；内部提示词重新渲染成着色 token 并同步到 internal_prompt
            const refreshAssets = () => {
                renderAssetWindow(windowBox, self.__promptBox, self);
                // 用 internal_prompt 持久值作为来源重渲染（配置恢复晚于 loadManager 时也能正确着色，修复刷新后无缩略图）
                const ipVal = ipWidget ? readWidgetValue(ipWidget) : "";
                // 仅在「显示引用」模式才重新着色对齐；「纯文本」模式保持纯文本——素材变化不自动切换模式
                if (self.__jzlAlignMode !== "text") {
                    renderPromptFromText(self.__promptBox, ipVal || getPromptText(self.__promptBox), self);
                    if (ipWidget) setWidgetValue(ipWidget, getPromptText(self.__promptBox));
                }
                updateAlignStatus();
            };

            // 生成详情只读显示：监听原生参数 widget（画幅/MP/时长/段数）变化后联动刷新
            const AR_MAP = {
                "1:1 (Square)": [1, 1], "2:3 (Portrait Photo)": [2, 3], "3:2 (Photo)": [3, 2],
                "3:4 (Portrait Standard)": [3, 4], "4:5 (Portrait Tall)": [4, 5], "4:3 (Standard)": [4, 3],
                "5:4 (Landscape Tall)": [5, 4], "9:16 (Portrait Widescreen)": [9, 16],
                "16:9 (Widescreen)": [16, 9], "21:9 (Ultrawide)": [21, 9],
            };
            const updateDisplay = () => {
                const gv = (nm) => {
                    const w = (self.widgets || []).find((x) => x.name === nm);
                    return w ? readWidgetValue(w) : null;
                };
                const ar = gv("aspect_ratio") || "16:9 (Widescreen)";
                const mp = parseFloat(gv("megapixels")) || 1.0;
                const dur = parseInt(gv("duration"), 10) || 8;
                const count = parseInt(gv("video_count"), 10) || 6;
                const [wr, hr] = AR_MAP[ar] || [16, 9];
                const total = mp * 1024 * 1024;
                const scale = Math.sqrt(total / (wr * hr));
                const W = Math.max(32, Math.round((wr * scale) / 32) * 32);
                const H = Math.max(32, Math.round((hr * scale) / 32) * 32);
                const base = Math.max(5, Math.round(dur * 24));
                const frames = base + (5 - (base % 17)) % 17;
                const disp = (self.widgets || []).find((x) => x.name === "display_info");
                if (disp) setWidgetValue(disp, `分辨率：${W}x${H}丨每段帧数：${frames}丨共计段数：${count}丨总帧数：${frames * count}丨总时长：${dur * count}秒`);
            };
            const watchChange = (nm) => {
                const w = (self.widgets || []).find((x) => x.name === nm);
                if (!w) return;
                const orig = w.callback;
                w.callback = function (...args) {
                    const r = orig ? orig.apply(this, args) : undefined;
                    setTimeout(updateDisplay, 0);
                    return r;
                };
            };
            ["aspect_ratio", "megapixels", "duration", "video_count"].forEach(watchChange);

            loadManager(self).then((data) => {
                cacheAssets(self, data.settings);
                // 恢复「参考元素切换」保存的状态（显示引用/纯文本），刷新不丢失
                self.__jzlAlignMode = (data?.settings && data.settings.align_mode === "text") ? "text" : "ref";
                updateDisplay();
                refreshAssets();
                updateInfo();
            }).catch(() => {});
            self.__jzlRefresh = refreshAssets;  // 弹窗保存资产后实时刷新本节点

            // 生成后控制回写：后端返回新 seed → 更新本节点 manager_settings
            const prevOnExecuted = self.onExecuted;
            self.onExecuted = function (message) {
                const r = prevOnExecuted?.apply(this, arguments);
                try {
                    const msW = (self.widgets || []).find((x) => x.name === "manager_settings");
                    // ComfyUI V3 会把 execute 返回的 ui 每个值打包成数组（见 execution.py
                    // get_output_from_returns: ui = {k: [...]}），必须解包取 [0]。
                    const unp = (v) => (Array.isArray(v) ? v[0] : v);
                    // 后端返回的业务错误（如未填故事名称）→ 弹错误提示
                    const merr = unp(message?.manager_error);
                    if (merr) { try { notify(`❌ ${merr}`, "error"); } catch (_) {} }
                    const su = unp(message?.seed_update) || {};
                    if (typeof su.seed === "number" && msW) {
                        const raw = readWidgetValue(msW);
                        let s = {};
                        try { s = raw ? JSON.parse(raw) : {}; } catch (_) {}
                        if (!s.enhance) s.enhance = {};
                        s.enhance.seed = su.seed;
                        s.enhance.seed_control = su.seed_control || s.enhance.seed_control || "randomize";
                        setWidgetValue(msW, JSON.stringify(s));
                        updateInfo();
                    }
                    // 采样种子回写（randomize 一采实际种子）→ 面板刷新后显示真实种子
                    const sus = unp(message?.seed_update_sample) || {};
                    if (typeof sus.seed === "number" && msW) {
                        const raw = readWidgetValue(msW);
                        let s = {};
                        try { s = raw ? JSON.parse(raw) : {}; } catch (_) {}
                        if (!s.sample_decode) s.sample_decode = {};
                        s.sample_decode.seed = sus.seed;
                        if (sus.seed_control) s.sample_decode.seed_mode = sus.seed_control;
                        setWidgetValue(msW, JSON.stringify(s));
                        updateInfo();
                    }
                } catch (_) {}
                return r;
            };

            // 节点最小宽度 600：min_width 在新版前端可能不生效（只在拖动时 clamp，初始化/加载不撑宽），
            // 这里主动兜底锁定：创建 / 工作流加载 / 缩放 / 拖拽后都检查，宽度 < 600 一律拉回 600
            self.min_width = 600;
            self.minWidth = 600;
            const lockMinWidth = () => {
                try {
                    const w = Number.isFinite(self.size?.[0]) ? self.size[0] : 0;
                    if (w >= 600) return;
                    const h = Number.isFinite(self.size?.[1]) ? self.size[1] : 300;
                    self.setSize?.([600, Math.max(h, 300)]);
                } catch (_) {}
            };
            lockMinWidth();

            // 3. addDOMWidget：不 unshift；固定高度（按钮区 + 提示词 + 资产窗）
            const widget = self.addDOMWidget?.("jzl_manager", "JZL_MANAGER", container, {
                serialize: false,
                hideOnZoom: false,
            });
            if (widget) {
                try { delete widget.computeSize; } catch { widget.computeSize = undefined; }
                // DOM widget 填满节点高度（Goohai 同款）：节点拉大 → 输入框自动跟随
                widget.options = widget.options || {};
                widget.options.serialize = false;
                widget.options.getMinHeight = () => 300;
                widget.options.getHeight = () => "100%";
                // 对齐 Director：computeLayoutSize 返回 minWidth（参与节点最小宽度计算，
                // 属性面板等重排不会把节点/overlay 算窄）
                widget.computeLayoutSize = () => ({ minHeight: 300, maxHeight: undefined, minWidth: 600 });
                // Director 同款：DOM widget 自身每次被绘制时同步宽度（最精准时机，绘制前宽度已对，杜绝闪压）；
                // afterResize 在节点尺寸变化后同步
                widget.options.onDraw = () => { try { syncDomWidth(); } catch (_) {} };
                widget.options.afterResize = () => { try { syncDomWidth(); } catch (_) {} };
            }

            // —— 关键防挤压（对齐 MiniMaxH3Director 的 ensureDirectorDomWidgetWidth + patchDirectorDomWidgetLayout）：
            //    ComfyUI 的 DomWidgets 用 widget.width ?? node.width 计算 overlay 宽度，属性面板等重排时
            //    若只依赖 node.width 会被算错压缩。做法：主动把 widget.width 钉为节点完整宽度，并在
            //    canvas.onDrawForeground（每帧绘制）里持续同步——任何重排触发重绘后，下一帧即纠正，
            //    打开属性面板也不会再挤压 UI。——
            const syncDomWidth = () => {
                try {
                    const fullW = Number.isFinite(self.size?.[0]) ? self.size[0] : 0;
                    if (widget && fullW && widget.width !== fullW) widget.width = fullW;
                } catch (_) {}
            };
            syncDomWidth();
            self._jzlSyncWidth = syncDomWidth;
            self._jzlDomWidget = widget;

            // 节点 resize 时触发重绘，让 DOM widget（输入框）跟随高度
            let _resizeTimer = null;
            const prevOnResize = self.onResize;
            self.onResize = function (...args) {
                const rr = prevOnResize?.apply(this, args);
                try {
                    syncDomWidth();  // 节点尺寸一变立即把 overlay 宽度钉为节点宽度（防挤压）
                    self.setDirtyCanvas?.(true, true);
                    // 节点宽度调整期间会频繁触发 → 防抖：调整结束后 200ms，按「最终宽度」重新渲染资产窗
                    // 并重算节点高度，保证换行后的多行素材全部显示、节点自动增高（修复调窄后第三行被吞）
                    clearTimeout(_resizeTimer);
                    _resizeTimer = setTimeout(() => {
                        lockMinWidth();  // 拖拽后锁定最小宽度 600（拖不窄）
                        renderAssetWindow(windowBox, self.__promptBox, self);  // 内部会调 windowBox.__onResize 重算高度
                        self.__updateAlignStatus?.();
                        self.setDirtyCanvas?.(true, true);
                    }, 200);
                } catch (_) {}
                return rr;
            };

            // 4. 刷新节点尺寸（隐藏 widget 后需重算），并多次调用应对异步布局
            const refreshSize = () => {
                try {
                    lockMinWidth();  // 初始化尺寸重算时同时锁定最小宽度 600
                    syncDomWidth();  // 同步 overlay 宽度 = 节点宽度（防属性面板挤压）
                    const size = self.computeSize?.();
                    if (Array.isArray(size) && size.length >= 2 && Number.isFinite(size[1])) {
                        // 只在节点高度未设置/过小时初始化，避免覆盖用户拖拽或工作流保存的高度；
                        // 最小高度保证 DOM 提示词框与资产窗不被截断（修复「提示词接口不显示」）
                        if (!self.size || !Number.isFinite(self.size[1]) || self.size[1] < 420) {
                            self.setSize?.([self.size?.[0] || size[0], Math.max(size[1], 520)]);
                        }
                    }
                } catch { /* ignore */ }
                self.setDirtyCanvas?.(true, true);
            };
            refreshSize();
            requestAnimationFrame(refreshSize);
            setTimeout(refreshSize, 50);

            // 每帧绘制前景时同步本节点 overlay 宽度（对齐 Director 的 patchDirectorDomWidgetLayout）：
            // 属性面板等任何画布重排触发重绘后，下一帧即把 widget.width 纠正为节点宽度，杜绝挤压
            try {
                const _cv = self.graph?.canvas ?? window.app?.canvas;
                if (_cv && !_cv.__jzlDomWidthPatch) {
                    _cv.__jzlDomWidthPatch = true;
                    const _prevDraw = _cv.onDrawForeground;
                    _cv.onDrawForeground = function (ctx) {
                        const _r = _prevDraw?.apply(this, arguments);
                        try {
                            const _g = self.graph ?? (window.app && window.app.graph);
                            const _ns = _g ? (_g._nodes || _g.nodes || []) : [];
                            for (const _n of _ns) {
                                if (_n && _n._jzlDomWidget && _n._jzlSyncWidth) _n._jzlSyncWidth();
                            }
                        } catch (_) {}
                        return _r;
                    };
                }
            } catch (_) {}
            return r;
        };

        // 工作流加载后恢复内部提示词窗口内容，并检查外部提示词端口连接状态
        const origConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            const r = origConfigure?.apply(this, arguments);
            const self = this;
            const box = self.__promptBox;
            if (!box) return r;
            const ip = (self.widgets || []).find((w) => w.name === "internal_prompt");
            const v = ip?.value ?? "";
            if (v && !getPromptText(box)) {
                box.innerText = v;
                renderPromptFromText(box, getPromptText(box), self);
            }
            // 幽灵接口兜底：configure 后清理内部存储字段端口
            try { self.__jzlKillGhost?.(); } catch (_) {}
            return r;
        };
    },
});
