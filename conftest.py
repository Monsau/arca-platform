"""Root pytest bootstrap — make the repo importable without PYTHONPATH.

The platform ships several import roots that are not installed as a
package: ``sdk/`` (shared config/health), ``adapters/`` (contract
adapters), ``services/*/src`` and the repo root itself (for
``services.bootstrap.src.main`` style imports). Inserting them here lets
``pytest`` run green from the repo root with no environment variables,
identically to ``python -m pytest``.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

for _path in (ROOT, ROOT / "src", ROOT / "adapters", ROOT / "sdk"):
    _str = str(_path)
    if _path.is_dir() and _str not in sys.path:
        sys.path.insert(0, _str)
