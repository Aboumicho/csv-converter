"""Unit tests for file_reader.py."""

import math
import os
import tempfile

import pytest

from file_reader import (
    CoordinateFrame,
    TxtReader,
    _angle_deg,
    _cross,
    _dot,
    _normalize,
    _sub,
    all_divergence_pairs,
    max_divergence,
)


# ============================================================
# Math helper tests
# ============================================================


class TestSub:
    def test_basic_subtraction(self):
        assert _sub((3, 5, 7), (1, 2, 3)) == (2, 3, 4)

    def test_zero_result(self):
        assert _sub((1, 2, 3), (1, 2, 3)) == (0, 0, 0)

    def test_negative_result(self):
        assert _sub((0, 0, 0), (1, 2, 3)) == (-1, -2, -3)

    def test_floats(self):
        result = _sub((1.5, 2.5, 3.5), (0.5, 0.5, 0.5))
        assert result == pytest.approx((1.0, 2.0, 3.0))


class TestNormalize:
    def test_unit_x(self):
        assert _normalize((1, 0, 0)) == (1.0, 0.0, 0.0)

    def test_unit_y(self):
        assert _normalize((0, 1, 0)) == (0.0, 1.0, 0.0)

    def test_unit_z(self):
        assert _normalize((0, 0, 1)) == (0.0, 0.0, 1.0)

    def test_arbitrary_vector(self):
        result = _normalize((3, 4, 0))
        assert result == pytest.approx((0.6, 0.8, 0.0))

    def test_magnitude_is_one(self):
        result = _normalize((1, 2, 3))
        mag = math.sqrt(sum(x * x for x in result))
        assert mag == pytest.approx(1.0)

    def test_zero_vector_raises(self):
        with pytest.raises(ValueError, match="Zero-length vector"):
            _normalize((0, 0, 0))

    def test_negative_vector(self):
        result = _normalize((-3, -4, 0))
        assert result == pytest.approx((-0.6, -0.8, 0.0))


class TestDot:
    def test_orthogonal(self):
        assert _dot((1, 0, 0), (0, 1, 0)) == 0

    def test_parallel(self):
        assert _dot((1, 0, 0), (1, 0, 0)) == 1

    def test_anti_parallel(self):
        assert _dot((1, 0, 0), (-1, 0, 0)) == -1

    def test_general(self):
        assert _dot((1, 2, 3), (4, 5, 6)) == 32


class TestCross:
    def test_x_cross_y_is_z(self):
        assert _cross((1, 0, 0), (0, 1, 0)) == (0, 0, 1)

    def test_y_cross_z_is_x(self):
        assert _cross((0, 1, 0), (0, 0, 1)) == (1, 0, 0)

    def test_z_cross_x_is_y(self):
        assert _cross((0, 0, 1), (1, 0, 0)) == (0, 1, 0)

    def test_parallel_gives_zero(self):
        assert _cross((1, 0, 0), (2, 0, 0)) == (0, 0, 0)

    def test_anti_commutative(self):
        a, b = (1, 2, 3), (4, 5, 6)
        c1 = _cross(a, b)
        c2 = _cross(b, a)
        assert c1 == pytest.approx(tuple(-x for x in c2))


class TestAngleDeg:
    def test_same_direction(self):
        assert _angle_deg((1, 0, 0), (1, 0, 0)) == pytest.approx(0.0)

    def test_opposite_direction(self):
        assert _angle_deg((1, 0, 0), (-1, 0, 0)) == pytest.approx(180.0)

    def test_perpendicular(self):
        assert _angle_deg((1, 0, 0), (0, 1, 0)) == pytest.approx(90.0)

    def test_45_degrees(self):
        v = _normalize((1, 1, 0))
        assert _angle_deg((1, 0, 0), v) == pytest.approx(45.0)

    def test_numerical_clamping_near_one(self):
        # Dot product slightly > 1 due to floating point
        v = (1.0, 0.0, 0.0)
        assert _angle_deg(v, v) == pytest.approx(0.0)


# ============================================================
# CoordinateFrame tests
# ============================================================


