# Notes for next time

Lessons from the Jane Street 2026 ASIC puzzle, written on 2026-10-02 after the
[results post](https://blog.janestreet.com/asic-puzzle-results/). There are two halves: what to do
when we solve someone else's puzzle, and what to copy if we ever host one. The evidence behind
both is in `evidence/easter-eggs.md` (see the 2026-10-02 addendum).

## As a solver: the Easter-egg pass

Everything we found came from analysing the circuit. Everything we missed needed someone to
*look*: at the VCD header, at the example inputs as text, at the region map as a picture. The
brief (`EASTER-EGG-HUNT.md`) had "look at it as a picture" as its top lead, and the work never
got around to it because proofs were going well.

You can't hunt for an egg you have no prior on. But "a playful author writes in everything they
control" is a prior, and it can be turned into a checklist:

1. **List every surface the author chose freely**: each shipped file, header and comment field,
   layer (especially unused ones), name, example input, and degree of freedom in the design
   itself (here, the region shapes).
2. **Ask two questions of each, cheaply:**
   - Does it decode as text? Try ASCII at 7 and 8 bits, MSB- and LSB-first, at every offset. If
     there is a natural 2-D shape (here 11×11), try it per row and per column too. The VCD
     message was 7 bits per 11-bit grid row, LSB-first, and a flat stream decode never finds it.
   - Does it look like something when drawn? Render it and actually look. Compare it against
     the author's logo and initials before reading it as anything else.
3. **Do this pass first.** It takes minutes, and it doesn't compete with the deep work if it
   happens before the deep work starts.

Two more lessons:

- **When the data looks odd, ask whether it's the design or the tool** before explaining it
  away. We read the floating net's `"` first as a pun, then as an extraction artifact. It was a
  real layout bug, left in on purpose. Our extractor had it right both times.
- **Matching the example waveform doesn't make a model correct.** A featured writeup's
  simulator reproduced the trace with every tie-high cell wrong. Cross-check against a second
  simulator on inputs the example never exercises.

## As a host: what Jane Street got right

If we ever run our own competition, these are worth copying:

- **A warm-up with full ground truth.** They shipped the same small design at every stage
  (source → netlist → DEF → GDS). Entrants could check their tools before trusting them on the
  real puzzle, and it became our regression test.
- **The right amount of help left in.** Cell names stayed in and net names were stripped, so
  the puzzle was about connectivity rather than cell recognition. The floorplan "islands"
  matched RTL modules: a hint for people who look, invisible to people who don't.
- **An answer that can't be extracted by shortcut.** The answer string was XORed with an LFSR
  keyed on the board, so forcing `success` printed garbage. Even so, someone reverse-engineered
  the LFSR, and that's worth expecting.
- **Eggs in layers of difficulty.** Some come straight out of the solve (the failure messages),
  some need you to look (the logo, "JSC", Morse), and some sit in files people skim (the VCD
  header and inputs). Two of 400+ entrants found all six, which looks about right.
- **Keep your own bugs as eggs.** Their LVS caught a floating wire. They left it in, and
  diagnosing it became a seventh egg.
- **A clear rule on publishing:** private until the close, then actively invited, with a
  follow-up post that links to entrants' writeups. The writeups became their marketing.
- **A results post about approaches, not a leaderboard.** It walks through extraction,
  simulation, logic tracing, impulse response, SAT and the output generator, with the unusual
  entries too (FPGA, Minecraft, SPICE, a ZK proof). It names no ranking, and it doesn't need one.
- **Plan for AI.** They noted that current models can solve it from one prompt in under 30
  minutes. A puzzle hosted today should either accept that and score the writeup and the
  eggs, or be designed to resist it.
