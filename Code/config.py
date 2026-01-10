from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class AppConfig:
    deepseek_url: str = "https://api.deepseek.com"   # 你原 constants 里的值放这里
    openai_url: str = "https://api.openai.com/v1"
    balance_url: str = ""                            # 如果你确实有余额接口
    default_model: str = "deepseek-chat"
    default_temperature: float = 1.0

def load_api_key(key_file: Path) -> str:
    key = key_file.read_text(encoding="utf-8").strip()
    if not key:
        raise ValueError(f"Empty API key file: {key_file}")
    return key
