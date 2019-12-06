-- -----------------------------------------------------------------------------
-- Copyright (c) Lukas Vik. All rights reserved.
-- -----------------------------------------------------------------------------

library vunit_lib;
use vunit_lib.bus_master_pkg.all;
use vunit_lib.memory_pkg.all;

library axi;
use axi.axil_pkg.all;

use work.artyz7_top_pkg.all;


package top_level_sim_pkg is

  constant axi_memory : memory_t := new_memory;

end;