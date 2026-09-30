# sync-fifo

Parameterized synchronous FIFO in Verilog, verified with a **cocotb** testbench on Icarus Verilog.

## Design — `rtl/sync_fifo.v`

| Parameter | Default | Meaning |
|---|---|---|
| `W` | 8 | data width |
| `D` | 8 | depth (power of 2) |
| `AW` | `$clog2(D)` | pointer width |

- Single clock, active-low asynchronous reset (`rst_n`)
- Occupancy counter with one extra bit (`[AW:0]`) so it can hold the value `D` → `full = (count == D)`, `empty = (count == 0)`
- Writes when full and reads when empty are **ignored** (`do_wr = wr_en && !full`, `do_rd = rd_en && !empty`)
- Registered read: `dout` updates on the clock edge where the read happens
- Storage array has no reset, so synthesis can infer block RAM
- Simultaneous read + write keeps the count unchanged

## Verification — `tb/test_sync_fifo.py`

| Test | What it checks |
|---|---|
| `test_reset` | `empty=1`, `full=0` after reset |
| `test_fill_and_drain` | fill to `full`, overflow write ignored, data read back in order, `empty` at the end, underflow read ignored |
| `test_simultaneous` | read+write every cycle holds occupancy steady; read+write on an empty FIFO only writes |
| `test_random` | 2000 cycles of random `wr_en`/`rd_en` against a Python `deque` reference model — checks `dout`, `count`, `full`, `empty` every cycle |

## Run

```bash
pip install cocotb          # cocotb 2.x
sudo apt install iverilog   # Icarus Verilog

cd tb
make                 # default W=8, D=8
make W=16 D=16       # other configurations
make WAVES=1         # also dump a waveform
```

Result:

```
** test_sync_fifo.test_reset            PASS **
** test_sync_fifo.test_fill_and_drain   PASS **
** test_sync_fifo.test_simultaneous     PASS **
** test_sync_fifo.test_random           PASS **
** TESTS=4 PASS=4 FAIL=0 SKIP=0              **
```

## Possible extensions
- `almost_full` / `almost_empty` thresholds
- First-word-fall-through (FWFT) read mode
- Asynchronous (dual-clock) version with Gray-code pointers
