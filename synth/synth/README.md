# Multiplier design-space exploration

Sweep the array and Dadda multipliers from `TOOLS/` (full, and truncated with
constant, variable, and hybrid correction) through error analysis, Design
Compiler, and Vivado, and collect everything into one table and plot.

## Quick start

```bash
make error ARCH=dadda CORR=vct W=8 K=2      # error stats, no license needed
make dc    ARCH=dadda CORR=vct W=16 K=2     # Design Compiler
make vivado ARCH=behav CORR=full W=16       # Vivado (will use DSP48s)
make sweep SYN="dc vivado"                  # the whole space -> synth/results.csv/.png
```

`make sweep` with no `SYN` runs only the error analysis, which is quick and free.
Narrow a sweep with `SWEEP_W="8 16" SWEEP_K="0 2 4" SWEEP_ARCH=dadda SWEEP_CORR="vct hct"`.

## Design knobs

| Variable | Meaning | Default |
|---|---|---|
| `ARCH` | `array`, `dadda`, or `behav` (plain `X*Y`, tool picks the implementation) | `dadda` |
| `CORR` | `full`, `cct`, `vct`, `hct`, or `trunc` (`behav` only: exact product, low bits chopped) | `full` |
| `W` | square multiplier width (`X`, `Y` override separately) | `8` |
| `Z` | output bits for truncated designs (`full` always uses `X+Y`) | `W` |
| `K` | extra product columns kept below the output | `2` |
| `R` | HCT: fraction of variable correction | `0.5` |

Each design lands in `synth/build/<name>/`, named
`<arch>_<corr>_<X>x<Y>_z<Z>_k<K>[_r<R>]`, e.g. `dadda_hct_16x16_z16_k2_r0p5`.

## Tool knobs

| Variable | Used by | Meaning | Default |
|---|---|---|---|
| `CLK_PERIOD` | both | virtual clock period, ns | 2.0 (DC), 10.0 (Vivado) |
| `DC_FLATTEN` | DC | `0` keeps the adder-cell hierarchy so you measure the generated architecture; `1` lets DC restructure freely | `0` |
| `PART` | Vivado | FPGA part | `xc7a100tcsg324-1` |
| `MAX_DSP` | Vivado | `0` forces LUT-only; `-1` lets Vivado use DSP48s | `-1` |
| `IMPL` | Vivado | `1` also places and routes for post-route timing | `0` |

**One-time setup for DC:** edit `synth/dc/dc_setup.tcl` (or set `SAED32_LIB`)
to point at your standard-cell library. It defaults to SAED32 RVT, TT corner.

## What gets measured

* **Error** (`mult_error.py`): Yosys flattens the netlist to gates and the
  script simulates them bit-parallel. Exhaustive when `X+Y <= 16`, otherwise
  65,536 random vectors. Error is in output ulps:
  `error = Z * 2^(X+Y-Z) - X*Y`. Full multipliers must report `EXACT`, so
  this doubles as a correctness check on the generators.
* **DC**: total cell area, critical-path delay (input to output), total power.
* **Vivado**: LUTs, DSPs, data-path delay (out-of-context, no I/O buffers).

`mult_error.py` needs `yosys` on your PATH, or `pip install yowasp-yosys` and
`export YOSYS=yowasp-yosys`.

## Things worth having students notice

* Array and Dadda versions of the same correction scheme give identical
  error numbers: same bits kept, same correction, different reduction tree.
  The difference shows up only in area and delay.
* `k=0` vs. `k=2` with CCT: error drops sharply; what does it cost in area?
* Plain truncation (`behav trunc`) is biased low by about half an ulp; the
  correction schemes pull the mean toward zero (HCT closest, at 8x8 with k=2).
* In Vivado, `behav full` maps to DSP48 blocks while the generated trees
  become LUTs. Compare delays, then rerun `behav` with `MAX_DSP=0`.
* `DC_FLATTEN=1` lets DC restructure your Dadda tree. How close does the
  array multiplier get once DC is free to optimize?
