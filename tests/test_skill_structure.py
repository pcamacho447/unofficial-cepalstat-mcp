from pathlib import Path
import re


def test_skill_structure_and_frontmatter():
    project_root = Path(__file__).resolve().parent.parent
    skill_dir = project_root / ".agents" / "skills" / "cepalstat-api"
    skill_file = skill_dir / "SKILL.md"
    dimensions_file = skill_dir / "references" / "dimensions-reference.md"

    # Verify files exist
    assert skill_file.exists(), f"Skill file does not exist at {skill_file}"
    assert dimensions_file.exists(), f"Dimensions reference file does not exist at {dimensions_file}"

    # Read SKILL.md
    skill_content = skill_file.read_text(encoding="utf-8")

    # Verify YAML frontmatter presence
    frontmatter_match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", skill_content, re.DOTALL)
    assert frontmatter_match is not None, "SKILL.md must start with YAML frontmatter bounded by ---"

    frontmatter_raw = frontmatter_match.group(1)
    assert len(frontmatter_raw) < 1024, "Frontmatter must be less than 1024 characters"

    # Extract name and description
    name_match = re.search(r"^name:\s*([a-zA-Z0-9_-]+)\s*$", frontmatter_raw, re.MULTILINE)
    assert name_match is not None, "Frontmatter must contain valid 'name' with letters, numbers, hyphens"
    assert name_match.group(1) == "cepalstat-api"

    desc_match = re.search(r"^description:\s*(.+)$", frontmatter_raw, re.MULTILINE)
    assert desc_match is not None, "Frontmatter must contain 'description'"
    desc = desc_match.group(1).strip().strip("'\"")
    assert desc.startswith("Use when"), "Description must start with 'Use when'"

    # Verify content references
    assert "dimensions-reference.md" in skill_content, "SKILL.md must reference dimensions-reference.md"
    assert "https://api-cepalstat.cepal.org" in skill_content, "SKILL.md must mention the base API URL"
    assert "statscepal" in skill_content, "SKILL.md must mention statscepal"
    assert "CepalStatClient" in skill_content, "SKILL.md must reference CepalStatClient"

    # Verify dimensions reference content
    dim_content = dimensions_file.read_text(encoding="utf-8")
    assert "dim_208" in dim_content
    assert "País__ESTANDAR" in dim_content
    assert "224" in dim_content  # Chile
    assert "dim_29117" in dim_content
    assert "Años__ESTANDAR" in dim_content
    assert "29190" in dim_content  # 2020
