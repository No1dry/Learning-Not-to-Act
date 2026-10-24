import os
import sys
from pathlib import Path

# The caller supplies the checkout; no vendored scorer or hidden server path.
if os.environ.get("EGRS_CORE_ROOT"):
    sys.path.insert(0, str(Path(os.environ["EGRS_CORE_ROOT"]).resolve()))
