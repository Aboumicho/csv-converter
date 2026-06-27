"""Unit tests for main.py."""

import os
import sys
import tempfile

import pytest

from main import DEFAULT_AXIS_LENGTH, DEFAULT_CAMERA_SERIAL, DiscoveryPipeline, FilePipeline


# ============================================================
# FilePipeline tests
# ============================================================


class TestFilePipeline:
    def _create_txt_file(self, tmpdir, name="Test.txt"):
        txt_dir = os.path.join(tmpdir, "txt_files")
        os.makedirs(txt_dir, exist_ok=True)
        txt_path = os.path.join(txt_dir, name)
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
        with open(txt_path, "w") as fh:
            fh.write(content)
        return txt_path

    def test_run_produces_csv_and_stl(self):
        tmpdir = tempfile.mkdtemp()
        txt_path = self._create_txt_file(tmpdir)

        pipeline = FilePipeline(txt_path, tmpdir)
        csv_path, stl_path = pipeline.run()

        assert os.path.isfile(csv_path)
        assert os.path.isfile(stl_path)
        assert csv_path.endswith(".csv")
        assert stl_path.endswith(".stl")

    def test_output_directory_structure(self):
        tmpdir = tempfile.mkdtemp()
        txt_path = self._create_txt_file(tmpdir, "MyPoints.txt")

        pipeline = FilePipeline(txt_path, tmpdir)
        csv_path, stl_path = pipeline.run()

        # Output should be in files/MyPoints/
        assert "MyPoints" in csv_path
        assert os.path.join("files", "MyPoints") in csv_path

    def test_custom_camera_serial(self):
        tmpdir = tempfile.mkdtemp()
        txt_path = self._create_txt_file(tmpdir)

        pipeline = FilePipeline(txt_path, tmpdir, camera_serial="12345678")
        csv_path, _ = pipeline.run()

        with open(csv_path) as fh:
            content = fh.read()
        assert "12345678" in content

    def test_custom_axis_length(self):
        tmpdir = tempfile.mkdtemp()
        txt_path = self._create_txt_file(tmpdir)

        # Should not raise - just uses the parameter
        pipeline = FilePipeline(txt_path, tmpdir, axis_length=15.0)
        csv_path, stl_path = pipeline.run()
        assert os.path.isfile(stl_path)

    def test_default_parameters(self):
        tmpdir = tempfile.mkdtemp()
        txt_path = self._create_txt_file(tmpdir)

        pipeline = FilePipeline(txt_path, tmpdir)
        assert pipeline.camera_serial == DEFAULT_CAMERA_SERIAL
        assert pipeline.axis_length == DEFAULT_AXIS_LENGTH


# ============================================================
# DiscoveryPipeline tests
# ============================================================


