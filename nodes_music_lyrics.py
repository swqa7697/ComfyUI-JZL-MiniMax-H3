"""JZL MiniMax Music3 — 歌词编辑节点（V1 经典 API）

纯文本编辑 + 官方段落标签快捷插入。插入逻辑在 js/music_lyrics_editor.js。
输出 STRING，可直接接到官方「MiniMax Music3 Text Encode」的 lyrics 输入。
"""


class JZL_MiniMaxMusicLyricsEditor:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "lyrics_text": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "歌词文本。点击下方按钮可在光标处插入官方段落标签：[Intro]/[Verse]/[Pre-Chorus]/[Chorus]/[Post-Chorus]/[Bridge]/[Instrumental]/[Solo]/[Outro] 等",
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("lyrics",)
    FUNCTION = "build"
    CATEGORY = "JZL/MiniMax"

    def build(self, lyrics_text):
        return (lyrics_text,)
