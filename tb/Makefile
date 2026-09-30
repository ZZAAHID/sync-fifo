# cocotb Makefile — run with:  make            (Icarus Verilog)
#                               make WAVES=1    (also dump sim_build/*.fst)
SIM             ?= icarus
TOPLEVEL_LANG   ?= verilog
VERILOG_SOURCES += $(PWD)/../rtl/sync_fifo.v
COCOTB_TOPLEVEL  = sync_fifo
COCOTB_TEST_MODULES = test_sync_fifo

# override FIFO params from the command line, e.g.  make W=16 D=16
W ?= 8
D ?= 8
COMPILE_ARGS += -Psync_fifo.W=$(W) -Psync_fifo.D=$(D)

include $(shell cocotb-config --makefiles)/Makefile.sim
