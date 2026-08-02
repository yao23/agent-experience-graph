"""Minimal reproduction of cool-RR/PySnooper commit 6e3d797.

The upstream project and this adapted fixture are MIT licensed. See ../SOURCE.md.
"""

import os


def get_write_function(output):
    if output is None:
        def write(value):
            print(value, end="")
    elif isinstance(output, (os.PathLike, str)):
        def write(value):
            with open(output_path, "a", encoding="utf-8") as output_file:
                output_file.write(value)
    elif callable(output):
        write = output
    else:
        raise TypeError("output must be a path, callable, or None")

    return write
