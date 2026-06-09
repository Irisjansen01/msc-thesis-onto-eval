from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPORT_DIR = REPO_ROOT / "results" / "phase1" / "card-sort-responses"
OUTPUT_DIR = REPO_ROOT / "results" / "phase1"

TOP_CATEGORY_LABELS = {
    "A": "Reference-based evaluation",
    "B": "Corpus/data-based evaluation",
    "C": "Task/application-based evaluation",
    "D": "Criteria-based evaluation",
}


def load_exports(export_dir: Path) -> list[dict]:
    export_files = sorted(export_dir.glob("*.json"))
    if not export_files:
        raise FileNotFoundError(f"No card-sort export files found in {export_dir}")
    return [json.loads(path.read_text(encoding="utf-8")) for path in export_files]


def collect_placements(export_data: dict) -> tuple[Counter, Counter, list[str], list[str]]:
    placements = Counter()
    set_aside_reasons = Counter()
    placed_cards: set[str] = set()
    set_aside_cards: set[str] = set()

    for category in export_data.get("top_categories", []):
        letter = category.get("letter", "")
        for card in category.get("direct_cards", []):
            placements[card["id"]] = letter
            placed_cards.add(card["id"])

        for instance in category.get("subcategory_instances", []):
            for card in instance.get("cards", []):
                placements[card["id"]] = letter
                placed_cards.add(card["id"])

    for item in export_data.get("set_aside", []):
        set_aside_cards.add(item["id"])
        set_aside_reasons[item.get("set_aside_reason", "unspecified")] += 1

    return placements, set_aside_reasons, sorted(placed_cards), sorted(set_aside_cards)


def build_export_summary(export_data: dict) -> dict:
    placements, set_aside_reasons, placed_cards, set_aside_cards = collect_placements(export_data)

    category_counts = Counter(placements.values())
    active_card_count = len(export_data.get("active_card_ids", []))

    return {
        "export_code": export_data.get("export_code", "UNKNOWN"),
        "source_file": f"card-sort-ontology-{export_data.get('export_code', 'UNKNOWN')}.json",
        "duration_seconds": export_data.get("duration_seconds", 0),
        "duration_hms": export_data.get("duration_hms", ""),
        "active_card_count": active_card_count,
        "placed_cards": len(placed_cards),
        "set_aside_count": len(set_aside_cards),
        "unsorted_count": len(export_data.get("unsorted", [])),
        "A_count": category_counts.get("A", 0),
        "B_count": category_counts.get("B", 0),
        "C_count": category_counts.get("C", 0),
        "D_count": category_counts.get("D", 0),
        "used_quality_dimensions": len({item.get("label") for category in export_data.get("top_categories", []) for item in category.get("subcategory_instances", [])}),
        "set_aside_reasons": dict(set_aside_reasons),
    }


def write_summary_tables(exports: list[dict]) -> None:
    summaries = [build_export_summary(item) for item in exports]
    summary_df = pd.DataFrame(summaries)

    summary_df.to_csv(OUTPUT_DIR / "card_sort_analysis_per_export.csv", index=False)

    reason_columns = [
        "reason_no_fitting_top_cat",
        "reason_other",
        "reason_unspecified",
        "reason_fits_multiple_groups",
        "reason_unclear_wording",
        "reason_not_an_evaluation",
        "reason_too_broad",
    ]
    reason_rows = []
    for item in summaries:
        row = {"export_code": item["export_code"], "source_file": item["source_file"], "set_aside_count": item["set_aside_count"]}
        reasons = item.get("set_aside_reasons", {})
        reason_map = {
            "reason_no_fitting_top_cat": reasons.get("no_fitting_top_cat", 0),
            "reason_other": reasons.get("other", 0),
            "reason_unspecified": reasons.get("unspecified", 0),
            "reason_fits_multiple_groups": reasons.get("fits_multiple_groups", 0),
            "reason_unclear_wording": reasons.get("unclear_wording", 0),
            "reason_not_an_evaluation": reasons.get("not_an_evaluation", 0),
            "reason_too_broad": reasons.get("too_broad", 0),
        }
        row.update(reason_map)
        reason_rows.append(row)
    pd.DataFrame(reason_rows).to_csv(OUTPUT_DIR / "card_sort_set_aside_summary.csv", index=False)

    # Build plurality bands from all card placements across all exports.
    card_votes = defaultdict(Counter)
    for export_item in exports:
        placements, _, _, _ = collect_placements(export_item)
        for card_id, letter in placements.items():
            card_votes[card_id][letter] += 1

    plurality_rows = []
    for card_id, votes in sorted(card_votes.items()):
        top_letter, plurality_count = votes.most_common(1)[0]
        total_votes = sum(votes.values())
        share = plurality_count / total_votes
        if share >= 0.80:
            band = "80-100%"
        elif share >= 0.60:
            band = "60-79%"
        elif share >= 0.40:
            band = "40-59%"
        else:
            band = "0-39%"
        plurality_rows.append({
            "card_id": card_id,
            "plurality_label": f"{top_letter}. {TOP_CATEGORY_LABELS.get(top_letter, 'Unknown')}",
            "plurality_count": plurality_count,
            "total_votes": total_votes,
            "plurality_share": share,
            "agreement_band": band,
        })

    pd.DataFrame(sorted(plurality_rows, key=lambda row: (row["agreement_band"], row["card_id"]))).to_csv(
        OUTPUT_DIR / "card_sort_plurality_bands.csv", index=False
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    exports = load_exports(EXPORT_DIR)
    write_summary_tables(exports)
    print(f"Wrote card-sort summaries to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
