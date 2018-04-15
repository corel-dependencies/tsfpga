library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library vunit_lib;
use vunit_lib.bus_master_pkg.all;
use vunit_lib.axi_slave_pkg.all;
use vunit_lib.memory_pkg.all;
context vunit_lib.vunit_context;
context vunit_lib.com_context;

library osvvm;
use osvvm.RandomPkg.all;

library bfm;

library common;
use common.addr_pkg.all;

use work.axi_pkg.all;
use work.axil_pkg.all;


entity tb_axil_mux is
  generic (
    runner_cfg : string
  );
end entity;

architecture tb of tb_axil_mux is

  constant data_width : integer := 32;
  constant bytes_per_word : integer := data_width / 8;
  constant num_slaves : integer := 4;
  subtype slaves_rng is integer range 0 to num_slaves - 1;

  constant num_words : integer := 32;
  constant addr_offset : integer := 4096; -- Corresponding to the base addresses below

  constant slave_addrs : addr_and_mask_vec_t(slaves_rng) := (
    (addr => x"0000_0000", mask => x"0000_3000"),
    (addr => x"0000_1000", mask => x"0000_3000"),
    (addr => x"0000_2000", mask => x"0000_3000"),
    (addr => x"0000_3000", mask => x"0000_3000")
  );

  signal clk : std_logic := '0';

  signal read_m2s : axil_read_m2s_t;
  signal read_s2m : axil_read_s2m_t;

  signal write_m2s : axil_write_m2s_t;
  signal write_s2m : axil_write_s2m_t;

  signal read_m2s_vec : axil_read_m2s_vec_t(slaves_rng);
  signal read_s2m_vec : axil_read_s2m_vec_t(slaves_rng);

  signal write_m2s_vec : axil_write_m2s_vec_t(slaves_rng);
  signal write_s2m_vec : axil_write_s2m_vec_t(slaves_rng);

  constant axi_master : bus_master_t := new_bus(data_length => data_width, address_length => read_m2s.ar.addr'length);

  type memory_vec_t is array (integer range <>) of memory_t;
  constant memory : memory_vec_t (slaves_rng) := (
    0 => new_memory,
    1 => new_memory,
    2 => new_memory,
    3 => new_memory
  );

  type axi_slave_vec_t is array (integer range <>) of axi_slave_t;
  constant axi_slave : axi_slave_vec_t(slaves_rng) := (
    0 => new_axi_slave(address_fifo_depth => 1, memory => memory(0)),
    1 => new_axi_slave(address_fifo_depth => 1, memory => memory(1)),
    2 => new_axi_slave(address_fifo_depth => 1, memory => memory(2)),
    3 => new_axi_slave(address_fifo_depth => 1, memory => memory(3))
  );

  type memory_data_t is array(0 to num_slaves - 1, 0 to num_words - 1) of std_logic_vector(data_width - 1 downto 0);

begin

  test_runner_watchdog(runner, 2 ms);
  clk <= not clk after 2 ns;


  ------------------------------------------------------------------------------
  main : process
    variable rnd : RandomPType;
    variable data : std_logic_vector(data_width - 1 downto 0);
    variable address : integer;
    variable buf : buffer_t;

    variable memory_data : memory_data_t;

    function bank_address(slave, word : integer) return integer is
    begin
      return slave * addr_offset + word * bytes_per_word;
    end function;
  begin
    test_runner_setup(runner, runner_cfg);
    rnd.InitSeed(rnd'instance_name);

    for slave in memory'range loop
      buf := allocate(memory(slave), bank_address(slave, num_words));
    end loop;

    for slave in axi_slave'range loop
      for word in 0 to num_words - 1 loop
        address := bank_address(slave, word);
        data := rnd.RandSLV(data'length);

        set_expected_word(memory(slave), address, data);
        memory_data(slave, word) := data;

        write_bus(net, axi_master, address, data); -- Call is non-blocking. I.e. we will build up a queue of writes.
        wait until rising_edge(clk);
      end loop;
    end loop;
    wait for 30 us; -- Wait until all writes are finished

    -- Test that everything was written correctly to memory
    for slave in memory'range loop
      check_expected_was_written(memory(slave));
    end loop;

    -- Test reading back data
    for slave in axi_slave'range loop
      for word in 0 to num_words - 1 loop
        address := bank_address(slave, word);
        data := memory_data(slave, word);

        check_bus(net, axi_master, address, data);
      end loop;
    end loop;

    test_runner_cleanup(runner);
  end process;


  ------------------------------------------------------------------------------
  axil_master_inst : entity bfm.axil_master
    generic map (
      bus_handle => axi_master
    )
    port map (
      clk => clk,

      axil_read_m2s => read_m2s,
      axil_read_s2m => read_s2m,

      axil_write_m2s => write_m2s,
      axil_write_s2m => write_s2m
    );


  ------------------------------------------------------------------------------
  axil_slave_gen : for i in axi_slave'range generate
  begin
    axil_slave_inst : entity bfm.axil_slave
    generic map (
      axi_slave => axi_slave(i),
      data_width => data_width
    )
    port map (
      clk => clk,

      axil_read_m2s => read_m2s_vec(i),
      axil_read_s2m => read_s2m_vec(i),

      axil_write_m2s => write_m2s_vec(i),
      axil_write_s2m => write_s2m_vec(i)
    );
  end generate;


  ------------------------------------------------------------------------------
  dut : entity work.axil_mux
    generic map (
      slave_addrs => slave_addrs
    )
    port map (
      clk => clk,

      read_m2s => read_m2s,
      read_s2m => read_s2m,

      write_m2s => write_m2s,
      write_s2m => write_s2m,

      read_m2s_vec => read_m2s_vec,
      read_s2m_vec => read_s2m_vec,

      write_m2s_vec => write_m2s_vec,
      write_s2m_vec => write_s2m_vec
    );

end architecture;
