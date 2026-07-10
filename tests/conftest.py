import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / "skill" / "charity-donor-outreach"

sys.path.insert(0, str(SKILL_DIR / "scripts"))
