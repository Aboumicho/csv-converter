
import os
import csv


class FileReader:
    """
    Reads a whitespace-delimited .txt file and converts it to a CSV file.
    The output CSV is saved in the /converted directory with the same base name.
    """

    HEADERS = ["Point", "X", "Y", "Z"]
    OUTPUT_DIR = "converted"

    def __init__(self, filepath: str):
        """
        Initialize the FileReader with the path to a .txt file.

        :param filepath: Full or relative path to the source .txt file.
        """
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.base_name = os.path.splitext(self.filename)[0]
        self._rows: list[dict] = []

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self) -> str:
        """
        Orchestrates the full pipeline: read → parse → save.

        :returns: Path to the generated CSV file.
        """
        self._read()
        output_path = self._save()
        return output_path

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _read(self) -> None:
        """Open the .txt file and parse every non-empty line into a row dict."""
        self._rows.clear()

        with open(self.filepath, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue

                parts = line.split()

                if len(parts) != 4:
                    print(
                        f"[WARNING] Skipping malformed line in '{self.filename}': {line!r}"
                    )
                    continue

                point, x, y, z = parts
                self._rows.append({"Point": point, "X": x, "Y": y, "Z": z})

    def _save(self) -> str:
        """Write the parsed rows to a CSV file inside OUTPUT_DIR."""
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(self.OUTPUT_DIR, f"{self.base_name}.csv")

        with open(output_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=self.HEADERS)
            writer.writeheader()
            writer.writerows(self._rows)

        print(f"[OK] '{self.filename}' → '{output_path}' ({len(self._rows)} rows)")
        return output_path

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"FileReader(filepath={self.filepath!r})"