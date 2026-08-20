/**
 * JZL MiniMax — 漫剧资产管理 modal
 * ============================================================
 * 点击「打开资产管理」弹窗：动态数量 + 每项(类型/名称/文件/开关)
 * 资产名 = 前缀(图片/视频/音频) + 序号 + 类型 + 名称，如「图片1角色孙悟空」
 */

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const NODE_TYPE = "JZL_MiniMaxAssetManager";
const ENDPOINT = "/jzl/assets";
const CHOOSE_ENDPOINT = "/jzl/choose_asset_file";

const ASSET_TYPES = ["角色", "场景", "道具", "分镜", "音效", "音乐", "其他"];
const KIND_LABEL = { image: "图片", video: "视频", audio: "音频" };

let settingsModal = null;

function notify(msg, type = "success") {
    try {
        if (app?.ui?.toast) { app.ui.toast.add({ text: msg, type }); return; }
    } catch (_) {}
    console.log(`[JZL Asset] ${msg}`);
}

async function loadSettings() {
    const resp = await api.fetchApi(ENDPOINT);
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok || !data?.ok) throw new Error(data?.error || `HTTP ${resp.status}`);
    return data.settings || { images: [], videos: [], audios: [] };
}

async function saveSettings(value) {
    const resp = await api.fetchApi(ENDPOINT, {
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

function resetToggle(node) {
    const widget = (node.widgets || []).find((w) => w.name === "open_manager");
    if (!widget) return;
    widget.value = false;
    if (widget._state) widget._state.value = false;
    node.setDirtyCanvas?.(true, true);
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
    const row = el("div", "display:flex;align-items:center;gap:10px;margin:8px 0;");
    row.append(el("span", "flex:0 0 88px;font-size:13px;color:var(--fg-color,#ddd);", labelText));
    const inp = el("input", "width:70px;background:var(--comfy-input-bg,#1d1d1d);color:var(--fg-color,#ddd);border:1px solid var(--border-color,#444);border-radius:4px;padding:5px 8px;font-size:13px;");
    inp.type = "number";
    inp.min = "0";
    inp.max = "64";
    inp.value = value;
    inp.addEventListener("change", () => onChange(Math.max(0, Math.min(64, parseInt(inp.value) || 0))));
    row.append(inp);
    row.append(el("span", "font-size:12px;color:var(--descrip-text,#999);", kind === "image" ? "图片" : kind === "video" ? "视频" : "音频"));
    return row;
}

function makeAssetRow(kind, index, item, onChanged) {
    const row = el("div", "display:flex;align-items:center;gap:6px;margin:4px 0;padding:4px 6px;background:var(--comfy-menu-bg,#232323);border:1px solid var(--border-color,#3a3a3a);border-radius:5px;");
    row.append(el("span", "flex:0 0 46px;font-size:12px;color:var(--descrip-text,#999);", `${KIND_LABEL[kind]}${index + 1}`));

    // 类型下拉
    const sel = el("select", "flex:0 0 64px;background:var(--comfy-input-bg,#1d1d1d);color:var(--fg-color,#ddd);border:1px solid var(--border-color,#444);border-radius:4px;padding:4px 2px;font-size:12px;");
    for (const t of ASSET_TYPES) {
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

    // 文件名显示（可编辑，也支持直接填绝对路径）
    const pathInp = el("input", "flex:2 1 160px;width:0;background:var(--comfy-input-bg,#1d1d1d);color:var(--fg-color,#aaa);border:1px solid var(--border-color,#444);border-radius:4px;padding:5px 6px;font-size:12px;");
    pathInp.type = "text";
    pathInp.placeholder = "文件路径";
    pathInp.value = item.path || "";
    pathInp.addEventListener("change", () => { item.path = pathInp.value.trim(); onChanged(); });

    const pickBtn = el("button", "flex:0 0 auto;background:var(--comfy-input-bg,#2a2a2a);color:var(--fg-color,#ddd);border:1px solid var(--border-color,#555);border-radius:4px;padding:5px 8px;font-size:12px;cursor:pointer;", "📁");
    pickBtn.title = "选择文件";
    pickBtn.addEventListener("click", async () => {
        const p = await chooseFile(kind);
        if (p) { item.path = p; pathInp.value = p; onChanged(); }
    });

    // 启用开关
    const chk = el("input", "flex:0 0 auto;width:16px;height:16px;cursor:pointer;");
    chk.type = "checkbox";
    chk.checked = item.enabled !== false;
    chk.title = "启用/禁用";
    chk.addEventListener("change", () => { item.enabled = chk.checked; onChanged(); });

    row.append(sel, nameInp, pathInp, pickBtn, chk);
    return row;
}

function renderSection(container, kind, list, onChanged) {
    container.innerHTML = "";
    for (let i = 0; i < list.length; i++) {
        container.append(makeAssetRow(kind, i, list[i], onChanged));
    }
}

function ensureCount(list, n) {
    while (list.length < n) list.push({ type: "角色", name: "", path: "", enabled: true });
    if (list.length > n) list.length = n;
}

function openModal(node) {
    if (settingsModal) { settingsModal.dialog?.querySelector?.("input,button,select")?.focus?.(); return; }

    const settings = {
        images: (settingsModal?.__data?.images || []).map(x => ({ ...x })),
        videos: (settingsModal?.__data?.videos || []).map(x => ({ ...x })),
        audios: (settingsModal?.__data?.audios || []).map(x => ({ ...x })),
    };

    loadSettings().then((loaded) => {
        settings.images = (loaded.images || []).map(x => ({ ...x }));
        settings.videos = (loaded.videos || []).map(x => ({ ...x }));
        settings.audios = (loaded.audios || []).map(x => ({ ...x }));
        buildModal(node, settings);
    }).catch((e) => {
        notify("读取资产配置失败：" + e.message, "error");
        buildModal(node, settings);
    });
}

function buildModal(node, settings) {
    const overlay = el("div", "position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;display:flex;align-items:center;justify-content:center;");
    const dialog = el("section", "background:var(--comfy-menu-bg,#202020);border:1px solid var(--border-color,#444);border-radius:10px;padding:16px;width:760px;max-height:86vh;overflow-y:auto;box-shadow:0 8px 32px rgba(0,0,0,0.5);");
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.setAttribute("aria-label", "漫剧资产管理");

    dialog.append(el("div", "font-size:16px;font-weight:700;color:var(--fg-color,#eee);margin-bottom:2px;", "🗂️ 漫剧资产管理"));
    dialog.append(el("div", "font-size:12px;color:var(--descrip-text,#999);margin-bottom:10px;", "资产名 = 图片/视频/音频 + 序号 + 类型 + 名称，如「图片1角色孙悟空」。启用开关关闭后不加载。"));

    const imgList = settings.images, vidList = settings.videos, audList = settings.audios;

    // 数量控制
    const countBox = el("div", "border:1px solid var(--border-color,#3a3a3a);border-radius:6px;padding:6px 10px;");
    const imgCount = makeCountRow("图片数量", "image", imgList.length, (n) => { ensureCount(imgList, n); renderSection(imgSec, "image", imgList, markDirty); });
    const vidCount = makeCountRow("视频数量", "video", vidList.length, (n) => { ensureCount(vidList, n); renderSection(vidSec, "video", vidList, markDirty); });
    const audCount = makeCountRow("音频数量", "audio", audList.length, (n) => { ensureCount(audList, n); renderSection(audSec, "audio", audList, markDirty); });
    countBox.append(imgCount, vidCount, audCount);
    dialog.append(countBox);

    // 图片区
    dialog.append(makeSectionTitle("🖼️ 图片"));
    const imgSec = el("div", "max-height:220px;overflow-y:auto;");
    dialog.append(imgSec);

    // 视频区
    dialog.append(makeSectionTitle("🎬 视频"));
    const vidSec = el("div", "max-height:140px;overflow-y:auto;");
    dialog.append(vidSec);

    // 音频区
    dialog.append(makeSectionTitle("🎧 音频"));
    const audSec = el("div", "max-height:140px;overflow-y:auto;");
    dialog.append(audSec);

    function markDirty() { /* 占位，实际保存时收集 */ }

    renderSection(imgSec, "image", imgList, markDirty);
    renderSection(vidSec, "video", vidList, markDirty);
    renderSection(audSec, "audio", audList, markDirty);

    // 底部按钮
    const error = el("div", "color:#e55;font-size:12px;margin-top:8px;min-height:16px;");
    const footer = el("div", "display:flex;justify-content:flex-end;gap:8px;margin-top:12px;");
    const cancelBtn = el("button", "background:var(--comfy-input-bg,#2a2a2a);color:var(--fg-color,#ddd);border:1px solid var(--border-color,#555);border-radius:5px;padding:7px 16px;font-size:13px;cursor:pointer;", "取消");
    const saveBtn = el("button", "background:#1a5fb4;color:#fff;border:none;border-radius:5px;padding:7px 20px;font-size:13px;font-weight:600;cursor:pointer;", "💾 保存");
    footer.append(cancelBtn, saveBtn);
    dialog.append(error, footer);

    overlay.append(dialog);
    document.body.append(overlay);

    const close = () => { overlay.remove(); settingsModal = null; };
    cancelBtn.addEventListener("click", close);
    overlay.addEventListener("mousedown", (e) => { if (e.target === overlay) close(); });

    saveBtn.addEventListener("click", async () => {
        saveBtn.disabled = true;
        saveBtn.textContent = "保存中…";
        try {
            const payload = { images: imgList, videos: vidList, audios: audList };
            await saveSettings(payload);
            notify("资产配置已保存，重新执行节点生效");
            // 触发节点重跑：改 open_manager 的开关状态刷新
            resetToggle(node);
            close();
        } catch (e) {
            error.textContent = "保存失败：" + e.message;
            saveBtn.disabled = false;
            saveBtn.textContent = "💾 保存";
        }
    });

    settingsModal = { dialog, close, __data: settings };
}

app.registerExtension({
    name: "JZL.MiniMaxAssetManager",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData?.name !== NODE_TYPE) return;
        const orig = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = orig?.apply(this, arguments);
            const self = this;
            const w = (self.widgets || []).find((x) => x.name === "open_manager");
            if (w) {
                const origCb = w.callback;
                w.callback = function (value) {
                    origCb?.apply?.(this, arguments);
                    if (value) openModal(self);
                    resetToggle(self);
                };
            }
            return r;
        };
    },
});
