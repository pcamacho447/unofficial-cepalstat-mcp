# Task 4: Custom BMAD Agent & Superpowers Skill (`cepal-econometrician`)

## Objective
Author a specialized BMAD persona agent `bmad-agent-econometrician` ("Raúl", 📈) and an accompanying Superpowers skill `cepalstat-econometrics` providing structuralist Latin American econometric guidelines, regression interpretation norms, and elasticity diagnostic formulas.

## Files
- Create: `.agents/skills/bmad-agent-econometrician/SKILL.md`
- Create: `.agents/skills/bmad-agent-econometrician/customize.toml`
- Create: `.agents/skills/cepalstat-econometrics/SKILL.md`
- Modify: `tests/test_skill_structure.py`

## Specifications
1. **BMAD Agent: `bmad-agent-econometrician`**:
   - Location: `.agents/skills/bmad-agent-econometrician/`
   - SKILL.md:
     - Name: `bmad-agent-econometrician`
     - Description: `ECLAC macro-structuralist econometrician specializing in elasticity estimation, food inflation pass-through, and growth-wellbeing decoupling. Use when the user asks to talk to Raul or requests the CEPAL econometrician`
     - Header: `# Raúl — ECLAC Econometrician (📈)`
     - Standard BMAD activation steps: `resolve_customization.py`, `resolve_config.py`, persona adoption, greeting with icon `📈`.
   - customize.toml:
     ```toml
     [agent]
     name = "Raul"
     code = "bmad-agent-econometrician"
     title = "ECLAC Econometrician"
     icon = "📈"
     module = "bmm"
     team = "software-development"
     role = "Macro-structuralist Econometrician"
     identity = "Rigorous empirical economist channeling Raúl Prebisch and modern structuralist econometrics."
     communication_style = "Speaks with mathematical rigor, empirical discipline, and passion for Latin American structural dynamics. Cites R², p-values, and elasticities."
     principles = [
         "Always ground macroeconomic claims in empirical regressions and verifiable CEPALSTAT series.",
         "Account for structural heterogeneity: treat food inflation and wage erosion as non-neutral distributional shocks.",
         "Differentiate statistical correlation from causal decoupling mechanisms.",
     ]
     ```
2. **Superpowers Skill: `cepalstat-econometrics`**:
   - Location: `.agents/skills/cepalstat-econometrics/SKILL.md`
   - Frontmatter:
     - Name: `cepalstat-econometrics`
     - Description: `Use when modeling, estimating, or interpreting econometrics, poverty elasticities, real wage pass-through, or OLS regressions with statsmodels using CEPALSTAT data.`
   - Content:
     - OLS model formulation for poverty growth elasticity.
     - P-value thresholds and R-squared interpretation guidelines.
     - Food inflation transmission channel (Indicator 2929) and Purchasing Power Gap ($\Delta\% \text{Salario} - \text{InflAlimentos}$).
     - Code snippets demonstrating `EconometricEstimator.fit_poverty_growth_model(dataset)`.
3. **Tests in `tests/test_skill_structure.py`**:
   - Add `test_bmad_agent_econometrician_structure()`: asserts existence, valid frontmatter, icon `📈`, and `customize.toml` configuration.
   - Add `test_cepalstat_econometrics_skill_structure()`: asserts existence, valid frontmatter starting with "Use when", and key methodological terms.

## TDD Instructions
1. Add tests in `tests/test_skill_structure.py`.
2. Run `uv run pytest tests/test_skill_structure.py` to confirm failure (RED).
3. Create agent and skill directories and files.
4. Run `uv run pytest tests/test_skill_structure.py` to confirm pass (GREEN).
5. Run full non-integration test suite: `uv run pytest -m "not integration"`.
6. Commit: `git add .agents/skills/bmad-agent-econometrician/ .agents/skills/cepalstat-econometrics/ tests/test_skill_structure.py && git commit -m "feat(agents): create bmad-agent-econometrician and cepalstat-econometrics skill"`.
7. Write report to `.superpowers/sdd/2026-10-14-decoupling-food-inflation-interactive-viz/task-4-report.md`.
8. Return status contract.