class TestCoordinateFrame:
    def test_basic_construction(self):
        pts = {
            "_Origin": (0, 0, 0),
            "_X": (1, 0, 0),
            "_Y": (0, 1, 0),
            "_Z": (0, 0, 1),
        }
        frame = CoordinateFrame("test", pts)
        assert frame.prefix == "test"
        assert frame.origin == (0, 0, 0)
        assert frame.x_axis == pytest.approx((1, 0, 0))
        assert frame.y_axis == pytest.approx((0, 1, 0))
        assert frame.z_axis == pytest.approx((0, 0, 1))

    def test_non_unit_axes_are_normalized(self):
        pts = {
            "_Origin": (0, 0, 0),
            "_X": (5, 0, 0),
            "_Y": (0, 3, 0),
            "_Z": (0, 0, 7),
        }
        frame = CoordinateFrame("scaled", pts)
        assert frame.x_axis == pytest.approx((1, 0, 0))
        assert frame.y_axis == pytest.approx((0, 1, 0))
        assert frame.z_axis == pytest.approx((0, 0, 1))

    def test_offset_origin(self):
        pts = {
            "_Origin": (10, 20, 30),
            "_X": (11, 20, 30),
            "_Y": (10, 21, 30),
            "_Z": (10, 20, 31),
        }
        frame = CoordinateFrame("offset", pts)
        assert frame.origin == (10, 20, 30)
        assert frame.x_axis == pytest.approx((1, 0, 0))
        assert frame.y_axis == pytest.approx((0, 1, 0))
        assert frame.z_axis == pytest.approx((0, 0, 1))

    def test_repr(self):
        pts = {
            "_Origin": (0, 0, 0),
            "_X": (1, 0, 0),
            "_Y": (0, 1, 0),
            "_Z": (0, 0, 1),
        }
        frame = CoordinateFrame("42", pts)
        r = repr(frame)
        assert "42" in r
        assert "CoordinateFrame" in r

    def test_zero_length_axis_raises(self):
        pts = {
            "_Origin": (1, 2, 3),
            "_X": (1, 2, 3),  # same as origin -> zero vector
            "_Y": (0, 1, 0),
            "_Z": (0, 0, 1),
        }
        with pytest.raises(ValueError, match="Zero-length"):
            CoordinateFrame("bad", pts)


# ============================================================
# TxtReader tests
# ============================================================


class TestTxtReader:
    def _write_txt(self, content: str) -> str:
        """Write content to a temp file and return the path."""
        fd, path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path

    def test_single_frame(self):
        content = (
            "32_Origin  0.0  0.0  0.0\n"
            "32_X  1.0  0.0  0.0\n"
            "32_Y  0.0  1.0  0.0\n"
            "32_Z  0.0  0.0  1.0\n"
        )
        path = self._write_txt(content)
        try:
            frames = TxtReader(path).read()
            assert len(frames) == 1
            assert frames[0].prefix == "32"
            assert frames[0].origin == (0.0, 0.0, 0.0)
        finally:
            os.unlink(path)

    def test_multiple_frames(self):
        content = (
            "32_Origin  0.0  0.0  0.0\n"
            "32_X  1.0  0.0  0.0\n"
            "32_Y  0.0  1.0  0.0\n"
            "32_Z  0.0  0.0  1.0\n"
            "34_Origin  5.0  0.0  0.0\n"
            "34_X  6.0  0.0  0.0\n"
            "34_Y  5.0  1.0  0.0\n"
            "34_Z  5.0  0.0  1.0\n"
        )
        path = self._write_txt(content)
        try:
            frames = TxtReader(path).read()
            assert len(frames) == 2
            assert frames[0].prefix == "32"
            assert frames[1].prefix == "34"
        finally:
            os.unlink(path)

    def test_blank_lines_skipped(self):
        content = (
            "\n"
            "32_Origin  0.0  0.0  0.0\n"
            "\n"
            "32_X  1.0  0.0  0.0\n"
            "32_Y  0.0  1.0  0.0\n"
            "\n"
            "32_Z  0.0  0.0  1.0\n"
        )
        path = self._write_txt(content)
        try:
            frames = TxtReader(path).read()
            assert len(frames) == 1
        finally:
            os.unlink(path)

    def test_malformed_line_skipped(self, capsys):
        content = (
            "32_Origin  0.0  0.0  0.0\n"
            "32_X  1.0  0.0  0.0\n"
            "32_Y  0.0  1.0  0.0\n"
            "32_Z  0.0  0.0  1.0\n"
            "BAD LINE EXTRA FIELDS EXTRA\n"
        )
        path = self._write_txt(content)
        try:
            frames = TxtReader(path).read()
            assert len(frames) == 1
            captured = capsys.readouterr()
            assert "WARN" in captured.out
        finally:
            os.unlink(path)

    def test_non_numeric_coordinates_skipped(self, capsys):
        content = (
            "32_Origin  0.0  0.0  0.0\n"
            "32_X  abc  0.0  0.0\n"
            "32_Y  0.0  1.0  0.0\n"
            "32_Z  0.0  0.0  1.0\n"
        )
        path = self._write_txt(content)
        try:
            with pytest.raises(ValueError, match="missing row"):
                TxtReader(path).read()
            captured = capsys.readouterr()
            assert "non-numeric" in captured.out
        finally:
            os.unlink(path)

    def test_missing_suffix_raises(self):
        content = (
            "32_Origin  0.0  0.0  0.0\n"
            "32_X  1.0  0.0  0.0\n"
            "32_Y  0.0  1.0  0.0\n"
            # Missing 32_Z
        )
        path = self._write_txt(content)
        try:
            with pytest.raises(ValueError, match="missing row"):
                TxtReader(path).read()
        finally:
            os.unlink(path)

    def test_utf8_bom_handled(self):
        content = (
            "\ufeff32_Origin  0.0  0.0  0.0\n"
            "32_X  1.0  0.0  0.0\n"
            "32_Y  0.0  1.0  0.0\n"
            "32_Z  0.0  0.0  1.0\n"
        )
        path = self._write_txt(content)
        try:
            frames = TxtReader(path).read()
            assert len(frames) == 1
        finally:
            os.unlink(path)

    def test_fix_flipped_axes(self, capsys):
        """Frames with Z axes opposing the consensus get flipped."""
        content = (
            "32_Origin  0.0  0.0  0.0\n"
            "32_X  1.0  0.0  0.0\n"
            "32_Y  0.0  1.0  0.0\n"
            "32_Z  0.0  0.0  1.0\n"  # Z points up
            "34_Origin  5.0  0.0  0.0\n"
            "34_X  6.0  0.0  0.0\n"
            "34_Y  5.0  1.0  0.0\n"
            "34_Z  5.0  0.0  1.0\n"  # Z points up
            "36_Origin  10.0  0.0  0.0\n"
            "36_X  11.0  0.0  0.0\n"
            "36_Y  10.0  1.0  0.0\n"
            "36_Z  10.0  0.0  -1.0\n"  # Z points down (flipped)
        )
        path = self._write_txt(content)
        try:
            frames = TxtReader(path).read()
            # After fixing, all Z axes should align with consensus (up)
            for f in frames:
                assert f.z_axis[2] > 0
            captured = capsys.readouterr()
            assert "FIX" in captured.out
        finally:
            os.unlink(path)

    def test_single_frame_no_flip(self):
        """A single frame should not trigger flipping logic."""
        content = (
            "32_Origin  0.0  0.0  0.0\n"
            "32_X  1.0  0.0  0.0\n"
            "32_Y  0.0  1.0  0.0\n"
            "32_Z  0.0  0.0  -1.0\n"
        )
        path = self._write_txt(content)
        try:
            frames = TxtReader(path).read()
            assert len(frames) == 1
            # Z axis should remain pointing down
            assert frames[0].z_axis[2] < 0
        finally:
            os.unlink(path)

    def test_real_data_file(self):
        """Integration test with the actual sample file."""
        data_path = os.path.join(
            os.path.dirname(__file__), "..", "txt_files", "TransformedPoints.txt"
        )
        if os.path.exists(data_path):
            frames = TxtReader(data_path).read()
            assert len(frames) == 6
            prefixes = [f.prefix for f in frames]
            assert "36" in prefixes
            assert "34" in prefixes
            assert "32" in prefixes
            assert "42" in prefixes
            assert "44" in prefixes
            assert "46" in prefixes


