# Python Project Checklist

Use this checklist when a Python target project needs lightweight Harness setup or verification planning.

- Detect project tooling from `pyproject.toml`, lockfiles, and documented commands.
- Prefer existing project scripts over invented commands.
- Run focused tests before broad package/build checks.
- Run typecheck when the project standard includes it.
- Keep virtualenvs, caches, coverage, and build outputs out of Harness evidence unless required.
- Do not assume a Python framework from Python markers alone.
