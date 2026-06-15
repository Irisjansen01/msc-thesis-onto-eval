from __future__ import annotations

import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPORT_DIR = REPO_ROOT / "results" / "phase1" / "card-sort-responses"
OUTPUT_DIR = REPO_ROOT / "results" / "phase1"

CARD_IDS = [f"M{index:02d}" for index in range(1, 41)]

TOP_CATEGORY_LABELS = {
    "A": "Reference-based evaluation",
    "B": "Corpus/data-based evaluation",
    "C": "Task/application-based evaluation",
    "D": "Criteria-based evaluation",
}

# Cards with plurality agreement below this threshold are reported as boundary cases.
BOUNDARY_AGREEMENT_THRESHOLD = 0.60

CATEGORY_CODES = ("A", "B", "C", "D")
HEATMAP_CATEGORY_CODES = ("A", "B", "C", "D", "SA")

CATEGORY_COLORS = {
    "A": "#4C78A8",
    "B": "#F58518",
    "C": "#54A24B",
    "D": "#E45756",
}


def load_exports(export_dir: Path = EXPORT_DIR) -> list[dict]:
    export_files = sorted(export_dir.glob("*.json"))
    if not export_files:
        raise FileNotFoundError(f"No card-sort export files found in {export_dir}")
    return [json.loads(path.read_text(encoding="utf-8")) for path in export_files]


def collect_placements(export_data: dict) -> tuple[Counter, Counter, set[str], set[str]]:
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

    return placements, set_aside_reasons, placed_cards, set_aside_cards


def participant_label(export_data: dict) -> str:
    return export_data.get("export_code", "UNKNOWN")


def collect_quality_dimension_stats(export_data: dict) -> dict:
    instances = [
        instance
        for category in export_data.get("top_categories", [])
        for instance in category.get("subcategory_instances", [])
    ]
    suggested_instances = [instance for instance in instances if not instance.get("is_custom_label", True)]
    custom_instances = [instance for instance in instances if instance.get("is_custom_label", False)]

    suggested_chip_ids = {
        instance.get("source_chip_id")
        for instance in suggested_instances
        if instance.get("source_chip_id")
    }

    return {
        "quality_concern_instances": len(instances),
        "suggested_instances": len(suggested_instances),
        "custom_instances": len(custom_instances),
        "distinct_suggested_chip_ids": len(suggested_chip_ids),
        "used_any_quality_concern": len(instances) > 0,
        "used_suggested_set": len(suggested_instances) > 0,
    }


def build_participant_matrix(exports: list[dict]) -> tuple[list[str], dict[str, dict[str, str]]]:
    participants = [participant_label(item) for item in exports]
    matrix: dict[str, dict[str, str]] = {}

    for export_data in exports:
        participant = participant_label(export_data)
        placements, _, _, set_aside_cards = collect_placements(export_data)
        row: dict[str, str] = {}

        for card_id in CARD_IDS:
            if card_id in placements:
                row[card_id] = placements[card_id]
            elif card_id in set_aside_cards:
                row[card_id] = "SA"
            else:
                row[card_id] = ""

        matrix[participant] = row

    return participants, matrix


def build_card_vote_table(exports: list[dict], n_participants: int) -> pd.DataFrame:
    card_votes: dict[str, Counter] = {card_id: Counter() for card_id in CARD_IDS}

    for export_data in exports:
        placements, _, _, set_aside_cards = collect_placements(export_data)
        for card_id in CARD_IDS:
            if card_id in placements:
                card_votes[card_id][placements[card_id]] += 1
            elif card_id in set_aside_cards:
                card_votes[card_id]["SA"] += 1

    rows = []
    for card_id in CARD_IDS:
        votes = card_votes[card_id]
        category_votes = {letter: votes.get(letter, 0) for letter in CATEGORY_CODES}
        sa_votes = votes.get("SA", 0)
        if category_votes:
            majority_letter, majority_count = max(category_votes.items(), key=lambda item: item[1])
        else:
            majority_letter, majority_count = "", 0

        # Set-aside is missing, not disagreement: exclude from the plurality denominator.
        plurality_denominator = n_participants - sa_votes
        agreement_rate = (
            majority_count / plurality_denominator if plurality_denominator > 0 else 0.0
        )

        rows.append({
            "card_id": card_id,
            "majority_category": majority_letter,
            "majority_label": f"{majority_letter}. {TOP_CATEGORY_LABELS.get(majority_letter, '')}".strip(". "),
            "majority_count": majority_count,
            "plurality_denominator": plurality_denominator,
            "agreement_rate": agreement_rate,
            "A_votes": category_votes["A"],
            "B_votes": category_votes["B"],
            "C_votes": category_votes["C"],
            "D_votes": category_votes["D"],
            "SA_votes": sa_votes,
            "total_placed_votes": sum(category_votes.values()),
        })

    return pd.DataFrame(rows)


