"""Instruction routing and mirrored skill integrity, not cue quality."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_chapter_workflow_is_reachable_from_agent_entrypoints():
    target = "docs/chapter-cue-workflow.md"
    assert (ROOT / target).is_file()
    for relative in (
        "AGENTS.md", "CLAUDE.md",
        ".agents/skills/mnemorized-agent-delegation/SKILL.md",
        ".claude/skills/mnemorized-agent-delegation/SKILL.md",
    ):
        assert target in (ROOT / relative).read_text(encoding="utf-8")


def test_delegation_skill_mirrors_match():
    relative = "skills/mnemorized-agent-delegation/SKILL.md"
    assert (ROOT / ".agents" / relative).read_bytes() == (ROOT / ".claude" / relative).read_bytes()
