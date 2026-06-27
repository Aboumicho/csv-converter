"""Unit tests for points_writer.py."""

import math
import os
import struct
import tempfile

import pytest

from points_writer import (
    CoordinateFrame,
    MicronMapperCSVWriter,
    STLWriter,
    TransformedPointsPipeline,
    TransformedPointsReader,
    _angle_between_deg,
    _cross,
    _dot,
    _normalize,
    _sub,
)


# ============================================================
# Helper function tests
# ============================================================


class TestPointsWriterHelpers:
    def test_sub(self):
        assert _sub((3, 5, 7), (1, 2, 3)) == (2, 3, 4)

    def test_normalize(self):
        result = _normalize((3, 4, 0))
        assert result == pytest.approx((0.6, 0.8, 0.0))

    def test_normalize_zero_raises(self):
        with pytest.raises(ValueError, match="Zero-length"):
            _normalize((0, 0, 0))

    def test_dot(self):
        assert _dot((1, 0, 0), (0, 1, 0)) == 0
        assert _dot((1, 0, 0), (1, 0, 0)) == 1

    def test_cross(self):
        assert _cross((1, 0, 0), (0, 1, 0)) == (0, 0, 1)

    def test_angle_between_deg_same(self):
        assert _angle_between_deg((1, 0, 0), (1, 0, 0)) == pytest.approx(0.0)

    def test_angle_between_deg_perpendicular(self):
        assert _angle_between_deg((1, 0, 0), (0, 1, 0)) == pytest.approx(90.0)

    def test_angle_between_deg_opposite(self):
        assert _angle_between_deg((1, 0, 0), (-1, 0, 0)) == pytest.approx(180.0)


# ============================================================
# TransformedPointsReader tests
# ============================================================


