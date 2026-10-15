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
    assert "bitacora lookup" in skill_content or "Bitácora First" in skill_content, (
        "SKILL.md must specify 'bitacora lookup' or 'Bitácora First' in its query workflow"
    )
    assert "token" in skill_content.lower(), "SKILL.md must mention token optimization"
    assert "anti-sesgo" in skill_content.lower() or "anti-bias" in skill_content.lower(), (
        "SKILL.md must mention anti-bias or anti-sesgo"
    )
    assert "catalog search" in skill_content.lower() or "catalog" in skill_content.lower(), (
        "SKILL.md must mention catalog or catalog search for offline indicator discovery"
    )

    # Verify dimensions reference content
    dim_content = dimensions_file.read_text(encoding="utf-8")
    assert "dim_208" in dim_content
    assert "País__ESTANDAR" in dim_content
    assert "224" in dim_content  # Chile
    assert "dim_29117" in dim_content
    assert "Años__ESTANDAR" in dim_content
    assert "29190" in dim_content  # 2020


def test_subagent_structure():
    project_root = Path(__file__).resolve().parent.parent
    subagent_file = project_root / ".agents" / "subagents" / "cepalstat-analyst.md"
    assert subagent_file.exists(), f"Subagent file does not exist at {subagent_file}"
    content = subagent_file.read_text(encoding="utf-8")
    assert "statscepal catalog search" in content
    assert "statscepal catalog stats" in content
    assert "statscepal search" in content


def test_bmad_agent_econometrician_structure():
    import tomllib

    project_root = Path(__file__).resolve().parent.parent
    agent_dir = project_root / ".agents" / "skills" / "bmad-agent-econometrician"
    skill_file = agent_dir / "SKILL.md"
    customize_file = agent_dir / "customize.toml"

    assert skill_file.exists(), f"Skill file does not exist at {skill_file}"
    assert customize_file.exists(), f"customize.toml does not exist at {customize_file}"

    # Verify SKILL.md
    content = skill_file.read_text(encoding="utf-8")
    fm_match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", content, re.DOTALL)
    assert fm_match is not None, "SKILL.md must start with YAML frontmatter bounded by ---"

    frontmatter_raw = fm_match.group(1)
    name_match = re.search(r"^name:\s*([a-zA-Z0-9_-]+)\s*$", frontmatter_raw, re.MULTILINE)
    assert name_match is not None
    assert name_match.group(1) == "bmad-agent-econometrician"

    desc_match = re.search(r"^description:\s*(.+)$", frontmatter_raw, re.MULTILINE)
    assert desc_match is not None
    desc = desc_match.group(1).strip().strip("'\"")
    assert "ECLAC macro-structuralist econometrician" in desc
    assert "Use when the user asks to talk to Raul or requests the CEPAL econometrician" in desc

    # Persona & Activation Steps
    assert "📈" in content
    assert "resolve_customization.py" in content
    assert "resolve_config.py" in content
    assert "Adopt Persona" in content
    assert "Raúl" in content or "Raul" in content

    # Verify customize.toml
    config = tomllib.loads(customize_file.read_text(encoding="utf-8"))
    assert "agent" in config
    agent = config["agent"]
    assert agent["name"] == "Raul"
    assert agent["code"] == "bmad-agent-econometrician"
    assert agent["title"] == "ECLAC Econometrician"
    assert agent["icon"] == "📈"
    assert agent["module"] == "bmm"
    assert agent["team"] == "software-development"
    assert agent["role"] == "Macro-structuralist Econometrician"
    assert "Raúl Prebisch" in agent["identity"]
    assert "R²" in agent["communication_style"]
    assert len(agent.get("principles", [])) >= 3


def test_cepalstat_econometrics_skill_structure():
    project_root = Path(__file__).resolve().parent.parent
    skill_dir = project_root / ".agents" / "skills" / "cepalstat-econometrics"
    skill_file = skill_dir / "SKILL.md"

    assert skill_file.exists(), f"Skill file does not exist at {skill_file}"

    content = skill_file.read_text(encoding="utf-8")
    fm_match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", content, re.DOTALL)
    assert fm_match is not None, "SKILL.md must start with YAML frontmatter bounded by ---"

    frontmatter_raw = fm_match.group(1)
    name_match = re.search(r"^name:\s*([a-zA-Z0-9_-]+)\s*$", frontmatter_raw, re.MULTILINE)
    assert name_match is not None
    assert name_match.group(1) == "cepalstat-econometrics"

    desc_match = re.search(r"^description:\s*(.+)$", frontmatter_raw, re.MULTILINE)
    assert desc_match is not None
    desc = desc_match.group(1).strip().strip("'\"")
    assert desc.startswith("Use when")
    assert "statsmodels" in desc or "econometrics" in desc

    # Verify methodological content
    assert "EconometricEstimator" in content
    assert "fit_poverty_growth_model" in content
    assert "2929" in content  # Food inflation indicator
    assert "p-value" in content.lower() or "p_value" in content.lower()
    assert "r-squared" in content.lower() or "r²" in content.lower() or "r_squared" in content.lower()
    assert "elasticity" in content.lower() or "elasticidad" in content.lower()
    assert "statsmodels" in content.lower()

