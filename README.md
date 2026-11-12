# HSCA_S27 — High-Speed Computer Arithmetic, Spring 2027

SystemVerilog designs, testbenches, generators, and reference material for
High-Speed Computer Arithmetic at the University of Nebraska-Lincoln. Everything
here is meant to be simulated, synthesized, and measured, not just read.

## Contents

| Folder | What's in it |
|---|---|
| [`SV/`](SV) | SystemVerilog starter examples and the *Digital Design and Computer Architecture (RISC-V)* HDL companion |
| [`TOOLS/`](TOOLS) | Generators for array and Dadda multipliers of any size, including truncated multipliers with constant, variable, and hybrid correction |
| [`synth/`](synth) | Design-space sweep: error analysis, Design Compiler, and Vivado results for the generated multipliers |
| [`addins/`](addins) | Berkeley SoftFloat-3 and TestFloat-3, the reference IEEE 754 model and test-vector generator |
| [`Xilinx/`](Xilinx) | Xilinx DSP48E1 guide and arithmetic app notes, with their Verilog/VHDL sources |
| [`papers/`](papers) | Standards (IEEE 754-1985/2019, SystemVerilog 1800-2017) and classic papers on adders and multipliers |
| [`summary/`](summary) | Weekly lecture summaries |

## Quick start

Clone the repo, then run the first example in Questa (ModelSim):

```bash
git clone https://github.com/stineje/HSCA_S27.git
cd HSCA_S27/SV/sample
vsim -c -do sample.do        # drop -c to open the GUI with waveforms
```

The transcript ends with the test count and `0 errors`, and every vector
is logged to `sample.out`.

Every example folder works the same way: `cd` into it and run its `.do` file.

<details>
<summary>Using VCS or Verilator instead</summary>

```bash
# Synopsys VCS
vcs -sverilog -full64 sample.sv tb_sample.sv && ./simv

# Verilator 5 (free; needs --timing for the # delays in the testbench)
verilator --binary --timing -Wno-fatal --top-module stimulus sample.sv tb_sample.sv
./obj_dir/Vstimulus
```

`std::randomize` is fully supported in Questa and VCS. Verilator supports a
subset, so if it complains, use `$urandom` instead.
</details>

## SystemVerilog examples (`SV/`)

| Example | What it shows |
|---|---|
| `SV/silly` | The smallest complete flow: a one-line combinational module, a testbench, and a `.do` file with waveforms |
| `SV/sample` | A **self-checking** testbench: random stimulus with `std::randomize`, a golden model computed in the testbench, an error count, and a results file (`sample.out`) |
| `SV/DDCArv_HDL_Companion` | Every HDL example from Harris & Harris *DDCA RISC-V*, numbered by figure (`0423-fulladder.sv` is Example 4.23), in both SystemVerilog and VHDL |

Highlights from the companion that this course builds on:
`0433a/b` unsigned and signed multipliers, `0434-mux_param` parameterized
modules, `0437`–`0439` three testbench styles (manual, clocked, and
vector-file driven), and `0501`–`0503` adders, subtractors, and comparators.

### Writing your own

Start a new design by copying `SV/sample`, which is already set up the way
your assignments should be:

```bash
cp -r SV/sample SV/my_adder
cd SV/my_adder
# rename sample.sv / tb_sample.sv, then update the vlog and vsim lines in the .do file
```

A testbench for this class should be **self-checking**, like `tb_sample.sv`:

```systemverilog
@(negedge clk) begin
  z_correct = a + b;                       // golden model
  if (z !== z_correct) begin
    errors++;
    $display("a=%h b=%h  got %h, expected %h", a, b, z, z_correct);
  end
end
...
$display("%0d tests completed with %0d errors", vectornum, errors);
```

Apply inputs on one clock edge and check on the other, compare against a
golden model rather than eyeballing waveforms, and always print a final
error count. For floating-point designs, the golden model is SoftFloat and
the vectors come from TestFloat (see below).

### Style conventions

* Use `logic`, not `reg`/`wire`.
* Use `always_comb` for combinational logic and `always_ff @(posedge clk)` for
  registers, never a bare `always`.
* Connect ports by name (`.a(a)`) once a module has more than three ports.
* Put one module per file, with the file named after the module.
* Parameterize widths (`parameter int WIDTH = 32`) instead of hard-coding them.
* Compare with `!==` in testbenches so `x` and `z` count as errors.

## Multiplier generators (`TOOLS/`)

Perl scripts generate structural Verilog multipliers of any size:

