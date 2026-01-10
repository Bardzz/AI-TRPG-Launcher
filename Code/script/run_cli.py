from pathlib import Path

from paths import find_project_root, ProjectPaths
from config import AppConfig, load_api_key
from core.file_manager import FileManager
from llm.llm_client import LLMClient
from llm.agent_manager import AgentManager, AgentSession


def main(rule="DET", story="THE_FIRSTMURDER"):
    root = find_project_root(Path.cwd())
    paths = ProjectPaths(root)
    cfg = AppConfig()
    api_key = load_api_key(paths.key_file)

    fm = FileManager()
    rule_text = fm.read_text(paths.rule_dir / f"{rule}_PROMPT.txt") or ""
    bg_text = fm.read_text(paths.story_dir / rule / f"{story}.txt") or ""

    agent = AgentManager(paths, LLMClient(api_key, cfg.deepseek_url, cfg.default_model), fm)
    agent.init_session(AgentSession(rule_text, bg_text))

    print(agent.show_beginning())
    while True:
        user = input("\n玩家> ").strip()
        if user in {"exit", "quit"}:
            break
        res = agent.talk(user, stream=False)
        reply = res.choices[0].message.content or ""
        agent.commit_assistant_reply(reply)
        print(f"\n主持人>\n{reply}")

if __name__ == "__main__":
    main()
