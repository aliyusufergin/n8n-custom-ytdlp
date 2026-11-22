# AGENTS.md

Guidance for coding agents working in this repo.

## How work is planned and recorded

Work follows the alice-skills flow: `/clarify` → `/survey` (when the approach is open) →
`/spec` (only the user starts it) → `/step` once per session, `/steer` when the user
changes the goal or plan. Wait for the user's confirmation at each gate.

- Each piece of work keeps its record in `.work/<name>/`: spec, `next.md` handover,
  journal, `done.md` and any survey. Read it before continuing that work.
- `.work/knowledge.md`, when it exists, holds what every piece of work here should know.
- Decisions are recorded in the work's spec, not as new ADRs. `docs/adr/` holds the
  project's earlier decisions; read the ones touching your area, and say so explicitly
  when a change contradicts one.
- Specs and tasks are not GitHub Issues. GitHub Issues are used only by the publishing
  workflow for its failure issues and notices (see the README).

## Domain language

Read `CONTEXT.md` before exploring. When your output names a domain concept (a commit
message, a test name, a README section), use the term as `CONTEXT.md` defines it and avoid
the synonyms it lists under _Avoid_. If a needed term is missing, add it to `CONTEXT.md`
as part of the work.
