def to_tcl_path(path, cygwin_root="C:\\cygwin64"):
    """
    Return a path string in a format suitable for TCL.
    """
    return cygwin_root + str(path.resolve())
