#!/usr/bin/env python3
"""
mult_error.py - measure the error of a (truncated) multiplier netlist.

No commercial license needed: Yosys flattens the design to simple gates,
then this script simulates every gate bit-parallel (one Python int holds
one bit for every test vector), so an 8x8 design is checked exhaustively
in well under a second.

  * x+y <= --exhaustive-limit (default 16): all 2^(x+y) input pairs
  * otherwise: --samples random pairs (default 65536, fixed seed)

Error is reported in ulps of the output: if the design keeps z of the
x+y product bits, 1 ulp = 2^(x+y-z), and
      error = Z * 2^(x+y-z) - X*Y
so a full multiplier must report every metric as exactly 0.

Usage
  mult_error.py build/dadda_cct_8x8_z8_k2/dadda_cct_8x8_z8_k2.v
  mult_error.py design.v --top mymult --csv errors.csv

Requires yosys on PATH (or `pip install yowasp-yosys`, which provides
yowasp-yosys; set YOSYS=yowasp-yosys).
"""
import argparse
import json
import math
import os
import pathlib
import random
import shutil
import subprocess
import sys
import tempfile


def find_yosys():
    for cand in (os.environ.get("YOSYS"), "yosys", "yowasp-yosys"):
        if cand and shutil.which(cand):
            return cand
    sys.exit("mult_error: yosys not found (install it, or pip install yowasp-yosys)")


def netlist(vfile, top):
    # Work next to the design with relative paths: the pip/WASM build of
    # yosys (yowasp-yosys) can only see the current directory tree.
    with tempfile.TemporaryDirectory(dir=vfile.parent) as td:
        out = pathlib.Path(td) / "net.json"
        script = (f"read_verilog {vfile.name}; hierarchy -check -top {top}; proc; flatten; "
                  f"techmap; opt_clean; write_json {out.relative_to(vfile.parent)}")
        r = subprocess.run([find_yosys(), "-q", "-p", script], cwd=vfile.parent,
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"mult_error: yosys failed on {vfile}\n{r.stdout}{r.stderr}")
        return json.loads(out.read_text())["modules"][top]


