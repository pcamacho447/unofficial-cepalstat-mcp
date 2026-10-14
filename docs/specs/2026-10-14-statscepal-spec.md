# UN CEPALSTAT Open Data Python Client, Skill, and Agent Specification

## 1. Overview
This specification defines the architecture, design, and deliverables for integrating the United Nations Economic Commission for Latin America and the Caribbean (UN CEPAL / ECLAC) CEPALSTAT Open Data API into the `statscepal` workspace.

## 2. Goals
1. Provide a modern, typed, tested Python library (`statscepal`) for accessing CEPALSTAT open statistics.
2. Provide a command-line interface (CLI) to search indicators, view metadata, and download tabular data into CSV or standard output.
3. Provide an Antigravity custom skill (`cepalstat-api`) that enables AI agents to query Latin American and Caribbean socioeconomic data accurately.
4. Define a specialized AI subagent (`cepalstat_analyst`) tailored for empirical research on ECLAC statistics.

## 3. Architecture & Components
- **HTTP Layer (`client.py`)**: Handles GET requests to `https://api-cepalstat.cepal.org`, format negotiation (`json`, `csv`, etc.), and exception handling.
- **Thematic Navigation (`thematic_tree.py`)**: Downloads and caches the hierarchical tree of topics, areas, and indicator IDs. Provides fast keyword search.
- **Dimension Resolution (`dimensions.py`)**: Fetches dimension structures (countries, years, sex, breakdowns) and maps natural language values to member IDs.
- **Data Extractor (`extractor.py`)**: Fetches raw data records and decodes dimensional IDs into human-readable labels, returning Pandas DataFrames or JSON records.
- **CLI (`cli.py`)**: Console commands (`search`, `info`, `fetch`).
- **Antigravity Skill (`.agents/skills/cepalstat-api/SKILL.md`)**: Progressive disclosure skill with operational instructions and dimensional lookup reference.
- **Subagent (`cepalstat_analyst`)**: Autonomous research assistant.

## 4. Global Constraints
- Target Python: Python >= 3.10
- Base URL: `https://api-cepalstat.cepal.org`
- Authentication: Public Open Data (none required)
- Packaging: `uv` and `pyproject.toml`
- Testing: `pytest` with mocked unit tests (`respx`) and integration smoke test.
