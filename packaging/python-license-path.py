"""Print the license for the Python runtime used by a package build."""

import sys
import sysconfig
from pathlib import Path


version = f"{sys.version_info.major}.{sys.version_info.minor}"
prefix = Path(sys.base_prefix)
prefixes = (prefix, *list(prefix.parents)[:4])
candidates = [directory / name for directory in prefixes for name in ("LICENSE", "LICENSE.txt")]
candidates.append(Path(sysconfig.get_path("stdlib")) / "LICENSE.txt")
candidates.extend(
    (
        Path("/usr/share/doc") / f"python{version}" / "copyright",
        Path("/usr/share/doc") / f"libpython{version}-stdlib" / "copyright",
    )
)

for candidate in candidates:
    if candidate.is_file():
        print(candidate)
        break
else:
    sys.exit(f"Could not locate the Python {version} license/copyright file")
