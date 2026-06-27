"""
run_app.py
==========
Entry point used by PyInstaller to build ConcoLab.exe.
Can also be run directly:  python run_app.py
"""

import os
import sys

if getattr(sys, "frozen", False):
    _ROOT = os.path.dirname(sys.executable)
else:
    _ROOT = os.path.dirname(os.path.abspath(__file__))

if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ui.app import main  # noqa: E402

if __name__ == "__main__":
    main()
