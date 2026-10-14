"""Tests to validate syntax, structure, and required content of Jupyter Notebooks."""

import json
from pathlib import Path
import pytest


def test_notebook_structure_and_syntax():
    """Verify that 01_desacople_crecimiento_bienestar.ipynb exists and complies with Jupyter nbformat v4."""
    nb_path = Path("notebooks/01_desacople_crecimiento_bienestar.ipynb")
    assert nb_path.exists(), f"Notebook file {nb_path} must exist"

    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # Basic structure validation
    assert "cells" in nb, "Notebook JSON must contain 'cells'"
    assert "metadata" in nb, "Notebook JSON must contain 'metadata'"
    assert nb.get("nbformat") == 4, "Notebook format must be nbformat 4"
    assert nb["metadata"]["language_info"]["name"] == "python", "Language info name must be 'python'"

    cells = nb["cells"]
    assert len(cells) >= 5, f"Expected at least 5 cells, got {len(cells)}"

    # Check cell structure
    cell_types = set()
    full_text = ""
    for idx, cell in enumerate(cells):
        assert "cell_type" in cell, f"Cell #{idx} missing 'cell_type'"
        assert "source" in cell, f"Cell #{idx} missing 'source'"
        cell_types.add(cell["cell_type"])

        # Source can be str or list of str in ipynb format
        if isinstance(cell["source"], list):
            full_text += "\n" + "".join(cell["source"])
        else:
            full_text += "\n" + cell["source"]

    assert "markdown" in cell_types, "Notebook should contain markdown cells"
    assert "code" in cell_types, "Notebook should contain code cells"

    # Verify that all code cells contain syntactically valid Python
    import ast
    for idx, cell in enumerate(cells):
        if cell["cell_type"] == "code":
            code_src = "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
            try:
                ast.parse(code_src)
            except SyntaxError as e:
                pytest.fail(f"Syntax error in notebook code cell #{idx}: {e}")

    # Validate presence of the 5 sections & key concepts
    required_keywords = [
        "DecouplingAnalyzer",
        "Crecimiento Virtuoso",
        "Crecimiento Excluyente",
        "Resiliencia Social",
        "Doble Vulnerabilidad",
        "Argentina",
        "Chile",
        "Colombia",
        "México",
        "Perú",
        "Uruguay",
        "2015-2019",
        "2021-2023",
        "Salario Mínimo Real",
    ]

    for kw in required_keywords:
        assert kw in full_text, f"Notebook missing required keyword or concept: '{kw}'"
