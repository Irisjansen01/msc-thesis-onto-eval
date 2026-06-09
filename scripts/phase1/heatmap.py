from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPORT_DIR = REPO_ROOT / "results" / "phase1" / "card-sort-responses"
OUTPUT_DIR = REPO_ROOT / "results" / "phase1"

CARD_ORDER = [
    "M13", "M19", "M21", "M22", "M23", "M24", "M25", "M26", "M27", "M29",
    "M28", "M31", "M37", "M40",
    "M32", "M34",
    "M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08", "M09", "M10",
    "M11", "M12", "M14", "M15", "M16", "M17", "M18", "M20", "M30", "M33",
    "M35", "M36", "M38", "M39",
]


def load_exports(export_dir: Path) -> list[dict]:
    export_files = sorted(export_dir.glob("*.json"))
    if not export_files:
        raise FileNotFoundError(f"No card-sort export files found in {export_dir}")
    return [json.loads(path.read_text(encoding="utf-8")) for path in export_files]


def collect_card_set(export_data: dict) -> set[str]:
    cards: set[str] = set()
    for category in export_data.get("top_categories", []):
        for card in category.get("direct_cards", []):
            cards.add(card["id"])
        for instance in category.get("subcategory_instances", []):
            for card in instance.get("cards", []):
                cards.add(card["id"])
    return cards


def build_heatmap_matrix(exports: list[dict]) -> pd.DataFrame:
    card_to_idx = {card: idx for idx, card in enumerate(CARD_ORDER)}
    matrix = np.zeros((len(CARD_ORDER), len(CARD_ORDER)), dtype=int)

    for export_data in exports:
        cards = sorted(collect_card_set(export_data))
        for left in cards:
            for right in cards:
                if left in card_to_idx and right in card_to_idx:
                    matrix[card_to_idx[left], card_to_idx[right]] += 1

    np.fill_diagonal(matrix, 0)
    return pd.DataFrame(matrix, index=CARD_ORDER, columns=CARD_ORDER)


def write_heatmap(df: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_DIR / "card_sort_heatmap.csv")

    plt.style.use("seaborn-v0_8-white")
    fig, ax = plt.subplots(figsize=(14, 14))
    mask = np.eye(df.shape[0], dtype=bool)
    sns.heatmap(
        df,
        mask=mask,
        cmap="Blues",
        annot=False,
        cbar_kws={"label": "Co-occurrences across exports"},
        ax=ax,
    )
    ax.set_title("Card-sort co-occurrence heatmap")
    ax.tick_params(axis="both", labelsize=6)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "card_sort_heatmap.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    exports = load_exports(EXPORT_DIR)
    df = build_heatmap_matrix(exports)
    write_heatmap(df)
    print(f"Wrote heatmap CSV/PNG to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
