#!/usr/bin/env python3
"""
gen_mult.py - wrap the TOOLS/ Perl multiplier generators so every design
comes out with a predictable name, a self-contained .v file (adder cells
from tadders.v appended), and a matching directory under synth/build/.

Design name:  <arch>_<corr>_<X>x<Y>_z<Z>_k<K>[_r<R>]
  arch : array | dadda | behav
  corr : full  (no truncation, z = x+y)
         cct   (constant correction,  Schulte/Swartzlander)
         vct   (variable correction,  King/Swartzlander)
         hct   (hybrid correction,    Stine/Duverne; needs -r)
         trunc (behav only: exact product with the low bits chopped)

Examples
  gen_mult.py --arch dadda --corr full -x 16 -y 16
  gen_mult.py --arch array --corr vct  -x 16 -y 16 -z 16 -k 2
  gen_mult.py --arch dadda --corr hct  -x 16 -y 16 -z 16 -k 2 -r 0.5
  gen_mult.py --arch behav --corr full -x 16 -y 16      # lets DC/Vivado pick (DesignWare / DSP48)

Prints the design name on stdout so Makefiles can capture it.
"""
import argparse
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
TOOLS = REPO / "TOOLS"
CELLS = TOOLS / "tadders.v"

# which Perl script implements each (arch, corr) pair
SCRIPTS = {
    ("array", "full"): "array_v_CCT.pl",   # CCT with z=x+y, k=0 -> correction constant 0 -> exact
    ("array", "cct"):  "array_v_CCT.pl",
    ("array", "vct"):  "array_v_VCT.pl",
    ("array", "hct"):  "array_v_HCT.pl",
    ("dadda", "full"): "dadda_v_CCT.pl",
    ("dadda", "cct"):  "dadda_v_CCT.pl",
    ("dadda", "vct"):  "dadda_v_VCT.pl",
    ("dadda", "hct"):  "dadda_v_HCT.pl",
}


def design_name(a):
    name = f"{a.arch}_{a.corr}_{a.x}x{a.y}_z{a.z}_k{a.k}"
    if a.corr == "hct":
        name += "_r" + str(a.r).replace(".", "p")
    return name


def behav_verilog(name, a):
    shift = a.x + a.y - a.z
    return f"""// Behavioral reference: lets the synthesis tool choose the implementation
// (DesignWare in DC, DSP48 in Vivado). corr={a.corr}
module {name} (Z, X, Y);
  input  [{a.x-1}:0] X;
  input  [{a.y-1}:0] Y;
  output [{a.z-1}:0] Z;
  wire   [{a.x+a.y-1}:0] P = X * Y;
  assign Z = P[{a.x+a.y-1}:{shift}];
endmodule
"""


def perl_verilog(name, a):
    script = TOOLS / SCRIPTS[(a.arch, a.corr)]
    cmd = ["perl", str(script), "-x", str(a.x), "-y", str(a.y),
           "-z", str(a.z), "-k", str(a.k), "-m", name]
    if a.corr == "hct":
        cmd += ["-r", str(a.r)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    text = res.stdout
    if res.returncode != 0 or "module" not in text:
        sys.exit(f"gen_mult: {' '.join(cmd)} failed:\n{text}{res.stderr}")
    # Some generators ignore -m and invent their own name; force ours on the
    # first (top) module so every flow can rely on TOP == design name.
    text = re.sub(r"^module\s+\w+", f"module {name}", text, count=1, flags=re.M)
    return text + "\n// ---- adder cells from TOOLS/tadders.v ----\n" + CELLS.read_text()


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--arch", required=True, choices=["array", "dadda", "behav"])
    p.add_argument("--corr", required=True, choices=["full", "cct", "vct", "hct", "trunc"])
    p.add_argument("-x", type=int, required=True)
    p.add_argument("-y", type=int, required=True)
    p.add_argument("-z", type=int, help="output bits (default x+y)")
    p.add_argument("-k", type=int, default=0, help="extra columns kept below the output (default 0)")
    p.add_argument("-r", type=float, default=0.5, help="HCT: fraction of variable correction")
    p.add_argument("-o", "--outdir", default=str(HERE / "build"))
    a = p.parse_args()

    if a.z is None:
        a.z = a.x + a.y
    if a.corr == "full":
        a.z, a.k = a.x + a.y, 0
    if a.z + a.k > a.x + a.y:
        sys.exit("gen_mult: need z + k <= x + y")
    if a.arch == "behav" and a.corr not in ("full", "trunc"):
        sys.exit("gen_mult: behav supports --corr full or trunc")
    if a.arch != "behav" and a.corr == "trunc":
        sys.exit("gen_mult: --corr trunc is only for --arch behav")

    name = design_name(a)
    d = pathlib.Path(a.outdir) / name
    d.mkdir(parents=True, exist_ok=True)
    src = behav_verilog(name, a) if a.arch == "behav" else perl_verilog(name, a)
    (d / f"{name}.v").write_text(src)
    print(name)


if __name__ == "__main__":
    main()
