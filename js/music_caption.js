import { app } from "../../scripts/app.js";

// ============================================================
// JZL_MiniMaxMusicCaption — 无人声时隐藏人声相关控件
//   复刻 llama_pro.js 的 widget.type="hidden" 折叠模式
// ============================================================

const NODE_TYPE = "JZL_MiniMaxMusicCaption";
const CONFIG = "人声配置";
const NO_VOCALS = "无人声 / Instrumental (No Vocals)";
const VOCAL_WIDGETS = ["声部音区", "人声音色", "人声唱法", "和声伴唱", "人声效果"];

function getWidget(node, name) {
    return (node.widgets || []).find(w => w.name === name) || null;
}

function rowHeight(node, w) {
    if (!w) return 0;
    if (w.__jzlMusicRowH > 0) return w.__jzlMusicRowH;
    const fn = w.computeSize;
    try {
        const width = Math.max(80, Number(node?.size?.[0]) || 220);
        const sz = fn?.call(w, width);
        const h = Number(sz?.[1]);
        if (h > 0) { w.__jzlMusicRowH = h; return h; }
    } catch (_) {}
    w.__jzlMusicRowH = 26;
    return 26;
}

function hideWidget(node, w) {
    if (!w || w.type === "hidden") return 0;
    const h = rowHeight(node, w);
    w.__jzlMusicOrigType = w.type;
    w.__jzlMusicOrigComputeSize = w.computeSize;
    w.hidden = true;
    if (w.inputEl) w.inputEl.style.display = "none";
    if (w.element) w.element.style.display = "none";
    w.type = "hidden";
    w.computeSize = () => [0, -4];
    w.computedHeight = 0;
    if (w._state) { w._state.hidden = true; w._state.type = "hidden"; w._state.computedHeight = 0; }
    return -h;
}

function showWidget(w) {
    if (!w || w.type !== "hidden" || !Object.prototype.hasOwnProperty.call(w, "__jzlMusicOrigType")) return 0;
    w.hidden = false;
    if (w.inputEl) w.inputEl.style.display = "";
    if (w.element) w.element.style.display = "";
    w.type = w.__jzlMusicOrigType;
    if (w.__jzlMusicOrigComputeSize) w.computeSize = w.__jzlMusicOrigComputeSize;
    else delete w.computeSize;
    delete w.computedHeight;
    const h = w.__jzlMusicRowH || 26;
    if (w._state) { w._state.hidden = false; w._state.type = w.type; delete w._state.computedHeight; }
    delete w.__jzlMusicOrigType;
    delete w.__jzlMusicOrigComputeSize;
    return h;
}

function adjustHeight(node, delta) {
    if (!delta || !node?.size) return;
    const w = Number(node.size[0]) || 0;
    const h = Math.max(0, Number(node.size[1]) + delta);
    node.setSize?.([w, h]);
}

function sync(node) {
    const cfg = getWidget(node, CONFIG);
    if (!cfg) return;
    const noVocals = cfg.value === NO_VOCALS;
    let delta = 0;
    for (const name of VOCAL_WIDGETS) {
        const w = getWidget(node, name);
        delta += noVocals ? hideWidget(node, w) : showWidget(w);
    }
    if (delta !== 0) adjustHeight(node, delta);
    node.setDirtyCanvas?.(true, true);
    node.graph?.setDirtyCanvas?.(true, true);
}

app.registerExtension({
    name: "JZL.MusicCaption",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData?.name !== NODE_TYPE) return;
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            const self = this;
            const cfg = getWidget(self, CONFIG);
            if (!cfg) return result;

            requestAnimationFrame(() => sync(self));

            const origCb = cfg.callback;
            cfg.callback = function (v) {
                if (origCb) origCb.apply(this, arguments);
                sync(self);
            };

            const onConfigure = self.onConfigure;
            self.onConfigure = function (info) {
                const r = onConfigure?.apply(this, arguments);
                requestAnimationFrame(() => sync(self));
                return r;
            };

            return result;
        };
    },
});
