#!/usr/bin/env python3
"""
collect.py - gather every design under synth/build/ into one results table.

For each design directory it reads (whatever exists):
  error.csv          from mult_error.py   -> error statistics in ulps
  dc/area.rpt        Design Compiler      -> total cell area
  dc/timing.rpt      Design Compiler      -> critical-path data arrival time (ns)
  dc/power.rpt       Design Compiler      -> total power
  vivado/util.rpt    Vivado               -> LUTs, DSPs
  vivado/timing.rpt  Vivado               -> data path delay (ns)

Writes synth/results.csv and prints a summary table. With --plot (needs
matplotlib) it also saves synth/results.png: area vs. RMS error for the
truncated designs, one series per correction scheme.
"""
import argparse
import csv
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
NAME_RE = re.compile(r"^(array|dadda|behav)_(\w+?)_(\d+)x(\d+)_z(\d+)_k(\d+)(?:_r(\w+))?$")


def grab(path, pattern, cast=float, flags=0):
    if not path.exists():
        return ""
    m = re.search(pattern, path.read_text(errors="replace"), flags)
    return cast(m.group(1)) if m else ""


def dc_power(path):
    """Total power in mW (DC prints its own units, so normalize)."""
    if not path.exists():
        return ""
    m = re.search(r"^Total\s+.*?\s([\d.eE+-]+)\s+(pW|nW|uW|mW|W)\s*$",
                  path.read_text(errors="replace"), re.M)
    if not m:
        return ""
    scale = {"pW": 1e-9, "nW": 1e-6, "uW": 1e-3, "mW": 1.0, "W": 1e3}[m.group(2)]
    return float(m.group(1)) * scale


def read_error(path):
    if not path.exists():
        return {}
    with open(path) as f:
        rows = list(csv.DictReader(f))
    return rows[-1] if rows else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default=str(HERE / "build"))
    ap.add_argument("--out", default=str(HERE / "results.csv"))
    ap.add_argument("--plot", action="store_true")
    a = ap.parse_args()

    rows = []
    for d in sorted(pathlib.Path(a.build).iterdir()):
        m = NAME_RE.match(d.name)
        if not d.is_dir() or not m:
            continue
        arch, corr, x, y, z, k, r = m.groups()
        err = read_error(d / "error.csv")
        rows.append({
            "design": d.name, "arch": arch, "corr": corr, "x": x, "y": y, "z": z, "k": k,
            "r": (r or "").replace("p", "."),
            "exact": err.get("exact", ""),
            "mean_ulp": err.get("mean_ulp", ""), "rms_ulp": err.get("rms_ulp", ""),
            "max_abs_ulp": err.get("max_abs_ulp", ""), "var_ulp2": err.get("var_ulp2", ""),
            "dc_area": grab(d / "dc/area.rpt", r"Total cell area:\s+([\d.]+)"),
            "dc_delay_ns": grab(d / "dc/timing.rpt", r"data arrival time\s+([\d.]+)"),
            "dc_power_mW": dc_power(d / "dc/power.rpt"),
            "fpga_luts": grab(d / "vivado/util.rpt", r"\|\s*(?:Slice|CLB) LUTs\*?\s*\|\s*(\d+)", int),
            "fpga_dsps": grab(d / "vivado/util.rpt", r"\|\s*DSPs\s*\|\s*(\d+)", int),
            "fpga_delay_ns": grab(d / "vivado/timing.rpt", r"Data Path Delay:\s+([\d.]+)ns"),
        })

    if not rows:
        print(f"collect: no designs in {a.build} (run `make sweep` first)")
        return

    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    cols = ["design", "rms_ulp", "max_abs_ulp", "dc_area", "dc_delay_ns", "fpga_luts", "fpga_dsps", "fpga_delay_ns"]
    def fmt(v):
        if v == "":
            return "-"
        try:
            return f"{float(v):.4g}"
        except ValueError:
            return str(v)

    table = [cols] + [[fmt(r[c]) for c in cols] for r in rows]
    widths = [max(len(row[i]) for row in table) for i in range(len(cols))]
    for row in table:
        print("  ".join(v.ljust(wd) for v, wd in zip(row, widths)))
    print(f"\nwrote {a.out}")

    if a.plot:
        plot(rows, pathlib.Path(a.out).with_suffix(".png"))


def plot(rows, out):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("collect: matplotlib not installed, skipping plot")
        return
    pts = [r for r in rows if r["dc_area"] != "" and r["rms_ulp"] != "" and r["exact"] != "True"]
    if not pts:
        print("collect: need DC area + error data for truncated designs to plot")
        return
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for key in sorted({(int(r["x"]), r["arch"], r["corr"]) for r in pts}):
        s = [r for r in pts if (int(r["x"]), r["arch"], r["corr"]) == key]
        ax.scatter([float(r["dc_area"]) for r in s], [float(r["rms_ulp"]) for r in s],
                   label=f"{key[0]}-bit {key[1]} {key[2].upper()}")
        for r in s:
            ax.annotate(f"k={r['k']}", (float(r["dc_area"]), float(r["rms_ulp"])),
                        fontsize=7, xytext=(3, 3), textcoords="offset points")
    ax.set_xlabel("DC cell area")
    ax.set_ylabel("RMS error (ulps)")
    ax.set_title("Truncated multipliers: area vs. error")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="best")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
