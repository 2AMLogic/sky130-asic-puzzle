"""Close the review's open limitation — and refute it: TRY AGAIN is NOT
universal. There is a FIFTH message, and this script proves the chip's
complete output behavior exactly.

evidence/independent-review-addendum.md confirmed claim 6 but qualified it:
"TRY AGAIN universality is sampled (169 failing words). A per-cycle BMC over
all failing inputs would close it; not run." This script runs it, over the
full 92-flop unrolling with the 4 unresettable dfxtp power-up bits left free
(so every verdict below covers all 16 power-up combinations):

1. Enumerates ALL distinct O[7:0] streams over failing words (blocking
   clauses until UNSAT): exactly TWO exist — TRY AGAIN and a previously
   unknown diagnostic spelling `TWO"NOT TOUCH` (0x22 between TWO and NOT —
   a ditto mark: read against the answer `(* TWO STARS *)`, it says
   "two STARS not touch", the adjacency rule).
2. Proves the diagnostic's firing condition is EXACT (iff):
   - every word with all 33 row/col/region counts == 2 and at least one
     touching pair emits the diagnostic (UNSAT on the negation);
   - only such words do: for each of the 33 counting constraints, a word
     emitting the diagnostic while violating it is UNSAT (66 queries).
3. Sweeps all 16 dfxtp power-ups on the witness word: identical stream.
4. Replays the witness gate-level with Icarus: success never asserts; every
   defined output byte matches the model (the 4 x-bytes are Icarus
   x-pessimism at exactly the positions step 3 proves constant).

Together with the accepted word's uniqueness (claim 3) this yields the
chip's complete message map over 121-bit active words:

    accepted word                          -> (* TWO STARS *), success=1
    all-zeros                              -> EMPTY SKY
    all-ones                               -> BIG BANG
    all counts == 2 and >=1 touching pair  -> TWO"NOT TOUCH
    everything else                        -> TRY AGAIN

Run from the repo root:

    PYTHONPATH=. .sim-work/review-venv/bin/python \
      evidence/easter-egg-try-again-universality.py
"""

from collections import defaultdict
from itertools import product
from pathlib import Path

from pysat.card import CardEnc, EncType

from tools.sim import bmc
from tools.sim.answer import decode_output_cycles
from tools.sim.solve import load_design, verify_by_simulation, windowed_scenario

# The unique accepted 121-bit active word (claim 3: unique at this bound).
# Recorded in evidence/puzzle-solve.md section 5; independently re-derived by
# evidence/easter-egg-lead4.py, and re-validated against the model below.
ACCEPTED = (
    "0000000101010000100000000000010101010000000000001010000001000001"
    "000000100000101000010000000100000010000010010001010000000"
)
# The 11 irregular regions recovered by evidence/easter-egg-lead4.py.
REGIONS = ["HHHHHCCKFFA", "HHIHHCKKFFA", "HHICCCCKKFA", "HHICGGGAKKA",
           "IHICGAAAAAA", "IIICGGGAEEE", "CCCCCCGAEBB", "CDDDGGGAEBB",
           "CDDJAAAAEBB", "CCDJJAAAEEE", "CDDJAAAAAAA"]

design = load_design(Path(".sim-work/independent-review/puzzle-extracted.v"),
                     work_dir=Path(".sim-work/independent-review/model"))
model = design.model
scenario = windowed_scenario(
    model, reset_cycles=3, idle_cycles=1, active_cycles=121, tail_cycles=65,
    free_ports=["I"], enable_port="enable", reset_port="rst_n",
    goal_output="success")
unrolling = bmc.unroll(model, cycles=scenario.cycles,
                       input_schedule=scenario.schedule)
active = scenario.free_cycles("I")
in_lits = [unrolling.input_lits[t]["I"] for t in active]
WINDOW = list(range(125, scenario.cycles))
cell = lambda r, c: in_lits[r * 11 + c]  # noqa: E731


def lv(o, lit):
    b = bool(o.model_bits[abs(lit)])
    return int(b if lit > 0 else not b)


def stream_of(o):
    return tuple(sum(lv(o, unrolling.output_lits[c][f"O[{i}]"]) << i
                     for i in range(8)) for c in WINDOW)


def render(s):
    return "".join(chr(b) if 32 <= b < 127 else "." for b in s).rstrip(".")


def word_assumptions(bits):
    return [l if b == "1" else -l for l, b in zip(in_lits, bits)]


def stream_differs_clause(s):
    out = []
    for c, exp in zip(WINDOW, s):
        row = unrolling.output_lits[c]
        for i in range(8):
            lit = row[f"O[{i}]"]
            out.append(-lit if (exp >> i) & 1 else lit)
    return out


# 0. Validate the accepted-word constant: success must assert.
acc = bmc.solve_cnf(unrolling, assumptions=word_assumptions(ACCEPTED))
assert acc.sat
assert max(lv(acc, unrolling.output_lits[c]["success"]) for c in WINDOW) == 1
print("accepted-word validation: success asserts")

# 1. Enumerate ALL distinct failure streams.
extra = [
    [-l if b == "1" else l for l, b in zip(in_lits, ACCEPTED)],  # != accepted
    list(in_lits),                                               # != all-zeros
    [-l for l in in_lits],                                       # != all-ones
]
streams = []
while True:
    out = bmc.solve_cnf(unrolling, assumptions=[], extra_clauses=extra)
    if not out.sat:
        break
    s = stream_of(out)
    word = "".join(str(out.inputs[t]["I"]) for t in active)
    streams.append((s, word))
    print(f"stream {len(streams)}: {render(s)!r}  ({out.seconds:.2f}s)")
    print(f"  witness word: {word}")
    extra.append(stream_differs_clause(s))
    assert len(streams) <= 8, "unexpectedly many streams"
