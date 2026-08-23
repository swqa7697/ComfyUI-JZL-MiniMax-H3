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

// ── 下拉选项（与后端节点保持一致的选项列表） ─────────────────────
const OPTIONS = {
    llmBackend: ["本地模型 [local]", "在线API [api]"],
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
    creativeReq: ["无特别要求", "节奏紧凑", "悬念反转", "情感细腻", "幽默搞笑", "视觉奇观", "燃向热血", "治愈温暖", "暗黑压抑", "多反转结局", "开放式结局", "强冲突"],
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
    accelModes: ["关闭", "XB-BOX - 🚀 Sage + 分块 黄金搭档", "SAGE注意力补丁KJ", "ModelAttentionBackend"],
    decodeVideo: ["XB-BOX - VAE解码（原版优化）", "VAE解码"],
    decodeAudio: ["VAE解码（音频）"],
};

const PANELS = {
    models: { label: "🤖 MiniMax模型设置" },
    assets: { label: "📁 引用资产设置" },
    prompt: { label: "📝 文本增强设置" },
    gen_params: { label: "⚙️ 生成参数设置" },
    preference: { label: "🎭 采样解码设置" },
    save: { label: "🚧 敬请期待" },
};

// 节点表面按钮定义（前端 addWidget 添加）
const PANEL_BUTTONS = [
    { widget: "btn_models", label: "🤖 MiniMax模型设置", panel: "models" },
    { widget: "btn_assets", label: "📁 引用资产设置", panel: "assets" },
    { widget: "btn_prompt", label: "📝 文本增强设置", panel: "prompt" },
    { widget: "btn_gen", label: "⚙️ 生成参数设置", panel: "gen_params" },
    { widget: "btn_pref", label: "🎭 采样解码设置", panel: "preference" },
    { widget: "btn_save", label: "🚧 敬请期待", panel: "save" },
];

const KIND_LABEL = { image: "图片", video: "视频", audio: "音频" };
// 每种资产类型不同的分类选项
const ASSET_TYPES_BY_KIND = {
    image: ["角色", "场景", "道具", "分镜", "其他"],
    video: ["主体", "运镜", "特效", "其他"],
    audio: ["音色", "音效", "配乐", "念白", "其他"],
};
const ASSET_TYPES = ASSET_TYPES_BY_KIND.image;

// 生成模式（与后端 GENERATION_MODES 一致）
const GEN_MODES = [
    "纯文本生成音视频-T2VA",
    "首帧图生成音视频-I2VA",
    "尾帧图生成音视频-L2VA",
    "首尾帧生成音视频-FL2VA",
    "音视频生成音视频-VA2VA",
    "多参考生成音视频-REF2VA",
];

let modal = null;

// ── @ 引用素材 ─────────────────────────────────────────────
let assetNameCache = { images: [], videos: [], audios: [] };
let mentionMenu = null;
let mentionState = null;  // { textarea, start, query }

const KIND_PREFIX = { image: "图片", video: "视频", audio: "音频" };
const KIND_ICON = { image: "🖼️", video: "🎬", audio: "🎧" };

function assetFullName(kind, index, item) {
    return [KIND_PREFIX[kind] + (index + 1), item?.type, item?.name].filter(Boolean).join(" ");
}

function cacheAssets(settings) {
    assetNameCache = settings?.assets || { images: [], videos: [], audios: [] };
}

function collectMentionItems() {
    const kindMap = { images: "image", videos: "video", audios: "audio" };
    const items = [];
    for (const kindKey of ["images", "videos", "audios"]) {
        const kind = kindMap[kindKey];
        (assetNameCache[kindKey] || []).forEach((item, i) => {
            if (item?.enabled === false) return;
            const name = assetFullName(kind, i, item);
            if (!name) return;
            items.push({ name, kind, path: item?.path || "" });
        });
    }
    return items;
}

function closeMentionMenu() {
    if (mentionMenu) { mentionMenu.remove(); mentionMenu = null; }
    mentionState = null;
}

