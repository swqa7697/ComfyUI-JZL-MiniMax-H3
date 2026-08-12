# ComfyUI-JZL-MiniMax-H3

MiniMax H3 视频生成节点（基于 ComfyUI V3 `io.Schema` 机制）。

## 当前节点

| 节点 | node_id | 说明 |
|------|---------|------|
| 🎬 MiniMax H3 参考编码 | `JZL_MiniMaxH3ReferenceToVideo` | ref2va 参考条件编码，100% 复刻官方 `MiniMaxH3ReferenceToVideo` |

## 特性

- **V3 原生动态接口**：参考图 / 参考视频 / 视频音轨 / 独立音频 四组端口用 `io.Autogrow` 实现「连接后自动长出下一个空槽」，与官方一致。
- **参考值放大**（JZL 扩展）：仅 `match` 模式生效，`ref_scale` 范围 `1.0~5.0`，步长 `0.1`。最终像素面积 = 生成画布面积 × 倍率（面积倍率，非分辨率倍率）。`1.0` = 官方行为。

## 提示词标签

| 标签 | 含义 |
|------|------|
| `<Picture i>` | 第 i 张参考图 |
| `<Video k>` | 第 k 段参考视频 |
| `<Audio j>` | 第 j 条参考音频（视频音轨会在其 `<Video>` 前单独成标签） |

## 安装

把本目录放入 ComfyUI 的 `custom_nodes/` 下，或建立符号链接：

```powershell
New-Item -ItemType Junction -Path "D:\...\ComfyUI\custom_nodes\ComfyUI-JZL-MiniMax-H3" -Target "D:\AI_JZL\ComfyUI-JZL-MiniMax-H3"
```

## 依赖

- ComfyUI（含 `comfy_api.latest`，即官方 MiniMax H3 节点可用的较新版本）
- `torch`、`torchaudio`
