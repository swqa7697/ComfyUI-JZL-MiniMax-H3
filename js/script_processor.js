import { app } from "../../scripts/app.js";

// ============================================================
// JZL_MiniMax_ScriptProcessor — 高级参数折叠 UI
//   完全复刻 llama_pro.js（模型加载Pro）的 widget.type="hidden" 折叠模式
// ============================================================

const NODE_TYPE = "JZL_MiniMax_ScriptProcessor";

const ADVANCED_NAMES = new Set([
    "enable_scene", "enable_props", "enable_video", "enable_audio",
    "ref_image_intro", "ref_video_intro", "ref_audio_intro",
]);

// ── 工具 ──

function asBoolean(v) { return v === true || v === "true" || Number(v) === 1; }

function getWidget(node, name) { return node.widgets?.find(w => w.name === name); }

function setWidgetOption(w, key, val) {
    if (!w.options) w.options = {};
    w.options[key] = val;
}

// ── 测量单个 widget 高度 ──

function getWidgetRowHeight(node, widget) {
    if (!widget) return 26;
    if (widget.__jzlRowHeight > 0) return widget.__jzlRowHeight;
    const fn = widget.computeSize;
    try {
        const w = Math.max(80, Number(node?.size?.[0]) || 220);
        const sz = fn?.call(widget, w);
        const h = Number(sz?.[1]);
        if (h > 0) { widget.__jzlRowHeight = h; return h; }
    } catch (_) {}
    const h = Number(widget.computedHeight) > 0 ? Number(widget.computedHeight) : 26;
    widget.__jzlRowHeight = h;
    return h;
}

// ── 隐藏 / 显示 ──

function hideConditionalWidget(widget) {
    if (!widget) return false;
    if (widget.type === "hidden" && widget.hidden === true) return false;
    if (!Object.prototype.hasOwnProperty.call(widget, "__jzlOrigType")) {
        widget.__jzlOrigType = widget.type;
        widget.__jzlOrigComputeSize = widget.computeSize;
        widget.__jzlOrigHidden = widget.hidden;
        widget.__jzlOrigComputedHeight = widget.computedHeight;
        widget.__jzlOrigOptionsHidden = widget.options?.hidden;
        widget.__jzlOrigOptionsCanvasOnly = widget.options?.canvasOnly;
    }
    widget.hidden = true;
    if (widget.inputEl) widget.inputEl.style.display = "none";
    if (widget.element) widget.element.style.display = "none";
    widget.type = "hidden";
    widget.computeSize = () => [0, -4];
    widget.computedHeight = 0;
    setWidgetOption(widget, "hidden", true);
    setWidgetOption(widget, "canvasOnly", true);
    if (widget._state) {
        widget._state.hidden = true;
        widget._state.type = "hidden";
        widget._state.computedHeight = 0;
    }
    return true;
}

function showConditionalWidget(widget) {
    if (!widget) return false;
    if (widget.type !== "hidden") return false;
    if (!Object.prototype.hasOwnProperty.call(widget, "__jzlOrigType")) return false;

    widget.hidden = widget.__jzlOrigHidden ?? false;
    if (widget.inputEl) widget.inputEl.style.display = "";
    if (widget.element) widget.element.style.display = "";
    widget.type = widget.__jzlOrigType || "INT";
    if (widget.__jzlOrigComputeSize) widget.computeSize = widget.__jzlOrigComputeSize;
    else delete widget.computeSize;
    widget.computedHeight = widget.__jzlOrigComputedHeight;
    setWidgetOption(widget, "hidden", widget.__jzlOrigOptionsHidden ?? false);
    setWidgetOption(widget, "canvasOnly", widget.__jzlOrigOptionsCanvasOnly ?? false);
    if (widget._state) {
        widget._state.hidden = widget.hidden;
        widget._state.type = widget.type;
        if (widget.__jzlOrigComputedHeight !== undefined) widget._state.computedHeight = widget.__jzlOrigComputedHeight;
        else delete widget._state.computedHeight;
    }

    delete widget.__jzlOrigType;
    delete widget.__jzlOrigComputeSize;
    delete widget.__jzlOrigHidden;
    delete widget.__jzlOrigComputedHeight;
    delete widget.__jzlOrigOptionsHidden;
    delete widget.__jzlOrigOptionsCanvasOnly;
    return true;
}

// ── 调整节点高度 (像素偏移) ──

function adjustNodeHeight(node, delta) {
    if (!node?.size || !delta) return;
    const w = Number(node.size[0]) || 0;
    const h = Math.max(0, Number(node.size[1]) + delta);
    node.setSize?.([w, h]);
    if (Array.isArray(node.size)) { node.size[0] = w; node.size[1] = h; }
}

// ── 批量切换可见性 ──

function syncAdvancedWidgets(node, { adjustHeight = true } = {}) {
    const show = asBoolean(getWidget(node, "advanced_settings")?.value);
    let delta = 0;

    for (const w of node.widgets || []) {
        if (!ADVANCED_NAMES.has(w.name)) continue;
        const rowH = getWidgetRowHeight(node, w);
        if (show) {
            if (showConditionalWidget(w)) delta += rowH + 4;
        } else {
            if (hideConditionalWidget(w)) delta -= rowH + 4;
        }
    }

    if (adjustHeight && delta !== 0) {
        adjustNodeHeight(node, delta);
    }

    node._widgetSlotsDirty = true;
    node.setDirtyCanvas?.(true, true);
    node.graph?.setDirtyCanvas?.(true, true);
}

// ── 注册扩展 ──

app.registerExtension({
    name: "JZL.MiniMax.ScriptProcessor",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData?.name !== NODE_TYPE) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            const self = this;

            const wToggle = getWidget(self, "advanced_settings");
            if (!wToggle) return result;

            // 等 ComfyUI 设置好 node.size 后再做首次折叠 (adjustHeight=true)
            requestAnimationFrame(() => {
                syncAdvancedWidgets(self, { adjustHeight: true });
            });

            // 用户点击 toggle
            const origCb = wToggle.callback;
            wToggle.callback = function (v) {
                if (origCb) origCb.apply(this, arguments);
                syncAdvancedWidgets(self, { adjustHeight: true });
            };

            // 加载工作流: ComfyUI 的 configure 已恢复 node.size，只需同步可见性
            const onConfigure = self.onConfigure;
            self.onConfigure = function (info) {
                const resultCfg = onConfigure?.apply(this, arguments);
                requestAnimationFrame(() => {
                    syncAdvancedWidgets(self, { adjustHeight: false });
                });
                return resultCfg;
            };

            return result;
        };
    },
});
