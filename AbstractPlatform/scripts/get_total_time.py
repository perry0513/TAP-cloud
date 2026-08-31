#!/usr/bin/env python3
"""Produce the model-statistics table from the proof sources and run artifacts.

Emits the LaTeX body of `tab:model-stats` in the paper: for each model or proof,
the number of procedures, uninterpreted functions, verification annotations and
lines, together with the verification time.

Sizes are counted from the .ucl sources, following the paper's conventions:
non-blank lines (comments included), `procedure` and `function` declarations
at the start of a line, and `ensures` + `invariant` for annotations, which is the
caption's "postconditions and loop/global invariants".  The proof rows count the
harness only, not the per-operation case-split step files, which is why their
procedure and function counts are zero; --verbose reports those separately.  Times come from a completed run:
`gen-chk/<proof>-<split>/` holds gen.time (SMT generation, CPU seconds) and
results.csv (per-obligation solver CPU time), both written by proofs/Makefile; the STAP row uses
modules/smt/ from `make -C modules tap-smt`.  Verification time is the sum
of the two, matching the paper's definition.

    python3 scripts/get_total_time.py              # LaTeX table
    python3 scripts/get_total_time.py --plain      # aligned text
    python3 scripts/get_total_time.py --verbose    # per-file and per-split detail
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # .../AbstractPlatform
MODULES, PROOFS = ROOT / "modules", ROOT / "proofs"

# A row is (label, source files, artifact directories).
def _g(pattern, base):
    return sorted(base.glob(pattern))

ROWS = [
    ("STAP",
     [ROOT.parent / "Common/common-types.ucl", MODULES / "ap-types.ucl",
      MODULES / "tap-mod-cache.ucl", MODULES / "tap-mod-cpu.ucl",
      *(_g("tap-mod-destroy.ucl", MODULES) + _g("tap-mod-enter.ucl", MODULES) +
        _g("tap-mod-exit.ucl", MODULES) + _g("tap-mod-launch.ucl", MODULES) +
        _g("tap-mod-pause.ucl", MODULES) + _g("tap-mod-resume.ucl", MODULES) +
        _g("tap-mod-block-memory-region.ucl", MODULES) +
        _g("tap-mod-release-memory-region.ucl", MODULES) +
        _g("tap-mod-load-storage.ucl", MODULES) + _g("tap-mod-store-storage.ucl", MODULES) +
        _g("tap-mod-kms.ucl", MODULES) + _g("tap-mod-tamper-storage.ucl", MODULES) +
        _g("tap-mod-replay-storage.ucl", MODULES)),
      MODULES / "tap-mod.ucl", PROOFS / "proof-common.ucl"],
     [MODULES / "smt"]),

    ("Measurement",
     [MODULES / "measure.ucl", PROOFS / "measurement-proof.ucl"],
     [PROOFS / "gen-chk/measurement"]),

    ("Integrity",
     [PROOFS / "integrity-proof.ucl", PROOFS / "integrity-proof-init.ucl",
      PROOFS / "integrity-proof-init-stub.ucl", PROOFS / "integrity-proof-next.ucl",
      MODULES / "tap-mod-integrity.ucl"],
     _g("gen-chk/integrity-*", PROOFS)),

    ("Mem. Conf.",
     [PROOFS / "mem-conf-proof.ucl", PROOFS / "mem-conf-proof-init.ucl",
      PROOFS / "mem-conf-proof-init-stub.ucl", MODULES / "tap-mod-conf.ucl"],
     _g("gen-chk/conf-*", PROOFS)),
]

# The per-operation step files define each case split's transition relation.
# The paper's table does not count them -- its proof rows show zero procedures --
# so they are reported only under --verbose, for completeness.
STEP_FILES = {
    "Integrity":  _g("tap-mod-integrity/*.ucl", MODULES),
    "Mem. Conf.": _g("tap-mod-conf/*.ucl", MODULES),
}

# tap-mod-cpu.ucl is the inherited TAP CPU model, not part of the TAP-cloud
# extension, so its procedures and lines are not counted in the STAP row.  Its
# annotations still are: they constrain the model the proofs rely on.
SIZE_EXCLUDED = {"tap-mod-cpu.ucl"}

PROC = re.compile(r"^\s*procedure\b")
FUNC = re.compile(r"^\s*function\s+\w+\s*\(")   # declaration, not a module import
ANNOT = re.compile(r"^\s*(ensures|invariant)\b")
COMMENT = re.compile(r"^\s*//")
BLANK = re.compile(r"^\s*$")


def measure(files):
    """Count procedures, uninterpreted functions, annotations and code lines."""
    pr = fn = an = ln = 0
    per_file = []
    for f in files:
        if not f.exists():
            continue
        a = b = c = d = 0
        skip_size = f.name in SIZE_EXCLUDED
        for line in f.read_text().splitlines():
            if BLANK.match(line):
                continue
            if not skip_size:
                d += 1                  # non-blank lines, comments included
            if COMMENT.match(line):
                continue
            if PROC.match(line) and not skip_size:
                a += 1
            elif FUNC.match(line):
                b += 1
            elif ANNOT.match(line):
                c += 1
        pr, fn, an, ln = pr + a, fn + b, an + c, ln + d
        per_file.append((f, a, b, c, d))
    return pr, fn, an, ln, per_file


def newest_source_mtime(files):
    return max((f.stat().st_mtime for f in files if f.exists()), default=0.0)


def timing(dirs):
    """Generation time + solver time, in seconds, over a set of artifact dirs."""
    gen = solve = 0.0
    n_obl = 0
    missing = []
    per_dir = []
    for d in dirs:
        if not d.is_dir():
            missing.append(d)
            continue
        g = 0.0
        t = d / "gen.time"
        if t.exists():
            try:                        # "%U %S" -> user + sys CPU seconds
                g = sum(float(x) for x in t.read_text().split())
            except (ValueError, IndexError):
                pass
        s, k = 0.0, 0
        csv_path = d / "results.csv"
        if csv_path.exists():
            with csv_path.open() as fh:
                for row in csv.DictReader(fh):
                    k += 1
                    try:
                        s += float(row["time_sec"])
                    except (KeyError, ValueError):
                        pass
        else:
            missing.append(d)
        gen, solve, n_obl = gen + g, solve + s, n_obl + k
        per_dir.append((d.name, g, s, k))
    return gen, solve, n_obl, missing, per_dir


def artifacts_mtime(dirs):
    ts = []
    for d in dirs:
        c = d / "results.csv"
        if c.exists():
            ts.append(c.stat().st_mtime)
    return min(ts) if ts else 0.0


def main(argv):
    plain = "--plain" in argv
    verbose = "--verbose" in argv
    rows, all_missing, stale = [], [], []

    for label, files, dirs in ROWS:
        pr, fn, an, ln, per_file = measure(files)
        gen, solve, n_obl, missing, per_dir = timing(dirs)
        all_missing += missing
        a_t, s_t = artifacts_mtime(dirs), newest_source_mtime(files)
        if a_t and s_t and a_t < s_t:
            stale.append(label)
        rows.append((label, pr, fn, an, ln, gen + solve, n_obl))
        if verbose:
            print(f"# {label}")
            for f, a, b, c, d in per_file:
                mark = "  (pr/ln excluded)" if f.name in SIZE_EXCLUDED else ""
            print(f"#   {f.relative_to(ROOT.parent)!s:<58} pr={a:<3} fn={b:<3} an={c:<4} ln={d}{mark}")
            for name, g, s, k in per_dir:
                print(f"#   {name:<58} gen={g:7.1f}s solve={s:8.1f}s obl={k}")
            if label in STEP_FILES:
                spr, sfn, san, sln, _ = measure(STEP_FILES[label])
                print(f"#   [not counted in the table: {len(STEP_FILES[label])} case-split step "
                      f"files, pr={spr} fn={sfn} an={san} ln={sln}]")
            print()

    if plain or verbose:
        print(f"{'Model/Proof':<14}{'#pr':>5}{'#fn':>5}{'#an':>6}{'#ln':>7}"
              f"{'Verif.(s)':>11}{'#obl':>8}")
        for label, pr, fn, an, ln, t, n in rows:
            print(f"{label:<14}{pr:>5}{fn:>5}{an:>6}{ln:>7}{t:>11.0f}{n:>8}")
        print(f"{'TOTAL':<14}{'':>5}{'':>5}{'':>6}"
              f"{sum(r[4] for r in rows):>7}{sum(r[5] for r in rows):>11.0f}"
              f"{sum(r[6] for r in rows):>8}")
    else:
        print(r"\begin{tabular}{lrrrrr}")
        print(r"\hline")
        print(r"\multirow{2}{*}{\textbf{Model/Proof}} & \multicolumn{4}{c}{\textbf{Size}}"
              r" & \textbf{Verif.} \\")
        print(r" & \textbf{\#pr} & \textbf{\#fn} & \textbf{\#an} & \textbf{\#ln}"
              r" & \textbf{Time} \\")
        print(r"\hline")
        for label, pr, fn, an, ln, t, _ in rows:
            print(f"{label} & {pr} & {fn} & {an} & {ln} & {t:.0f} \\\\")
        print(r"\hline")
        print(r"\end{tabular}")

    if stale:
        print(f"\n! Stale artifacts (older than the sources): {', '.join(stale)}",
              file=sys.stderr)
        print("! Those verification times do not describe the current model.",
              file=sys.stderr)

    if all_missing:
        names = ", ".join(str(d.relative_to(ROOT)) for d in all_missing)
        print(f"\n! No run artifacts for: {names}", file=sys.stderr)
        print("! Times above are incomplete.  Regenerate with:", file=sys.stderr)
        print("!   make -C proofs check-all  &&  make -C modules tap-smt",
              file=sys.stderr)
        return 1
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
