from __future__ import annotations

import json
import time
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import tkinter as tk
from tkinter import scrolledtext, filedialog

import markdown
from tkhtmlview import HTMLLabel

# 依赖你的新架构
from paths import ProjectPaths
from core.general_tools import markdown_to_text
from core.json_tools import parse_json_object



@dataclass
class UIFlags:
    read_aloud: bool = False
    auto_save: bool = True


class StreamDisplayApp:
    """
    Tk UI（Web-like 三栏布局）
    - 左：输入 + 主回复
    - 右上：历史（倒序）
    - 右下：状态（diff 高亮）
    """

    def __init__(self, tk_root: tk.Tk, agent, paths: ProjectPaths, voice=None):
        self.root = tk_root
        self.agent = agent
        self.paths = paths
        self.voice = voice

        self.flags = UIFlags(read_aloud=False, auto_save=True)

        self.streaming = False
        self.cancel_event = threading.Event()

        self.full_response_md = ""
        self.last_user_input = ""
        self.last_final_assistant_md = ""
        self.status: dict[str, Any] = {}

        # history filter
        self.history_filter_var = tk.StringVar(value="")

        # UI status bar
        self.status_var = tk.StringVar(value="准备就绪")

        self._build_window()
        self._build_layout()
        self._bind_shortcuts()

        self._init_window_content()

        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)

    # ---------------------------
    # Window / Layout
    # ---------------------------

    def _build_window(self):
        self.root.title("AI TRPG Manager")
        self.root.geometry("1100x700")

        # Grid: 2 columns main, row 0 content, row 1 controls, row 2 statusbar
        self.root.grid_columnconfigure(0, weight=2, uniform="col")
        self.root.grid_columnconfigure(1, weight=1, uniform="col")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)
        self.root.grid_rowconfigure(2, weight=0)

    def _build_layout(self):
        # Left (chat)
        self.left = tk.Frame(self.root)
        self.left.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.left.grid_rowconfigure(0, weight=0)  # input
        self.left.grid_rowconfigure(1, weight=1)  # reply
        self.left.grid_columnconfigure(0, weight=1)

        # Right (history + status)
        self.right = tk.Frame(self.root)
        self.right.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.right.grid_rowconfigure(0, weight=2)
        self.right.grid_rowconfigure(1, weight=1)
        self.right.grid_columnconfigure(0, weight=1)

        self._build_input_panel()
        self._build_reply_panel()
        self._build_history_panel()
        self._build_status_panel()
        self._build_controls()
        self._build_statusbar()

    def _build_input_panel(self):
        frame = tk.Frame(self.left)
        frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        frame.grid_columnconfigure(0, weight=1)

        tk.Label(frame, text="玩家输入：").grid(row=0, column=0, sticky="w")

        self.input_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=7)
        self.input_text.grid(row=1, column=0, sticky="nsew")
        # Enter to send, Shift+Enter newline
        self.input_text.bind("<Return>", self._on_enter)

        # helper line
        helper = "Enter 发送 | Shift+Enter 换行 | Ctrl+L 清空输入"
        tk.Label(frame, text=helper, fg="#666").grid(row=2, column=0, sticky="w", pady=(4, 0))

    def _build_reply_panel(self):
        frame = tk.Frame(self.left)
        frame.grid(row=1, column=0, sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        tk.Label(frame, text="主持人：").grid(row=0, column=0, sticky="w")
        self.reply_label = HTMLLabel(frame, html="", wrap=tk.WORD)
        self.reply_label.grid(row=1, column=0, sticky="nsew")

    def _build_history_panel(self):
        frame = tk.Frame(self.right)
        frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        header = tk.Frame(frame)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        tk.Label(header, text="历史记录：").grid(row=0, column=0, sticky="w")

        tk.Label(header, text="搜索").grid(row=0, column=1, sticky="e", padx=(0, 6))
        search = tk.Entry(header, textvariable=self.history_filter_var, width=18)
        search.grid(row=0, column=2, sticky="e")
        search.bind("<KeyRelease>", lambda e: self.safe_update_history())

        hint = tk.Label(frame, text="（倒序显示，输入关键字过滤）", fg="#666")
        hint.grid(row=1, column=0, sticky="w", pady=(4, 4))

        self.history_label = HTMLLabel(frame, html="", wrap=tk.WORD)
        self.history_label.grid(row=2, column=0, sticky="nsew")

    def _build_status_panel(self):
        frame = tk.Frame(self.right, bd=2, relief=tk.GROOVE)
        frame.grid(row=1, column=0, sticky="nsew")

        tk.Label(frame, text="玩家状态", font=("Arial", 16, "bold")).pack(pady=6)

        self.player_status_table = tk.Frame(frame)
        self.player_status_table.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        # 初始化默认状态
        self.status = {
            "生理状态": "良好",
            "恐惧程度": "低",
            "NPC队友": "暂无",
            "背包物品": "暂无",
            "对怪物的认知": "暂无",
        }
        self.update_player_status(self.status, old_status={})

    def _build_controls(self):
        bar = tk.Frame(self.root)
        bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 8))
        bar.grid_columnconfigure(0, weight=1)

        left = tk.Frame(bar)
        left.grid(row=0, column=0, sticky="w")

        right = tk.Frame(bar)
        right.grid(row=0, column=1, sticky="e")

        # left controls
        self.load_btn = tk.Button(left, text="读档", command=self.load_from_json, bg="#e6ffe6")
        self.load_btn.pack(side=tk.LEFT, padx=4)

        self.save_btn = tk.Button(left, text="存档", command=lambda: self.save_to_json(auto=False), bg="#e6f3ff")
        self.save_btn.pack(side=tk.LEFT, padx=4)

        self.export_btn = tk.Button(left, text="导出回放", command=self.export_replay_txt)
        self.export_btn.pack(side=tk.LEFT, padx=4)

        # toggles
        self.read_var = tk.BooleanVar(value=self.flags.read_aloud)
        self.auto_save_var = tk.BooleanVar(value=self.flags.auto_save)

        tk.Checkbutton(left, text="文本朗读", variable=self.read_var, command=self._on_toggle_read).pack(side=tk.LEFT, padx=10)
        tk.Checkbutton(left, text="自动存档", variable=self.auto_save_var, command=self._on_toggle_autosave).pack(side=tk.LEFT)

        # right controls
        self.stop_btn = tk.Button(right, text="停止", command=self.stop_stream, state=tk.DISABLED, bg="#ffe6e6")
        self.stop_btn.pack(side=tk.RIGHT, padx=4)

        self.retry_btn = tk.Button(right, text="重试", command=self.retry_last, state=tk.NORMAL, bg="#fff3cd")
        self.retry_btn.pack(side=tk.RIGHT, padx=4)

        self.send_btn = tk.Button(right, text="下一步", command=self.process_input, state=tk.NORMAL)
        self.send_btn.pack(side=tk.RIGHT, padx=4)

    def _build_statusbar(self):
        status_label = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_label.grid(row=2, column=0, columnspan=2, sticky="ew")

    def _bind_shortcuts(self):
        self.root.bind_all("<Control-l>", lambda e: self._clear_input())

    # ---------------------------
    # Init content
    # ---------------------------

    def _init_window_content(self):
        self.safe_update_status("初始化中...")

        # 初始输入提示
        self.input_text.insert(tk.END, "# 欢迎使用\n玩家在这里输入...")

        # 开场白：调用 agent.show_beginning()
        try:
            beginning = self._agent_show_beginning()
        except Exception as e:
            beginning = ""
            self.safe_set_error(f"初始化失败：{e}")

        initial_bottom = "# 这里是每轮主持人的回复\n" + (beginning or "")
        self.reply_label.set_html(self._wrap_html(markdown.markdown(initial_bottom)))

        self.safe_update_history()
        self.safe_update_status("准备就绪")

        # 可选朗读
        if self.read_var.get() and beginning:
            self._voice_speak(markdown_to_text(beginning))

    # ---------------------------
    # Agent compatibility layer
    # ---------------------------

    def _agent_show_beginning(self) -> str:
        # 新版：show_beginning；旧版：show_background
        if hasattr(self.agent, "show_beginning"):
            return self.agent.show_beginning()
        if hasattr(self.agent, "show_background"):
            return self.agent.show_background()
        return ""

    def _agent_stream_chat(self, user_text: str):
        # 新版：talk(user_text, stream=True)；旧版：talk_2_kp(prompt=..., stream_mode=True)
        if hasattr(self.agent, "talk"):
            return self.agent.talk(user_text, stream=True)
        if hasattr(self.agent, "talk_2_kp"):
            return self.agent.talk_2_kp(prompt=user_text, stream_mode=True)
        raise AttributeError("Agent does not support streaming chat")

    def _agent_commit_assistant(self, full_md: str):
        # 新版：commit_assistant_reply；旧版：UI 自己 append kp_history（你之前做法）
        if hasattr(self.agent, "commit_assistant_reply"):
            self.agent.commit_assistant_reply(full_md)
        else:
            # fallback: try kp_history/history
            hist = self._agent_get_history()
            if hist is not None:
                hist.append({"role": "assistant", "content": markdown_to_text(full_md)})

    def _agent_update_status(self) -> dict:
        # 新版：update_status_json；旧版：json_reply(last_status) 返回 json str
        if hasattr(self.agent, "update_status_json"):
            return self.agent.update_status_json()
        if hasattr(self.agent, "json_reply"):
            raw = self.agent.json_reply(self.status)
            return parse_json_object(raw)
        return self.status

    def _agent_get_history(self) -> Optional[list[dict]]:
        # 新版：history；旧版：kp_history
        if hasattr(self.agent, "history"):
            return self.agent.history
        if hasattr(self.agent, "kp_history"):
            return self.agent.kp_history
        return None

    # ---------------------------
    # Input / Streaming
    # ---------------------------

    def _on_enter(self, event):
        # Shift+Enter => newline
        if event.state & 0x1:
            return
        self.process_input()
        return "break"

    def process_input(self):
        if self.streaming:
            return

        user_text = self.input_text.get("1.0", tk.END).strip()
        if not user_text:
            return

        self.last_user_input = user_text
        self.full_response_md = ""
        self.cancel_event.clear()

        self.streaming = True
        self.send_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.safe_update_status("正在获取回复...")

        t = threading.Thread(target=self._fetch_stream_worker, args=(user_text,), daemon=True)
        t.start()

    def stop_stream(self):
        if not self.streaming:
            return
        self.cancel_event.set()
        self.safe_update_status("正在停止生成...")

    def retry_last(self):
        if self.streaming:
            return
        if not self.last_user_input:
            self.safe_update_status("没有可重试的上一轮输入")
            return

        # 可选：若最后一条是 assistant，则弹出，避免重复堆叠
        hist = self._agent_get_history()
        if hist and hist[-1].get("role") == "assistant":
            hist.pop()

        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", self.last_user_input)
        self.process_input()

    def _fetch_stream_worker(self, user_text: str):
        try:
            resp = self._agent_stream_chat(user_text)
            self.safe_update_status("正在接收回复...")

            for chunk in resp:
                if self.cancel_event.is_set():
                    break

                # OpenAI/DeepSeek stream chunk parsing
                content = ""
                try:
                    if hasattr(chunk, "choices") and chunk.choices and chunk.choices[0].delta:
                        content = chunk.choices[0].delta.content or ""
                except Exception:
                    content = ""

                if content:
                    self.full_response_md += content
                    self.root.after(0, self._render_reply_stream)

            self.root.after(0, self._finalize_stream)

        except Exception as e:
            self.root.after(0, lambda: self.safe_set_error(f"发生错误: {e}"))
        finally:
            self.streaming = False
            self.root.after(0, self._reset_buttons)

    def _render_reply_stream(self):
        # 渲染当前累计的 markdown
        html = markdown.markdown(self.full_response_md)
        self.reply_label.set_html(self._wrap_html(html))
        self.status_var.set(f"接收中... {len(self.full_response_md)} 字符")

    def _finalize_stream(self):
        if self.cancel_event.is_set():
            self.safe_update_status("已停止（本轮未提交）")
            return

        self.last_final_assistant_md = self.full_response_md

        # 1) commit assistant
        self._agent_commit_assistant(self.full_response_md)

        # 2) read aloud
        if self.read_var.get() and self.full_response_md:
            self._voice_speak(markdown_to_text(self.full_response_md))

        # 3) update history panel
        self.safe_update_history()

        # 4) update status (diff highlight)
        old_status = dict(self.status)
        try:
            new_status = self._agent_update_status()
            if not isinstance(new_status, dict):
                new_status = old_status
        except Exception as e:
            self.safe_update_status(f"状态更新失败：{e}")
            new_status = old_status

        self.status = new_status
        self.update_player_status(new_status, old_status=old_status)

        # 5) auto save
        if self.auto_save_var.get():
            self.save_to_json(auto=True)

        self.safe_update_status("回复接收完成")

    def _reset_buttons(self):
        self.send_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    # ---------------------------
    # History render
    # ---------------------------

    def safe_update_history(self):
        hist = self._agent_get_history() or []
        keyword = self.history_filter_var.get().strip()

        # 过滤：跳过最前面的系统/规则等（你原来从 3 开始）
        # 新版 history: [system(rule), system(bg), user(beginning), assistant(...), ...]
        # 旧版 kp_history: 结构可能不同
        start_idx = 0
        if len(hist) >= 3:
            start_idx = 2  # 保留规则/背景不显示，按你习惯可调整

        filtered = hist[start_idx:][::-1]

        parts = []
        for msg in filtered:
            role = msg.get("role", "unknown")
            role_cn = {"system": "系统", "user": "玩家", "assistant": "主持人", "tool": "工具"}.get(role, role)

            content = msg.get("content", "")
            content_txt = content
            try:
                # 旧版工具函数可能叫 markdown_to_text_simple；这里用新工具
                content_txt = markdown_to_text(str(content))
            except Exception:
                content_txt = str(content)

            if keyword and (keyword not in content_txt) and (keyword not in role_cn):
                continue

            parts.append("─" * 40)
            parts.append(f"{role_cn}：")
            parts.append(content_txt)

        html = "<br>".join([markdown.markdown(p) if p.startswith("#") else p.replace("\n", "<br>") for p in parts])
        self.history_label.set_html(self._wrap_html(html))

    # ---------------------------
    # Status render
    # ---------------------------

    def update_player_status(self, status_data: dict, *, old_status: dict):
        for w in self.player_status_table.winfo_children():
            w.destroy()

        for k, v in status_data.items():
            changed = old_status.get(k) != v
            self._add_status_row(k, v, changed)

    def _add_status_row(self, name: str, value: Any, changed: bool):
        row = tk.Frame(self.player_status_table)
        row.pack(fill=tk.X, pady=2)

        bg = "#fff2cc" if changed else None
        tk.Label(row, text=f"{name}:", anchor="w", font=("Arial", 9), bg=bg).pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(
            row,
            text=str(value),
            anchor="w",
            font=("Arial", 9),
            bg=bg,
            wraplength=280,
            justify="left"
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

    # ---------------------------
    # Persistence: Save / Load / Export
    # ---------------------------

    def save_to_json(self, *, auto: bool):
        hist = self._agent_get_history()
        if not hist:
            self.safe_update_status("无历史可存档")
            return

        self.paths.save_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        tag = "AUTO" if auto else "MANUAL"
        file_path = self.paths.save_dir / f"TRPG_SAVE_{tag}_{ts}.json"

        payload = {
            "history": hist,
            "status": self.status,
            "meta": {"timestamp": ts}
        }

        try:
            file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self.safe_update_status(f"存档成功：{file_path.name}")
        except Exception as e:
            self.safe_update_status(f"存档失败：{e}")

    def load_from_json(self):
        initial = str(self.paths.save_dir) if self.paths.save_dir.exists() else str(self.paths.root)
        fp = filedialog.askopenfilename(
            title="选择存档文件",
            initialdir=initial,
            filetypes=[("JSON存档", "*.json"), ("所有文件", "*.*")]
        )
        if not fp:
            self.safe_update_status("已取消读档")
            return

        try:
            data = json.loads(Path(fp).read_text(encoding="utf-8"))
            # 新格式：{history,status,meta}
            if isinstance(data, dict) and "history" in data:
                hist = data["history"]
                status = data.get("status", self.status)
            # 旧格式：直接是 list[dict]
            elif isinstance(data, list):
                hist = data
                status = self.status
            else:
                raise ValueError("存档格式不支持")

            # 写回 agent
            if hasattr(self.agent, "history"):
                self.agent.history = hist
            elif hasattr(self.agent, "kp_history"):
                self.agent.kp_history = hist

            old_status = dict(self.status)
            if isinstance(status, dict):
                self.status = status
                self.update_player_status(self.status, old_status=old_status)

            self.safe_update_history()
            self.safe_update_status(f"读档成功：{Path(fp).name}")

        except Exception as e:
            self.safe_set_error(f"读档失败：{e}")

    def export_replay_txt(self):
        hist = self._agent_get_history()
        if not hist:
            self.safe_update_status("无历史可导出")
            return

        self.paths.log_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        file_path = self.paths.log_dir / f"TRPG_REPLAY_{ts}.txt"

        try:
            with file_path.open("w", encoding="utf-8") as f:
                for msg in hist:
                    role = msg.get("role", "unknown")
                    role_cn = {"system": "系统", "user": "玩家", "assistant": "主持人", "tool": "工具"}.get(role, role)
                    content = msg.get("content", "")
                    f.write(f"【{role_cn}】\n{content}\n" + "-" * 40 + "\n\n")
            self.safe_update_status(f"回放已导出：{file_path.name}")
        except Exception as e:
            self.safe_update_status(f"导出失败：{e}")

    # ---------------------------
    # Voice
    # ---------------------------

    def _voice_speak(self, text: str):
        if not self.voice:
            return
        try:
            self.voice.speak(text, interrupt=True)
        except Exception:
            pass

    # ---------------------------
    # UI helpers
    # ---------------------------

    def _wrap_html(self, inner_html: str) -> str:
        return f"""
        <div style='
            font-family: Arial, sans-serif;
            font-size: 14px;
            line-height: 1.6;
            padding: 10px;
        '>{inner_html}</div>
        """

    def safe_update_status(self, message: str):
        self.root.after(0, lambda: self.status_var.set(message))

    def safe_set_error(self, error_msg: str):
        self.root.after(0, lambda: self.reply_label.set_html(
            self._wrap_html(f"<div style='color:red;'><b>错误：</b>{error_msg}</div>")
        ))

    def _on_toggle_read(self):
        self.flags.read_aloud = bool(self.read_var.get())

    def _on_toggle_autosave(self):
        self.flags.auto_save = bool(self.auto_save_var.get())

    def _clear_input(self):
        self.input_text.delete("1.0", tk.END)
        self.safe_update_status("已清空输入")

    # ---------------------------
    # Close
    # ---------------------------

    def on_window_close(self):
        try:
            # 自动导出回放（不弹窗）
            self.export_replay_txt()
        except Exception:
            pass

        try:
            if self.voice and hasattr(self.voice, "close"):
                self.voice.close()
        except Exception:
            pass

        self.root.destroy()
