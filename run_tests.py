from pathlib import Path
import sys
import unittest


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


if __name__ == "__main__":
    package_root = Path(__file__).resolve().parent
    suite = unittest.defaultTestLoader.discover(str(package_root / "tests"), top_level_dir=str(package_root.parent))
    raise SystemExit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