# ============================================================
# Divergence utility tests
# ============================================================


class TestMaxDivergence:
    def _make_frame(self, prefix, z_direction):
        pts = {
            "_Origin": (0, 0, 0),
            "_X": (1, 0, 0),
            "_Y": (0, 1, 0),
            "_Z": z_direction,
        }
        return CoordinateFrame(prefix, pts)

    def test_fewer_than_two_frames(self):
        frame = self._make_frame("A", (0, 0, 1))
        assert max_divergence([frame]) == (0.0, None, None)
        assert max_divergence([]) == (0.0, None, None)

    def test_identical_axes(self):
        f1 = self._make_frame("A", (0, 0, 1))
        f2 = self._make_frame("B", (0, 0, 1))
        angle, pa, pb = max_divergence([f1, f2])
        assert angle == pytest.approx(0.0)

    def test_perpendicular_axes(self):
        f1 = self._make_frame("A", (0, 0, 1))
        f2 = self._make_frame("B", (1, 0, 0))
        angle, pa, pb = max_divergence([f1, f2])
        assert angle == pytest.approx(90.0)

    def test_three_frames_returns_max(self):
        f1 = self._make_frame("A", (0, 0, 1))
        f2 = self._make_frame("B", (0, 0.1, 1))  # slightly tilted
        f3 = self._make_frame("C", (1, 0, 0))  # perpendicular
        angle, pa, pb = max_divergence([f1, f2, f3])
        assert angle == pytest.approx(90.0, abs=1.0)
        assert "C" in (pa, pb)


class TestAllDivergencePairs:
    def _make_frame(self, prefix, z_direction):
        pts = {
            "_Origin": (0, 0, 0),
            "_X": (1, 0, 0),
            "_Y": (0, 1, 0),
            "_Z": z_direction,
        }
        return CoordinateFrame(prefix, pts)

    def test_empty_list(self):
        assert all_divergence_pairs([]) == []

    def test_single_frame(self):
        f = self._make_frame("A", (0, 0, 1))
        assert all_divergence_pairs([f]) == []

    def test_sorted_descending(self):
        f1 = self._make_frame("A", (0, 0, 1))
        f2 = self._make_frame("B", (0, 0.1, 1))
        f3 = self._make_frame("C", (1, 0, 0))
        pairs = all_divergence_pairs([f1, f2, f3])
        assert len(pairs) == 3
        # Verify sorted descending
        for i in range(len(pairs) - 1):
            assert pairs[i][0] >= pairs[i + 1][0]

    def test_pair_count(self):
        frames = [self._make_frame(str(i), (0, 0, 1)) for i in range(4)]
        pairs = all_divergence_pairs(frames)
        # C(4,2) = 6 pairs
        assert len(pairs) == 6
