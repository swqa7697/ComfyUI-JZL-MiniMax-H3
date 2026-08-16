import { app } from "../../scripts/app.js";

// ============================================================
// JZL_MiniMaxMusicLyricsEditor — 官方段落标签快捷插入
//   点击按钮 → 在当前光标处插入标签并另起一行
// ============================================================

const NODE_TYPE = "JZL_MiniMaxMusicLyricsEditor";
const TEXT_WIDGET = "lyrics_text";
const PICKER_ID = "jzl-lyrics-tag-picker";

const TAGS = [
    ["[前奏][Intro]", "[Intro]"],
    ["[主歌][Verse]", "[Verse]"],
    ["[主歌1][Verse 1]", "[Verse 1]"],
    ["[主歌2][Verse 2]", "[Verse 2]"],
    ["[主歌3][Verse 3]", "[Verse 3]"],
    ["[预副歌][Pre-Chorus]", "[Pre-Chorus]"],
    ["[副歌][Chorus]", "[Chorus]"],
    ["[副歌1][Chorus 1]", "[Chorus 1]"],
    ["[副歌2][Chorus 2]", "[Chorus 2]"],
    ["[后副歌][Post-Chorus]", "[Post-Chorus]"],
    ["[桥段][Bridge]", "[Bridge]"],
    ["[钩子][Hook]", "[Hook]"],
    ["[间奏][Instrumental]", "[Instrumental]"],
    ["[独奏][Solo]", "[Solo]"],
    ["[舞曲间奏桥][Instrumental dance bridge]", "[Instrumental dance bridge]"],
    ["[分解][Breakdown]", "[Breakdown]"],
    ["[分解转副歌][Breakdown to drums-Chorus]", "[Breakdown to drums-Chorus]"],
    ["[全员副歌][All in Chorus]", "[All in Chorusar Break]"],
    ["[分解][Breakdown]", "[Breakdown]"],
    ["[最终副歌][Final Chorus]", "[Final Chorus]"],
    ["[尾奏][Outro]", "[Outro]"],
];

function getLyricsWidget(node) {
    return (node.widgets || []).find(w => w.name === TEXT_WIDGET) || null;
}

function findTextarea(w) {
    const el = w.element || w.inputEl;
    if (!el) return null;
    if (el.tagName === "TEXTAREA") return el;
    if (typeof el.querySelector === "function") {
        return el.querySelector("textarea") || el.querySelector("input[type='text']") || null;
    }
    return null;
}

function bindCursorTracking(w) {
    const ta = findTextarea(w);
    if (!ta || ta.__jzlLyricsBound) return;
    ta.__jzlLyricsBound = true;
    const rec = () => {
        w._jzlSelStart = ta.selectionStart;
        w._jzlSelEnd = ta.selectionEnd;
    };
    for (const ev of ["focus", "click", "keyup", "mouseup"]) {
        ta.addEventListener(ev, rec);
    }
}

function insertTag(node, w, tag) {
    bindCursorTracking(w);
    const ta = findTextarea(w);
    const text = String(w.value ?? "");
    let start, end;

    if (typeof w._jzlSelStart === "number") {
        start = w._jzlSelStart;
        end = typeof w._jzlSelEnd === "number" ? w._jzlSelEnd : start;
    } else if (ta && document.activeElement === ta) {
        start = ta.selectionStart ?? text.length;
        end = ta.selectionEnd ?? start;
    } else {
        start = text.length;
        end = text.length;
    }
    if (!Number.isFinite(start) || start < 0) start = text.length;
    if (!Number.isFinite(end) || end < start) end = start;

    const prefix = start > 0 && text[start - 1] !== "\n" ? "\n" : "";
    const inserted = prefix + tag + "\n";
    const next = text.slice(0, start) + inserted + text.slice(end);
    const pos = start + inserted.length;

    w.value = next;
    if (ta) {
        ta.value = next;
        try { ta.focus(); ta.setSelectionRange(pos, pos); } catch (_) {}
        ta.dispatchEvent(new Event("input", { bubbles: true }));
    }
    if (w.callback) w.callback(next);

    w._jzlSelStart = pos;
    w._jzlSelEnd = pos;
    node.graph?.setDirtyCanvas?.(true, true);
}

function closeTagPicker() {
    document.getElementById(PICKER_ID)?.remove();
    if (pickerEscHandler) {
        window.removeEventListener("keydown", pickerEscHandler);
        pickerEscHandler = null;
    }
}

let pickerEscHandler = null;

function showTagPicker(node, w) {
    closeTagPicker();
    const overlay = document.createElement("div");
    overlay.id = PICKER_ID;
    overlay.style.cssText = "position:fixed;left:0;top:0;right:0;bottom:0;background:rgba(0,0,0,.45);z-index:99999;display:flex;align-items:center;justify-content:center;";
    overlay.addEventListener("mousedown", (e) => { if (e.target === overlay) closeTagPicker(); });

    const panel = document.createElement("div");
    panel.style.cssText = "background:#1b1b1f;border:1px solid #444;border-radius:10px;padding:14px;max-width:640px;width:92%;box-shadow:0 10px 40px rgba(0,0,0,.6);";

    const title = document.createElement("div");
    title.textContent = "添加段落标签（插入到当前光标处）";
    title.style.cssText = "color:#eee;font-size:14px;font-weight:600;margin-bottom:10px;";
    panel.appendChild(title);

    const grid = document.createElement("div");
    grid.style.cssText = "display:grid;grid-template-columns:repeat(3,1fr);gap:6px;";
    for (const [label, tag] of TAGS) {
        const b = document.createElement("button");
        b.textContent = label;
        b.style.cssText = "padding:7px 6px;border:1px solid #555;border-radius:6px;background:#2a2a2e;color:#eee;cursor:pointer;font-size:12px;line-height:1;";
        b.addEventListener("mouseenter", () => { b.style.background = "#3a3a40"; });
        b.addEventListener("mouseleave", () => { b.style.background = "#2a2a2e"; });
        b.addEventListener("click", () => { insertTag(node, w, tag); closeTagPicker(); });
        grid.appendChild(b);
    }
    panel.appendChild(grid);
    overlay.appendChild(panel);
    document.body.appendChild(overlay);

    pickerEscHandler = (e) => { if (e.key === "Escape") closeTagPicker(); };
    window.addEventListener("keydown", pickerEscHandler);
}

app.registerExtension({
    name: "JZL.MusicLyricsEditor",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData?.name !== NODE_TYPE) return;
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            const self = this;
            const w = getLyricsWidget(self);
            if (!w) return result;

            setTimeout(() => bindCursorTracking(w), 300);

            const btn = self.addWidget("button", "➕ 添加元素", "➕ 添加元素", () => {
                showTagPicker(self, w);
            }, { serialize: false });

            // 把「添加元素」按钮移到文本框上方
            const arr = self.widgets;
            const i = arr.indexOf(btn);
            if (i > -1) arr.splice(i, 1);
            const ti = arr.findIndex(x => x.name === TEXT_WIDGET);
            arr.splice(ti < 0 ? 0 : ti, 0, btn);
            self.setDirtyCanvas?.(true, true);

            return result;
        };
    },
});
