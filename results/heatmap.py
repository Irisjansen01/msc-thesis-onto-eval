"""Create a heatmap of top-level placements across card-sort JSON exports."""

from __future__ import annotations

import argparse
import csv
import json
import textwrap
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = Path(__file__).resolve().parent / "card-sort-outcome"
DEFAULT_OUTPUT = Path(__file__).with_name("card_sort_heatmap.png")
DEFAULT_CSV_OUTPUT = Path(__file__).with_name("card_sort_heatmap.csv")
SPECIAL_PLACEMENTS = ("Set aside", "Unsorted")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot how often each card was assigned to each top-level category."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=f"Directory containing card-sort JSON files (default: {DEFAULT_INPUT_DIR})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"PNG output path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=DEFAULT_CSV_OUTPUT,
        help=f"CSV output path (default: {DEFAULT_CSV_OUTPUT})",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Open the plot after writing the output files.",
    )
    return parser.parse_args()


def load_exports(input_dir: Path) -> list[dict[str, Any]]:
    files = sorted(input_dir.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No JSON files found in {input_dir}")

    exports = []
    for path in files:
        try:
            with path.open(encoding="utf-8") as file:
                export = json.load(file)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Could not parse {path}: {exc}") from exc
        export["_source_file"] = path.name
        exports.append(export)
    return exports


def card_label(card_id: str, titles: dict[str, str]) -> str:
    return f"{card_id} - {titles.get(card_id, 'Unknown card')}"


def collect_placements(
    exports: list[dict[str, Any]],
) -> tuple[list[str], dict[str, str], list[str], dict[str, Counter[str]]]:
    category_labels: list[str] = []
    titles: dict[str, str] = {}
    placements: dict[str, Counter[str]] = {}

    for export in exports:
        seen_in_export: set[str] = set()

        for category in export.get("top_categories", []):
            label = f"{category['letter']}. {category['name']}"
            if label not in category_labels:
                category_labels.append(label)

            cards = list(category.get("direct_cards", []))
            for subcategory in category.get("subcategory_instances", []):
                cards.extend(subcategory.get("cards", []))
            record_cards(cards, label, titles, placements, seen_in_export, export)

        record_cards(
            export.get("set_aside", []),
            "Set aside",
            titles,
            placements,
            seen_in_export,
            export,
        )
        record_cards(
            export.get("unsorted", []),
            "Unsorted",
            titles,
            placements,
            seen_in_export,
            export,
        )

        expected_ids = set(export.get("active_card_ids", []))
        missing_ids = expected_ids - seen_in_export
        if missing_ids:
            source = export["_source_file"]
            missing = ", ".join(sorted(missing_ids))
            raise ValueError(f"{source} has cards without a placement: {missing}")

    card_ids = sorted(placements, key=card_sort_key)
    return category_labels, titles, card_ids, placements


def record_cards(
    cards: list[dict[str, Any]],
    placement: str,
    titles: dict[str, str],
    placements: dict[str, Counter[str]],
    seen_in_export: set[str],
    export: dict[str, Any],
) -> None:
    for card in cards:
        card_id = card["id"]
        if card_id in seen_in_export:
            source = export["_source_file"]
            raise ValueError(f"{source} places {card_id} more than once")
        seen_in_export.add(card_id)
        titles.setdefault(card_id, card.get("title", "Unknown card"))
        placements.setdefault(card_id, Counter())[placement] += 1


def card_sort_key(card_id: str) -> tuple[str, int | str]:
    prefix = card_id.rstrip("0123456789")
    suffix = card_id[len(prefix) :]
    return prefix, int(suffix) if suffix else card_id


def build_matrix(
    card_ids: list[str],
    columns: list[str],
    placements: dict[str, Counter[str]],
) -> np.ndarray:
    return np.array(
        [[placements[card_id][column] for column in columns] for card_id in card_ids],
        dtype=int,
    )


def write_csv(
    output_path: Path,
    card_ids: list[str],
    titles: dict[str, str],
    columns: list[str],
    matrix: np.ndarray,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["card_id", "card_title", *columns])
        for card_id, row in zip(card_ids, matrix, strict=True):
            writer.writerow([card_id, titles[card_id], *row])


def plot_heatmap(
    output_path: Path,
    card_ids: list[str],
    titles: dict[str, str],
    columns: list[str],
    matrix: np.ndarray,
    participant_count: int,
    show: bool,
) -> None:
    row_height = 0.34
    fig_height = max(8, len(card_ids) * row_height + 2.5)
    fig, ax = plt.subplots(figsize=(15, fig_height))
    image = ax.imshow(matrix, cmap="Blues", aspect="auto", vmin=0, vmax=participant_count)

    ax.set_xticks(range(len(columns)))
    ax.set_xticklabels(
        ["\n".join(textwrap.wrap(column, width=24)) for column in columns],
        rotation=30,
        ha="right",
    )
    ax.set_yticks(range(len(card_ids)))
    ax.set_yticklabels([card_label(card_id, titles) for card_id in card_ids], fontsize=8)
    ax.set_xlabel("Top-level card-sort placement")
    ax.set_ylabel("Evaluation method card")
    ax.set_title(f"Card-sort placements across {participant_count} submissions")

    for row_index, row in enumerate(matrix):
        for column_index, value in enumerate(row):
            text_color = "white" if value > participant_count / 2 else "black"
            ax.text(
                column_index,
                row_index,
                str(value),
                ha="center",
                va="center",
                color=text_color,
                fontsize=8,
            )

    colorbar = fig.colorbar(image, ax=ax, pad=0.01)
    colorbar.set_label("Number of submissions")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)


def main() -> None:
    args = parse_args()
    exports = load_exports(args.input_dir)
    category_labels, titles, card_ids, placements = collect_placements(exports)
    columns = [*category_labels, *SPECIAL_PLACEMENTS]
    matrix = build_matrix(card_ids, columns, placements)

    write_csv(args.csv_output, card_ids, titles, columns, matrix)
    plot_heatmap(
        args.output,
        card_ids,
        titles,
        columns,
        matrix,
        participant_count=len(exports),
        show=args.show,
    )
    print(f"Processed {len(exports)} card-sort exports.")
    print(f"Wrote heatmap to {args.output}")
    print(f"Wrote counts to {args.csv_output}")


if __name__ == "__main__":
    main()

