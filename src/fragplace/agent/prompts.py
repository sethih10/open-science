"""Load an agent's prompt from agents/<name>.md, the single copy Claude Code also reads."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def prompt(name: str) -> str:
    text = (ROOT / "agents" / f"{name}.md").read_text()
    return text.split("---", 2)[2].strip() if text.startswith("---") else text
