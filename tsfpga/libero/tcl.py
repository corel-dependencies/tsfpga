from pathlib import Path
from os.path import relpath
from corel_tsfpga.tsfpga import libero


def to_tcl_path(path, project_folder, cygwin_root="C:\\cygwin64"):
    """
    Return a path string in a format suitable for TCL.
    """
    return relpath(path.resolve(), start=project_folder)


class LiberoTcl:
    """
    Class with methods for translating a set of sources into Libero TCL
    """

    def __init__(
        self,
        name,
    ):
        self.name = name

    # pylint: disable=too-many-arguments
    def create(
        self,
        project_folder,
        modules,
        part,
        family,
        top,
        run_index,
        generics=None,
        constraints=None,
        tcl_sources=None,
        build_step_hooks=None,
        ip_cache_path=None,
        disable_io_buffers=True,
        # Add no sources other than IP cores
        ip_cores_only=False,
        # Will be passed on to module functions. Enables parameterization of
        # e.g. IP cores.
        other_arguments=None,
    ):

        self.top = top
        project = self.name

        # Split the string
        parts = part.split("-")

        # Assign values based on the length of parts
        device = parts[0]
        speed = parts[1]
        package = parts[2]
        temp_range = parts[3] if len(parts) > 3 else "COM"  # Default value set to "COM" i.e. also the libero tool's default

        generics = {} if generics is None else generics
        other_arguments = {} if other_arguments is None else other_arguments

        tcl = ""

        # top-module first
        modules._modules.sort(key=lambda m: m.name == f"{self.top}", reverse=True)

        for module in modules:
            synthesis_files = module.get_synthesis_files(**other_arguments)

            # top hdl file first (it has be to be called as <module name>.vhd)
            synthesis_files.sort(
                key=lambda hdl_file: hdl_file.path.stem == f"{self.top}", reverse=True
            )

            for hdl_file in synthesis_files:
                hdl_file_path = to_tcl_path(
                    hdl_file.path, project_folder=project_folder
                )
                if module.library_name == self.top:
                    tcl += f"fpga_file {{{hdl_file_path}}}\n"  # work library for top.
                else:
                    tcl += f"fpga_file {{{hdl_file_path}}} {module.library_name}\n"

            for ip_core_file in module.get_ip_core_files(**other_arguments):
                if ip_core_file.path.suffix == ".cxf":
                    tcl += f"fpga_file {{{to_tcl_path(ip_core_file.path, project_folder=project_folder)}}}\n"

        for constraint in constraints:
            tcl += f"fpga_file {{{to_tcl_path(constraint.file, project_folder=project_folder)}}}\n"

        with open(Path(libero.__path__[0]) / "template.tcl") as fin:
            tcl_result = fin.read()
            tcl_result = tcl_result.replace("__project__", self.name)
            tcl_result = tcl_result.replace("__part__", part)
            tcl_result = tcl_result.replace("__family__", family)
            tcl_result = tcl_result.replace("__device__", device)
            tcl_result = tcl_result.replace("__package__", package)
            tcl_result = tcl_result.replace("__speed__", speed)
            tcl_result = tcl_result.replace("__temp_range__", temp_range)
            tcl_result = tcl_result.replace("__top__", top)
            tcl_result = tcl_result.replace("__destination__", str(project_folder))

            tcl_result = tcl_result.replace("__fpga_files__", tcl)

        return tcl_result

    def _add_module_source_files(self, modules, other_arguments):
        tcl = ""
        for module in modules:
            synthesis_files = module.get_synthesis_files(**other_arguments)
            if not synthesis_files:
                continue

            # top goes first.  I must be called as library_name.vhd.
            synthesis_files.sort(
                key=lambda name: name.path.stem == f"{self.top}", reverse=True
            )

            tcl += "\n"
            if module.library_name != self.top:
                # for top library needs to be top
                tcl += f"\tadd_library -library {module.library_name}\n"

            for hdl_file in synthesis_files:
                tcl += f"\tcreate_links -hdl_source {{{to_tcl_path(hdl_file.path)}}}\n"

                if hdl_file.is_vhdl:
                    if module.library_name != self.top:
                        tcl += f"\tadd_file_to_library -library {module.library_name} -file {{{to_tcl_path(hdl_file.path)}}}\n"

        return tcl

    @staticmethod
    def _add_tcl_sources(tcl_sources):
        if tcl_sources is None:
            return ""

        tcl = ""
        for tcl_source_file in tcl_sources:
            tcl += f"source -notrace {{{to_tcl_path(tcl_source_file)}}}\n"
        return tcl

    @staticmethod
    def _add_generics(generics):
        """
        Generics are set according to this weird format:
        https://www.xilinx.com/support/answers/52217.html
        """
        if not generics:
            return ""

        generic_list = []
        for name, value in generics.items():
            if isinstance(value, bool):
                value_tcl_formatted = "1'b1" if value else "1'b0"
                generic_list.append(f"{name}={value_tcl_formatted}")
            else:
                generic_list.append(f"{name}={value}")

        generics_string = " ".join(generic_list)
        return f"set_property generic {{{generics_string}}} [current_fileset]\n"

    @staticmethod
    def _iterate_constraints(modules, constraints, other_arguments):
        for module in modules:
            for constraint in module.get_scoped_constraints(**other_arguments):
                yield constraint

        if constraints is not None:
            for constraint in constraints:
                yield constraint

    @staticmethod
    def _add_constraints(constraints, skip_tcl=True):
        # TODO remove skip_tcl and fix the tcl for libero

        tcl = ""
        for constraint in constraints:
            constraint_file = to_tcl_path(constraint.file)

            if constraint.file.suffix == ".pdc":
                tcl += f"\tcreate_links -pdc {{{constraint_file}}}\n"
            elif constraint.file.suffix == ".sdc":
                tcl += f"\tcreate_links -sdc {{{constraint_file}}}\n"
            elif constraint.file.suffix == ".tcl":
                if skip_tcl:
                    continue
                tcl += f"\tsource -notrace {{{constraint_file}}}\n"
            else:
                raise NotImplementedError(f"Can not handle file: {constraint.file}")

        return tcl
