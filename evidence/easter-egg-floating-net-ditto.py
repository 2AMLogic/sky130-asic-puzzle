"""Post-close correction (2026-09-08): is the 0x22 ditto mark in the fifth
message real, or an artifact of the extracted netlist's one undriven net?

`net_00575` is read by two gates in the output generator and driven by
nothing (evidence/easter-eggs.md, Lead 5). The cycle model fills undriven
nets with a constant (`undriven_value`, default 0); Icarus leaves them `x`.
This script replays every known message class under both constants and then
shows, cycle by cycle, which O bits Icarus reports as `x` for the
adjacency-violation witness.

Run from the repo root after `./scripts/fetch-puzzle.sh`:

    PYTHONPATH=. .sim-work/review-venv/bin/python \
        evidence/easter-egg-floating-net-ditto.py
"""

from pathlib import Path
from tools.sim.solve import load_design, windowed_scenario, verify_by_simulation
from tools.sim.seqmodel import simulate

ACCEPTED = (
    "0000000101010000100000000000010101010000000000001010000001000001"
    "000000100000101000010000000100000010000010010001010000000"
)
DIAG = "1000000001000001010000000000010100011000000010000010000000001001000100000010000000100001000100000010000100100001100000000"
WORDS = {
    "accepted": ACCEPTED,
    "diag(touch)": DIAG,
    "zeros": "0" * 121,
    "ones": "1" * 121,
    "tryagain": "1" * 120 + "0",
}

design = load_design(
    Path(".sim-work/independent-review/puzzle-extracted.v"),
    work_dir=Path(".sim-work/independent-review/model"),
)
model = design.model
print("undriven nets:", model.undriven_nets)
sc = windowed_scenario(
    model,
    reset_cycles=3,
    idle_cycles=1,
    active_cycles=121,
    tail_cycles=65,
    free_ports=["I"],
    enable_port="enable",
    reset_port="rst_n",
    goal_output="success",
)
active = sc.free_cycles("I")
WINDOW = list(range(125, sc.cycles))


def run(word, uv):
    seq = []
    for t in range(sc.cycles):
        d = {p: (sc.schedule[t].get(p) or 0) for p in model.inputs if p != "clk"}
        seq.append(d)
    for t, b in zip(active, word):
        seq[t]["I"] = int(b)
    tr = simulate(model, seq, undriven_value=uv)
    bytes_ = [sum(tr.outputs[c][f"O[{i}]"] << i for i in range(8)) for c in WINDOW]
    succ = [c for c in range(len(tr.outputs)) if tr.outputs[c].get("success") == 1]
    return bytes_, succ, seq


def render(bs):
    return "".join(chr(b) if 32 <= b < 127 else "." for b in bs).rstrip(".")


for name, word in WORDS.items():
    b0, s0, _ = run(word, 0)
    b1, s1, seq = run(word, 1)
    diff = [(WINDOW[i], b0[i], b1[i]) for i in range(len(b0)) if b0[i] != b1[i]]
    print(
        f"{name:12s} uv=0 {render(b0)!r}  uv=1 {render(b1)!r}  success@{s0[:1]}/{s1[:1]}  diffs={[(c, f'{a:02x}', f'{b:02x}') for c, a, b in diff]}"
    )

# Icarus, x-aware, for the diag word
drive = {}
for p in model.inputs:
    if p == "clk":
        continue
    drive[p] = [(sc.schedule[t].get(p) or 0) for t in range(sc.cycles)]
for t, b in zip(active, DIAG):
    drive["I"][t] = int(b)
watch = [f"\\O[{i}]" for i in range(8)] + ["success"]
v = verify_by_simulation(
    design, drive=drive, watch=watch, expect=[], work_dir=Path(".sim-work/ditto-probe")
)
print("icarus ok:", v.ok)
for cyc in WINDOW[:20]:
    bits = [str(v.samples[cyc].get(f"O[{i}]")) for i in range(8)]
    s = "".join(bits[::-1])
    val = (
        "x"
        if any(b not in "01" for b in bits)
        else f"{int(s, 2):02x} {chr(int(s, 2)) if 32 <= int(s, 2) < 127 else '.'}"
    )
    print(f"  cycle {cyc}: O[7:0]={s} -> {val}")
