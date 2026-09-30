// Synchronous FIFO
//  - Single clock, active-low async reset
//  - Registered read data (dout valid the cycle after rd_en)
//  - Occupancy counter drives full/empty
//  - Writes when full and reads when empty are ignored
//  - D must be a power of 2 (pointers wrap naturally)
module sync_fifo #(parameter W = 8, D = 8, AW = $clog2(D)) (
  input              clk, rst_n,
  input              wr_en, rd_en,
  input      [W-1:0] din,
  output reg [W-1:0] dout,
  output             full, empty
);
  reg [W-1:0]  mem [0:D-1];
  reg [AW-1:0] wptr, rptr;
  reg [AW:0]   count;          // one extra bit, so it can hold D

  wire do_wr = wr_en && !full;
  wire do_rd = rd_en && !empty;

  assign full  = (count == D);
  assign empty = (count == 0);

  // storage: no reset, so it can map to block RAM
  always @(posedge clk) begin
    if (do_wr) mem[wptr] <= din;
    if (do_rd) dout      <= mem[rptr];
  end

  // pointers and count
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      wptr <= 0; rptr <= 0; count <= 0;
    end else begin
      if (do_wr) wptr <= wptr + 1'b1;   // wraps at D because D is a power of 2
      if (do_rd) rptr <= rptr + 1'b1;
      case ({do_wr, do_rd})
        2'b10:   count <= count + 1'b1;
        2'b01:   count <= count - 1'b1;
        default: count <= count;          // both or neither
      endcase
    end
  end
endmodule
