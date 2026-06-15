"""Per-export summaries and plurality bands. See phase1_report.py for the full analysis."""

from __future__ import annotations

from card_sort_common import EXPORT_DIR, OUTPUT_DIR, load_exports
from phase1_report import write_per_export_tables


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    exports = load_exports(EXPORT_DIR)
    write_per_export_tables(exports)
    print(f"Wrote card-sort summaries to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
