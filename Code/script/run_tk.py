print(">>> run_tk.py started")
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from paths import find_project_root, ProjectPaths
from core.file_manager import FileManager
from config import AppConfig, load_api_key
from llm.llm_client import LLMClient
from llm.agent_manager import AgentManager, AgentSession
from audio.voice_manager import VoiceManager
from ui.tk_app import StreamDisplayApp


def list_rules(paths: ProjectPaths) -> list[str]:
    """
    从 Gameplay/Rule 下枚举规则文件：XXX_PROMPT.txt -> 规则名 XXX
    """
    rule_dir = paths.rule_dir
    if not rule_dir.exists():
        return []
    rules = []
    for p in sorted(rule_dir.glob("*_PROMPT.txt")):
        name = p.stem.replace("_PROMPT", "")
        rules.append(name)
    return rules


def list_stories(paths: ProjectPaths, rule_name: str) -> list[str]:
    """
    从 Gameplay/Story/<RULE>/ 下枚举所有 .txt 剧本文件，返回 stem（不带扩展名）
    """
    story_dir = paths.story_dir / rule_name
    if not story_dir.exists():
        return []
    return [p.stem for p in sorted(story_dir.glob("*.txt"))]


def load_rule_story(paths: ProjectPaths, rule_name: str, story_name: str) -> AgentSession:
    """
    读取规则 prompt + 剧本 txt，封装成 AgentSession
    """
    fm = FileManager()
    rule_path = paths.rule_dir / f"{rule_name}_PROMPT.txt"

    # story_name 允许传 stem 或带 .txt
    if story_name.lower().endswith(".txt"):
        story_file = story_name
    else:
        story_file = f"{story_name}.txt"
    story_path = paths.story_dir / rule_name / story_file

    rule = fm.read_text(rule_path) or ""
    background = fm.read_text(story_path) or ""

    if not rule.strip():
        raise FileNotFoundError(f"规则文件为空或不存在：{rule_path}")
    if not background.strip():
        raise FileNotFoundError(f"剧本文件为空或不存在：{story_path}")

    return AgentSession(rule_text=rule, background_text=background)


class NewGameDialog(tk.Toplevel):
    """
    启动时的“新游戏配置”对话框：选择 Rule + Story
    """
    def __init__(self, master: tk.Tk, paths: ProjectPaths):
        super().__init__(master)
        self.title("新游戏配置")
        self.resizable(False, False)
        self.paths = paths
        self.result = None  # (rule_name, story_name) 或 None

        # 让它成为模态窗口
        self.transient(master)
        self.grab_set()

        # UI
        frm = ttk.Frame(self, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frm, text="选择规则（Rule）：").grid(row=0, column=0, sticky="w")
        self.rule_var = tk.StringVar()
        self.rule_cb = ttk.Combobox(frm, textvariable=self.rule_var, state="readonly", width=40)
        self.rule_cb.grid(row=1, column=0, sticky="ew", pady=(4, 10))

        ttk.Label(frm, text="选择剧本（Story）：").grid(row=2, column=0, sticky="w")
        self.story_var = tk.StringVar()
        self.story_cb = ttk.Combobox(frm, textvariable=self.story_var, state="readonly", width=40)
        self.story_cb.grid(row=3, column=0, sticky="ew", pady=(4, 10))

        btn_row = ttk.Frame(frm)
        btn_row.grid(row=4, column=0, sticky="e", pady=(6, 0))

        self.ok_btn = ttk.Button(btn_row, text="开始游戏", command=self._on_ok)
        self.ok_btn.grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btn_row, text="取消", command=self._on_cancel).grid(row=0, column=1)

        # 数据加载
        rules = list_rules(paths)
        if not rules:
            messagebox.showerror("错误", f"未找到规则文件：{paths.rule_dir}\\*_PROMPT.txt")
            self.destroy()
            return

        self.rule_cb["values"] = rules
        self.rule_cb.bind("<<ComboboxSelected>>", self._on_rule_change)

        # 默认选第一个规则
        self.rule_var.set(rules[0])
        self._reload_stories(rules[0])

        # 默认选第一个剧本
        if self.story_cb["values"]:
            self.story_var.set(self.story_cb["values"][0])

        # 回车确认、Esc 取消
        self.bind("<Return>", lambda e: self._on_ok())
        self.bind("<Escape>", lambda e: self._on_cancel())

        # 居中
        self.update_idletasks()
        self._center_over_master(master)

    def _center_over_master(self, master: tk.Tk):
        mx = master.winfo_rootx()
        my = master.winfo_rooty()
        mw = master.winfo_width() or 800
        mh = master.winfo_height() or 600
        w = self.winfo_width()
        h = self.winfo_height()
        x = mx + (mw - w) // 2
        y = my + (mh - h) // 2
        self.geometry(f"+{x}+{y}")

    def _on_rule_change(self, _event=None):
        rule = self.rule_var.get().strip()
        self._reload_stories(rule)

    def _reload_stories(self, rule_name: str):
        stories = list_stories(self.paths, rule_name)
        self.story_cb["values"] = stories
        if stories:
            self.story_var.set(stories[0])
            self.ok_btn["state"] = "normal"
        else:
            self.story_var.set("")
            self.ok_btn["state"] = "disabled"
            messagebox.showwarning("提示", f"未找到该规则的剧本：{self.paths.story_dir / rule_name}")

    def _on_ok(self):
        rule = self.rule_var.get().strip()
        story = self.story_var.get().strip()
        if not rule or not story:
            messagebox.showwarning("提示", "请选择规则与剧本。")
            return
        self.result = (rule, story)
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()


def choose_session(root: tk.Tk, paths: ProjectPaths) -> tuple[str, str] | None:
    dlg = NewGameDialog(root, paths)
    root.wait_window(dlg)
    return dlg.result


def main():
    print(">>> main() entered")

    project_root = find_project_root(Path.cwd())
    paths = ProjectPaths(project_root)

    cfg = AppConfig()
    api_key = load_api_key(paths.key_file)
    print(">>> creating Tk root")

    # 先创建 root，用于弹“新游戏配置”窗口
    root = tk.Tk()
    print(">>> Tk root created")

    root.title("AI TRPG - Launcher")
    root.geometry("420x220")
    root.update_idletasks()  # 确保 Tk 初始化完成

    sel = choose_session(root, paths)
    if sel is None:
        root.destroy()
        return


    rule_name, story_name = sel

    # 初始化 Agent
    client = LLMClient(api_key=api_key, base_url=cfg.deepseek_url, model=cfg.default_model)
    fm = FileManager()
    agent = AgentManager(paths=paths, client=client, file_manager=fm)

    session = load_rule_story(paths, rule_name=rule_name, story_name=story_name)
    agent.init_session(session)

    voice = VoiceManager(rate=200)

    # 进入主 UI
    root.deiconify()
    app = StreamDisplayApp(root, agent=agent, paths=paths, voice=voice)
    root.protocol("WM_DELETE_WINDOW", lambda: (voice.close(), root.destroy()))
    print(">>> entering mainloop")

    root.mainloop()


if __name__ == "__main__":
    main()
