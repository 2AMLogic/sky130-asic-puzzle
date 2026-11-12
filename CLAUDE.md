# Working in sky130-asic-puzzle

This repo is a **reverse-engineering canary** for `klayout-tools`. Read
[`README.md`](README.md) first for what the subject is and why it is here.

It sits under the 2AM Logic map — the cross-cutting rules in
[`2am/CLAUDE.md`](https://github.com/2AMLogic/2am/blob/main/CLAUDE.md) hold here too. The
rules below are local and sit on top of them.

## 1. This repo is private until 2026-09-04, and that is load-bearing

**Lifted 2026-09-04.** The repository is public and publishing is invited. Everything below is
kept as the record of why it stayed dark; the only rule that still binds is §3 (do not vendor
the puzzle files).


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
- `scripts/check-embargo.sh` checks the one thing a script can still check — that no upstream puzzle
  file is tracked (§3). It cannot judge prose. **If you
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
This repository has [Repo Skills](https://github.com/rjwalters/repo) v0.26.1 installed —
general repository hygiene and environment commands invoked as `/repo:<command>`. Run
`/repo:help` for the command list, or see `.claude/skills/repo/SKILL.md` for the full
guide. Hygiene commands apply safe, reversible fixes by default and report each
change; run with `--ask` to review first, and `--prune` to allow irreversible
removals. Managed by `install.sh` — edit outside the markers only.
<!-- END REPO-SKILLS -->
<!-- BEGIN SQUAD -->
## Squad — cross-agent collaboration

This repo has [Squad](https://github.com/rjwalters/squad) installed. Claude,
Codex and opencode share the same room and MCP tools. Before touching shared state, read
and follow the installed Squad skill, including its room/identity conventions:

- Claude: `.claude/skills/squad/SKILL.md`
- Codex: `.agents/skills/squad/SKILL.md` (invoke `$squad` or ask naturally)
- opencode: `.agents/skills/squad/SKILL.md` (reads this `AGENTS.md`; use the
  `/squad-<workflow>` commands, and loop with `squad wait`)

Both expose join, wait, goals, card, fanout, steward, and clear workflows. Claude aliases are
`/squad:<workflow>`; legacy Codex prompts are `/squad-<workflow>`.

**Other channels:** in a squad-enabled repo, coordinate in the room, including
between agents of the same harness: repo work discussion, ownership questions,
hand-offs and collisions. A harness's built-in cross-session messaging (for
example Claude's) is only for pointing or waking a session that is not watching
the room ("see the squad room, message N"), or for repos without squad. If you
receive such a message about this repo's work, record the substance in the room
with a short summary naming the sender, and post any answer you give there too.
Rooms persist for later joiners; direct messages do not.

For research work, discover and reuse the durable Science Card node IDs surfaced
by join/node list; the shared card workflow connects dependencies, committed
artifacts and revision-bound bank provenance.
<!-- END SQUAD -->
