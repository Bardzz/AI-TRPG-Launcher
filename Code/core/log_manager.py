from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

@dataclass(order=True)
class LogData:
    start_time: str
    time: str
    owner: str
    content: str

class LogManager:
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.game_log: list[LogData] = []
        self.story_log: list[LogData] = []
        self.total_log: list[LogData] = []

    def update(self, content: str, owner: str="system", mode: str="total") -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        item = LogData(self.start_time, now, owner, content)

        if mode == "game":
            self.game_log.append(item); self.total_log.append(item)
        elif mode == "story":
            self.story_log.append(item); self.total_log.append(item)
        elif mode == "total":
            self.total_log.append(item)
        else:
            raise ValueError("mode must be one of: total/game/story")

    def dump(self) -> None:
        def write(path: Path, data: list[LogData]):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                for x in data:
                    f.write(f"[{x.start_time}] >> [{x.owner}]: {x.content}\n")

        write(self.log_dir / "game_log.txt", self.game_log)
        write(self.log_dir / "story_log.txt", self.story_log)
        write(self.log_dir / "total_log.txt", self.total_log)
