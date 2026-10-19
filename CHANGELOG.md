# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-19

### Added
- **4-Stage Semantic Resolution Engine**: High-speed, deterministic pipeline resolving natural language statistical queries to official CEPALSTAT indicators.
- **Cross-Country Dynamic Temporal Anchors**: Automatic resolution of adjacent observed years (`previous_anchor_year`, `next_anchor_year`) and survey gaps across Latin American household surveys with `forbid_interpolation: true`.
- **Multidimensional Facet Ontology**: Declarative mappings for demographic, economic, and geographic facets (`area`, `sexo`, `edad`, `quintil`, `etnia`).
- **Decoupling Analyzer**: Analytical engine measuring the decoupling between economic growth (GDP per capita) and social wellbeing (poverty, extreme poverty, real wages, food inflation).
- **Bitácora Anti-Bias System**: Verification and certification framework for empirical queries, auditing scale factors, units, and methodological notes.
- **Multi-Platform Cache Resolution**: Automatic cache management using `platformdirs`, supporting `UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH` and `STATSCEPAL_CACHE_PATH` environment overrides with local repository fallback.
- **Model Context Protocol (MCP) Server**: Native MCP integration with tools for semantic resolution, data extraction, and thematic catalog inspection.
- **Dual CLI Entrypoints**: Command-line interfaces `unofficial-cepalstat-mcp` and `cepalstat-mcp` with full backward compatibility.

### Fixed
- **Unconsumed Semantic Tokens Guard**: Stage 3.5 guard eliminating false substitutions by detecting unsupported specificities (e.g., sectors, inflation sub-components, informal exchange rates) and degrading confidence to `ALTERNATIVE_PROPOSED` or `ABSTAINED`.
- **Member ID Collision Resolution**: Disambiguation of shared dimension codes across heterogeneous statistical areas.
- **Dynamic Mapping Aliases**: Robust empirical table routing for complex multi-table distributions (e.g., deciles vs quintiles).

### Performance
- **Local Resolution Latency**: Sub-millisecond SQLite and in-memory index resolution ($p50 < 0.5\text{ ms}$).
- **Canonical Benchmark**: 100.0% Top-1 Accuracy across 200 benchmark questions.
- **Adversarial Benchmark**: 100.0% (40/40) passing with **0.00% False Substitution Rate (FSR)**.
