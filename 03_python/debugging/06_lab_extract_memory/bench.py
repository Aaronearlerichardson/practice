"""Peak Python memory of summarize_lab_extract at increasing file sizes.

    python 03_python\\debugging\\06_lab_extract_memory\\bench.py

Target: peak < 8 MB regardless of file size (the Glue worker has to handle
multi-GB extracts). Stops early once a size goes over the budget.
Files are generated in a temporary directory and deleted afterwards.
"""
import tempfile
import time
import tracemalloc
from pathlib import Path

from buggy import summarize_lab_extract
from test_06_lab_extract_memory import write_extract

BUDGET_MB = 8.0


def main():
    print(f"target: peak < {BUDGET_MB} MB at every size")
    with tempfile.TemporaryDirectory() as tmp:
        for size_mb in (5, 10, 25, 50, 100):
            path = Path(tmp) / f"labs_{size_mb}mb.csv"
            write_extract(path, size_mb * 2**20)
            tracemalloc.start()
            t0 = time.perf_counter()
            summarize_lab_extract(path)
            elapsed = time.perf_counter() - t0
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            peak_mb = peak / 2**20
            print(f"{size_mb:>5} MB file  peak {peak_mb:8.2f} MB  ({elapsed:.1f} s, traced)")
            path.unlink()
            if peak_mb > BUDGET_MB:
                print(f"over budget at {size_mb} MB; stopping")
                return
    print("within budget at every size")


if __name__ == "__main__":
    main()
