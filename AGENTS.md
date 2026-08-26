# AGENTS.md - Python project Harness profile

## Scope

This profile is for Python projects that use `pyproject.toml`, `requirements.txt`, `setup.py`, `setup.cfg`, `tox.ini`, or `pytest.ini`.

It extends the base xian-harness lifecycle. It does not replace `xian-open`, `xian-spec`, `xian-design`, `xian-plan`, `xian-build`, `xian-verify`, `xian-gate`, or `xian-archive`.

## Language

- User-facing conversation and delivery notes should follow the target project's language preference.
- Machine-readable JSON/YAML/state/gate fields must use ISO 8601 timestamps with timezone offsets.

## Python Work Rules

- Detect the environment and package manager before running commands:
  - `pyproject.toml` may indicate `uv`, Poetry, Hatch, PDM, setuptools, or another backend.
  - `requirements.txt` usually implies pip-compatible dependency management.
  - existing lockfiles and project scripts are stronger evidence than assumptions.
- Prefer project scripts or documented commands over ad hoc commands.
- Do not assume a framework. Django, FastAPI, Flask, CLI tools, libraries, notebooks, and data jobs need different checks.
- Keep virtualenvs, caches, coverage folders, build artifacts, and generated files out of Harness evidence unless they are explicitly required.
- For behavior changes, include at least one focused test or a documented TDD exception with replacement verification.

## Harness Boundaries

- This profile is a profile overlay, not a new lifecycle.
- External agents, delegate outputs, or review artifacts remain candidate-only unless the owning xian skill accepts them.
- Assets from unrelated profiles are not active under this profile.
- `xian-commit` remains an independent tool boundary; do not implement commit/push behavior inside this profile.

## Verification Hints

When the project provides the commands, prefer this order:

1. dependency/environment availability check.
2. focused test command such as `pytest path/to/test.py`.
3. typecheck when the project uses mypy, pyright, or basedpyright.
4. lint/format check when it is already part of the project standard.
5. build/package check only when it proves an acceptance criterion.
