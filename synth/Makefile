# HSCA_S27 top-level Makefile
#
#   make help                     list targets
#
# Housekeeping (replaces build_me.sh, clean_me.sh, delete_work_dirs.sh,
# remove.sh, removeDS.sh)
#   make softfloat                build Berkeley SoftFloat-3 + TestFloat-3
#   make softfloat-clean          clean them
#   make tidy                     delete *~, .DS_Store and every work/ dir
#
# Multiplier design-space exploration (see synth/README.md)
#   make gen    ARCH=dadda CORR=vct W=16 K=2     generate one design
#   make error  ARCH=dadda CORR=vct W=8  K=2     error stats (free, uses yosys)
#   make dc     ARCH=dadda CORR=vct W=16 K=2     Design Compiler
#   make vivado ARCH=dadda CORR=vct W=16 K=2     Vivado
#   make sweep  SYN="dc vivado"                  everything below, then results
#   make results                                 synth/results.csv (+ .png)

SHELL   := /bin/bash
PYTHON  ?= python3
SYNTH   := synth
BUILD   := $(SYNTH)/build

# ---- design knobs --------------------------------------------------------
ARCH ?= dadda          # array | dadda | behav
CORR ?= full           # full | cct | vct | hct | trunc (behav only)
W    ?= 8              # square multiplier: X = Y = W
X    ?= $(W)
Y    ?= $(W)
Z    ?= $(W)           # output bits for truncated designs (full forces 2W)
K    ?= 2              # extra columns kept below the output
R    ?= 0.5            # HCT: fraction of variable correction

# ---- sweep knobs ---------------------------------------------------------
SWEEP_W     ?= 8 16
SWEEP_K     ?= 0 1 2 3 4
SWEEP_ARCH  ?= array dadda
SWEEP_CORR  ?= cct vct hct
SYN         ?=                 # e.g. "dc vivado"; empty = error stats only

# ---- tool knobs (passed through to the Tcl scripts) ----------------------
export CLK_PERIOD DC_FLATTEN PART MAX_DSP IMPL
DC_SHELL ?= dc_shell
VIVADO   ?= vivado

strip = $(strip $(1))
GEN = $(PYTHON) $(SYNTH)/gen_mult.py --arch $(call strip,$(ARCH)) --corr $(call strip,$(CORR)) \
      -x $(call strip,$(X)) -y $(call strip,$(Y)) -z $(call strip,$(Z)) \
      -k $(call strip,$(K)) -r $(call strip,$(R))

.PHONY: help softfloat softfloat-clean tidy gen error dc vivado sweep results clean-synth

help:
	@sed -n '2,22p' Makefile | sed 's/^# \{0,1\}//'

# ---- housekeeping --------------------------------------------------------
SF_BUILD := addins/berkeley-softfloat-3/build/Linux-x86_64-GCC
TF_BUILD := addins/berkeley-testfloat-3/build/Linux-x86_64-GCC

softfloat:
	$(MAKE) -C $(SF_BUILD)
	$(MAKE) -C $(TF_BUILD)

softfloat-clean:
	$(MAKE) -C $(SF_BUILD) clean
	$(MAKE) -C $(TF_BUILD) clean

tidy:
	find . -type f -name '*~'        -not -path './.git/*' -print -delete
	find . -type f -name '.DS_Store' -not -path './.git/*' -print -delete
	find . -type d -name work        -not -path './.git/*' -prune -print -exec rm -rf {} +

# ---- one design ----------------------------------------------------------
gen:
	@$(GEN)

error:
	@n=$$($(GEN)) && rm -f $(BUILD)/$$n/error.csv && \
	 $(PYTHON) $(SYNTH)/mult_error.py $(BUILD)/$$n/$$n.v --csv $(BUILD)/$$n/error.csv

dc:
	@n=$$($(GEN)) && cd $(BUILD)/$$n && mkdir -p dc && \
	 DESIGN=$$n SRC=$$n.v OUTDIR=dc $(DC_SHELL) -f ../../dc/dc_syn.tcl > dc/dc.log 2>&1 \
	 && echo "DC     $$n: $$(grep -m1 'Total cell area' dc/area.rpt)" \
	 || { echo "DC failed for $$n, see $(BUILD)/$$n/dc/dc.log"; exit 1; }

vivado:
	@n=$$($(GEN)) && cd $(BUILD)/$$n && mkdir -p vivado && \
	 DESIGN=$$n SRC=$$n.v OUTDIR=vivado $(VIVADO) -mode batch -nojournal -nolog \
	   -source ../../vivado/vivado_syn.tcl > vivado/vivado.log 2>&1 \
	 && echo "Vivado $$n: done" \
	 || { echo "Vivado failed for $$n, see $(BUILD)/$$n/vivado/vivado.log"; exit 1; }

# ---- sweep ---------------------------------------------------------------
# Full multipliers (array, dadda, behav) at each width, then every
# truncated arch x correction x k at each width with Z = W.
sweep:
	@set -e; for w in $(SWEEP_W); do \
	  for a in $(SWEEP_ARCH) behav; do \
	    for t in error $(SYN); do $(MAKE) --no-print-directory $$t ARCH=$$a CORR=full W=$$w; done; \
	  done; \
	  for t in error $(SYN); do $(MAKE) --no-print-directory $$t ARCH=behav CORR=trunc W=$$w K=0; done; \
	  for a in $(SWEEP_ARCH); do for c in $(SWEEP_CORR); do for k in $(SWEEP_K); do \
	    for t in error $(SYN); do $(MAKE) --no-print-directory $$t ARCH=$$a CORR=$$c W=$$w K=$$k; done; \
	  done; done; done; \
	done
	@$(MAKE) --no-print-directory results

results:
	@$(PYTHON) $(SYNTH)/collect.py --plot

clean-synth:
	rm -rf $(BUILD) $(SYNTH)/results.csv $(SYNTH)/results.png