class TestTransformedPointsReader:
    def _write_csv(self, content: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path

    def test_basic_read(self):
        content = (
            "Point,X,Y,Z\n"
            "32_Origin,0.0,0.0,0.0\n"
            "32_X,1.0,0.0,0.0\n"
            "32_Y,0.0,1.0,0.0\n"
            "32_Z,0.0,0.0,1.0\n"
        )
        path = self._write_csv(content)
        try:
            data = TransformedPointsReader(path).read()
            assert data["prefix"] == "32"
            assert data["origin"] == (0.0, 0.0, 0.0)
            assert data["x"] == (1.0, 0.0, 0.0)
            assert data["y"] == (0.0, 1.0, 0.0)
            assert data["z"] == (0.0, 0.0, 1.0)
        finally:
            os.unlink(path)

    def test_prefix_detection(self):
        content = (
            "Point,X,Y,Z\n"
            "Tooth44_Origin,10.0,20.0,30.0\n"
            "Tooth44_X,11.0,20.0,30.0\n"
            "Tooth44_Y,10.0,21.0,30.0\n"
            "Tooth44_Z,10.0,20.0,31.0\n"
        )
        path = self._write_csv(content)
        try:
            data = TransformedPointsReader(path).read()
            assert data["prefix"] == "Tooth44"
        finally:
            os.unlink(path)

    def test_missing_suffix_raises(self):
        content = (
            "Point,X,Y,Z\n"
            "NoSuffix,0.0,0.0,0.0\n"
            "Another,1.0,0.0,0.0\n"
        )
        path = self._write_csv(content)
        try:
            with pytest.raises(ValueError, match="Cannot detect prefix"):
                TransformedPointsReader(path).read()
        finally:
            os.unlink(path)

    def test_utf8_bom(self):
        content = (
            "\ufeffPoint,X,Y,Z\n"
            "32_Origin,0.0,0.0,0.0\n"
            "32_X,1.0,0.0,0.0\n"
            "32_Y,0.0,1.0,0.0\n"
            "32_Z,0.0,0.0,1.0\n"
        )
        path = self._write_csv(content)
        try:
            data = TransformedPointsReader(path).read()
            assert data["prefix"] == "32"
        finally:
            os.unlink(path)


# ============================================================
# CoordinateFrame tests (points_writer version)
# ============================================================


class TestPointsWriterCoordinateFrame:
    def test_basic_frame(self):
        data = {
            "prefix": "32",
            "origin": (0, 0, 0),
            "x": (1, 0, 0),
            "y": (0, 1, 0),
            "z": (0, 0, 1),
        }
        frame = CoordinateFrame(data)
        assert frame.prefix == "32"
        assert frame.origin == (0, 0, 0)
        assert frame.x_axis == pytest.approx((1, 0, 0))
        assert frame.y_axis == pytest.approx((0, 1, 0))
        assert frame.z_axis == pytest.approx((0, 0, 1))

    def test_non_unit_axes_normalized(self):
        data = {
            "prefix": "A",
            "origin": (0, 0, 0),
            "x": (5, 0, 0),
            "y": (0, 3, 0),
            "z": (0, 0, 7),
        }
        frame = CoordinateFrame(data)
        mag = math.sqrt(sum(c * c for c in frame.z_axis))
        assert mag == pytest.approx(1.0)

    def test_offset_origin(self):
        data = {
            "prefix": "B",
            "origin": (10, 20, 30),
            "x": (11, 20, 30),
            "y": (10, 21, 30),
            "z": (10, 20, 31),
        }
        frame = CoordinateFrame(data)
        assert frame.origin == (10, 20, 30)
        assert frame.x_axis == pytest.approx((1, 0, 0))


# ============================================================
# MicronMapperCSVWriter tests (points_writer version)
# ============================================================


class TestPointsWriterCSV:
    def _make_frame(self, prefix="32", z=(0, 0, 1)):
        data = {
            "prefix": prefix,
            "origin": (0, 0, 0),
            "x": (1, 0, 0),
            "y": (0, 1, 0),
            "z": z,
        }
        return CoordinateFrame(data)

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def _output_path(self, name="test.csv"):
        return os.path.join(self.tmpdir, name)

    def test_creates_file(self):
        path = self._output_path()
        frames = [self._make_frame()]
        MicronMapperCSVWriter(frames, path).write()
        assert os.path.isfile(path)

    def test_returns_path(self):
        path = self._output_path()
        result = MicronMapperCSVWriter([self._make_frame()], path).write()
        assert result == path

    def test_single_frame_na_divergence(self):
        path = self._output_path()
        MicronMapperCSVWriter([self._make_frame()], path).write()
        with open(path) as fh:
            content = fh.read()
        assert "N/A" in content

    def test_two_frames_divergence(self):
        path = self._output_path()
        f1 = self._make_frame("A", z=(0, 0, 1))
        f2 = self._make_frame("B", z=(1, 0, 0))
        MicronMapperCSVWriter([f1, f2], path).write()
        with open(path) as fh:
            content = fh.read()
        assert "90.0 deg" in content

    def test_metadata_footer(self):
        path = self._output_path()
        MicronMapperCSVWriter(
            [self._make_frame()], path, camera_serial="99999999"
        ).write()
        with open(path) as fh:
            content = fh.read()
        assert "Camera:, 99999999" in content
        assert "Application:," in content
        assert "MicronMapper" in content

    def test_custom_application_string(self):
        path = self._output_path()
        MicronMapperCSVWriter(
            [self._make_frame()], path, application="TestApp v1.0"
        ).write()
        with open(path) as fh:
            content = fh.read()
        assert "TestApp v1.0" in content

    def test_creates_parent_directory(self):
        path = os.path.join(self.tmpdir, "sub", "deep", "test.csv")
        MicronMapperCSVWriter([self._make_frame()], path).write()
        assert os.path.isfile(path)


# ============================================================
# STLWriter tests (points_writer version)
# ============================================================


class TestPointsWriterSTL:
    def _make_frame(self, prefix="32"):
        data = {
            "prefix": prefix,
            "origin": (0, 0, 0),
            "x": (1, 0, 0),
            "y": (0, 1, 0),
            "z": (0, 0, 1),
        }
        return CoordinateFrame(data)

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def _output_path(self, name="test.stl"):
        return os.path.join(self.tmpdir, name)

    def test_creates_valid_stl(self):
        path = self._output_path()
        STLWriter([self._make_frame()], path).write()
        file_size = os.path.getsize(path)
        with open(path, "rb") as fh:
            fh.read(80)
            tri_count = struct.unpack("<I", fh.read(4))[0]
        assert file_size == 80 + 4 + tri_count * 50

    def test_returns_path(self):
        path = self._output_path()
        result = STLWriter([self._make_frame()], path).write()
        assert result == path

    def test_custom_axis_length(self):
        path = self._output_path()
        STLWriter([self._make_frame()], path, axis_length=20.0).write()
        assert os.path.isfile(path)

    def test_custom_shaft_radius(self):
        path = self._output_path()
        STLWriter([self._make_frame()], path, shaft_radius=1.0).write()
        assert os.path.isfile(path)

    def test_multiple_frames(self):
        path = self._output_path()
        f1 = self._make_frame("A")
        data2 = {"prefix": "B", "origin": (10, 0, 0),
                 "x": (11, 0, 0), "y": (10, 1, 0), "z": (10, 0, 1)}
        f2 = CoordinateFrame(data2)
        STLWriter([f1, f2], path).write()

        with open(path, "rb") as fh:
            fh.read(80)
            tri_count = struct.unpack("<I", fh.read(4))[0]
        assert tri_count > 0


# ============================================================
# TransformedPointsPipeline tests
# ============================================================


class TestTransformedPointsPipeline:
    def _write_csv(self, content: str, name="input.csv") -> str:
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path, tmpdir

    def test_full_pipeline(self):
        content = (
            "Point,X,Y,Z\n"
            "32_Origin,0.0,0.0,0.0\n"
            "32_X,1.0,0.0,0.0\n"
            "32_Y,0.0,1.0,0.0\n"
            "32_Z,0.0,0.0,1.0\n"
        )
        input_path, tmpdir = self._write_csv(content)
        output_dir = os.path.join(tmpdir, "output")

        pipeline = TransformedPointsPipeline(
            input_paths=[input_path],
            output_dir=output_dir,
            camera_serial="11111111",
            axis_length=8.0,
        )
        csv_out, stl_out = pipeline.run()

        assert os.path.isfile(csv_out)
        assert os.path.isfile(stl_out)
        assert csv_out.endswith(".csv")
        assert stl_out.endswith(".stl")

    def test_pipeline_multiple_inputs(self):
        content1 = (
            "Point,X,Y,Z\n"
            "32_Origin,0.0,0.0,0.0\n"
            "32_X,1.0,0.0,0.0\n"
            "32_Y,0.0,1.0,0.0\n"
            "32_Z,0.0,0.0,1.0\n"
        )
        content2 = (
            "Point,X,Y,Z\n"
            "34_Origin,5.0,0.0,0.0\n"
            "34_X,6.0,0.0,0.0\n"
            "34_Y,5.0,1.0,0.0\n"
            "34_Z,5.0,0.0,1.0\n"
        )
        tmpdir = tempfile.mkdtemp()
        path1 = os.path.join(tmpdir, "input1.csv")
        path2 = os.path.join(tmpdir, "input2.csv")
        with open(path1, "w") as fh:
            fh.write(content1)
        with open(path2, "w") as fh:
            fh.write(content2)

        output_dir = os.path.join(tmpdir, "output")
        pipeline = TransformedPointsPipeline(
            input_paths=[path1, path2],
            output_dir=output_dir,
        )
        csv_out, stl_out = pipeline.run()

        assert os.path.isfile(csv_out)
        assert os.path.isfile(stl_out)

        # CSV should contain both frames
        with open(csv_out) as fh:
            content = fh.read()
        assert "32," in content
        assert "34," in content
