"""Tests for the 4 universal quantitative skills."""

from pathlib import Path
import pytest
import yaml

SKILLS_DIR = Path(".agents/skills")

EXPECTED_SKILLS = [
    "applied-econometrics",
    "applied-statistics",
    "applied-mathematics",
    "macroeconomic-analysis",
]


@pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
def test_skill_structure_and_frontmatter(skill_name: str):
    skill_file = SKILLS_DIR / skill_name / "SKILL.md"
    assert skill_file.exists(), f"Skill file {skill_file} does not exist"

    content = skill_file.read_text(encoding="utf-8")
    assert content.startswith("---"), f"Skill {skill_name} must start with YAML frontmatter"

    parts = content.split("---", 2)
    assert len(parts) >= 3, f"Skill {skill_name} missing closing frontmatter delimiter '---'"

    frontmatter = yaml.safe_load(parts[1])
    assert isinstance(frontmatter, dict), f"Frontmatter in {skill_name} is not a valid YAML mapping"

    # Name validation
    name = frontmatter.get("name")
    assert name == skill_name, f"Expected name {skill_name}, got {name}"

    # Description validation
    desc = frontmatter.get("description", "")
    assert isinstance(desc, str) and len(desc.strip()) > 0, f"Description in {skill_name} cannot be empty"
    assert desc.strip().startswith("Use when"), f"Description in {skill_name} must start with 'Use when...'"
    assert len(desc) < 500, f"Description in {skill_name} should be concise (< 500 chars)"

    # Body validations
    body = parts[2]
    assert len(body.strip()) > 200, f"Skill {skill_name} body is too brief"
    assert "## Overview" in body, f"Skill {skill_name} missing Overview section"
    assert "## When to Use" in body, f"Skill {skill_name} missing When to Use section"
    assert "```python" in body, f"Skill {skill_name} must include concrete Python examples"
