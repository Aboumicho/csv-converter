"""Unit tests for csv_writer.py."""

import os
import tempfile

import pytest

from csv_writer import MicronMapperCSVWriter
from file_reader import CoordinateFrame


def _make_frame(prefix, origin=(0, 0, 0), z=(0, 0, 1), x=(1, 0, 0), y=(0, 1, 0)):
    pts = {"_Origin": origin, "_X": tuple(o + a for o, a in zip(origin, x)),
           "_Y": tuple(o + a for o, a in zip(origin, y)),
           "_Z": tuple(o + a for o, a in zip(origin, z))}
    return CoordinateFrame(prefix, pts)


class TestMicronMapperCSVWriter:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def _output_path(self, name="test.csv"):
        return os.path.join(self.tmpdir, "sub", name)

    def test_creates_output_directory(self):
        path = self._output_path()
        frames = [_make_frame("32")]
        MicronMapperCSVWriter(frames, path).write()
        assert os.path.isfile(path)

    def test_returns_output_path(self):
        path = self._output_path()
        frames = [_make_frame("32")]
        result = MicronMapperCSVWriter(frames, path).write()
        assert result == path

    def test_single_frame_data_row(self):
        path = self._output_path()
        frames = [_make_frame("32", origin=(1.0, 2.0, 3.0))]
        MicronMapperCSVWriter(frames, path).write()

        with open(path, "r") as fh:
            content = fh.read()

        # Should contain prefix
        assert "32," in content
        # Should contain origin coordinates
        assert "1.00000" in content
        assert "2.00000" in content
        assert "3.00000" in content

    def test_multiple_frames(self):
        path = self._output_path()
        frames = [_make_frame("32"), _make_frame("34", origin=(5, 0, 0))]
        MicronMapperCSVWriter(frames, path).write()

        with open(path, "r") as fh:
            lines = fh.readlines()

        data_lines = [l for l in lines if l.startswith("3")]
        assert len(data_lines) == 2

    def test_divergence_line_present(self):
        path = self._output_path()
        frames = [_make_frame("32"), _make_frame("34")]
        MicronMapperCSVWriter(frames, path).write()

        with open(path, "r") as fh:
            content = fh.read()

        assert "Max divergence angle:" in content

    def test_divergence_na_for_single_frame(self):
        path = self._output_path()
        frames = [_make_frame("32")]
        MicronMapperCSVWriter(frames, path).write()

        with open(path, "r") as fh:
            content = fh.read()

        assert "N/A" in content

    def test_divergence_with_angle(self):
        path = self._output_path()
        f1 = _make_frame("32", z=(0, 0, 1))
        f2 = _make_frame("34", z=(1, 0, 0))
        MicronMapperCSVWriter([f1, f2], path).write()

        with open(path, "r") as fh:
            content = fh.read()

        assert "90.0 deg" in content
        assert "32-34" in content

    def test_metadata_footer(self):
        path = self._output_path()
        frames = [_make_frame("32")]
        MicronMapperCSVWriter(frames, path, camera_serial="12345678").write()

        with open(path, "r") as fh:
            content = fh.read()

        assert "Application:," in content
        assert "MicronMapper" in content
        assert "Camera:, 12345678" in content

    def test_default_camera_serial(self):
        path = self._output_path()
        frames = [_make_frame("32")]
        MicronMapperCSVWriter(frames, path).write()

        with open(path, "r") as fh:
            content = fh.read()

        assert "Camera:, 00000000" in content

    def test_crlf_line_endings(self):
        path = self._output_path()
        frames = [_make_frame("32")]
        MicronMapperCSVWriter(frames, path).write()

        with open(path, "rb") as fh:
            content = fh.read()

        assert b"\r\n" in content

    def test_csv_format_values(self):
        """Verify the exact formatting of normal and tangent vectors."""
        path = self._output_path()
        frames = [_make_frame("A", origin=(0, 0, 0), z=(0, 0, 1), x=(1, 0, 0))]
        MicronMapperCSVWriter(frames, path).write()

        with open(path, "r") as fh:
            first_line = fh.readline()

        # z_axis (normal) values: 0, 0, 1 → 6 decimal places
        assert "0.000000,0.000000,1.000000" in first_line
        # x_axis (tangent) values: 1, 0, 0 → 6 decimal places
        assert "1.000000" in first_line
