"""Tests for github-repo-search skill and github-scout subagent."""

from pathlib import Path

import yaml


def test_github_repo_search_skill_structure():
    project_root = Path(__file__).resolve().parent.parent
    skill_dir = project_root / ".agents" / "skills" / "github-repo-search"
    skill_file = skill_dir / "SKILL.md"

    assert skill_file.exists(), f"Skill file does not exist at {skill_file}"

    content = skill_file.read_text(encoding="utf-8")
    assert content.startswith("---"), "Skill must start with YAML frontmatter"

    parts = content.split("---", 2)
    assert len(parts) >= 3, "Missing closing frontmatter delimiter '---'"

    frontmatter = yaml.safe_load(parts[1])
    assert isinstance(frontmatter, dict), "Frontmatter is not a valid YAML mapping"

    # Name validation
    name = frontmatter.get("name")
    assert name == "github-repo-search", f"Expected name 'github-repo-search', got '{name}'"

    # Description validation
    desc = frontmatter.get("description", "")
    assert isinstance(desc, str) and len(desc.strip()) > 0, "Description cannot be empty"
    assert desc.strip().startswith("Use when"), "Description must start with 'Use when...'"
    assert len(desc) < 500, "Description should be concise (< 500 chars)"

    # Body validations
    body = parts[2]
    assert "## Overview" in body
    assert "## When to Use" in body
    assert "gh search repos" in body
    assert "gh search code" in body
    assert "gh repo view" in body
    assert "Health Score" in body or "Rubric" in body
    assert "```python" in body or "```bash" in body


def test_github_scout_subagent_spec():
    project_root = Path(__file__).resolve().parent.parent
    subagent_file = project_root / ".agents" / "subagents" / "github-scout.md"

    assert subagent_file.exists(), f"Subagent file does not exist at {subagent_file}"
    content = subagent_file.read_text(encoding="utf-8")

    assert "github_scout" in content or "github-scout" in content
    assert "gh search repos" in content
    assert "Health" in content or "Score" in content
    assert "License" in content or "licencia" in content.lower()