def agreement_band(share: float) -> str:
    if share >= 0.80:
        return "80-100%"
    if share >= 0.60:
        return "60-79%"
    if share >= 0.40:
        return "40-59%"
    return "0-39%"


def build_agreement_band_table(card_table: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for card_id, share in zip(card_table["card_id"], card_table["agreement_rate"], strict=True):
        rows.append({
            "card_id": card_id,
            "agreement_rate": share,
            "agreement_band": agreement_band(share),
        })

    summary = (
        pd.DataFrame(rows)
        .groupby("agreement_band", as_index=False)
        .size()
        .rename(columns={"size": "card_count"})
    )
    band_order = ["80-100%", "60-79%", "40-59%", "0-39%"]
    summary["agreement_band"] = pd.Categorical(summary["agreement_band"], categories=band_order, ordered=True)
    return summary.sort_values("agreement_band").reset_index(drop=True)


def boundary_card_ids(
    card_table: pd.DataFrame,
    threshold: float = BOUNDARY_AGREEMENT_THRESHOLD,
) -> list[str]:
    """Cards with plurality agreement strictly below *threshold* (default 60%)."""
    return sorted(
        card_table.loc[card_table["agreement_rate"] < threshold, "card_id"].tolist()
    )


def krippendorff_alpha_nominal(
    participants: list[str],
    participant_matrix: dict[str, dict[str, str]],
) -> tuple[float, float, float]:
    """
    Nominal Krippendorff's alpha over top-level placements (A/B/C/D).
    Set-aside and missing placements are excluded from each unit.
    Returns (alpha, D_o, D_e).
    """
    units = []
    for card_id in CARD_IDS:
        values = []
        for participant in participants:
            code = participant_matrix[participant].get(card_id, "")
            if code in CATEGORY_CODES:
                values.append(code)
        if len(values) >= 2:
            units.append(values)

    do_num = 0
    do_den = 0
    category_counts: Counter[str] = Counter()
    total_values = 0

    for values in units:
        total_values += len(values)
        category_counts.update(values)
        for left, right in itertools.combinations(values, 2):
            do_den += 1
            if left != right:
                do_num += 1

    d_o = do_num / do_den if do_den else 0.0

    de_num = 0
    for left in category_counts:
        for right in category_counts:
            if left != right:
                de_num += category_counts[left] * category_counts[right]
    de_den = total_values * (total_values - 1) if total_values > 1 else 0
    d_e = de_num / de_den if de_den else 0.0

    if d_e == 0:
        alpha = 1.0 if d_o == 0 else 0.0
    else:
        alpha = 1.0 - (d_o / d_e)

    return alpha, d_o, d_e


def build_cooccurrence_matrix(
    participants: list[str],
    participant_matrix: dict[str, dict[str, str]],
) -> pd.DataFrame:
    n = len(CARD_IDS)
    index = {card_id: idx for idx, card_id in enumerate(CARD_IDS)}
    matrix = np.zeros((n, n), dtype=int)

    for participant in participants:
        placements = {
            card_id: code
            for card_id, code in participant_matrix[participant].items()
            if code in CATEGORY_CODES
        }
        placed_cards = sorted(placements)
        for left, right in itertools.combinations(placed_cards, 2):
            if placements[left] == placements[right]:
                i, j = index[left], index[right]
                matrix[i, j] += 1
                matrix[j, i] += 1

    np.fill_diagonal(matrix, 0)
    return pd.DataFrame(matrix, index=CARD_IDS, columns=CARD_IDS)


def build_pairwise_rater_agreement(
    participants: list[str],
    participant_matrix: dict[str, dict[str, str]],
) -> pd.DataFrame:
    n = len(participants)
    matrix = np.zeros((n, n), dtype=float)

    for row_idx, left_participant in enumerate(participants):
        for col_idx, right_participant in enumerate(participants):
            if row_idx == col_idx:
                matrix[row_idx, col_idx] = 1.0
                continue

            agreements = 0
            comparable = 0
            for card_id in CARD_IDS:
                left_code = participant_matrix[left_participant].get(card_id, "")
                right_code = participant_matrix[right_participant].get(card_id, "")
                if left_code in CATEGORY_CODES and right_code in CATEGORY_CODES:
                    comparable += 1
                    if left_code == right_code:
                        agreements += 1

            matrix[row_idx, col_idx] = agreements / comparable if comparable else np.nan

    return pd.DataFrame(matrix, index=participants, columns=participants)


def build_participant_card_heatmap(
    participants: list[str],
    participant_matrix: dict[str, dict[str, str]],
) -> pd.DataFrame:
    rows = []
    for participant in participants:
        row = {"participant": participant}
        for card_id in CARD_IDS:
            code = participant_matrix[participant].get(card_id, "")
            row[card_id] = code if code else "MISSING"
        rows.append(row)
    return pd.DataFrame(rows).set_index("participant")


def majority_by_card(card_table: pd.DataFrame) -> pd.Series:
    return card_table.set_index("card_id")["majority_category"]


def ordered_cards_by_majority(card_table: pd.DataFrame) -> list[str]:
    majors = majority_by_card(card_table)
    ordered: list[str] = []
    for letter in CATEGORY_CODES:
        ordered.extend(sorted(card_id for card_id in CARD_IDS if majors.get(card_id) == letter))
    return ordered


def category_block_sizes(card_order: list[str], card_table: pd.DataFrame) -> list[tuple[str, int]]:
    majors = majority_by_card(card_table)
    blocks: list[tuple[str, int]] = []
    for letter in CATEGORY_CODES:
        count = sum(1 for card_id in card_order if majors.get(card_id) == letter)
        if count:
            blocks.append((letter, count))
    return blocks


def build_category_group_cooccurrence(
    cooccurrence: pd.DataFrame,
    card_table: pd.DataFrame,
) -> pd.DataFrame:
    majors = majority_by_card(card_table)
    totals = pd.DataFrame(0.0, index=CATEGORY_CODES, columns=CATEGORY_CODES)
    counts = pd.DataFrame(0, index=CATEGORY_CODES, columns=CATEGORY_CODES)

    for left, right in itertools.combinations(cooccurrence.index, 2):
        value = float(cooccurrence.loc[left, right])
        left_cat = majors[left]
        right_cat = majors[right]
        totals.loc[left_cat, right_cat] += value
        totals.loc[right_cat, left_cat] += value
        counts.loc[left_cat, right_cat] += 1
        counts.loc[right_cat, left_cat] += 1

    return totals / counts.replace(0, np.nan)


def build_cooccurrence_top_pairs(cooccurrence: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    rows = []
    for left, right in itertools.combinations(cooccurrence.index, 2):
        rows.append({
            "card_a": left,
            "card_b": right,
            "cooccurrence_count": int(cooccurrence.loc[left, right]),
        })
    return (
        pd.DataFrame(rows)
        .sort_values(["cooccurrence_count", "card_a", "card_b"], ascending=[False, True, True])
        .head(top_n)
        .reset_index(drop=True)
    )


def build_export_summary(export_data: dict) -> dict:
    placements, set_aside_reasons, placed_cards, set_aside_cards = collect_placements(export_data)
    category_counts = Counter(placements.values())
    quality_stats = collect_quality_dimension_stats(export_data)

    return {
        "export_code": participant_label(export_data),
        "source_file": f"card-sort-ontology-{participant_label(export_data)}.json",
        "duration_seconds": export_data.get("duration_seconds", 0),
        "duration_hms": export_data.get("duration_hms", ""),
        "active_card_count": len(export_data.get("active_card_ids", [])),
        "placed_cards": len(placed_cards),
        "set_aside_count": len(set_aside_cards),
        "unsorted_count": len(export_data.get("unsorted", [])),
        "A_count": category_counts.get("A", 0),
        "B_count": category_counts.get("B", 0),
        "C_count": category_counts.get("C", 0),
        "D_count": category_counts.get("D", 0),
        "set_aside_reasons": dict(set_aside_reasons),
        **quality_stats,
    }
