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
const CHOOSE_ENDPOINT = "/jzl/choose_asset_file";
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
    samplers: ["res_multistep", "euler", "euler_ancestral", "dpmpp_2m", "dpmpp_2m_sde", "dpmpp_sde", "ddim", "uni_pc", "lcm", "gradient_estimation"],
    schedulers: ["simple", "normal", "karras", "exponential", "sgm_uniform", "beta", "ddim_uniform"],
    seedModes: ["randomize", "fixed", "increment"],
    decodeVideo: ["XB-BOX - VAE解码（原版优化）", "VAE解码"],
    decodeAudio: ["VAE解码（音频）"],
};

const PANELS = {
    assets: { label: "📁 参考素材管理" },
    prompt: { label: "📝 剧本拆解配置" },
    preference: { label: "🎭 采样解码设置" },
    preference_settings: { label: "🎯 镜头参数预设" },
    prompt_elements: { label: "➕ 常用提示词元素" },
    coming_soon: { label: "🚧 敬请期待..." },
};

// 节点表面按钮定义（前端 addWidget 添加）
const PANEL_BUTTONS = [
    { widget: "btn_assets", label: "📁 参考素材管理", panel: "assets" },
    { widget: "btn_prompt", label: "📝 剧本拆解配置", panel: "prompt" },
    { widget: "btn_pref", label: "🎭 采样解码设置", panel: "preference" },
    { widget: "btn_preference", label: "🎯 镜头参数预设", panel: "preference_settings" },
    { widget: "btn_elements", label: "➕ 常用提示词元素", panel: "prompt_elements" },
    { widget: "btn_coming", label: "🚧 敬请期待...", panel: "coming_soon" },
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
    // 与 getPromptText 一致的全名视图偏移：token 按 dataset.jzlAsset（全名）计长，
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
                    out += child.dataset.jzlAsset || "";
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
    // 与 caretOffset/getPromptText 保持一致的「全名视图」偏移：
    // 资产 token 整体按 dataset.jzlAsset（全名）长度计，而非内部简称文本长度。
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
                    const len = (child.dataset.jzlAsset || "").length;
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

function collectMentionItems(node) {
    const kindMap = { images: "image", videos: "video", audios: "audio" };
    const cache = node?.__jzlAssets || { images: [], videos: [], audios: [] };
    const items = [];
    for (const kindKey of ["images", "videos", "audios"]) {
        const kind = kindMap[kindKey];
        let displayIndex = 0;  // 显示连续编号（跳过空槽位，避免跳号：音频1、音频3）
        (cache[kindKey] || []).forEach((item) => {
            if (item?.enabled === false) return;
            if (!(item?.path || "").trim()) return;  // 空槽口（未上传素材）不显示在主界面
            const name = assetFullName(kind, displayIndex, item);  // 全名（图片1 角色 碗碗）
            displayIndex++;
            if (!name) return;
            items.push({
                name,                    // 全名（带空格）→ 后端匹配用
                token: name.replace(/\s+/g, ""),  // 去空格全名（后端提取用）
                display: (item?.name || "").trim() || name.replace(/\s+/g, ""),  // 简称（输入框显示）
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
        label.textContent = item.name;

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
    const space = document.createTextNode(" ");
    const afterRange = document.createRange();
    afterRange.setStartAfter(span);
    afterRange.collapse(true);
    afterRange.insertNode(space);
    const caretRange = document.createRange();
    caretRange.setStartAfter(space);
    caretRange.collapse(true);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(caretRange);
    promptCaretPos = start + token.length + 1;
    editable.dispatchEvent(new Event("input", { bubbles: true }));
    editable.dispatchEvent(new Event("change"));
}

function makeAssetToken(token, item) {
    const span = document.createElement("span");
    span.dataset.jzlAsset = token;  // 全名（去空格），后端匹配用
    span.dataset.jzlKind = item.kind || "";
    span.contentEditable = "false";
    span.className = "jzl-asset-token";
    span.title = item.name || token;  // hover 显示全名
    // 图片：内嵌缩略图；视频/音频：CSS 伪元素图标（不占用文本）
    if (item.kind === "image") {
        const img = document.createElement("img");
        img.className = "jzl-asset-thumb";
        img.src = item.path ? `${ASSET_PREVIEW_ENDPOINT}?path=${encodeURIComponent(item.path)}` : "/extensions/ComfyUI-JZL-MiniMax-H3/icon.png";
        img.onerror = () => { img.src = "/extensions/ComfyUI-JZL-MiniMax-H3/icon.png"; };
        span.appendChild(img);
    }
    const text = document.createElement("span");
    text.textContent = item.display || token;  // 输入框显示简称（如「碗碗」）
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
    // 把纯文本里的 @资产名 重新渲染成「缩略图 + 彩色文字」锁死 token（刷新恢复着色/缩略图）
    promptBox.innerHTML = "";
    const source = text || "";
    const re = /(?:图片|视频|音频)\d+[^\s@，。；,.、]*/g;
    let last = 0;
    for (const m of source.matchAll(re)) {
        if (m.index > last) promptBox.appendChild(document.createTextNode(source.slice(last, m.index)));
        const token = m[0];
        const item = findAssetByToken(token, node);
        if (item) {
            promptBox.appendChild(makeAssetToken(token, item));
        } else {
            promptBox.appendChild(document.createTextNode(token));
        }
        last = m.index + m[0].length;
    }
    if (last < source.length) promptBox.appendChild(document.createTextNode(source.slice(last)));
}

function insertAssetToken(editable, item) {
    // 在内部编辑窗口（contenteditable）光标处插入「缩略图 + 彩色」锁死 token（资产显示窗点击）
    if (!editable) return;
    const token = item.token;  // 去空格全名（后端匹配用）
    const span = makeAssetToken(token, item);
    const space = document.createTextNode(" ");
    editable.focus();
    // 用记忆的光标位置插入（点击资产窗时实时 selection 会丢失，导致 token 跑到开头）
    const offset = (typeof promptCaretPos === "number") ? promptCaretPos : getPromptText(editable).length;
    const range = setCaretToOffset(editable, offset);
    range.insertNode(span);
    const afterRange = document.createRange();
    afterRange.setStartAfter(span);
    afterRange.collapse(true);
    afterRange.insertNode(space);
    const caretRange = document.createRange();
    caretRange.setStartAfter(space);
    caretRange.collapse(true);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(caretRange);
    promptCaretPos = offset + token.length + 1;
    editable.dispatchEvent(new Event("input", { bubbles: true }));
    editable.dispatchEvent(new Event("change"));
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
    // 自动换行宫格：始终显示全部素材，多行时窗口与节点自动增高
    const grid = document.createElement("div");
    grid.style.cssText = "display:flex;flex-wrap:wrap;gap:4px;padding:2px;align-content:flex-start;";
    for (const item of items) {
        const cell = document.createElement("div");
        cell.style.cssText = "flex:0 0 52px;width:52px;cursor:pointer;border-radius:4px;overflow:hidden;border:1px solid #333;background:#111;";
        cell.title = [item.name, item.description].filter(Boolean).join("\n");  // hover 显示完整内容
        // 缩略图（图片）或图标（视频/音频）
        const thumb = document.createElement("div");
        thumb.style.cssText = "width:52px;height:34px;display:flex;align-items:center;justify-content:center;overflow:hidden;font-size:16px;background:#000;";
        if (item.kind === "image") {
            const img = document.createElement("img");
            img.style.cssText = "width:100%;height:100%;object-fit:cover;";
            img.src = item.path ? `${ASSET_PREVIEW_ENDPOINT}?path=${encodeURIComponent(item.path)}` : "";
            img.onerror = () => { img.remove(); };
            thumb.appendChild(img);
        } else {
            thumb.textContent = item.kind === "video" ? "🎬" : "🎧";
        }
        // 名称标签（类型 + 自定义名）
        const label = document.createElement("div");
        label.style.cssText = "width:100%;height:16px;line-height:16px;font-size:9px;color:#cdd8e2;background:rgba(10,20,30,.7);text-align:center;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding:0 2px;box-sizing:border-box;";
        label.textContent = ([item.type, item.display].filter(Boolean).join("")) || item.display || "";
        cell.append(thumb, label);
        cell.addEventListener("mousedown", (e) => e.stopPropagation());
        cell.addEventListener("click", () => insertAssetToken(textarea, item));
        grid.appendChild(cell);
    }
    windowBox.appendChild(grid);
    // 高度自适应内容（多行换行时增高），并通知节点调整整体高度
    const h = Math.max(grid.offsetHeight, 30);
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
        };
    } catch (_) {
        return { llm_models: [], mmproj_models: ["None"], chat_handlers: ["None"], story_styles: [] };
    }
}

async function loadManager(node) {
    // 节点独立配置：优先读工作流内保存的 manager_settings；空则全新默认（不继承其他节点/全局）
    const w = node?.widgets?.find((x) => x.name === "manager_settings");
    const raw = w ? readWidgetValue(w) : "";
    let settings = null;
    if (raw && typeof raw === "string" && raw.trim()) {
        try { const s = JSON.parse(raw); if (s && typeof s === "object") settings = s; } catch (_) {}
    }
    const lists = await loadLists();
    return { settings: settings || defaultSettings(), ...lists };
}

async function saveManager(node, value) {
    const w = node?.widgets?.find((x) => x.name === "manager_settings");
    if (w) setWidgetValue(w, JSON.stringify(value));
    return value;
}

async function chooseFile(kind) {
    const resp = await api.fetchApi(CHOOSE_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!data?.path) return null;
    return data.path;
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
    const renderList = () => {
        box.innerHTML = "";
        list.forEach((item, i) => {
            const isLast = i === list.length - 1;
            box.append(makeAssetCard(kind, i, item, list, fireEdit, () => {
                list.splice(i, 1);
                renderList();
                fireEdit();
            }, isLast, renderList));
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

function setupInternalPrompt(node, box, piWidget, ipWidget) {
    // 外部提示词端口（prompt_input）：只保留接线小圆点，隐藏文本框控件（只读、不可手输）
    const piTa = getPromptTextarea(piWidget);
    if (piTa) {
        piTa.readOnly = true;
        piTa.title = "外部提示词端口：连线后替代节点内编辑";
        piTa.style.display = "none";  // 隐藏文本框
    }
    if (piWidget) {
        // 隐藏整个控件容器（含 label/包裹层），只保留左侧接线圆点
        const el = piWidget.element;
        if (el) {
            try {
                if (el.style) el.style.display = "none";
                el.querySelectorAll?.("textarea, input, label").forEach((x) => { x.style.display = "none"; });
            } catch (_) {}
        }
        // 压缩 widget 高度为一行（端口圆点所在），避免空白占位
        piWidget.computeSize = () => [0, 24];
        if (!piWidget.options) piWidget.options = {};
        piWidget.options.serialize = false;
        piWidget.options.hidden = false;  // 不隐藏 widget（否则圆点也没了）
    }

    const syncInternal = () => {
        if (ipWidget) setWidgetValue(ipWidget, getPromptText(box));
    };
    const applyLock = (locked) => {
        box.contentEditable = locked ? "false" : "true";
        box.style.opacity = locked ? "0.45" : "1";
        box.title = locked ? "已接入外部提示词，节点内编辑锁定" : "";
    };
    const checkLink = () => {
        const inp = (node.inputs || []).find((i) => i.name === "prompt_input");
        applyLock(!!(inp && inp.link != null));
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
    box.addEventListener("blur", () => setTimeout(closeMentionMenu, 150));
    // 监听连线变化 → 锁定/解锁内部编辑（替代关系）
    // 用 type/connected 参数直接判定（type=1=LiteGraph.INPUT），避免断开后 inp.link 未及时清空导致无法解锁
    const origCC = node.onConnectionsChange;
    node.onConnectionsChange = function (type, index, connected, link_info) {
        const r = origCC?.apply(this, arguments);
        if (type === 1 && this.inputs && this.inputs[index]) {
            const inp = this.inputs[index];
            if (inp.name === "prompt_input") {
                applyLock(!!connected);
            } else if (inp.name === "internal_prompt" && connected) {
                // 拒绝：internal_prompt 是内部存储，禁止接线（幽灵防护）
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
    node.checkPromptLink = checkLink;
    syncInternal();
    checkLink();
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
        label.textContent = item.name;
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
    control.style.flex = "1";
    control.style.minWidth = "0";
    // 复选框/开关是 label 包裹，不加输入框样式；真正的输入控件才有 .jzl-input
    if (control.tagName === "INPUT" || control.tagName === "SELECT" || control.tagName === "TEXTAREA") {
        control.classList.add("jzl-input");
    }
    g.append(lab, control);
    return g;
}

function selectControl(options, value, onChange) {
    const s = el("select", "flex:1;min-width:0;");
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
    const i = el("input", "flex:1;min-width:0;");
    i.className = "jzl-input";
    i.type = "text";
    i.value = value || "";
    if (placeholder) i.placeholder = placeholder;
    i.addEventListener("change", () => onChange(i.value.trim()));
    return i;
}

function numberControl(value, opts, onChange) {
    const i = el("input", "flex:1;min-width:0;");
    i.className = "jzl-input";
    i.type = "number";
    i.value = value;
    if (opts) { i.min = opts.min; i.max = opts.max; i.step = opts.step; }
    i.addEventListener("change", () => onChange(parseFloat(i.value) || 0));
    return i;
}

function checkboxControl(value, labelText, onChange) {
    const w = el("label", "display:flex;align-items:center;gap:8px;cursor:pointer;font-size:13px;color:var(--fg-color,#ddd);");
    const c = el("input", "accent-color:#2d5a88;");
    c.type = "checkbox";
    c.checked = !!value;
    c.addEventListener("change", () => onChange(c.checked));
    w.append(c, el("span", "", labelText));
    return w;
}

// control_after_generate（生成后控制）：随机/固定/递增
const SEED_CONTROL_KEYS = ["randomize", "fixed", "increment"];
const SEED_CONTROL_LABEL = { randomize: "随机", fixed: "固定", increment: "递增" };

function seedControlRow(p) {
    // 原生感：标签 + 数字输入 + control_after_generate 按钮（点击循环 随机/固定/递增）
    const g = el("div", "display:flex;align-items:center;gap:12px;margin-bottom:10px;");
    const lab = el("label", "flex:0 0 160px;font-size:13px;color:var(--descrip-text,#999);white-space:nowrap;", "种子");
    const i = el("input", "flex:1;min-width:0;");
    i.type = "number";
    i.value = p.seed ?? 0;
    i.min = 0; i.max = 0xffffffffffffffff; i.step = 1;
    i.className = "jzl-input";
    i.addEventListener("change", () => { p.seed = Math.round(parseFloat(i.value) || 0); });
    const ctrl = el("button", "flex:0 0 auto;background:var(--comfy-input-bg,#2a2a2a);color:var(--fg-color,#ddd);border:1px solid var(--border-color,#555);border-radius:4px;padding:6px 10px;font-size:12px;cursor:pointer;white-space:nowrap;");
    const curKey = () => (SEED_CONTROL_LABEL[p.seed_control] ? p.seed_control : "randomize");
    const render = () => {
        ctrl.textContent = "🔁 " + SEED_CONTROL_LABEL[curKey()];
        ctrl.title = "生成后控制（control_after_generate）：随机=每次运行自动换新种子；固定=锁定当前值；递增=每次运行+1。点击切换";
    };
    ctrl.addEventListener("click", () => {
        const next = SEED_CONTROL_KEYS[(SEED_CONTROL_KEYS.indexOf(curKey()) + 1) % SEED_CONTROL_KEYS.length];
        p.seed_control = next;
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
                model: "", api_key: "", base_url: "",
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
            seed_mode: "randomize",
            decode_video: "XB-BOX - VAE解码（原版优化）", decode_audio: "VAE解码（音频）",
        },
    };
}

// ── 配置面板 ──────────────────────────────────────────────
function renderAssetsPanel(c, s, mode) {
    const assets = s.assets;
    // 素材引用提示（生成路径由引用内容自动推断）
    c.append(el("div", "background:#2b3a4a;border:1px solid #5b9bd5;border-radius:6px;padding:8px 12px;margin-bottom:8px;font-size:12px;color:#cfe3f7;", `素材引用上限：图片 ≤9 / 视频 ≤3 / 音频 ≤3（生成路径按引用内容自动推断：有视频→多参考，≥2图→首尾帧，1图→首帧，无→纯文本）`));

    renderAssetSection(c, "image", assets.images, "🖼️ 图片");
    renderAssetSection(c, "video", assets.videos, "🎬 视频");
    renderAssetSection(c, "audio", assets.audios, "🎧 音频");
}

function renderAutoSave(c, s) {
    c.append(field("自动保存", checkboxControl(s.auto_save !== false, "修改参数即时保存（无需点保存按钮）", v => { s.auto_save = v; })));
}

function renderPromptPanel(c, s, d) {
    const p = s.enhance;
    renderAutoSave(c, s);

    // ── 开关 ──
    c.append(makeSectionTitle("开关"));
    c.append(field("故事拆解", checkboxControl(p.story_decompose !== false, "把故事通过 LLM 拆解为分段提示词", v => { p.story_decompose = v; })));
    c.append(field("开启增强", checkboxControl(p.enabled === true, "拆解后对每个分段的详细描述再做润色", v => { p.enabled = v; })));
    c.append(field("强制卸载", checkboxControl(p.force_offload === true, "LLM 用完即卸载（增强开启时等增强后再卸）", v => { p.force_offload = v; })));

    // ── LLM 后端 ──
    c.append(makeSectionTitle("LLM 后端"));
    c.append(field("后端切换", selectControl(OPTIONS.llmBackend, p.llm_backend || OPTIONS.llmBackend[0], v => { p.llm_backend = v; })));

    // ── 本地 LLM 模型 ──
    const llm = p.llm || (p.llm = {});
    c.append(makeSectionTitle("本地 LLM 模型"));
    const llmModels = (d?.llm_models && d.llm_models.length) ? d.llm_models : ["（未找到本地 LLM 模型）"];
    const mmprojModels = (d?.mmproj_models && d.mmproj_models.length) ? d.mmproj_models : ["None"];
    const chatHandlers = (d?.chat_handlers && d.chat_handlers.length) ? d.chat_handlers : ["None"];
    // 关键修复：下拉默认显示第一个模型，但 llm.model 仍为空 → 之前点保存会存成空串触发「未选择本地 LLM 模型」。
    // 打开面板时把「所见即所得」同步进存储：不切换直接保存也会持久化当前显示的模型。
    if (!llm.model && llmModels.length && !llmModels[0].startsWith("（")) llm.model = llmModels[0];
    c.append(field("模型", selectControl(llmModels, llm.model || llmModels[0], v => { llm.model = v; })));
    c.append(field("视觉模块 mmproj", selectControl(mmprojModels, llm.mmproj || "None", v => { llm.mmproj = v; })));
    c.append(field("Chat Handler", selectControl(chatHandlers, llm.chat_handler || "None", v => { llm.chat_handler = v; })));
    c.append(field("推理后端", selectControl(["llama-cpp-python", "llama-server"], llm.backend || "llama-cpp-python", v => { llm.backend = v; })));
    c.append(field("上下文长度 n_ctx", numberControl(llm.n_ctx ?? 32768, { min: 1024, max: 262144, step: 128 }, v => { llm.n_ctx = Math.round(v); })));
    c.append(field("显存上限 vram_limit (GB)", numberControl(llm.vram_limit ?? -1, { min: -1, max: 1024, step: 1 }, v => { llm.vram_limit = Math.round(v); })));
    c.append(field("图像最小 tokens", numberControl(llm.image_min_tokens ?? 0, { min: 0, max: 4096, step: 32 }, v => { llm.image_min_tokens = Math.round(v); })));
    c.append(field("图像最大 tokens", numberControl(llm.image_max_tokens ?? 0, { min: 0, max: 4096, step: 32 }, v => { llm.image_max_tokens = Math.round(v); })));
    c.append(field("max_tokens", numberControl(llm.max_tokens ?? 8192, { min: 0, max: 262144, step: 1 }, v => { llm.max_tokens = Math.round(v); })));
    c.append(field("top_k", numberControl(llm.top_k ?? 40, { min: 0, max: 1000, step: 1 }, v => { llm.top_k = Math.round(v); })));
    c.append(field("top_p", numberControl(llm.top_p ?? 0.9, { min: 0, max: 1, step: 0.01 }, v => { llm.top_p = v; })));
    c.append(field("min_p", numberControl(llm.min_p ?? 0.05, { min: 0, max: 1, step: 0.01 }, v => { llm.min_p = v; })));
    c.append(field("typical_p", numberControl(llm.typical_p ?? 1.0, { min: 0, max: 1, step: 0.01 }, v => { llm.typical_p = v; })));
    c.append(field("temperature", numberControl(llm.temperature ?? 0.6, { min: 0, max: 2, step: 0.01 }, v => { llm.temperature = v; })));
    c.append(field("repeat_penalty", numberControl(llm.repeat_penalty ?? 1.05, { min: 0, max: 10, step: 0.01 }, v => { llm.repeat_penalty = v; })));
    c.append(field("frequency_penalty", numberControl(llm.frequency_penalty ?? 0.0, { min: 0, max: 1, step: 0.01 }, v => { llm.frequency_penalty = v; })));
    c.append(field("present_penalty", numberControl(llm.present_penalty ?? 0.0, { min: 0, max: 2, step: 0.01 }, v => { llm.present_penalty = v; })));
    c.append(field("mirostat_mode", numberControl(llm.mirostat_mode ?? 0, { min: 0, max: 2, step: 1 }, v => { llm.mirostat_mode = Math.round(v); })));
    c.append(field("mirostat_eta", numberControl(llm.mirostat_eta ?? 0.1, { min: 0, max: 1, step: 0.01 }, v => { llm.mirostat_eta = v; })));
    c.append(field("mirostat_tau", numberControl(llm.mirostat_tau ?? 5.0, { min: 0, max: 10, step: 0.01 }, v => { llm.mirostat_tau = v; })));
    c.append(field("GPU 设备", selectControl(["auto", "0", "1", "2", "3"], llm.gpu_device || "auto", v => { llm.gpu_device = v; })));

    // ── 在线 API ──
    const api = p.api || (p.api = {});
    c.append(makeSectionTitle("在线 API"));
    c.append(field("服务商", selectControl(OPTIONS.providers, api.provider || OPTIONS.providers[0], v => { api.provider = v; })));
    c.append(field("模型", textControl(api.model || "", "如 gpt-4o / deepseek-chat…", v => { api.model = v; })));
    c.append(field("API Key", textControl(api.api_key || "", "sk-…", v => { api.api_key = v; })));
    c.append(field("Base URL", textControl(api.base_url || "", "https://api.openai.com/v1", v => { api.base_url = v; })));
    c.append(field("temperature", numberControl(api.temperature ?? 0.6, { min: 0, max: 2, step: 0.01 }, v => { api.temperature = v; })));
    c.append(field("max_tokens", numberControl(api.max_tokens ?? 8192, { min: 1, max: 262144, step: 1 }, v => { api.max_tokens = Math.round(v); })));
    c.append(field("thinking", selectControl(["disabled", "enabled"], api.thinking || "disabled", v => { api.thinking = v; })));

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

function renderPrefPanel(c, s) {
    const p = s.sample_decode;
    renderAutoSave(c, s);
    c.append(makeSectionTitle("采样"));
    c.append(field("K采样器", selectControl(OPTIONS.samplers, p.sampler || OPTIONS.samplers[0], v => { p.sampler = v; })));
    c.append(field("调度器", selectControl(OPTIONS.schedulers, p.scheduler || OPTIONS.schedulers[0], v => { p.scheduler = v; })));
    c.append(field("步数", numberControl(p.steps ?? 4, { min: 1, max: 200, step: 1 }, v => { p.steps = Math.round(v); })));
    c.append(field("CFG", numberControl(p.cfg ?? 1.0, { min: 0, max: 30, step: 0.1 }, v => { p.cfg = v; })));
    c.append(field("种子模式", selectControl(OPTIONS.seedModes, p.seed_mode || OPTIONS.seedModes[0], v => { p.seed_mode = v; })));
    c.append(makeSectionTitle("解码"));
    c.append(field("视频解码", selectControl(OPTIONS.decodeVideo, p.decode_video || OPTIONS.decodeVideo[0], v => { p.decode_video = v; })));
    c.append(field("音频解码", selectControl(OPTIONS.decodeAudio, p.decode_audio || OPTIONS.decodeAudio[0], v => { p.decode_audio = v; })));
}

function buildModal(node, data, panelId) {
    ensureManagerStyle();
    const settings = (data && data.settings) ? data.settings : defaultSettings();
    const d = data || { llm_models: [], mmproj_models: ["None"], chat_handlers: ["None"] };
    const title = (PANELS[panelId] && PANELS[panelId].label) || "🎬 MiniMax-H3生成管理器";

    const overlay = el("div", "position:fixed;inset:0;background:rgba(0,0,0,0.78);z-index:9999;display:flex;align-items:center;justify-content:center;");
    const dialog = el("section", "background:#1c1c1e;border:1px solid #333;border-radius:8px;width:820px;max-height:90vh;display:flex;flex-direction:column;box-shadow:0 20px 40px rgba(0,0,0,0.6);");
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
        case "assets": renderAutoSave(panelBox, settings); renderAssetsPanel(panelBox, settings, d.mode); break;
        case "prompt": renderPromptPanel(panelBox, settings, d); break;
        case "preference": renderPrefPanel(panelBox, settings); break;
        case "preference_settings": renderPreferenceSettingsPanel(panelBox, settings); break;
        default: renderAutoSave(panelBox, settings);
    }
    dialog.append(panelBox);

    // 底部
    const error = el("div", "color:#e55;font-size:12px;margin:0 20px;min-height:16px;");
    const footer = el("div", "padding:15px 20px;border-top:1px solid var(--border-color,#444);display:flex;justify-content:flex-end;gap:10px;background:#18181a;border-bottom-left-radius:8px;border-bottom-right-radius:8px;");
    const cancelBtn = el("button", "background:transparent;border:1px solid var(--border-color,#555);color:#fff;border-radius:4px;padding:8px 20px;font-size:14px;cursor:pointer;", "取消");
    const saveBtn = el("button", "background:#2d5a88;color:#fff;border:none;border-radius:4px;padding:8px 20px;font-size:14px;font-weight:600;cursor:pointer;", "💾 保存");
    footer.append(cancelBtn, saveBtn);
    dialog.append(error, footer);

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

            // 1. 隐藏内部存储 widget（internal_prompt）与旧 mode；prompt_input 原生显示（只读外部端口）
            const vcWidget = (self.widgets || []).find((w) => w.name === "video_count");
            const piWidget = (self.widgets || []).find((w) => w.name === "prompt_input");
            const ipWidget = (self.widgets || []).find((w) => w.name === "internal_prompt");
            const hiddenNames = new Set(["mode", "internal_prompt", "manager_settings"]);
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

            // 按钮区（2×2）
            const btnGrid = document.createElement("div");
            btnGrid.style.cssText = "display:grid;grid-template-columns:repeat(3,1fr);grid-auto-rows:30px;gap:6px;";
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
                btn.addEventListener("mousedown", (e) => e.stopPropagation());
                btn.addEventListener("mouseenter", () => { btn.style.background = "#4a4a4a"; });
                btn.addEventListener("mouseleave", () => { btn.style.background = "#3a3a3a"; });
                btn.addEventListener("click", () => {
                    if (b.panel === "prompt_elements") { showPromptElements(self); return; }
                    if (b.panel === "coming_soon") { notify("🚧 该功能敬请期待...", "success"); return; }
                    openModal(self, b.panel);
                });
                btnGrid.appendChild(btn);
            }
            container.appendChild(btnGrid);

            // 提示词：内部编辑窗口（DOM 富文本 @ 着色）+ 外部提示词端口（prompt_input 只读，连线后替代）
            const promptLabel = el("div", "font-size:12px;color:#bbb;", "📝 提示词（用 @ 引用素材）");
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
            setupInternalPrompt(self, promptBox, piWidget, ipWidget);

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
                return r;
            };

            // 端口顺序：外部提示词（prompt_input）小圆点与 clip 等端口并列，移到音频VAE下方
            const reorderInputs = () => {
                const ins = self.inputs;
                if (!ins) return;
                const pi = ins.findIndex((i) => i.name === "prompt_input");
                const av = ins.findIndex((i) => i.name === "audio_vae");
                if (pi < 0 || av < 0 || pi === av + 1) return;
                const item = ins.splice(pi, 1)[0];
                ins.splice(av + 1, 0, item);
                ins.forEach((i, k) => { i.slot = k; });
                self.setDirtyCanvas?.(true, true);
            };
            setTimeout(reorderInputs, 0);

            // 清理 internal_prompt 的幽灵连线 + 强制无 socket（socketless 内部存储接口不应被接线；
            // 旧工作流残留连线（如「字符串A」→internal_prompt）会渲染幽灵接口/幽灵显示栏）。
            // 多次重试覆盖工作流加载时序（链接在节点 configure 之后才连上）。
            const killGhost = () => {
                try {
                    const ipIn = (self.inputs || []).find((i) => i.name === "internal_prompt");
                    if (ipIn) {
                        // 1. 断开残留连线（旧工作流曾把「字符串A」接到 internal_prompt）
                        if (ipIn.link != null) {
                            const linkId = ipIn.link;
                            ipIn.link = null;
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
                            console.log("[JZL-管理器] 已清理 internal_prompt 幽灵连线");
                        }
                        // 2. 彻底移除端口（internal_prompt 是内部存储字段，无端口；widget 值保留供 execute 取值）
                        const idx = self.inputs.indexOf(ipIn);
                        if (idx >= 0) {
                            self.inputs.splice(idx, 1);
                            (self.inputs || []).forEach((i, k) => { i.slot = k; });
                        }
                        self.setDirtyCanvas?.(true, true);
                    }
                } catch (_) {}
            };
            [0, 150, 500, 1200].forEach((d) => setTimeout(killGhost, d));

            // 资产显示窗（缩略图墙，点击插入 @引用；自动换行，多行时节点同步增高）
            const windowTitle = el("div", "font-size:12px;color:#bbb;margin-top:2px;", "📁 资产显示窗（点击插入）");
            const windowBox = el("div", "min-height:30px;overflow:hidden;flex:0 0 auto;");
            const resizeNodeForContent = () => {
                requestAnimationFrame(() => {
                    try {
                        const jy = (self.widgets || []).find((w) => w.name === "jzl_manager")?.y || 200;
                        const assetsH = windowBox.offsetHeight || 30;
                        const btnRows = Math.ceil(PANEL_BUTTONS.length / 3);
                        const minDom = btnRows * 36 + 8 + 64 + 22 + assetsH + 18;  // 按钮N行 + gap + 提示词min + 资产窗标题 + padding
                        const need = jy + minDom;
                        if (self.size && need > (self.size[1] || 0) + 1) {
                            self.setSize([self.size[0], need]);
                            self.setDirtyCanvas?.(true, true);
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
                renderPromptFromText(self.__promptBox, getPromptText(self.__promptBox), self);
                if (ipWidget) setWidgetValue(ipWidget, getPromptText(self.__promptBox));
            };

            // 分辨率/帧数只读显示：监听原生参数 widget（画幅/MP/时长）变化后联动刷新
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
                const [wr, hr] = AR_MAP[ar] || [16, 9];
                const total = mp * 1024 * 1024;
                const scale = Math.sqrt(total / (wr * hr));
                const W = Math.max(32, Math.round((wr * scale) / 32) * 32);
                const H = Math.max(32, Math.round((hr * scale) / 32) * 32);
                const base = Math.max(5, Math.round(dur * 24));
                const frames = base + (5 - (base % 17)) % 17;
                const disp = (self.widgets || []).find((x) => x.name === "display_info");
                if (disp) setWidgetValue(disp, `${W}x${H} · ${frames}帧`);
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
            ["aspect_ratio", "megapixels", "duration"].forEach(watchChange);

            loadManager(self).then((data) => {
                cacheAssets(self, data.settings);
                updateDisplay();
                refreshAssets();
            }).catch(() => {});
            self.__jzlRefresh = refreshAssets;  // 弹窗保存资产后实时刷新本节点

            // 生成后控制回写：后端返回新 seed → 更新本节点 manager_settings
            const prevOnExecuted = self.onExecuted;
            self.onExecuted = function (message) {
                const r = prevOnExecuted?.apply(this, arguments);
                try {
                    const su = message?.seed_update;
                    if (su && typeof su.seed === "number") {
                        const msW = (self.widgets || []).find((x) => x.name === "manager_settings");
                        if (msW) {
                            const raw = readWidgetValue(msW);
                            let s = {};
                            try { s = raw ? JSON.parse(raw) : {}; } catch (_) {}
                            if (!s.enhance) s.enhance = {};
                            s.enhance.seed = su.seed;
                            s.enhance.seed_control = su.seed_control || s.enhance.seed_control || "randomize";
                            setWidgetValue(msW, JSON.stringify(s));
                        }
                    }
                } catch (_) {}
                return r;
            };

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
            }

            // 节点 resize 时触发重绘，让 DOM widget（输入框）跟随高度
            const prevOnResize = self.onResize;
            self.onResize = function (...args) {
                const rr = prevOnResize?.apply(this, args);
                try { self.setDirtyCanvas?.(true, true); } catch (_) {}
                return rr;
            };

            // 4. 刷新节点尺寸（隐藏 widget 后需重算），并多次调用应对异步布局
            const refreshSize = () => {
                try {
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
            if (typeof self.checkPromptLink === "function") self.checkPromptLink();
            return r;
        };
    },
});
