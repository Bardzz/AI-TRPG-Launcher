from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from core.file_manager import FileManager
from core.general_tools import markdown_to_text
from core.json_tools import parse_json_object
from llm.llm_client import LLMClient
from paths import ProjectPaths


@dataclass
class AgentSession:
    rule_text: str
    background_text: str

class AgentManager:
    def __init__(self, paths: ProjectPaths, client: LLMClient, file_manager: FileManager):
        self.paths = paths
        self.client = client
        self.fm = file_manager

        self.history: list[dict] = []
        self.last_status = {
            "生理状态": "良好",
            "恐惧程度": "低",
            "NPC队友": "暂无",
            "背包物品": "暂无",
            "对怪物的认知": "暂无"
        }

    def init_session(self, session: AgentSession) -> None:
        self.history = [{"role": "system", "content": session.rule_text}]
        self.history.append({"role": "system", "content": session.background_text})

    def show_beginning(self) -> str:
        prompt_path = self.paths.function_dir / "BEGINNING_PROMPT.txt"
        prompt = self.fm.read_text(prompt_path) or ""
        prompt = markdown_to_text(prompt)
        self.history.append({"role": "user", "content": prompt})
        res = self.client.chat(self.history, temperature=1.0, stream=False)
        reply = res.choices[0].message.content or ""
        self.history.append({"role": "assistant", "content": markdown_to_text(reply)})
        return reply

    def talk(self, user_text: str, *, stream: bool=False, temperature: float=1.0):
        user_text = markdown_to_text(user_text)
        self.history.append({"role": "user", "content": user_text})
        return self.client.chat(self.history, temperature=temperature, stream=stream)

    def commit_assistant_reply(self, reply_text: str) -> None:
        self.history.append({"role": "assistant", "content": markdown_to_text(reply_text)})

    def update_status_json(self) -> dict:
        json_prompt = (
            '请你根据上一阶段的玩家信息以及这一阶段的剧情推进，'
            '严格按照以下JSON格式响应：'
            '{"生理状态":"良好","恐惧程度":"低","NPC队友":"暂无","背包物品":"暂无","对怪物的认知":"暂无"}'
            '注意回答要简短、表意明确。'
            f'上一阶段玩家信息：{self.last_status}。'
            f'当前剧情片段：{self.history[-4:]}'
        )
        msg = [{"role": "system", "content": json_prompt}]
        res = self.client.chat(
            msg,
            temperature=0.7,
            stream=False,
            response_format={"type": "json_object"}
        )
        raw = res.choices[0].message.content or "{}"
        data = parse_json_object(raw)
        self.last_status = data
        return data