def pattern_bits(nbits, nvec):
    """Exhaustive patterns: pattern[b] has bit v set iff bit b of v is 1."""
    full = (1 << nvec) - 1
    pats = []
    for b in range(nbits):
        half = 1 << b
        period = half << 1
        block = ((1 << half) - 1) << half              # 0..0 1..1 within one period
        pats.append(block * (full // ((1 << period) - 1)))
    return pats


def sampled_bits(values, nbits):
    pats = [0] * nbits
    for v_idx, val in enumerate(values):
        b = 0
        while val:
            if val & 1:
                pats[b] |= 1 << v_idx
            val >>= 1
            b += 1
    return pats


def simulate(mod, inputs, nvec):
    """inputs: {port_name: [int per bit]}; returns {port_name: [int per bit]} for outputs."""
    mask = (1 << nvec) - 1
    val = {}
    for pname, bits in inputs.items():
        for nid, pv in zip(mod["ports"][pname]["bits"], bits):
            val[nid] = pv

    def get(n):
        if isinstance(n, str):           # yosys constants: "0", "1", "x", "z"
            return mask if n == "1" else 0
        return val[n]

    ops = {
        "$_BUF_":   lambda c: get(c["A"]),
        "$_NOT_":   lambda c: ~get(c["A"]) & mask,
        "$_AND_":   lambda c: get(c["A"]) & get(c["B"]),
        "$_NAND_":  lambda c: ~(get(c["A"]) & get(c["B"])) & mask,
        "$_OR_":    lambda c: get(c["A"]) | get(c["B"]),
        "$_NOR_":   lambda c: ~(get(c["A"]) | get(c["B"])) & mask,
        "$_XOR_":   lambda c: get(c["A"]) ^ get(c["B"]),
        "$_XNOR_":  lambda c: ~(get(c["A"]) ^ get(c["B"])) & mask,
        "$_ANDNOT_": lambda c: get(c["A"]) & ~get(c["B"]) & mask,
        "$_ORNOT_": lambda c: (get(c["A"]) | ~get(c["B"])) & mask,
        "$_MUX_":   lambda c: (get(c["A"]) & ~get(c["S"]) | get(c["B"]) & get(c["S"])) & mask,
    }

    # topological evaluation: repeat passes until every cell is evaluated
    pending = []
    for name, cell in mod["cells"].items():
        if cell["type"] == "$scopeinfo":     # hierarchy bookkeeping left by flatten
            continue
        if cell["type"] not in ops:
            sys.exit(f"mult_error: unsupported cell {cell['type']} ({name})")
        conn = {k: v[0] for k, v in cell["connections"].items()}
        out = "Y"
        ins = [conn[k] for k in conn if k != out]
        pending.append((cell["type"], conn, ins, conn[out]))

    while pending:
        nxt = []
        for typ, conn, ins, out in pending:
            if all(isinstance(i, str) or i in val for i in ins):
                val[out] = ops[typ](conn)
            else:
                nxt.append((typ, conn, ins, out))
        if len(nxt) == len(pending):
            sys.exit("mult_error: combinational loop or undriven net")
        pending = nxt

    outs = {}
    for pname, p in mod["ports"].items():
        if p["direction"] == "output":
            outs[pname] = [get(n) for n in p["bits"]]
    return outs


def words(bitints, nvec):
    """Transpose per-bit ints back to one integer per test vector."""
    res = [0] * nvec
    for b, bi in enumerate(bitints):
        s = format(bi, f"0{nvec}b")[::-1]
        w = 1 << b
        for v, ch in enumerate(s):
            if ch == "1":
                res[v] += w
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("vfile")
    ap.add_argument("--top", help="top module (default: file stem)")
    ap.add_argument("--samples", type=int, default=65536)
    ap.add_argument("--exhaustive-limit", type=int, default=16,
                    help="run exhaustively when x+y <= this (default 16)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--csv", help="append one result row to this CSV")
    a = ap.parse_args()

    vfile = pathlib.Path(a.vfile).resolve()
    top = a.top or vfile.stem
    mod = netlist(vfile, top)

    ports = mod["ports"]
    outs = [p for p, d in ports.items() if d["direction"] == "output"]
    if "X" not in ports or "Y" not in ports or len(outs) != 1:
        sys.exit("mult_error: expected inputs X, Y and one output")
    xb, yb, zb = len(ports["X"]["bits"]), len(ports["Y"]["bits"]), len(ports[outs[0]]["bits"])

    if xb + yb <= a.exhaustive_limit:
        mode, nvec = "exhaustive", 1 << (xb + yb)
        pats = pattern_bits(xb + yb, nvec)
        xbits, ybits = pats[:xb], pats[xb:]
        xs = [v & ((1 << xb) - 1) for v in range(nvec)]
        ys = [v >> xb for v in range(nvec)]
    else:
        mode, nvec = f"sampled({a.samples})", a.samples
        rng = random.Random(a.seed)
        xs = [rng.getrandbits(xb) for _ in range(nvec)]
        ys = [rng.getrandbits(yb) for _ in range(nvec)]
        xbits, ybits = sampled_bits(xs, xb), sampled_bits(ys, yb)

    zbits = simulate(mod, {"X": xbits, "Y": ybits}, nvec)[outs[0]]
    zs = words(zbits, nvec)

    ulp = 1 << (xb + yb - zb)
    errs = [(z * ulp - x * y) / ulp for x, y, z in zip(xs, ys, zs)]
    mean = sum(errs) / nvec
    var = sum((e - mean) ** 2 for e in errs) / nvec
    row = {
        "design": top, "x": xb, "y": yb, "z": zb, "mode": mode,
        "mean_ulp": mean, "max_ulp": max(errs), "min_ulp": min(errs),
        "max_abs_ulp": max(abs(e) for e in errs), "rms_ulp": math.sqrt(sum(e * e for e in errs) / nvec),
        "var_ulp2": var, "exact": all(e == 0 for e in errs),
    }

    print(f"{top}: {xb}x{yb} -> {zb} bits, {mode}")
    if row["exact"]:
        print("  EXACT: every output matches X*Y")
    else:
        print(f"  mean {mean:+.4f}  min {row['min_ulp']:+.4f}  max {row['max_ulp']:+.4f}  "
              f"rms {row['rms_ulp']:.4f}  var {var:.4f}   (ulps)")

    if a.csv:
        new = not os.path.exists(a.csv)
        with open(a.csv, "a") as f:
            if new:
                f.write(",".join(row) + "\n")
            f.write(",".join(f"{v:.6g}" if isinstance(v, float) else str(v) for v in row.values()) + "\n")


if __name__ == "__main__":
    main()
