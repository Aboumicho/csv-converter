"""
stl_utils.py
============
Shared helper for writing binary STL files.

A triangle list is a sequence of ``(normal, v1, v2, v3)`` tuples where each
element is an ``(x, y, z)`` tuple of floats.
"""

import os
import struct


def write_binary_stl(output_path: str, triangles: list) -> str:
    """
    Write *triangles* to a binary STL file at *output_path*.

    Parameters
    ----------
    output_path : str
        Destination file path (parent directories are created automatically).
    triangles : list[(normal, v1, v2, v3)]
        Each entry contains four ``(x, y, z)`` float tuples.

    Returns
    -------
    str : the absolute path written.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "wb") as fh:
        fh.write(b"\x00" * 80)                          # 80-byte header
        fh.write(struct.pack("<I", len(triangles)))      # triangle count
        for normal, v1, v2, v3 in triangles:
            fh.write(struct.pack("<fff", *normal))
            fh.write(struct.pack("<fff", *v1))
            fh.write(struct.pack("<fff", *v2))
            fh.write(struct.pack("<fff", *v3))
            fh.write(b"\x00\x00")                       # attribute byte count

    return output_path
