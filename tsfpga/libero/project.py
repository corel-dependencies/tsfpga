from copy import deepcopy

from corel_tsfpga.tsfpga.system_utils import create_file
from .tcl import LiberoTcl


class LiberoProject:
    """
    Used for handling a Microsemi Libero 11 HDL project
    """

    # pylint: disable=too-many-arguments,too-many-instance-attributes
    def __init__(
        self,
        name,
        modules,
        part,
        family,
        top=None,
        generics=None,
        constraints=None,
        tcl_sources=None,
        build_step_hooks=None,
        vivado_path=None,
        default_run_index=1,
        defined_at=None,
        **other_arguments,
    ):
        """
        Class constructor. Performs a shallow copy of the mutable arguments, so
        that the user can e.g. append items to their list after creating an object.

        Arguments:
            name (str): Project name.
            modules (list(:class:`Module <.BaseModule>`)): Modules that shall
                be included in the project.
            part (str): Part identification.
            top (str): Name of top level entity. If left out, the top level
                name will be inferred from the ``name``.
            generics: A dict with generics values (`dict(name: value)`). Use
                this parameter for "static" generics that do not change between
                multiple builds of this project. These will be set in the
                project when it is created.

                Compare to the build-time generic argument in :meth:`build`.
            constraints (list(Constraint)): Constraints that will be applied
                to the project.
            tcl_sources (list(`pathlib.Path`)): A list of TCL files. Use for
                e.g. block design, pinning, settings, etc.
            build_step_hooks (list(BuildStepTclHook)): Build step hooks that
                will be applied to the project.
            vivado_path (`pathlib.Path`): A path to the Libero executable.
                If omitted, the default location from the system PATH will be used.
            default_run_index (int): Default run index (synth_X and impl_X)
                that is set in the project. Can also use the argument to
                :meth:`build() <LiberoProject.build>` to specify at build-time.
            defined_at (`pathlib.Path`): Optional path to the file where you
                defined this project. To get a useful ``build.py --list``
                message. Is useful when you have many projects set up.
            other_arguments: Optional further arguments. Will not be used by
                tsfpga, but will instead be passed on to

                * :func:`BaseModule.get_synthesis_files()
                  <tsfpga.module.BaseModule.get_synthesis_files>`
                * :func:`BaseModule.get_ip_core_files()
                  <tsfpga.module.BaseModule.get_ip_core_files>`
                * :func:`BaseModule.get_scoped_constraints()
                  <tsfpga.module.BaseModule.get_scoped_constraints>`
                * :func:`LiberoProject.pre_create`
                * :func:`BaseModule.pre_build() <tsfpga.module.BaseModule.pre_build>`
                * :func:`LiberoProject.pre_build`
                * :func:`LiberoProject.post_build`

                along with further arguments supplied at build-time to :meth:`.create`
                and :meth:`.build`.

                .. note::
                    This is a "kwargs" style argument. You can pass any number
                    of named arguments.
        """
        self.name = name
        self.modules = modules.copy()
        self.part = part
        self.family = family
        self.static_generics = dict() if generics is None else generics.copy()
        self.constraints = [] if constraints is None else constraints.copy()
        self.tcl_sources = [] if tcl_sources is None else tcl_sources.copy()
        self.build_step_hooks = (
            [] if build_step_hooks is None else build_step_hooks.copy()
        )
        self._vivado_path = vivado_path
        self.default_run_index = default_run_index
        self.defined_at = defined_at
        self.other_arguments = (
            None if other_arguments is None else other_arguments.copy()
        )

        # Will be set by child class when applicable
        self.is_netlist_build = False
        self.analyze_synthesis_timing = True
        self.report_logic_level_distribution = False
        self.ip_cores_only = False

        self.top = "top_" + name if top is None else top

        self.tcl = LiberoTcl(name=self.name)

    def project_file(self, project_path):
        """
        Arguments:
            project_path (`pathlib.Path`): A path containing a Libero project.
        Return:
            `pathlib.Path`: The project file of this project, in the given folder
        """
        return project_path / (self.name + ".xpr")

        # def _setup_tcl_sources(self):
        #     tsfpga_tcl_sources = [
        #         TSFPGA_TCL / "vivado_default_run.tcl",
        #         TSFPGA_TCL / "vivado_fast_run.tcl",
        #         TSFPGA_TCL / "vivado_messages.tcl",
        #     ]

        # Add tsfpga TCL sources first. The user might want to change something
        # in the tsfpga settings. Conversely, tsfpga should not modify
        # something that the user has set up.
        # self.tcl_sources = tsfpga_tcl_sources + self.tcl_sources

    def _create_tcl(self, project_path, ip_cache_path, all_arguments):
        """
        Make a TCL file that creates a Libero project
        """
        if project_path.exists():
            raise ValueError(f"Folder already exists: {project_path}")
        project_path.mkdir(parents=True)

        create_libero_project_tcl = project_path / "create_libero_project.tcl"
        tcl = self.tcl.create(
            project_folder=project_path,
            modules=self.modules,
            part=self.part,
            family=self.family,
            top=self.top,
            run_index=self.default_run_index,
            generics=self.static_generics,
            constraints=self.constraints,
            tcl_sources=self.tcl_sources,
            build_step_hooks=self.build_step_hooks,
            ip_cache_path=ip_cache_path,
            disable_io_buffers=self.is_netlist_build,
            ip_cores_only=self.ip_cores_only,
            other_arguments=all_arguments,
        )
        create_file(create_libero_project_tcl, tcl)

        return create_libero_project_tcl

    def create(self, project_path, ip_cache_path=None, **other_arguments):
        """
        Create a Libero project

        Arguments:
            project_path (`pathlib.Path`): Path where the project shall be placed.
            ip_cache_path (`pathlib.Path`): Path to a folder where the Libero
                IP cache can be placed. If omitted, the Libero IP cache mechanism
                will not be enabled.
            other_arguments: Optional further arguments. Will not be used by
                tsfpga, but will instead be sent to

                * :func:`BaseModule.get_synthesis_files()
                  <tsfpga.module.BaseModule.get_synthesis_files>`
                * :func:`BaseModule.get_ip_core_files()
                  <tsfpga.module.BaseModule.get_ip_core_files>`
                * :func:`BaseModule.get_scoped_constraints()
                  <tsfpga.module.BaseModule.get_scoped_constraints>`
                * :func:`LiberoProject.pre_create`

                along with further ``other_arguments`` supplied to :meth:`.__init__`.

                .. note::
                    This is a "kwargs" style argument. You can pass any number
                    of named arguments.
        Returns:
            bool: True if everything went well.
        """
        print(f"Creating Libero project in {project_path}")
        # self._setup_tcl_sources()
        # self._setup_build_step_hooks()

        # The pre-create hook might have side effects. E.g. change some
        # register constants.
        # So we make a deep copy of the module list before the hook is called.
        # Note that the modules are copied before the pre-build hooks as well,
        # since we do not know if we might be performing a create-only or
        # build-only operation. The copy does not take any significant time,
        # so this is not an issue.
        self.modules = deepcopy(self.modules)

        # Send all available arguments that are reasonable to use in
        # pre-create and module getter functions. Prefer run-time values over
        # the static.
        all_arguments = copy_and_combine_dicts(self.other_arguments, other_arguments)
        all_arguments.update(
            generics=self.static_generics,
            part=self.part,
        )

        if not self.pre_create(
            project_path=project_path, ip_cache_path=ip_cache_path, **all_arguments
        ):
            print("ERROR: Project pre-create hook returned False. Failing the build.")
            return False

        self._create_tcl(
            project_path=project_path,
            ip_cache_path=ip_cache_path,
            all_arguments=all_arguments,
        )
        return True

    def pre_create(self, **kwargs):  # pylint: disable=no-self-use, unused-argument
        """
        Override this function in a child class if you wish to do something
        useful with it.
        Will be called from :meth:`.create` right before the call to Libero.

        An example use case for this function is when TCL source scripts for
        the Libero project have to be auto generated. This could e.g. be
        scripts that set IP repo paths based on the Libero system PATH.

        .. Note::
            This default method does nothing. Shall be overridden by project
            that utilize this mechanism.

        Arguments:
            kwargs: Will have all the :meth:`.create` parameters in it, as
            well as everything in the ``other_arguments`` argument to
            :func:`LiberoProject.__init__`.

        Return:
            bool: True if everything went well.
        """
        return True

    # def _build_tcl(
    #     self, project_path, output_path, num_threads, run_index, all_generics,
    #     synth_only
    # ):
    #     """
    #     Make a TCL file that builds a Libero project
    #     """
    #     project_file = self.project_file(project_path)
    #     if not project_file.exists():
    #         raise ValueError(
    #             f"Project file does not exist in the specified location: {project_file}"
    #         )

    #     build_vivado_project_tcl = project_path / "build_vivado_project.tcl"
    #     tcl = self.tcl.build(
    #         project_file=project_file,
    #         output_path=output_path,
    #         num_threads=num_threads,
    #         run_index=run_index,
    #         generics=all_generics,
    #         synth_only=synth_only,
    #         analyze_synthesis_timing=self.analyze_synthesis_timing,
    #     )
    #     create_file(build_vivado_project_tcl, tcl)

    #     return build_vivado_project_tcl

    def __str__(self):
        result = f"{self.name}\n"

        if self.defined_at is not None:
            result += f"Defined at: {self.defined_at.resolve()}\n"

        result += f"Type:       {self.__class__.__name__}\n"
        result += f"Top level:  {self.top}\n"

        if self.static_generics:
            generics = self._dict_to_string(self.static_generics)
        else:
            generics = "-"
        result += f"Generics:   {generics}\n"

        if self.other_arguments:
            result += f"Arguments:  {self._dict_to_string(self.other_arguments)}\n"

        return result

    @staticmethod
    def _dict_to_string(data):
        return ", ".join([f"{name}={value}" for name, value in data.items()])


def copy_and_combine_dicts(dict_first, dict_second):
    """
    Will prefer values in the second dict, in case the same key occurs in both.
    Will return ``None`` if both are ``None``.
    """
    if dict_first is None and dict_second is None:
        return None

    if dict_first is None:
        return dict_second.copy()

    if dict_second is None:
        return dict_first.copy()

    result = dict_first.copy()
    result.update(dict_second)
    return result
