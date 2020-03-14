# ------------------------------------------------------------------------------
# Copyright (c) Lukas Vik. All rights reserved.
# ------------------------------------------------------------------------------

from pathlib import Path

from tsfpga.hdl_file import HdlFile


def test_file_type():
    assert HdlFile(Path("file.vhd")).is_vhdl
    assert not HdlFile(Path("file.vhd")).is_verilog_source
    assert not HdlFile(Path("file.vhd")).is_verilog_header

    assert HdlFile(Path("file.vh")).is_verilog_header
    assert HdlFile(Path("file.v")).is_verilog_source