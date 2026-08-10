# Working in sky130-asic-puzzle

This repo is a **reverse-engineering canary** for `klayout-tools`. Read
[`README.md`](README.md) first for what the subject is and why it is here.

It sits under the 2AM Logic map — the cross-cutting rules in
[`2am/CLAUDE.md`](https://github.com/2AMLogic/2am/blob/main/CLAUDE.md) hold here too. The
rules below are local and sit on top of them.

## 1. This repo is private until 2026-09-04, and that is load-bearing

Jane Street asks solvers to refrain from posting spoilers or a full writeup online until
**submissions close 2026-09-04**. Privacy is how that is honored, and it means the work
itself is unconstrained: **commit the netlist, the solve and the answer here freely.** A
private repo is not a public post.

What is constrained is the boundary out of this repo. Before 2026-09-04:

- **Never make this repository public.** Visibility flips are operator-only across the fleet
  (`2am/README.md`), and here it is also a commitment to a third party. An agent does not
  flip it, does not ask a workflow to flip it, and does not add a CI step that could.
- **Never copy content out.** Not into `marketing`, the site, the pulse or X. Not into a
  public issue, PR, or commit message on `klayout-tools` or any public canary.
- **Upstream findings must be written toolkit-first.** *"Cell-level extraction is missing
  from `klt extract`"* is a fine public `klayout-tools` issue. *"…and here is the netlist it
  failed to recover from the puzzle"* is not. Report the gap, not the subject.
- `scripts/check-embargo.sh` checks the things a script can check — that the repo is still
  private and that no remote here points at a public repo. It cannot judge prose. **If you
  are unsure whether something may leave this repo, it may not.**

After submissions close this reverses: publishing is invited, and the writeup becomes the
deliverable. Mark this section lifted rather than deleting it, so the record of why the repo
stayed dark survives.

## 2. Findings about the toolkit go upstream

This repo is the *harness*, not the product. A defect or gap in `klt` is filed on
[`2AMLogic/klayout-tools`](https://github.com/2AMLogic/klayout-tools) and referenced here.
Do not fix `klt` by working around it in `tools/` and staying quiet — the entire point of a
canary is that the toolkit hears about it.

## 3. Do not vendor the puzzle files

`janestreet/asic-puzzle-2026` carries **no license**. Its files are fetched into `puzzle/`,
which is gitignored, and are never committed here. Do not copy fragments of them into
documentation either.

## 4. The warm-up is the regression test, and it is the priority

`warmup/04_final.gds → extract → compare to warmup/01_netlist.v` is an objective pass/fail
check with published ground truth. It is worth more to the toolkit than the puzzle answer is,
it is not embargoed, and it should stay green independently of the puzzle.

## 5. Claims are evidence-backed

Same standard as the design canaries: a claim about what the circuit does is backed by a
simulation that a reader can re-run, not by inference from the layout. State what was
actually executed.

<!-- BEGIN LOOM ORCHESTRATION -->
This repository uses [Loom](https://github.com/rjwalters/loom) for AI-powered development orchestration — see the Loom repository for the full guide (roles, labels, worktrees, configuration). When installed, Loom also writes a locally-substituted copy of that guide to `.loom/CLAUDE.md`.
<!-- END LOOM ORCHESTRATION -->
<!-- BEGIN REPO-SKILLS -->
This repository has [Repo Skills](https://github.com/rjwalters/repo) v0.10.0 installed —
general repository hygiene and environment commands invoked as `/repo:<command>`. Run
`/repo:help` for the command list, or see `.claude/skills/repo/SKILL.md` for the full
guide. Hygiene commands apply safe, reversible fixes by default and report each
change; run with `--ask` to review first, and `--prune` to allow irreversible
removals. Managed by `install.sh` — edit outside the markers only.
<!-- END REPO-SKILLS -->
<!-- BEGIN SQUAD -->
## Squad — cross-agent collaboration

This repo has [squad](https://github.com/rjwalters/squad) installed: a chat
room private to this repo (SQLite at `.squad/squad.db`) shared by every agent
working here — Claude and Codex are peers with identical tools. Use it to
split work, hand off results, and track shared goals (e.g. divide the lemmas
of a Lean proof and claim them in chat).

Tools (all pull-based; nothing ever wakes you):
- `squad_join` — register, get members + open goals + recent history
- `squad_send` — post to the room; `@name` addresses a teammate
- `squad_check` — your unread messages (consumes; `peek: true` to look
  without consuming; `wait_seconds: 25` long-polls for live conversation)
- `squad_goals` / `squad_goal_add` / `squad_goal_done` /
  `squad_goal_reopen` — shared goal board (reopen undoes a mistaken done);
  every change is auto-announced in chat
- `squad_clear` — wipe the room (destructive; needs explicit user intent)

Conventions: claim a goal in chat before working on it; report results when
done; only mark goals done that you verified (in Lean work: it compiles with
no `sorry`); never speak as another persona; coordinate before editing files
a teammate said they're working on. At session start, a `squad_check` with
`peek: true` shows whether a teammate left you a message.

Join commands: `/squad:join` (Claude) or `/squad-join` (Codex) — then hold
the loop: check(wait 25s) → respond/work → repeat.
<!-- END SQUAD -->
