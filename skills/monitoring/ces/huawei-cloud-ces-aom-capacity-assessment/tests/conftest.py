import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
SKILL_DIR = Path(__file__).resolve().parent.parent

# The skill ships `scripts/` as its import root (capacity_cli.py + the capacity/ package).
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))