print(f"enumeration COMPLETE: exactly {len(streams)} failure streams exist")
assert len(streams) == 2
diag_stream, diag_word = next(
    (s, w) for s, w in streams if 0x22 in s)
print("diagnostic bytes:", " ".join(f"{b:02x}" for b in diag_stream[:16]))

# 2a. Every counts-perfect word with a touching pair emits the diagnostic.
top = unrolling.cnf.n_vars
clauses = []
constraints = []
for r in range(11):
    constraints.append((f"row{r}", [cell(r, c) for c in range(11)]))
for c in range(11):
    constraints.append((f"col{c}", [cell(r, c) for r in range(11)]))
regmap = defaultdict(list)
for r in range(11):
    for c in range(11):
        regmap[REGIONS[r][c]].append(cell(r, c))
for k in sorted(regmap):
    constraints.append((f"region{k}", regmap[k]))
for _, lits in constraints:
    enc = CardEnc.equals(lits=lits, bound=2, top_id=top,
                         encoding=EncType.seqcounter)
    top = max(top, enc.nv)
    clauses.extend(enc.clauses)
pair_lits = []
for r in range(11):
    for c in range(11):
        for dr, dc in ((0, 1), (1, -1), (1, 0), (1, 1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < 11 and 0 <= cc < 11:
                top += 1
                clauses.append([-top, cell(r, c)])
                clauses.append([-top, cell(rr, cc)])
                pair_lits.append(top)
clauses.append(pair_lits)
out = bmc.solve_cnf(unrolling, assumptions=[],
                    extra_clauses=clauses + [stream_differs_clause(diag_stream)])
print(f"class proof (counts-ok+touch => diagnostic): sat={out.sat} "
      f"({out.seconds:.2f}s)")
assert not out.sat

# 2b. Converse: the diagnostic implies every count == 2 (66 queries).
diag_assum = []
for cyc, exp in zip(WINDOW, diag_stream):
    row = unrolling.output_lits[cyc]
    for i in range(8):
        lit = row[f"O[{i}]"]
        diag_assum.append(lit if (exp >> i) & 1 else -lit)
unexpected = 0
for name, lits in constraints:
    for enc in (CardEnc.atmost(lits=lits, bound=1, top_id=unrolling.cnf.n_vars,
                               encoding=EncType.seqcounter),
                CardEnc.atleast(lits=lits, bound=3, top_id=unrolling.cnf.n_vars,
                                encoding=EncType.seqcounter)):
        r = bmc.solve_cnf(unrolling, assumptions=diag_assum,
                          extra_clauses=enc.clauses)
        if r.sat:
            unexpected += 1
            print(f"UNEXPECTED SAT: {name}")
print(f"converse proof: {len(constraints) * 2} queries, "
      f"{unexpected} unexpected SAT")
assert unexpected == 0

# 3. All 16 power-ups give the identical stream for the witness word.
dfx_idx = [i for i, ff in enumerate(model.ffs) if "dfxtp" in ff.name]
assert len(dfx_idx) == 4
init_lits = [unrolling.state_lits[0][i] for i in dfx_idx]
variants = set()
for combo in product((0, 1), repeat=4):
    a = word_assumptions(diag_word) + [
        lit if v else -lit for lit, v in zip(init_lits, combo)]
    r = bmc.solve_cnf(unrolling, assumptions=a)
    assert r.sat
    variants.add(stream_of(r))
print(f"power-up sweep: {len(variants)} distinct stream(s) across 16 combos")
assert len(variants) == 1

# 4. Gate-level Icarus replay of the witness.
drive = {}
for p in model.inputs:
    if p == "clk":
        continue
    drive[p] = [(scenario.schedule[t].get(p) or 0)
                for t in range(scenario.cycles)]
for t, b in zip(active, diag_word):
    drive["I"][t] = int(b)
watch = [f"\\O[{i}]" for i in range(8)] + ["success"]
verified = verify_by_simulation(
    design, drive=drive, watch=watch, expect=[],
    work_dir=Path(".sim-work/fourth-message-verify"))
print("icarus sim ok:", verified.ok)
samples = verified.samples
succ = [c for c, row in enumerate(samples)
        if str(row.get("success")) == "1"]
print("success cycles:", succ if succ else "none")
mismatch = 0
xcycles = []
for cyc, exp in zip(WINDOW, diag_stream):
    bits = [str(samples[cyc].get(f"O[{i}]")) for i in range(8)]
    if any(b not in ("0", "1") for b in bits):
        xcycles.append(cyc)
        continue
    got = sum(int(b) << i for i, b in enumerate(bits))
    if got != exp:
        mismatch += 1
        print(f"MISMATCH cycle {cyc}: icarus {got:02x} model {exp:02x}")
print(f"icarus vs model: {mismatch} mismatches; x-pessimism cycles {xcycles} "
      "(model proves these constant across all 16 power-ups)")
assert mismatch == 0 and not succ

print()
print("COMPLETE MESSAGE MAP (proven, all 16 power-ups):")
print("  accepted word                          -> (* TWO STARS *), success")
print("  all-zeros                              -> EMPTY SKY")
print("  all-ones                               -> BIG BANG")
print('  all counts == 2 and >=1 touching pair  -> TWO"NOT TOUCH')
print("  everything else                        -> TRY AGAIN")
