from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

@dataclass
class FileManager:
    encoding: str = "utf-8"

    def read_text(self, path: Path, *, verbose: bool=False) -> Optional[str]:
        try:
            text = path.read_text(encoding=self.encoding)
            if verbose:
                print(f"Read: {path}")
            return text
        except FileNotFoundError:
            if verbose:
                print(f"File not found: {path}")
            return None

    def iter_txt(self, folder: Path, *, recursive: bool=False) -> Iterable[Path]:
        if recursive:
            yield from sorted(folder.rglob("*.txt"))
        else:
            yield from sorted(folder.glob("*.txt"))
