# Building ConcoLab.exe

## Prerequisites

- Python 3.12+
- All runtime dependencies installed:

```
pip install numpy matplotlib
```

- PyInstaller:

```
pip install pyinstaller
```

---

## Build command

Run from the project root:

```
pyinstaller --onefile --windowed --name ConcoLab --hidden-import matplotlib.backends.backend_agg run_app.py
```

| Flag | Purpose |
|------|---------|
| `--onefile` | Bundle everything into a single `.exe` |
| `--windowed` | No console window (GUI-only app) |
| `--name ConcoLab` | Output file name |
| `--hidden-import matplotlib.backends.backend_agg` | Required — matplotlib's Agg backend isn't auto-detected |

---

## Output

```
dist/
  ConcoLab.exe   ← distribute this file
build/           ← intermediate files, safe to delete
ConcoLab.spec    ← keep this to rebuild without re-typing the command
```

To rebuild later using the saved spec:

```
pyinstaller ConcoLab.spec
```

---

## Distribution

Copy `ConcoLab.exe` to any folder on the target machine.  
The app will automatically create `txt_files/` and `files/` subdirectories next to the `.exe` on first use.

No Python installation is required on the target machine.

---

## Troubleshooting

**Slow first launch** — normal for `--onefile`; PyInstaller extracts to a temp folder on startup. Use `--onedir` instead if startup time is a concern (produces a folder rather than a single file).

**Antivirus false positive** — common with PyInstaller bundles. Sign the `.exe` or instruct users to whitelist it.

**Missing module error** — add `--hidden-import <module>` for any package PyInstaller fails to detect automatically.
