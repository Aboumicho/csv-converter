import os
import glob

from file_reader import FileReader


class ConversionPipeline:
    """
    Discovers all .txt files in the 'files' directory and converts each one
    to CSV using FileReader.
    """

    def __init__(self):
        """Initialize the pipeline with the fixed 'files' input directory."""
        self.source_dir = "files"
        self._txt_files: list[str] = []
        self._results: list[str] = []

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Full pipeline: discover files → convert each one → report."""
        self._discover()

        if not self._txt_files:
            print(f"[INFO] No .txt files found in '{self.source_dir}/'. Exiting.")
            return

        print(f"[INFO] Found {len(self._txt_files)} .txt file(s) to convert.\n")

        for filepath in self._txt_files:
            reader = FileReader(filepath)
            output_path = reader.run()
            self._results.append(output_path)

        self._report()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _discover(self) -> None:
        """Collect all .txt files inside source_dir (non-recursive)."""
        pattern = os.path.join(self.source_dir, "*.txt")
        self._txt_files = sorted(glob.glob(pattern))

    def _report(self) -> None:
        """Print a summary of converted files."""
        print(f"\n{'=' * 50}")
        print(f"Conversion complete: {len(self._results)} file(s) saved.")
        print(f"Output directory  : '{FileReader.OUTPUT_DIR}/'")
        print("=" * 50)

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"ConversionPipeline(source_dir={self.source_dir!r})"


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    pipeline = ConversionPipeline()
    pipeline.run()


if __name__ == "__main__":
    main()