class TestDiscoveryPipeline:
    def _setup_project(self, tmpdir, files=None):
        """Create a project directory with txt_files/ containing given files."""
        txt_dir = os.path.join(tmpdir, "txt_files")
        os.makedirs(txt_dir, exist_ok=True)

        if files is None:
            files = {"Test.txt": (
                "32_Origin  0.0  0.0  0.0\n"
                "32_X  1.0  0.0  0.0\n"
                "32_Y  0.0  1.0  0.0\n"
                "32_Z  0.0  0.0  1.0\n"
            )}

        for name, content in files.items():
            with open(os.path.join(txt_dir, name), "w") as fh:
                fh.write(content)

        return tmpdir

    def test_discovers_and_processes_files(self, capsys):
        tmpdir = tempfile.mkdtemp()
        self._setup_project(tmpdir)

        pipeline = DiscoveryPipeline(tmpdir)
        pipeline.run()

        # Output files should be created
        output_dir = os.path.join(tmpdir, "files", "Test")
        assert os.path.isdir(output_dir)

        captured = capsys.readouterr()
        assert "succeeded" in captured.out

    def test_no_files_exits_gracefully(self, capsys):
        tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(tmpdir, "txt_files"))

        pipeline = DiscoveryPipeline(tmpdir)
        pipeline.run()

        captured = capsys.readouterr()
        assert "No .txt files" in captured.out

    def test_multiple_files(self, capsys):
        tmpdir = tempfile.mkdtemp()
        files = {
            "A.txt": (
                "32_Origin  0.0  0.0  0.0\n"
                "32_X  1.0  0.0  0.0\n"
                "32_Y  0.0  1.0  0.0\n"
                "32_Z  0.0  0.0  1.0\n"
            ),
            "B.txt": (
                "34_Origin  5.0  0.0  0.0\n"
                "34_X  6.0  0.0  0.0\n"
                "34_Y  5.0  1.0  0.0\n"
                "34_Z  5.0  0.0  1.0\n"
            ),
        }
        self._setup_project(tmpdir, files)

        pipeline = DiscoveryPipeline(tmpdir)
        pipeline.run()

        captured = capsys.readouterr()
        assert "2 succeeded" in captured.out

    def test_handles_error_in_file(self, capsys):
        tmpdir = tempfile.mkdtemp()
        files = {
            "Good.txt": (
                "32_Origin  0.0  0.0  0.0\n"
                "32_X  1.0  0.0  0.0\n"
                "32_Y  0.0  1.0  0.0\n"
                "32_Z  0.0  0.0  1.0\n"
            ),
            "Bad.txt": (
                "32_Origin  0.0  0.0  0.0\n"
                # Missing _X, _Y, _Z -> will fail validation
            ),
        }
        self._setup_project(tmpdir, files)

        pipeline = DiscoveryPipeline(tmpdir)
        pipeline.run()

        captured = capsys.readouterr()
        assert "1 succeeded" in captured.out
        assert "1 failed" in captured.out
        assert "FAILED" in captured.out

    def test_project_dir_resolved_to_absolute(self):
        tmpdir = tempfile.mkdtemp()
        self._setup_project(tmpdir)

        pipeline = DiscoveryPipeline(tmpdir)
        assert os.path.isabs(pipeline.project_dir)

    def test_custom_camera_and_axis(self, capsys):
        tmpdir = tempfile.mkdtemp()
        self._setup_project(tmpdir)

        pipeline = DiscoveryPipeline(
            tmpdir, camera_serial="99887766", axis_length=5.0
        )
        pipeline.run()

        csv_path = os.path.join(tmpdir, "files", "Test", "Test.csv")
        with open(csv_path) as fh:
            content = fh.read()
        assert "99887766" in content

    def test_print_summary_with_all_errors(self, capsys):
        tmpdir = tempfile.mkdtemp()
        files = {
            "Bad1.txt": (
                "32_Origin  0.0  0.0  0.0\n"
                # Missing _X, _Y, _Z
            ),
            "Bad2.txt": (
                "34_Origin  5.0  0.0  0.0\n"
                # Missing _X, _Y, _Z
            ),
        }
        self._setup_project(tmpdir, files)

        pipeline = DiscoveryPipeline(tmpdir)
        pipeline.run()

        captured = capsys.readouterr()
        assert "0 succeeded" in captured.out
        assert "2 failed" in captured.out


# ============================================================
# CLI argument parsing tests
# ============================================================


class TestCLI:
    def test_parse_args_defaults(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["main.py"])
        from main import _parse_args
        args = _parse_args()
        assert args.project_dir == os.getcwd()
        assert args.camera_serial == DEFAULT_CAMERA_SERIAL
        assert args.axis_length == DEFAULT_AXIS_LENGTH

    def test_parse_args_custom(self, monkeypatch):
        monkeypatch.setattr(
            sys, "argv",
            ["main.py", "/tmp/proj", "--camera", "ABCD1234", "--axis-length", "12.5"]
        )
        from main import _parse_args
        args = _parse_args()
        assert args.project_dir == "/tmp/proj"
        assert args.camera_serial == "ABCD1234"
        assert args.axis_length == 12.5
