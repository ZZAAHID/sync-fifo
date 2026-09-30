"""cocotb testbench for sync_fifo.

Tests
  1. test_reset          - flags after reset
  2. test_fill_and_drain - write D items (full), try overflow, read all back in order, try underflow
  3. test_simultaneous   - read and write in the same cycle keeps count steady
  4. test_random         - random wr_en/rd_en for many cycles, checked against a Python reference model
"""
import random
from collections import deque

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge


def params(dut):
    return int(dut.W.value), int(dut.D.value)


async def setup(dut):
    """Start the clock and apply reset."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)


async def reset(dut):
    """Hold rst_n low for 3 cycles, release on a falling edge."""
    await FallingEdge(dut.clk)
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    dut.din.value = 0
    dut.rst_n.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1


async def cycle(dut, wr=0, rd=0, data=0):
    """Drive inputs on the falling edge, return after the next rising edge settles."""
    await FallingEdge(dut.clk)
    dut.wr_en.value = wr
    dut.rd_en.value = rd
    dut.din.value = data
    await RisingEdge(dut.clk)
    await ReadOnly()


@cocotb.test()
async def test_reset(dut):
    await setup(dut)
    await ReadOnly()
    assert dut.empty.value == 1, "FIFO should be empty after reset"
    assert dut.full.value == 0, "FIFO should not be full after reset"


@cocotb.test()
async def test_fill_and_drain(dut):
    W, D = params(dut)
    await setup(dut)
    data = [random.getrandbits(W) for _ in range(D)]

    # fill
    for i, x in enumerate(data):
        await cycle(dut, wr=1, data=x)
        assert dut.empty.value == 0
        assert dut.full.value == (1 if i == D - 1 else 0), f"full wrong after {i+1} writes"

    # overflow write must be ignored
    await cycle(dut, wr=1, data=(~data[0]) & ((1 << W) - 1))
    assert dut.full.value == 1, "overflow write changed state"

    # drain, check order (dout is registered: valid right after the read edge)
    for i, x in enumerate(data):
        await cycle(dut, rd=1)
        got = int(dut.dout.value)
        assert got == x, f"read {i}: expected {x:#x}, got {got:#x}"
        assert dut.full.value == 0
        assert dut.empty.value == (1 if i == D - 1 else 0), f"empty wrong after {i+1} reads"

    # underflow read must be ignored (dout holds its last value)
    last = int(dut.dout.value)
    await cycle(dut, rd=1)
    assert dut.empty.value == 1
    assert int(dut.dout.value) == last, "underflow read changed dout"
    dut._log.info("fill/drain OK: %d entries, overflow and underflow ignored", D)


@cocotb.test()
async def test_simultaneous(dut):
    W, D = params(dut)
    await setup(dut)
    model = deque()

    # half fill
    for _ in range(D // 2):
        x = random.getrandbits(W)
        model.append(x)
        await cycle(dut, wr=1, data=x)

    # read + write every cycle: occupancy must stay at D/2
    for _ in range(4 * D):
        x = random.getrandbits(W)
        exp = model.popleft()
        model.append(x)
        await cycle(dut, wr=1, rd=1, data=x)
        assert int(dut.dout.value) == exp
        assert int(dut.count.value) == D // 2
        assert dut.full.value == 0 and dut.empty.value == 0

    # also: write+read when EMPTY -> only the write happens
    await reset(dut)
    await cycle(dut, wr=1, rd=1, data=0x5A & ((1 << W) - 1))
    assert int(dut.count.value) == 1, "wr+rd on empty: only write should happen"


@cocotb.test()
async def test_random(dut):
    """Random traffic vs. a Python queue model."""
    W, D = params(dut)
    await setup(dut)
    random.seed(1234)
    model = deque()
    n_wr = n_rd = 0

    for _ in range(2000):
        wr = random.random() < 0.55
        rd = random.random() < 0.45
        x = random.getrandbits(W)

        # what the DUT should do this cycle (based on state before the edge)
        do_wr = wr and len(model) < D
        do_rd = rd and len(model) > 0
        exp = model[0] if do_rd else None

        await cycle(dut, wr=int(wr), rd=int(rd), data=x)

        if do_rd:
            model.popleft()
            n_rd += 1
            assert int(dut.dout.value) == exp, f"expected {exp:#x}, got {int(dut.dout.value):#x}"
        if do_wr:
            model.append(x)
            n_wr += 1

        assert int(dut.count.value) == len(model), "count mismatch"
        assert dut.full.value == (len(model) == D)
        assert dut.empty.value == (len(model) == 0)

    dut._log.info("random test OK: %d writes, %d reads", n_wr, n_rd)