function openMentionMenu(textarea, start, query) {
    const items = collectMentionItems().filter((it) =>
        !query || it.name.toLowerCase().includes(query.toLowerCase()));
    if (!items.length) { closeMentionMenu(); return; }

    closeMentionMenu();
    mentionState = { textarea, start };

    const rect = textarea.getBoundingClientRect();
    const menu = document.createElement("div");
    menu.style.cssText = "position:fixed;z-index:10001;background:#1e1e1e;border:1px solid #444;border-radius:6px;max-height:220px;overflow-y:auto;min-width:220px;box-shadow:0 8px 20px rgba(0,0,0,0.5);";
    menu.style.left = rect.left + "px";
    menu.style.top = (rect.bottom + 4) + "px";

    for (const item of items) {
        const row = document.createElement("div");
        row.style.cssText = "display:flex;align-items:center;gap:8px;padding:6px 10px;font-size:12px;color:#ddd;cursor:pointer;";
        row.append(el("span", "flex:0 0 auto;", KIND_ICON[item.kind] || "📁"));
        const label = el("span", "flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;", item.name);
        row.append(label);
        if (item.kind === "image" && item.path) {
            const thumb = document.createElement("img");
            thumb.src = `${ASSET_PREVIEW_ENDPOINT}?path=${encodeURIComponent(item.path)}`;
            thumb.style.cssText = "width:24px;height:24px;object-fit:cover;border-radius:3px;border:1px solid #555;flex:0 0 auto;";
            thumb.onerror = () => { thumb.remove(); };
            row.append(thumb);
        }
        row.addEventListener("mousedown", (e) => { e.preventDefault(); e.stopPropagation(); });
        row.addEventListener("click", () => chooseMention(item));
        row.addEventListener("mouseenter", () => { row.style.background = "#2a2a2a"; });
        row.addEventListener("mouseleave", () => { row.style.background = "transparent"; });
        menu.appendChild(row);
    }

    document.body.appendChild(menu);
    mentionMenu = menu;

    const dismiss = (e) => {
        if (!menu.contains(e.target)) closeMentionMenu();
    };
    setTimeout(() => document.addEventListener("mousedown", dismiss, { once: true }), 0);
}

function chooseMention(item) {
    if (!mentionState) return;
    const { textarea, start } = mentionState;
    const val = textarea.value;
    const cursor = textarea.selectionStart;
    // 插入去空格资产名（后端 @(\S+) 提取），显示名仍带空格
    const token = item.name.replace(/\s+/g, "");
    textarea.value = val.slice(0, start) + token + " " + val.slice(cursor);
    const pos = start + token.length + 1;
    closeMentionMenu();
    textarea.dispatchEvent(new Event("change"));
    textarea.focus();
    try { textarea.setSelectionRange(pos, pos); } catch (_) {}
}

function notify(msg, type = "success") {
    try {
        if (app?.ui?.toast) { app.ui.toast.add({ text: msg, type }); return; }
    } catch (_) {}
    console.log(`[JZL Asset] ${msg}`);
}

async function loadManager() {
    const resp = await api.fetchApi(MANAGER_ENDPOINT);
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok || !data?.ok) throw new Error(data?.error || `HTTP ${resp.status}`);
    return data;
}

