---
name: github-repo-search
description: Use when searching, discovering, filtering, or evaluating GitHub repositories, finding open-source code libraries, analyzing repository health metrics, or inspecting repo architectures.
---

# GitHub Repository Search & Quality Evaluation

## Overview
This skill provides automated workflows to discover, filter, and critically evaluate open-source GitHub repositories using the GitHub CLI (`gh`) and Git. It enables agents to benchmark candidate libraries, evaluate maintenance vitality, and prevent adopting abandoned or poor-quality dependencies.

## When to Use
- Searching for open-source repositories matching specific keywords, domains, or programming languages.
- Benchmarking 2 to 5 alternative packages or libraries for a project.
- Evaluating repository vitality, health score, license compatibility, and release cadence before adopting a dependency.
- Searching for concrete implementation patterns or functions across public GitHub code using `gh search code`.
- Inspecting repository architectures and README documentation without polluting the working directory.

When NOT to use:
- For managing local git commits, branches, and merges in the current repository (use standard git tools).
- For statistical or econometrical modeling (use `applied-econometrics` or `applied-statistics`).

---

## 1. Structured GitHub Search (`gh search repos`)

> [!TIP]
> Always request structured JSON output (`--json`) to parse repository metadata programmatically with zero scraping errors.

### Key Query Modifiers & Filters
- **Language**: `--language python` (or `--language rust,r,typescript`)
- **Stars threshold**: `--stars ">50"` (filters out empty student homework/dead stubs)
- **Activity / Recency**: `--pushed ">2025-01-01"` (excludes unmaintained projects)
- **Sorting**: `--sort stars` or `--sort updated`
- **Output fields**: `--json fullName,description,stargazersCount,forksCount,updatedAt,licenseInfo,url,primaryLanguage`

### Command Examples
```bash
# 1. Search repos by keyword with language and stars filter
gh search repos "macroeconomic forecasting" --language python --stars ">20" --sort stars --limit 10 --json fullName,description,stargazersCount,updatedAt,licenseInfo,url

# 2. Search by GitHub topic tag
gh search repos "econometrics" --topic econometrics --sort stars --limit 5 --json fullName,stargazersCount,description,url

# 3. Search code for specific functions or API clients
gh search code "class CepalStatClient" --language python --limit 5 --json path,repository
```

---

## 2. Repository Health & Quality Rubric (0–100 Score)

Never evaluate a repository solely by its star count. Stars can be accumulated over a decade on an abandoned project, or inflated artificially. Use this weighted evaluation matrix:

| Dimension | Weight | Good Signal | Red Flag |
| :--- | :--- | :--- | :--- |
| **Maintenance Vitality** | 30% | Commit/push in the last 6 months; active release tags. | Last commit > 2 years ago; unresolved security vulnerabilities. |
| **Community & Adoption** | 20% | > 100 stars, active forks, community discussions. | 0-5 stars with no documentation; dead author account. |
| **Licensing Safety** | 20% | Permissive open-source license: MIT, Apache-2.0, BSD-3-Clause. | No license file (all rights reserved by default); incompatible AGPL/GPL for commercial use. |
| **Engineering Rigor** | 20% | Passing CI workflow (`.github/workflows`), unit tests (`tests/`), type annotations (`py.typed`). | No test suite; zero CI status; broken build badges. |
| **Issue Resolution** | 10% | Healthy open/closed issue ratio; responsive maintainers. | Hundreds of open PRs/issues with 0 responses from authors. |

---

## 3. Safe Non-Invasive Inspection Protocol

Before cloning a repository into your local disk, inspect it remotely:

### Step 1: Remote README & Details (`gh repo view`)
```bash
# View formatted README directly in terminal
gh repo view <owner/repo>

# View release history and latest version
gh release list -R <owner/repo> --limit 3
```

### Step 2: Shallow Inspection Clone (When code audit is needed)
When you need to inspect the source code, tests, or `pyproject.toml`, always clone with depth 1 into a temporary scratch directory:

```bash
# Shallow clone (only latest commit, fastest download, minimal disk usage)
git clone --depth 1 https://github.com/<owner>/<repo>.git temp_inspect_repo

# Inspect dependencies and architecture
ls temp_inspect_repo

# Clean up immediately after inspection
rm -rf temp_inspect_repo
```

---

## 4. Python Automation: Search, Score & Compare Repositories

Use this Python script to query the GitHub CLI, calculate health scores, and generate a markdown comparison table:

```python
import json
import subprocess
from datetime import datetime, timezone


def search_and_evaluate_repos(query: str, limit: int = 5) -> list[dict]:
  """Search GitHub repos and compute an objective Health Score (0-100)."""
  cmd = [
      "gh",
      "search",
      "repos",
      query,
      "--sort",
      "stars",
      f"--limit={limit}",
      (
          "--json=fullName,description,stargazersCount,forksCount,updatedAt,licenseInfo,url"
      ),
  ]

  res = subprocess.run(cmd, capture_output=True, text=True, check=True)
  repos = json.loads(res.stdout)

  now = datetime.now(timezone.utc)
  evaluated = []

  for r in repos:
    # 1. Maintenance score (max 30 pts)
    updated_str = r.get("updatedAt", "")
    days_since_update = 9999
    if updated_str:
      updated_dt = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
      days_since_update = (now - updated_dt).days

    maint_score = 30 if days_since_update < 90 else (
        20 if days_since_update < 180 else (10 if days_since_update < 365 else 0)
    )

    # 2. Popularity score (max 25 pts)
    stars = r.get("stargazersCount", 0)
    pop_score = 25 if stars >= 500 else (
        20 if stars >= 100 else (10 if stars >= 20 else 5)
    )

    # 3. License score (max 25 pts)
    lic = (r.get("licenseInfo") or {}).get("key", "").lower()
    lic_score = 25 if lic in ["mit", "apache-2.0", "bsd-3-clause", "bsd-2-clause"] else (
        15 if lic else 0
    )

    # 4. Forks/Community score (max 20 pts)
    forks = r.get("forksCount", 0)
    fork_score = 20 if forks >= 50 else (
        15 if forks >= 10 else (5 if forks >= 1 else 0)
    )

    total_score = maint_score + pop_score + lic_score + fork_score

    evaluated.append({
        "name": r["fullName"],
        "stars": stars,
        "license": lic or "None",
        "last_pushed_days": days_since_update,
        "health_score": total_score,
        "url": r["url"],
        "description": r.get("description", ""),
    })

  return sorted(evaluated, key=lambda x: x["health_score"], reverse=True)
```

---

## 5. Common Pitfalls & Anti-Patterns

| Anti-Pattern | Why it Fails | Correct Approach |
| :--- | :--- | :--- |
| **Trusting Stars Blindly** | High-star repos may have been abandoned years ago or created for demo videos. | Verify `updatedAt` and check if commits were made in the past 6 months. |
| **Adopting Code Without License** | Code without an explicit open-source license is legally copyrighted ("all rights reserved"). | Only adopt repos with explicit permissive licenses (MIT, Apache-2.0, BSD). |
| **Heavy Full Git Clones** | Full clones download gigabytes of commit history and binary git blobs. | Use `gh repo view` or `git clone --depth 1` into a temporary folder. |
| **Ignoring Issue Backlog** | Hundreds of unaddressed bugs indicate maintainer burnout or abandoned project. | Check the open vs. closed issues ratio with `gh issue list -R <owner/repo>`. |
