# retainer-kit: rules for agents

Read `README.md` for how it works, `RUNBOOK.md` for procedures, `TASK.md` for what is open.
Global rules in `~/.claude/CLAUDE.md` still apply.

- Public repo: no personal data, account figures, third-party names or the owner's email in any file; the git gate blocks them.
- Real-time commits only; never backdate, never set `GIT_AUTHOR_DATE`.
- Releases follow hq CONVENTIONS (`~/developer/hq/CONVENTIONS.md`); the RUNBOOK names the steps.
- Docs follow the four-file skeleton: a fact lives in one file, and the commands table is generated.
- Traps: never un-ignore `clients/` or `demo_clients/`, exports hold customer emails; tests and the Pages site run on the synthetic store only; shares are compared in percentage points, do not "fix" that to relative changes.
