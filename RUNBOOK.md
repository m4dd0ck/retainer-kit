# Runbook

Procedures for retainer-kit. `README.md` describes what each command does; this file says when
to run it and in what order.

## On open

```bash
git status --short
git log -3 --oneline
```

## On close

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest -q
```

## Monthly: a client's report

1. Export the month's orders from Shopify ("Export orders", CSV) into the client's exports
   folder. Overlaps with earlier files are fine; the newest file wins per order.
2. `uv run retainer report <client folder> --month YYYY-MM`.
3. Read the report's footer: date range of the exports, cancelled and test orders left out. If
   the exports do not cover the comparison months, the comparisons are blank, not wrong.
4. Deliver the HTML file. Nothing is committed: client folders are outside git.

## New client

`uv run retainer init <folder> --name "<client>"`, edit the `client.toml` it writes, then drop
in exports and run the monthly procedure.

## Release

Conventions in `~/developer/hq/CONVENTIONS.md` §Versioning.

1. Bump `version` in `pyproject.toml` and `__version__` in `src/retainer_kit/__init__.py` to the
   same value; `uv lock`.
2. Commit `chore: Release vX.Y.Z`, then `git tag -a vX.Y.Z -m "vX.Y.Z"` and
   `git push origin main --tags`.
3. `gh release create vX.Y.Z --title "retainer-kit vX.Y.Z" --notes "<what changed>"` with the
   compare link to the previous tag, marked latest.
4. CI must be green on the tagged commit. Nothing pins this package.

## Deploy

Nothing to do by hand: every push to `main` rebuilds the sample site (`retainer site`) and
deploys it to GitHub Pages from `ci.yml`. If the site is stale, check the Actions run; if Pages
was never enabled, set the source to "GitHub Actions" in the repo settings once.

## Restore on a new machine

1. Clone `git@github.com:m4dd0ck/retainer-kit.git`; `uv sync`.
2. No secrets, no data in the repo. Client folders come from wherever the analyst keeps them.
3. `uv run retainer demo` recreates the sample store.

## Validate

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy src/
uv run pytest
uv run retainer site --out site
python3 ~/.claude/scripts/doc-check.py --repo .
```
