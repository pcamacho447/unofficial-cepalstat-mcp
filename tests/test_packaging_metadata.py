"""Tests for packaging metadata in pyproject.toml and CLI binary entrypoints."""

import sys
from pathlib import Path

import tomllib

from unofficial_cepalstat_mcp.cli import _resolve_prog, main


def test_pyproject_packaging_metadata():
    """Verify pyproject.toml contains complete PyPI packaging metadata."""
    pyproject_path = Path("pyproject.toml")
    assert pyproject_path.exists(), "pyproject.toml not found"

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    assert "project" in data, "Missing [project] section in pyproject.toml"
    project = data["project"]

    # Name and version
    assert project.get("name") == "unofficial-cepalstat-mcp"
    assert project.get("version") == "0.1.0"
    assert "description" in project and len(project["description"]) > 10
    assert project.get("requires-python") == ">=3.10"

    # License
    assert "license" in project, "Missing license in pyproject.toml"
    license_data = project["license"]
    if isinstance(license_data, dict):
        assert license_data.get("text") == "MIT"
    else:
        assert license_data == "MIT"

    # Authors
    assert "authors" in project, "Missing authors in pyproject.toml"
    assert any(a.get("name") == "Patricio Camacho" for a in project["authors"])

    # Keywords
    assert "keywords" in project, "Missing keywords in pyproject.toml"
    keywords = project["keywords"]
    expected_keywords = {
        "cepal",
        "cepalstat",
        "eclac",
        "mcp",
        "model-context-protocol",
        "latin-america",
        "economics",
        "statistics",
    }
    assert expected_keywords.issubset(set(keywords))

    # Classifiers
    assert "classifiers" in project, "Missing classifiers in pyproject.toml"
    classifiers = set(project["classifiers"])
    assert "License :: OSI Approved :: MIT License" in classifiers
    assert "Programming Language :: Python :: 3" in classifiers
    assert "Programming Language :: Python :: 3.10" in classifiers
    assert "Topic :: Scientific/Engineering :: Information Analysis" in classifiers

    # URLs
    assert "urls" in project, "Missing [project.urls] in pyproject.toml"
    urls = project["urls"]
    assert urls.get("Homepage") == "https://github.com/pcamacho447/unofficial-cepalstat-mcp"
    assert urls.get("Repository") == "https://github.com/pcamacho447/unofficial-cepalstat-mcp"
    assert urls.get("Issues") == "https://github.com/pcamacho447/unofficial-cepalstat-mcp/issues"

    # Console Scripts
    assert "scripts" in project, "Missing [project.scripts] in pyproject.toml"
    scripts = project["scripts"]
    assert scripts.get("unofficial-cepalstat-mcp") == "unofficial_cepalstat_mcp.cli:main"
    assert scripts.get("cepalstat-mcp") == "unofficial_cepalstat_mcp.cli:main"
    assert scripts.get("statscepal") == "unofficial_cepalstat_mcp.cli:main"

    # Dependencies
    dependencies = project.get("dependencies", [])
    assert any(dep.startswith("platformdirs") for dep in dependencies)


def test_cli_prog_resolution(monkeypatch):
    """Verify CLI dynamically resolves prog based on argv or defaults to unofficial-cepalstat-mcp."""
    # When no argv is set or empty
    monkeypatch.setattr(sys, "argv", [])
    assert _resolve_prog() == "unofficial-cepalstat-mcp"

    # When invoked via statscepal binary
    monkeypatch.setattr(sys, "argv", ["/usr/local/bin/statscepal", "search", "pobreza"])
    assert _resolve_prog() == "statscepal"

    # When invoked via statscepal.exe on Windows
    monkeypatch.setattr(sys, "argv", [r"C:\venv\Scripts\statscepal.exe", "--help"])
    assert _resolve_prog() == "statscepal"

    # When invoked via cepalstat-mcp binary
    monkeypatch.setattr(sys, "argv", ["/usr/bin/cepalstat-mcp"])
    assert _resolve_prog() == "cepalstat-mcp"

    # When invoked via unofficial-cepalstat-mcp binary
    monkeypatch.setattr(sys, "argv", [r"C:\Python310\Scripts\unofficial-cepalstat-mcp.exe"])
    assert _resolve_prog() == "unofficial-cepalstat-mcp"

    # When invoked via unrelated binary (e.g. pytest or python runner)
    monkeypatch.setattr(sys, "argv", ["pytest", "tests/test_cli.py"])
    assert _resolve_prog() == "unofficial-cepalstat-mcp"

    # Explicit override takes precedence
    assert _resolve_prog("custom-tool") == "custom-tool"


def test_cli_main_help_uses_resolved_prog(monkeypatch, capsys):
    """Verify main --help renders the appropriate prog in usage."""
    monkeypatch.setattr(sys, "argv", ["statscepal", "--help"])
    ret = main(["--help"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "usage: statscepal" in captured.out
