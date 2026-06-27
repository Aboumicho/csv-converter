"""
discovery_pipeline.py
=====================
Scans ``PROJECT_DIR/txt_files/`` for ``.txt`` files and runs
:class:`~csv_writer.file_pipeline.FilePipeline` on each one.
"""

import glob
import os

from csv_writer.file_pipeline import FilePipeline, DEFAULT_CAMERA_SERIAL


class DiscoveryPipeline:
    """
    Discovers every ``.txt`` file inside ``PROJECT_DIR/txt_files/`` and runs
    :class:`FilePipeline` on each one.

    Parameters
    ----------
    project_dir : str
        Root project directory.
    camera_serial : str
        Forwarded to :class:`FilePipeline` / :class:`MicronMapperCSVWriter`.
    """

    TXT_SUBDIR = "txt_files"

    def __init__(
        self,
        project_dir: str,
        camera_serial: str = DEFAULT_CAMERA_SERIAL,
    ):
        self.project_dir = os.path.abspath(project_dir)
        self.camera_serial = camera_serial

    # ----------------------------------------------------------
    def run(self) -> list:
        """Scan for ``.txt`` files, process each one, print a summary."""
        txt_dir = os.path.join(self.project_dir, self.TXT_SUBDIR)
        files = sorted(glob.glob(os.path.join(txt_dir, "*.txt")))

        if not files:
            print(f"[INFO] No .txt files found in '{txt_dir}'. Exiting.")
            return []

        print(f"Project dir   : {self.project_dir}")
        print(f"Input dir     : {txt_dir}")
        print(f"Files found   : {[os.path.basename(f) for f in files]}")
        print(f"Camera serial : {self.camera_serial}")

        results = []
        for txt_path in files:
            try:
                csv_path = FilePipeline(
                    txt_path=txt_path,
                    project_dir=self.project_dir,
                    camera_serial=self.camera_serial,
                ).run()
                results.append((txt_path, csv_path, None))
            except Exception as exc:
                print(f"  [ERROR] {exc}")
                results.append((txt_path, None, exc))

        self._print_summary(results)
        return results

    # ----------------------------------------------------------
    def _print_summary(self, results: list) -> None:
        ok = sum(1 for *_, e in results if e is None)
        err = len(results) - ok
        print(f"\n{'=' * 60}")
        print(f"Done: {ok} succeeded, {err} failed.")
        if ok:
            print(f"Outputs written to: {os.path.join(self.project_dir, 'files')}/")
        if err:
            for txt_path, _, exc in results:
                if exc:
                    print(f"  FAILED: {os.path.basename(txt_path)} - {exc}")
        print("=" * 60)