async function saveManager(value) {
    const resp = await api.fetchApi(MANAGER_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(value),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok || !data?.ok) throw new Error(data?.error || `HTTP ${resp.status}`);
    return data.settings || value;
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

function makeAssetRow(kind, index, item, onChanged) {
    const row = el("div", "display:flex;align-items:center;gap:6px;margin:4px 0;padding:4px 6px;background:var(--comfy-menu-bg,#232323);border:1px solid var(--border-color,#3a3a3a);border-radius:5px;");
    row.append(el("span", "flex:0 0 46px;font-size:12px;color:var(--descrip-text,#999);", `${KIND_LABEL[kind]}${index + 1}`));

    // 类型下拉（按 kind 分类）
    const sel = el("select", "flex:0 0 64px;background:var(--comfy-input-bg,#1d1d1d);color:var(--fg-color,#ddd);border:1px solid var(--border-color,#444);border-radius:4px;padding:4px 2px;font-size:12px;");
    for (const t of (ASSET_TYPES_BY_KIND[kind] || ASSET_TYPES)) {
        const o = el("option", "", t);
        if (t === item.type) o.selected = true;
        sel.append(o);
    }
    sel.addEventListener("change", () => { item.type = sel.value; onChanged(); });

    // 名称输入
    const nameInp = el("input", "flex:1 1 90px;width:0;background:var(--comfy-input-bg,#1d1d1d);color:var(--fg-color,#ddd);border:1px solid var(--border-color,#444);border-radius:4px;padding:5px 6px;font-size:12px;");
    nameInp.type = "text";
    nameInp.placeholder = "名称（孙悟空/天神殿…）";
    nameInp.value = item.name || "";
    nameInp.addEventListener("change", () => { item.name = nameInp.value.trim(); onChanged(); });

    // 图片缩略图预览（仅图片槽位）
    let preview = null;
    if (kind === "image") {
        preview = el("img", "flex:0 0 42px;width:42px;height:42px;object-fit:cover;border-radius:4px;border:1px solid var(--border-color,#444);background:#111;cursor:pointer;");
        preview.alt = "预览";
        preview.title = "点击查看大图";
        preview.addEventListener("click", () => {
            const p = (item.path || "").trim();
            if (p) window.open(api.apiURL(`/jzl/asset_preview?path=${encodeURIComponent(p)}`), "_blank");
        });
    }

    // 文件名显示（可编辑，也支持直接填绝对路径）
    const pathInp = el("input", "flex:2 1 160px;width:0;background:var(--comfy-input-bg,#1d1d1d);color:var(--fg-color,#aaa);border:1px solid var(--border-color,#444);border-radius:4px;padding:5px 6px;font-size:12px;");
    pathInp.type = "text";
    pathInp.placeholder = "文件路径";
    pathInp.value = item.path || "";
    pathInp.addEventListener("change", () => { item.path = pathInp.value.trim(); refreshPreview(); onChanged(); });

    const refreshPreview = () => {
        if (!preview) return;
        const p = (item.path || "").trim();
        if (p) preview.src = api.apiURL(`/jzl/asset_preview?path=${encodeURIComponent(p)}`);
        else preview.src = "/extensions/ComfyUI-JZL-MiniMax-H3/icon.png"; // 无图时显示节点 logo
    };

    const pickBtn = el("button", "flex:0 0 auto;background:var(--comfy-input-bg,#2a2a2a);color:var(--fg-color,#ddd);border:1px solid var(--border-color,#555);border-radius:4px;padding:5px 8px;font-size:12px;cursor:pointer;", "📁");
    pickBtn.title = "选择文件";
    pickBtn.addEventListener("click", async () => {
        const p = await chooseFile(kind);
        if (p) { item.path = p; pathInp.value = p; refreshPreview(); onChanged(); }
    });

    // 启用开关
    const chk = el("input", "flex:0 0 auto;width:16px;height:16px;cursor:pointer;");
    chk.type = "checkbox";
    chk.checked = item.enabled !== false;
    chk.title = "启用/禁用";
    chk.addEventListener("change", () => { item.enabled = chk.checked; onChanged(); });

    if (preview) row.append(preview);
    row.append(sel, nameInp, pathInp, pickBtn, chk);
    refreshPreview();
    return row;
}

function renderSection(container, kind, list, onChanged) {
    container.innerHTML = "";
    for (let i = 0; i < list.length; i++) {
        container.append(makeAssetRow(kind, i, list[i], onChanged));
    }
}

function ensureCount(list, n, kind) {
    const defaultType = (ASSET_TYPES_BY_KIND[kind] || ASSET_TYPES)[0] || "其他";
    while (list.length < n) list.push({ type: defaultType, name: "", path: "", enabled: true });
    if (list.length > n) list.length = n;
}

function openModal(node, panelId) {
    if (modal) { modal.overlay?.querySelector?.("input,button,select")?.focus?.(); return; }

    const modeWidget = (node?.widgets || []).find((w) => w.name === "mode");
    loadManager().then((data) => {
        data.mode = modeWidget?.value || "";
        buildModal(node, data, panelId);
    }).catch((e) => {
        notify("读取管理器配置失败：" + e.message, "error");
        buildModal(node, { settings: null, llm_models: [], mmproj_models: ["None"], chat_handlers: ["None"], mode: modeWidget?.value || "" }, panelId);
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
    ].join("\n");
    document.head.append(st);
}

// ── 表单控件 ──────────────────────────────────────────────
function field(labelText, control) {
    const g = el("div", "display:flex;align-items:center;gap:10px;margin-bottom:12px;background:#232323;padding:10px;border-radius:6px;border:1px solid #333;");
    const lab = el("label", "flex:0 0 150px;font-size:14px;color:#bbb;", labelText);
    control.style.flex = "1";
    control.style.minWidth = "0";
    g.append(lab, control);
    return g;
}

function selectControl(options, value, onChange) {
    const s = el("select", "background:var(--input-bg,#2a2a2a);border:1px solid var(--border-color,#444);color:#fff;padding:8px 12px;border-radius:4px;outline:none;");
    for (const o of options) {
        const op = el("option", "", o);
        if (o === value) op.selected = true;
        s.append(op);
    }
    s.addEventListener("change", () => onChange(s.value));
    return s;
}

function textControl(value, placeholder, onChange) {
    const i = el("input", "background:var(--input-bg,#2a2a2a);border:1px solid var(--border-color,#444);color:#fff;padding:8px 12px;border-radius:4px;outline:none;");
    i.type = "text";
    i.value = value || "";
    if (placeholder) i.placeholder = placeholder;
    i.addEventListener("change", () => onChange(i.value.trim()));
    return i;
}

function numberControl(value, opts, onChange) {
    const i = el("input", "background:var(--input-bg,#2a2a2a);border:1px solid var(--border-color,#444);color:#fff;padding:8px 12px;border-radius:4px;outline:none;");
    i.type = "number";
    i.value = value;
    if (opts) { i.min = opts.min; i.max = opts.max; i.step = opts.step; }
    i.addEventListener("change", () => onChange(parseFloat(i.value) || 0));
    return i;
}

function checkboxControl(value, labelText, onChange) {
    const w = el("label", "display:flex;align-items:center;gap:8px;cursor:pointer;font-size:13px;color:#bbb;");
    const c = el("input", "accent-color:#2d5a88;");
    c.type = "checkbox";
    c.checked = !!value;
    c.addEventListener("change", () => onChange(c.checked));
    w.append(c, el("span", "", labelText));
    return w;
}

function defaultSettings() {
    return {
        auto_save: true,
        models: {
            fl2va: { model: "", loras: [] },
            ref2va: { model: "", loras: [] },
            common: { clip: "", video_vae: "", audio_vae: "", accel_mode: "关闭" },
        },
        assets: { images: [], videos: [], audios: [] },
        enhance: {
            enabled: false, llm_backend: "本地模型 [local]",
            preset_mode: "首尾帧生成音视频[中文]-FL2VA [ZH]",
            duration: 8, visual_style: "不指定 / Unspecified", music: "禁止音乐 / No Music",
            aspect: "16:9", cuts: "不指定 / Unspecified",
            preset_prompt: "", custom_prompt: "", system_prompt: "",
            inference_mode: "one by one", max_frames: 24, max_size: 256, seed: 0,
        },
        gen_params: {
            aspect_ratio: "16:9 (Widescreen)", megapixels: 1.0, multiple: 32, duration: 8,
            width: 0, height: 0, scale_factor: 1.0, upscale_scale: 1.5,
        },
        sample_decode: {
            sampler: "res_multistep", scheduler: "simple", steps: 25, cfg: 1.0,
            shift_video: 12.0, shift_audio: 3.0, seed_mode: "randomize",
            decode_video: "XB-BOX - VAE解码（原版优化）", decode_audio: "VAE解码（音频）",
        },
    };
}

// ── 六个配置面板 ────────────────────────────────────────────
function selectOpts(options, current) {
    if (options && options.length) return options;
    return [current || "（无模型）"];
}

function renderLoraGroup(c, group, loraOpts) {
    group.loras = group.loras || [];
    const countRow = el("div", "display:flex;align-items:center;gap:8px;margin:4px 0;");
    countRow.append(el("span", "font-size:12px;color:#bbb;flex:0 0 80px;", "LoRA 数量"));
    const dec = el("button", "width:24px;height:24px;background:#2a2a2a;color:#ddd;border:1px solid #555;border-radius:5px;font-size:12px;cursor:pointer;", "◀");
    const cnt = el("input", "width:40px;height:24px;text-align:center;background:#2a2a2a;color:#ddd;border:1px solid #444;border-radius:4px;font-size:12px;");
    cnt.type = "number"; cnt.min = "0"; cnt.max = "8"; cnt.value = group.loras.length;
    const inc = el("button", "width:24px;height:24px;background:#2a2a2a;color:#ddd;border:1px solid #555;border-radius:5px;font-size:12px;cursor:pointer;", "▶");
    const loraBox = el("div", "margin-left:8px;");

    const renderLoras = () => {
        loraBox.innerHTML = "";
        group.loras.forEach((lr, i) => {
            const row = el("div", "display:flex;align-items:center;gap:6px;margin:4px 0;");
            row.append(el("span", "font-size:11px;color:#999;flex:0 0 48px;", `LoRA ${i + 1}`));
            const sel = selectControl(selectOpts(loraOpts, lr.name), lr.name || "", v => { lr.name = v; });
            sel.style.flex = "2";
            sel.style.minWidth = "0";
            const str = numberControl(lr.strength ?? 1.0, { min: -10, max: 10, step: 0.05 }, v => { lr.strength = v; });
            str.style.flex = "1";
            str.style.minWidth = "0";
            row.append(sel, el("span", "font-size:11px;color:#999;white-space:nowrap;", "强度"), str);
            loraBox.appendChild(row);
        });
    };
    const apply = (n) => {
        n = Math.max(0, Math.min(8, Math.floor(n)));
        cnt.value = n;
        while (group.loras.length < n) group.loras.push({ name: "", strength: 1.0 });
        group.loras.length = n;
        renderLoras();
    };
    [dec, cnt, inc].forEach(x => x.addEventListener("mousedown", (e) => e.stopPropagation()));
    dec.addEventListener("click", () => apply(group.loras.length - 1));
    inc.addEventListener("click", () => apply(group.loras.length + 1));
    cnt.addEventListener("change", () => apply(parseInt(cnt.value, 10) || 0));
    countRow.append(dec, cnt, inc);
    c.append(countRow, loraBox);
    renderLoras();
}

function renderModelsPanel(c, d, s) {
    const m = s.models;
    const diffOpts = d.diffusion_models || [];
    const clipOpts = d.clip_models || [];
    const vaeOpts = d.vae_models || [];
    const loraOpts = d.lora_models || [];
    const fl = m.fl2va, rf = m.ref2va, cm = m.common;

    c.append(makeSectionTitle("fl2va"));
    c.append(field("fl2va 模型", selectControl(selectOpts(diffOpts, fl.model), fl.model || "", v => { fl.model = v; })));
    renderLoraGroup(c, fl, loraOpts);

    c.append(makeSectionTitle("ref2va"));
    c.append(field("ref2va 模型", selectControl(selectOpts(diffOpts, rf.model), rf.model || "", v => { rf.model = v; })));
    renderLoraGroup(c, rf, loraOpts);

    c.append(makeSectionTitle("通用"));
    c.append(field("CLIP 选择", selectControl(selectOpts(clipOpts, cm.clip), cm.clip || "", v => { cm.clip = v; })));
    c.append(field("视频 VAE", selectControl(selectOpts(vaeOpts, cm.video_vae), cm.video_vae || "", v => { cm.video_vae = v; })));
    c.append(field("音频 VAE", selectControl(selectOpts(vaeOpts, cm.audio_vae), cm.audio_vae || "", v => { cm.audio_vae = v; })));
    c.append(field("加速模式", selectControl(OPTIONS.accelModes, cm.accel_mode || "关闭", v => { cm.accel_mode = v; })));
}

// 各生成模式需要的引用素材上限
const MODE_ASSET_LIMITS = {
    "纯文本生成音视频-T2VA": { hint: "T2VA 纯文本生成，无需引用素材", img: 0, vid: 0, aud: 0 },
    "首帧图生成音视频-I2VA": { hint: "I2VA 需要 1 张首帧图", img: 1, vid: 0, aud: 0 },
    "尾帧图生成音视频-L2VA": { hint: "L2VA 需要 1 张尾帧图", img: 1, vid: 0, aud: 0 },
    "首尾帧生成音视频-FL2VA": { hint: "FL2VA 需要 2 张图（首帧 + 尾帧）", img: 2, vid: 0, aud: 0 },
    "音视频生成音视频-VA2VA": { hint: "VA2VA 需要 1 个视频 + 1 段音频", img: 0, vid: 1, aud: 1 },
    "多参考生成音视频-REF2VA": { hint: "REF2VA 完整引用：图片 ≤9 / 视频 ≤3 / 音频 ≤3", img: 9, vid: 3, aud: 3 },
};

function renderAssetsPanel(c, s, mode) {
    const noop = () => {};
    const assets = s.assets;
    const imgList = assets.images, vidList = assets.videos, audList = assets.audios;
    const lim = MODE_ASSET_LIMITS[mode] || MODE_ASSET_LIMITS["多参考生成音视频-REF2VA"];
    const clamp = (n, max) => (max <= 0 ? 0 : Math.max(0, Math.min(max, n)));

    // 模式提示
    c.append(el("div", "background:#2b3a4a;border:1px solid #5b9bd5;border-radius:6px;padding:8px 12px;margin-bottom:8px;font-size:12px;color:#cfe3f7;", `当前模式：${mode || "未选择"} — ${lim.hint}`));

    const countBox = el("div", "border:1px solid var(--border-color,#3a3a3a);border-radius:6px;padding:6px 10px;margin-bottom:6px;display:flex;align-items:center;gap:20px;flex-wrap:wrap;");
    const imgSec = el("div", "max-height:220px;overflow-y:auto;");
    const vidSec = el("div", "max-height:140px;overflow-y:auto;");
    const audSec = el("div", "max-height:140px;overflow-y:auto;");

    const imgCount = makeCountRow("图片", "image", clamp(imgList.length, lim.img), (n) => { ensureCount(imgList, clamp(n, lim.img), "image"); renderSection(imgSec, "image", imgList, noop); });
    const vidCount = makeCountRow("视频", "video", clamp(vidList.length, lim.vid), (n) => { ensureCount(vidList, clamp(n, lim.vid), "video"); renderSection(vidSec, "video", vidList, noop); });
    const audCount = makeCountRow("音频", "audio", clamp(audList.length, lim.aud), (n) => { ensureCount(audList, clamp(n, lim.aud), "audio"); renderSection(audSec, "audio", audList, noop); });
    countBox.append(imgCount, vidCount, audCount);

    c.append(countBox);
    c.append(makeSectionTitle("🖼️ 图片"));
    c.append(imgSec);
    c.append(makeSectionTitle("🎬 视频"));
    c.append(vidSec);
    c.append(makeSectionTitle("🎧 音频"));
    c.append(audSec);

    renderSection(imgSec, "image", imgList, noop);
    renderSection(vidSec, "video", vidList, noop);
    renderSection(audSec, "audio", audList, noop);
}

function renderAutoSave(c, s) {
    c.append(field("自动保存", checkboxControl(s.auto_save !== false, "修改参数即时保存（无需点保存按钮）", v => { s.auto_save = v; })));
}

function renderPromptPanel(c, s) {
    const p = s.enhance;
    renderAutoSave(c, s);
    c.append(
        field("文本增强", checkboxControl(p.enabled === true, "开启后将提示词引入 LLM 增强（仅 fl2va 模式）", v => { p.enabled = v; })),
        field("LLM 模型选择", selectControl(OPTIONS.llmBackend, p.llm_backend || OPTIONS.llmBackend[0], v => { p.llm_backend = v; })),
    );
    c.append(makeSectionTitle("fl2va 提示词预设"));
    c.append(field("预设模式", selectControl(OPTIONS.presetModes, p.preset_mode || OPTIONS.presetModes[5], v => { p.preset_mode = v; })));
    c.append(field("视频时长 (秒)", numberControl(p.duration ?? 8, { min: 4, max: 15, step: 1 }, v => { p.duration = Math.round(v); })));
    c.append(field("视觉风格", selectControl(OPTIONS.style, p.visual_style || OPTIONS.style[0], v => { p.visual_style = v; })));
    c.append(field("音乐风格", selectControl(OPTIONS.music, p.music || OPTIONS.music[0], v => { p.music = v; })));
    c.append(field("画面比例", selectControl(OPTIONS.aspectShort, p.aspect || OPTIONS.aspectShort[0], v => { p.aspect = v; })));
    c.append(field("切镜次数", selectControl(OPTIONS.cuts, p.cuts || OPTIONS.cuts[0], v => { p.cuts = v; })));
    c.append(makeSectionTitle("指令推理"));
    c.append(field("自定义提示词", textControl(p.custom_prompt || "", "选填：自定义增强指令…", v => { p.custom_prompt = v; })));
    c.append(field("系统提示词", textControl(p.system_prompt || "", "选填…", v => { p.system_prompt = v; })));
    c.append(field("推理模式", selectControl(OPTIONS.inferenceModes, p.inference_mode || OPTIONS.inferenceModes[0], v => { p.inference_mode = v; })));
    c.append(field("最大帧数", numberControl(p.max_frames ?? 24, { min: 2, max: 1024, step: 1 }, v => { p.max_frames = Math.round(v); })));
    c.append(field("最大尺寸", numberControl(p.max_size ?? 256, { min: 128, max: 16384, step: 64 }, v => { p.max_size = Math.round(v); })));
    c.append(field("种子", numberControl(p.seed ?? 0, { min: 0, max: 0xffffffffffffffff, step: 1 }, v => { p.seed = Math.round(v); })));
}

function renderGenPanel(c, s) {
    const g = s.gen_params;
    renderAutoSave(c, s);
    const aspectMap = {
        "1:1 (Square)": [1, 1], "2:3 (Portrait Photo)": [2, 3], "3:2 (Photo)": [3, 2],
        "3:4 (Portrait Standard)": [3, 4], "4:5 (Portrait Tall)": [4, 5], "4:3 (Standard)": [4, 3],
        "5:4 (Landscape Tall)": [5, 4], "9:16 (Portrait Widescreen)": [9, 16],
        "16:9 (Widescreen)": [16, 9], "21:9 (Ultrawide)": [21, 9],
    };
    const calcWH = () => {
        const [wr, hr] = aspectMap[g.aspect_ratio] || [16, 9];
        const total = (g.megapixels ?? 1.0) * 1024 * 1024;
        const scale = Math.sqrt(total / (wr * hr));
        const m = g.multiple ?? 32;
        return [
            Math.max(32, Math.round((wr * scale) / m) * m),
            Math.max(32, Math.round((hr * scale) / m) * m),
        ];
    };
    let wInp, hInp;
    const applyWH = () => {
        const [w, h] = calcWH();
        g.width = w; g.height = h;
        if (wInp) wInp.value = w;
        if (hInp) hInp.value = h;
    };
    wInp = numberControl(g.width ?? 0, { min: 32, max: 8192, step: 32 }, v => { g.width = Math.round(v / 32) * 32; });
    hInp = numberControl(g.height ?? 0, { min: 32, max: 8192, step: 32 }, v => { g.height = Math.round(v / 32) * 32; });
    c.append(
        field("画幅比例", selectControl(OPTIONS.aspectRatio, g.aspect_ratio || OPTIONS.aspectRatio[8], v => { g.aspect_ratio = v; applyWH(); })),
        field("百万像素 MP", numberControl(g.megapixels ?? 1.0, { min: 0.1, max: 16, step: 0.1 }, v => { g.megapixels = v; applyWH(); })),
        field("对齐倍数", numberControl(g.multiple ?? 32, { min: 8, max: 128, step: 4 }, v => { g.multiple = Math.round(v / 4) * 4; applyWH(); })),
        field("时长 (秒)", numberControl(g.duration ?? 8, { min: 4, max: 15, step: 1 }, v => { g.duration = Math.round(v); })),
        field("宽度", wInp),
        field("高度", hInp),
        field("参考图放大系数", numberControl(g.scale_factor ?? 1.0, { min: 1, max: 5, step: 0.1 }, v => { g.scale_factor = v; })),
        field("二采放大倍数", numberControl(g.upscale_scale ?? 1.5, { min: 1.1, max: 4, step: 0.05 }, v => { g.upscale_scale = v; })),
    );
    if (!g.width || !g.height) applyWH();
}

function renderPrefPanel(c, s) {
    const p = s.sample_decode;
    renderAutoSave(c, s);
    c.append(makeSectionTitle("采样"));
    c.append(field("K采样器", selectControl(OPTIONS.samplers, p.sampler || OPTIONS.samplers[0], v => { p.sampler = v; })));
    c.append(field("基本调度器", selectControl(OPTIONS.schedulers, p.scheduler || OPTIONS.schedulers[0], v => { p.scheduler = v; })));
    c.append(field("步数", numberControl(p.steps ?? 25, { min: 1, max: 200, step: 1 }, v => { p.steps = Math.round(v); })));
    c.append(field("CFG", numberControl(p.cfg ?? 1.0, { min: 0, max: 30, step: 0.1 }, v => { p.cfg = v; })));
    c.append(field("shift_video", numberControl(p.shift_video ?? 12.0, { min: 0.01, max: 100, step: 0.01 }, v => { p.shift_video = v; })));
    c.append(field("shift_audio", numberControl(p.shift_audio ?? 3.0, { min: 0.01, max: 100, step: 0.01 }, v => { p.shift_audio = v; })));
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

    const overlay = el("div", "position:fixed;inset:0;background:rgba(0,0,0,0.7);backdrop-filter:blur(4px);z-index:9999;display:flex;align-items:center;justify-content:center;");
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
        case "models": renderModelsPanel(panelBox, d, settings); break;
        case "assets": renderAutoSave(panelBox, settings); renderAssetsPanel(panelBox, settings, d.mode); break;
        case "prompt": renderPromptPanel(panelBox, settings); break;
        case "gen_params": renderGenPanel(panelBox, settings); break;
        case "preference": renderPrefPanel(panelBox, settings); break;
        default: renderModelsPanel(panelBox, d, settings);
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
    const doSave = async (silent) => {
        try {
            await saveManager(settings);
            if (!silent) notify("配置已保存，重新执行节点生效");
            return true;
        } catch (e) {
            error.textContent = "保存失败：" + e.message;
            return false;
        }
    };
    saveBtn.addEventListener("click", async () => {
        saveBtn.disabled = true;
        saveBtn.textContent = "保存中…";
        const ok = await doSave(false);
        if (ok) close();
        else { saveBtn.disabled = false; saveBtn.textContent = "💾 保存"; }
    });

    // 自动保存：任何控件 change 后 800ms 防抖保存
    panelBox.addEventListener("change", () => {
        if (settings.auto_save !== false) {
            clearTimeout(autoSaveTimer);
            autoSaveTimer = setTimeout(() => doSave(true), 800);
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

            // 1. 隐藏后端原生 widget（mode / video_count / prompt_input），值保留，UI 由 DOM widget 承接
            const modeWidget = (self.widgets || []).find((w) => w.name === "mode");
            const vcWidget = (self.widgets || []).find((w) => w.name === "video_count");
            const piWidget = (self.widgets || []).find((w) => w.name === "prompt_input");
            for (const w of [modeWidget, vcWidget, piWidget]) {
                if (!w) continue;
                w.hidden = true;
                if (!w.options) w.options = {};
                w.options.hidden = true;
                // 关键：无条件强制布局高度为 0（原生 widget 没有 computeSize，必须无条件赋值）
                w.computeSize = () => [0, -4];
            }

            // 2. 单个 DOM widget：按钮区(3×2) + 生成模式 + 生成视频数量 + 提示词输入
            const container = document.createElement("div");
            container.style.cssText = "width:100%;display:flex;flex-direction:column;gap:8px;padding:8px;box-sizing:border-box;";

            // 按钮区
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
                    if (b.panel === "save") { notify("🚧 敬请期待", "info"); return; }
                    openModal(self, b.panel);
                });
                btnGrid.appendChild(btn);
            }
            container.appendChild(btnGrid);

            // 生成模式切换
            const modeRow = document.createElement("div");
            modeRow.style.cssText = "display:flex;align-items:center;gap:8px;";
            const modeLabel = document.createElement("span");
            modeLabel.textContent = "生成模式";
            modeLabel.style.cssText = "font-size:12px;color:#bbb;flex:0 0 auto;white-space:nowrap;";
            const modeSel = document.createElement("select");
            modeSel.style.cssText = "flex:1;min-width:0;height:26px;box-sizing:border-box;background:#2a2a2a;color:#ddd;border:1px solid #444;border-radius:4px;padding:2px 6px;font-size:12px;";
            for (const m of GEN_MODES) {
                const o = document.createElement("option");
                o.textContent = m;
                if (m === (modeWidget?.value ?? GEN_MODES[3])) o.selected = true;
                modeSel.appendChild(o);
            }
            modeSel.addEventListener("mousedown", (e) => e.stopPropagation());
            modeSel.addEventListener("change", () => {
                if (modeWidget?.callback) modeWidget.callback.call(modeWidget, modeSel.value);
            });
            modeRow.append(modeLabel, modeSel);
            container.appendChild(modeRow);

            // 生成视频数量（箭头样式）
            const countRow = document.createElement("div");
            countRow.style.cssText = "display:flex;align-items:center;gap:8px;";
            const countLabel = document.createElement("span");
            countLabel.textContent = "生成视频数量";
            countLabel.style.cssText = "font-size:12px;color:#bbb;flex:0 0 auto;white-space:nowrap;";
            const countDec = document.createElement("button");
            countDec.textContent = "◀";
            countDec.style.cssText = "width:26px;height:26px;background:#2a2a2a;color:#ddd;border:1px solid #555;border-radius:5px;font-size:12px;line-height:1;cursor:pointer;";
            const countInp = document.createElement("input");
            countInp.type = "number";
            countInp.min = "1";
            countInp.max = "12";
            countInp.value = vcWidget?.value ?? 6;
            countInp.style.cssText = "width:56px;height:26px;box-sizing:border-box;text-align:center;background:#2a2a2a;color:#ddd;border:1px solid #444;border-radius:4px;font-size:13px;";
            const countInc = document.createElement("button");
            countInc.textContent = "▶";
            countInc.style.cssText = "width:26px;height:26px;background:#2a2a2a;color:#ddd;border:1px solid #555;border-radius:5px;font-size:12px;line-height:1;cursor:pointer;";
            const applyCount = (n) => {
                n = Math.max(1, Math.min(12, Math.floor(n)));
                countInp.value = n;
                if (vcWidget?.callback) vcWidget.callback.call(vcWidget, n);
            };
            [countDec, countInp, countInc].forEach((x) => x.addEventListener("mousedown", (e) => e.stopPropagation()));
            countDec.addEventListener("click", () => applyCount((parseInt(countInp.value, 10) || 1) - 1));
            countInc.addEventListener("click", () => applyCount((parseInt(countInp.value, 10) || 1) + 1));
            countInp.addEventListener("change", () => applyCount(parseInt(countInp.value, 10) || 1));
            countRow.append(countLabel, countDec, countInp, countInc);
            container.appendChild(countRow);

            // 提示词输入栏
            const promptTextarea = document.createElement("textarea");
            promptTextarea.placeholder = "输入故事/剧本提示词，用 @ 引用素材…";
            promptTextarea.value = piWidget?.value ?? "";
            promptTextarea.style.cssText = "width:100%;height:120px;box-sizing:border-box;background:#2a2a2a;color:#ddd;border:1px solid #444;border-radius:4px;padding:6px 8px;font-size:12px;resize:none;overflow-y:auto;";
            promptTextarea.addEventListener("mousedown", (e) => e.stopPropagation());
            const syncPrompt = () => {
                const v = promptTextarea.value;
                if (piWidget?.callback) piWidget.callback.call(piWidget, v);
                else if (piWidget) piWidget.value = v;
            };
            promptTextarea.addEventListener("change", syncPrompt);
            promptTextarea.addEventListener("input", () => {
                syncPrompt();
                const val = promptTextarea.value;
                const cursor = promptTextarea.selectionStart;
                const before = val.slice(0, cursor);
                const m = before.match(/@([^@\s]*)$/);
                if (m) {
                    openMentionMenu(promptTextarea, cursor - m[0].length, m[1]);
                } else {
                    closeMentionMenu();
                }
            });
            promptTextarea.addEventListener("blur", () => {
                setTimeout(closeMentionMenu, 150);
            });
            container.appendChild(promptTextarea);

            // 缓存资产名（@ 引用用），失败静默
            loadManager().then((data) => cacheAssets(data.settings)).catch(() => {});

            // 3. addDOMWidget：不 unshift；固定高度（按钮66 + 模式26 + 数量26 + 提示词120 + padding16 + gap24 = 278）
            const widget = self.addDOMWidget?.("jzl_manager", "JZL_MANAGER", container, {
                serialize: false,
                hideOnZoom: false,
            });
            if (widget) {
                try { delete widget.computeSize; } catch { widget.computeSize = undefined; }
                widget.computeLayoutSize = () => ({ minHeight: 278, maxHeight: 278, minWidth: 0 });
            }

            // 4. 刷新节点尺寸（隐藏 widget 后需重算），并多次调用应对异步布局
            const refreshSize = () => {
                try {
                    const size = self.computeSize?.();
                    if (Array.isArray(size) && size.length >= 2 && Number.isFinite(size[1])) {
                        self.setSize?.([self.size?.[0] || size[0], size[1]]);
                    }
                } catch { /* ignore */ }
                self.setDirtyCanvas?.(true, true);
            };
            refreshSize();
            requestAnimationFrame(refreshSize);
            setTimeout(refreshSize, 50);
            return r;
        };
    },
});
