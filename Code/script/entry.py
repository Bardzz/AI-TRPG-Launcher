import os
import sys
import traceback
from pathlib import Path

def runtime_root() -> Path:
    # 打包后 sys.executable = exe 路径
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # 源码运行：Code/script/entry.py -> 回到 AI_TRPG_Demo
    return Path(__file__).resolve().parents[2]

def main():
    root = runtime_root()
    os.chdir(root)  # 关键：保证 find_project_root(Path.cwd()) 找得到 Gameplay/Save/Log/key.txt

    try:
        from script.run_tk import main as run_main
        run_main()
    except Exception:
        # windowed 模式下看不到控制台，所以写日志
        err_path = root / "error.log"
        err_path.write_text(traceback.format_exc(), encoding="utf-8")
        raise

if __name__ == "__main__":
    main()
