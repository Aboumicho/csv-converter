"""Unit tests for stl_writer.py."""

import os
import struct
import tempfile

import pytest

from file_reader import CoordinateFrame
from stl_writer import STLWriter


def _make_frame(prefix, origin=(0, 0, 0), z=(0, 0, 1), x=(1, 0, 0), y=(0, 1, 0)):
    pts = {"_Origin": origin, "_X": tuple(o + a for o, a in zip(origin, x)),
           "_Y": tuple(o + a for o, a in zip(origin, y)),
           "_Z": tuple(o + a for o, a in zip(origin, z))}
    return CoordinateFrame(prefix, pts)


class TestSTLWriter:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def _output_path(self, name="test.stl"):
        return os.path.join(self.tmpdir, name)

    def test_creates_file(self):
        path = self._output_path()
        frames = [_make_frame("32")]
        STLWriter(frames, path).write()
        assert os.path.isfile(path)

    def test_returns_output_path(self):
        path = self._output_path()
        frames = [_make_frame("32")]
        result = STLWriter(frames, path).write()
        assert result == path

    def test_binary_stl_header(self):
        path = self._output_path()
        frames = [_make_frame("32")]
        STLWriter(frames, path).write()

        with open(path, "rb") as fh:
            header = fh.read(80)
            assert len(header) == 80
            assert header == b"\x00" * 80

    def test_triangle_count_in_header(self):
        path = self._output_path()
        frames = [_make_frame("32")]
        STLWriter(frames, path).write()

        with open(path, "rb") as fh:
            fh.read(80)  # skip header
            tri_count = struct.unpack("<I", fh.read(4))[0]
            assert tri_count > 0

    def test_file_size_matches_triangle_count(self):
        """Binary STL: 80 header + 4 count + 50 bytes per triangle."""
        path = self._output_path()
        frames = [_make_frame("32")]
        STLWriter(frames, path).write()

        file_size = os.path.getsize(path)
        with open(path, "rb") as fh:
            fh.read(80)
            tri_count = struct.unpack("<I", fh.read(4))[0]

        expected_size = 80 + 4 + tri_count * 50
        assert file_size == expected_size

    def test_multiple_frames(self):
        path = self._output_path()
        frames = [_make_frame("32"), _make_frame("34", origin=(10, 0, 0))]
        STLWriter(frames, path).write()

        with open(path, "rb") as fh:
            fh.read(80)
            tri_count = struct.unpack("<I", fh.read(4))[0]

        # Two frames should have more triangles than one
        path2 = self._output_path("single.stl")
        STLWriter([_make_frame("32")], path2).write()
        with open(path2, "rb") as fh:
            fh.read(80)
            tri_count_single = struct.unpack("<I", fh.read(4))[0]

        assert tri_count > tri_count_single

    def test_creates_parent_directory(self):
        path = os.path.join(self.tmpdir, "sub", "dir", "test.stl")
        frames = [_make_frame("32")]
        STLWriter(frames, path).write()
        assert os.path.isfile(path)

    def test_custom_parameters(self):
        """STLWriter accepts custom implant geometry parameters."""
        path = self._output_path()
        frames = [_make_frame("32")]
        writer = STLWriter(
            frames, path,
            implant_length=12.0,
            outer_radius=3.5,
            groove_depth=0.3,
            groove_count=5,
            screw_radius=1.0,
            screw_depth=3.0,
            segments=12,
        )
        writer.write()
        assert os.path.isfile(path)

    def test_legacy_axis_params_ignored(self):
        """Legacy axis_length and shaft_radius params are accepted but ignored."""
        path = self._output_path()
        frames = [_make_frame("32")]
        writer = STLWriter(frames, path, axis_length=20.0, shaft_radius=0.5)
        writer.write()
        assert os.path.isfile(path)

    def test_minimum_segments(self):
        """Segments are clamped to a minimum of 6."""
        path = self._output_path()
        frames = [_make_frame("32")]
        writer = STLWriter(frames, path, segments=2)
        assert writer.segments == 6
        writer.write()
        assert os.path.isfile(path)

    def test_different_axis_orientations(self):
        """Frames with various Z-axis orientations produce valid STL."""
        path = self._output_path()
        frames = [
            _make_frame("A", z=(0, 0, 1), x=(1, 0, 0)),
            _make_frame("B", origin=(5, 0, 0), z=(1, 0, 0), x=(0, 1, 0)),
            _make_frame("C", origin=(10, 0, 0), z=(0, 1, 0), x=(0, 0, 1)),
        ]
        STLWriter(frames, path).write()

        file_size = os.path.getsize(path)
        with open(path, "rb") as fh:
            fh.read(80)
            tri_count = struct.unpack("<I", fh.read(4))[0]

        expected_size = 80 + 4 + tri_count * 50
        assert file_size == expected_size
        assert tri_count > 0

    def test_empty_frames_list(self):
        """An empty frame list produces a valid STL with 0 triangles."""
        path = self._output_path()
        STLWriter([], path).write()

        with open(path, "rb") as fh:
            fh.read(80)
            tri_count = struct.unpack("<I", fh.read(4))[0]

        assert tri_count == 0
        assert os.path.getsize(path) == 84  # 80 + 4
