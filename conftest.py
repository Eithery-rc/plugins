"""Root conftest — adds scripts dir to sys.path so modules can be imported by name."""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent / "skills" / "bank-statement-to-elba" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
