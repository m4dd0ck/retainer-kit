# retainer-kit: rules for agents

Instructions for coding agents working in this repo; a human reader wants `README.md`. Read
`README.md` for how it works, `RUNBOOK.md` for procedures, `TASK.md` for what is open. The
owner's global agent rules apply on top of these.

- Public repo: no personal data, account figures, third-party names or the owner's email in any file; a pre-commit scan blocks them.
- Real-time commits only; never backdate, never set `GIT_AUTHOR_DATE`.
- Release steps: `RUNBOOK.md` §Release.
- README, RUNBOOK, CLAUDE and TASK each hold one kind of fact; the README commands table is
  generated, never hand-edited.
- Traps: never un-ignore `clients/` or `demo_clients/`, exports hold customer emails; tests and the Pages site run on the synthetic store only; shares are compared in percentage points, do not "fix" that to relative changes.
