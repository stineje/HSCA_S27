# vivado_syn.tcl - Vivado non-project flow for one generated multiplier.
#
# Driven by environment variables (the Makefile sets them):
#   DESIGN      top module name (== file stem)
#   SRC         Verilog source
#   OUTDIR      where reports go
#   PART        FPGA part (default xc7a100tcsg324-1, Nexys A7-100T)
#   CLK_PERIOD  virtual clock period in ns (default 10.0)
#   MAX_DSP     -1 = let Vivado use DSP48s (default), 0 = LUTs only
#   IMPL        1 = also place & route for real (post-route) timing
#
# Run by hand from the design directory:
#   DESIGN=behav_full_16x16_z32_k0 SRC=behav_full_16x16_z32_k0.v OUTDIR=vivado \
#     vivado -mode batch -nojournal -nolog -source ../../vivado/vivado_syn.tcl

proc envor {name default} {
    if {[info exists ::env($name)] && $::env($name) ne ""} { return $::env($name) }
    return $default
}

set DESIGN  $::env(DESIGN)
set SRC     $::env(SRC)
set OUTDIR  $::env(OUTDIR)
set PART    [envor PART xc7a100tcsg324-1]
set PERIOD  [envor CLK_PERIOD 10.0]
set MAX_DSP [envor MAX_DSP -1]
set IMPL    [envor IMPL 0]

file mkdir $OUTDIR
read_verilog $SRC

# Out-of-context: no I/O buffers, so we time the multiplier itself.
synth_design -top $DESIGN -part $PART -mode out_of_context \
    -flatten_hierarchy rebuilt -max_dsp $MAX_DSP

create_clock -name vclk -period $PERIOD
set_input_delay  0 -clock vclk [all_inputs]
set_output_delay 0 -clock vclk [all_outputs]

if {$IMPL} {
    opt_design
    place_design
    route_design
}

report_utilization            -file $OUTDIR/util.rpt
report_timing -max_paths 1    -file $OUTDIR/timing.rpt
report_timing_summary         -file $OUTDIR/timing_summary.rpt
write_checkpoint -force       $OUTDIR/${DESIGN}.dcp
