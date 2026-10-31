"""Tests for open source governance, legal disclaimers, and repository cleanliness."""

import json
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]


def test_governance_files_exist_and_non_empty():
    """Verify LICENSE, CHANGELOG.md, and CONTRIBUTING.md exist and are non-empty."""
    for filename in ("LICENSE", "CHANGELOG.md", "CONTRIBUTING.md"):
        path = Path(filename)
        assert path.exists(), f"Governance file '{filename}' must exist in repository root."
        content = path.read_text(encoding="utf-8").strip()
        assert len(content) > 0, f"Governance file '{filename}' must not be empty."


def test_license_contains_disclaimer():
    """Verify LICENSE contains MIT text and UN ECLAC / CEPAL non-affiliation disclaimer."""
    license_path = Path("LICENSE")
    assert license_path.exists(), "LICENSE file must exist."
    content = license_path.read_text(encoding="utf-8")
    assert "MIT License" in content
    assert "Patricio Camacho" in content
    normalized = " ".join(content.split())
    assert "NOT an official product of, sponsored by, or affiliated with" in normalized
    assert "United Nations" in normalized
    assert "ECLAC" in normalized or "CEPAL" in normalized


def test_readme_contains_disclaimer():
    """Verify README.md contains non-affiliation disclaimer banner."""
    readme_path = Path("README.md")
    assert readme_path.exists(), "README.md file must exist."
    content = readme_path.read_text(encoding="utf-8")
    assert (
        "no constituye una publicación oficial" in content
        or "NOT an official product" in content
        or "not an official product" in content
    )
    assert "CEPAL" in content or "ECLAC" in content


def test_statscepal_db_does_not_exist():
    """Verify statscepal.db orphan file does not exist in repository root."""
    orphan_db = Path("statscepal.db")
    assert not orphan_db.exists(), "statscepal.db must NOT exist in repository root."


def test_notebooks_do_not_import_legacy_statscepal():
    """Verify notebooks in notebooks/ do not contain 'from statscepal' or 'import statscepal'."""
    notebook_dir = Path("notebooks")
    assert notebook_dir.exists(), "notebooks/ directory must exist."
    ipynb_files = list(notebook_dir.glob("*.ipynb"))
    assert len(ipynb_files) > 0, "Expected at least one notebook in notebooks/."

    legacy_patterns = ["from statscepal", "import statscepal"]

    for ipynb in ipynb_files:
        with open(ipynb, "r", encoding="utf-8") as f:
            data = json.load(f)

        for cell_idx, cell in enumerate(data.get("cells", [])):
            if cell.get("cell_type") == "code":
                source = "".join(cell.get("source", []))
                for pattern in legacy_patterns:
                    assert (
                        pattern not in source
                    ), f"Notebook '{ipynb.name}' cell #{cell_idx} contains legacy import '{pattern}'."


def test_bmad_custom_config_no_personal_identity():
    """Verify tracked _bmad/custom/config.toml sets team defaults without personal user_name."""
    custom_cfg = Path("_bmad/custom/config.toml")
    assert custom_cfg.exists(), "_bmad/custom/config.toml must exist."
    data = tomllib.loads(custom_cfg.read_text(encoding="utf-8"))
    core = data.get("core", {})
    assert core.get("project_name") == "unofficial-cepalstat-mcp"
    assert core.get("communication_language") == "Spanish"
    assert "user_name" not in core, (
        "Personal user_name belongs in gitignored _bmad/custom/config.user.toml, "
        "not tracked _bmad/custom/config.toml."
    )
