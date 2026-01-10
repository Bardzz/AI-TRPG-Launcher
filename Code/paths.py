from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

def find_project_root(start: Path) -> Path:
    """
    从 start 往上找，直到包含 Gameplay/Log/Save/key.txt 的目录。
    """
    for p in [start, *start.parents]:
        if (p / "Gameplay").exists() and (p / "Log").exists() and (p / "Save").exists() and (p / "key.txt").exists():
            return p
    raise FileNotFoundError(
        "Cannot locate project root. Expected folders Gameplay/Log/Save and key.txt."
    )

@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    @property
    def gameplay(self) -> Path: return self.root / "Gameplay"
    @property
    def rule_dir(self) -> Path: return self.gameplay / "Rule"
    @property
    def story_dir(self) -> Path: return self.gameplay / "Story"
    @property
    def function_dir(self) -> Path: return self.gameplay / "Function"

    @property
    def log_dir(self) -> Path: return self.root / "Log"
    @property
    def save_dir(self) -> Path: return self.root / "Save"
    @property
    def key_file(self) -> Path: return self.root / "key.txt"
