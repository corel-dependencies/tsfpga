# ------------------------------------------------------------------------------
# Copyright (c) Lukas Vik. All rights reserved.
# ------------------------------------------------------------------------------

from os.path import abspath, dirname, join

import tsfpga
from tsfpga.constraint import Constraint
from tsfpga.vivado_project import VivadoProject

from tsfpga_example_env import get_tsfpga_modules

THIS_DIR = abspath(dirname(__file__))
THIS_FILE = abspath(__file__)


def get_projects():
    projects = []

    modules = get_tsfpga_modules(tsfpga.ALL_TSFPGA_MODULES_FOLDERS)
    part = "xc7z020clg400-1"

    tcl_dir = join(THIS_DIR, "tcl")
    pinning = Constraint(join(tcl_dir, "artyz7_pinning.tcl"))
    block_design = join(tcl_dir, "block_design.tcl")

    projects.append(VivadoProject(
        name="artyz7",
        modules=modules,
        part=part,
        tcl_sources=[block_design],
        constraints=[pinning],
        defined_at=THIS_FILE
    ))

    projects.append(SpecialVivadoProject(
        name="artyz7_dummy",
        modules=modules,
        part=part,
        top="artyz7_top",
        generics=dict(dummy=True, values=123),
        constraints=[pinning],
        tcl_sources=[block_design]
    ))

    return projects


class SpecialVivadoProject(VivadoProject):

    def post_build(self, output_path, **kwargs):
        print(f"We can do useful things here. In the output path {output_path} for example")