```bash
cd TOOLS
perl array_sv.pl -x 8 -y 8 -m mult8            # array multiplier, SystemVerilog
perl dadda_v_VCT.pl -x 16 -y 16 -z 16 -k 2     # 16x16 Dadda, truncated to 16 bits, variable correction
```

Generated designs use the full-adder and half-adder cells in `TOOLS/tadders.v`.
See [`TOOLS/README.md`](TOOLS/README.md) for the truncation schemes.

## Design-space exploration (`synth/`)

Generate, check, and synthesize any multiplier with one command from the repo root:

```bash
make error  ARCH=dadda CORR=vct W=8 K=2     # error statistics, no license needed
make dc     ARCH=dadda CORR=vct W=16 K=2    # Design Compiler area, delay, power
make vivado ARCH=behav CORR=full W=16       # Vivado LUTs, DSPs, delay
make sweep  SYN="dc vivado"                 # everything -> synth/results.csv and results.png
```

Full multipliers are checked against `X*Y`, so this also verifies the
generators. Details and suggested experiments are in
[`synth/README.md`](synth/README.md).

## IEEE 754 reference (`addins/`)

```bash
make softfloat                                       # build SoftFloat and TestFloat
addins/berkeley-testfloat-3/build/Linux-x86_64-GCC/testfloat_gen f32_add | head
```

`testfloat_gen` prints one test per line in hex: the operands, the
correctly rounded result, and the exception flags:

```
00000000 3C072C85 3C072C85 00
```

Read them into your testbench with `$fscanf` or `$readmemh` to verify
floating-point hardware against the reference model.

## Housekeeping

| Command | Does |
|---|---|
| `make help` | List all targets |
| `make softfloat` / `make softfloat-clean` | Build or clean SoftFloat and TestFloat |
| `make tidy` | Delete `*~`, `.DS_Store`, and every simulator `work/` directory |
| `make clean-synth` | Remove all generated multipliers and results |

The older `build_me.sh`, `clean_me.sh`, `delete_work_dirs.sh`, `remove.sh`,
and `removeDS.sh` do the same jobs as the `make` targets.

## Tools

| Tool | Used for |
|---|---|
| Questa / ModelSim | Simulation (`.do` files) |
| Synopsys VCS | Simulation (alternative) |
| Synopsys Design Compiler | ASIC synthesis (`make dc`) |
| AMD Vivado | FPGA synthesis (`make vivado`) |
| Verilator, Yosys | Free alternatives for simulation, linting, and error analysis |
| Perl, Python 3, GCC | Generators, scripts, SoftFloat |

## SystemVerilog Practice

[HDLBits](https://hdlbits.01xz.net/wiki/Main_Page) provides short
Verilog exercises with automatic feedback. The exercises reinforce
RTL concepts we’ll use in SystemVerilog.

Before the first arithmetic lab, try these in order:

1. [Vectors](https://hdlbits.01xz.net/wiki/Vector0) — work with multi-bit signals.
2. [Full adder](https://hdlbits.01xz.net/wiki/Fadd) — practice sum and carry logic.
3. [4-bit binary adder](https://hdlbits.01xz.net/wiki/Adder) — connect full adders to build a ripple-carry adder.

## Digital Logic and Computer Arithmetic

- **MIT Computation Structures** — Review logic gates, combinational and sequential circuits, and finite-state machines. Start with combinational logic before the first RTL lab and revisit sequential logic before the first pipelined design. [MIT OpenCourseWare](https://ocw.mit.edu/courses/6-004-computation-structures-spring-2017/)
- **Logisim-evolution** — Build a full adder, chain four together, and toggle the inputs to see how carry propagates. [Logisim-evolution](https://github.com/logisim-evolution/logisim-evolution)
- **MIT Arithmetic Circuits** — Compare ripple-carry and carry-lookahead adders and see how propagation delay scales with operand width. [MIT Arithmetic Circuits (PDF)](https://courses.csail.mit.edu/6.896/spring04/handouts/arithmetic-ckts.pdf)

**Suggested pre-lab activity.** Build a 4-bit ripple-carry adder in Logisim-evolution and trace the carry path in the schematic. Then describe the same hardware in RTL using the [HDLBits 4-bit adder exercise](https://hdlbits.01xz.net/wiki/Adder).

## License

See [LICENSE](LICENSE). Third-party material in `addins/`, `Xilinx/`,
`papers/`, and `SV/DDCArv_HDL_Companion/` remains under its original
authors' terms.

