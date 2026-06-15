"""
Phase 1 card-sort analysis — full thesis metrics and readable outputs.

Reads all JSON exports from results/phase1/card-sort-responses/ and writes:
  - phase1_summary.txt              human-readable report for the thesis
  - card_sort_analysis_per_export.csv
  - card_sort_set_aside_summary.csv
  - card_sort_per_card_agreement.csv
  - card_sort_plurality_bands.csv
  - card_sort_agreement_bands.csv
  - card_sort_category_distribution.csv
  - card_sort_boundary_votes.csv
  - card_sort_quality_dimensions.csv
  - cooccurrence_matrix.csv + .png
  - cooccurrence_by_category_groups.csv + .png
  - cooccurrence_top_pairs.csv
  - plurality_vote_heatmap.csv + .png
  - participant_card_heatmap.csv + .png
  - pairwise_rater_agreement.csv + .png
  - cooccurrence_dendrogram.png
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform

from card_sort_common import (
    BOUNDARY_AGREEMENT_THRESHOLD,
    CARD_IDS,
    CATEGORY_CODES,
    CATEGORY_COLORS,
    EXPORT_DIR,
    HEATMAP_CATEGORY_CODES,
    OUTPUT_DIR,
    TOP_CATEGORY_LABELS,
    agreement_band,
    boundary_card_ids,
    build_agreement_band_table,
    build_card_vote_table,
    build_category_group_cooccurrence,
    build_cooccurrence_matrix,
    build_cooccurrence_top_pairs,
    build_export_summary,
    build_pairwise_rater_agreement,
    build_participant_card_heatmap,
    build_participant_matrix,
    category_block_sizes,
    collect_placements,
    krippendorff_alpha_nominal,
    load_exports,
    majority_by_card,
    ordered_cards_by_majority,
)


def write_per_export_tables(exports: list[dict]) -> pd.DataFrame:
    summaries = [build_export_summary(item) for item in exports]
    summary_df = pd.DataFrame(summaries)
    summary_df.to_csv(OUTPUT_DIR / "card_sort_analysis_per_export.csv", index=False)

    reason_rows = []
    for item in summaries:
        reasons = item.get("set_aside_reasons", {})
        reason_rows.append({
            "export_code": item["export_code"],
            "source_file": item["source_file"],
            "set_aside_count": item["set_aside_count"],
            "reason_no_fitting_top_cat": reasons.get("no_fitting_top_cat", 0),
            "reason_other": reasons.get("other", 0),
            "reason_unspecified": reasons.get("unspecified", 0),
            "reason_fits_multiple_groups": reasons.get("fits_multiple_groups", 0),
            "reason_unclear_wording": reasons.get("unclear_wording", 0),
            "reason_not_an_evaluation": reasons.get("not_an_evaluation", 0),
            "reason_too_broad": reasons.get("too_broad", 0),
        })
    pd.DataFrame(reason_rows).to_csv(OUTPUT_DIR / "card_sort_set_aside_summary.csv", index=False)

    quality_rows = [
        {
            "export_code": item["export_code"],
            "quality_concern_instances": item["quality_concern_instances"],
            "suggested_instances": item["suggested_instances"],
            "custom_instances": item["custom_instances"],
            "distinct_suggested_chip_ids": item["distinct_suggested_chip_ids"],
            "used_any_quality_concern": item["used_any_quality_concern"],
            "used_suggested_set": item["used_suggested_set"],
        }
        for item in summaries
    ]
    pd.DataFrame(quality_rows).to_csv(OUTPUT_DIR / "card_sort_quality_dimensions.csv", index=False)

    return summary_df


def write_card_tables(card_table: pd.DataFrame) -> pd.DataFrame:
    card_table.to_csv(OUTPUT_DIR / "card_sort_per_card_agreement.csv", index=False)

    plurality_rows = []
    for _, row in card_table.iterrows():
        plurality_rows.append({
            "card_id": row["card_id"],
            "plurality_label": row["majority_label"],
            "plurality_count": row["majority_count"],
            "total_votes": row["total_placed_votes"],
            "plurality_share": row["agreement_rate"],
            "agreement_band": agreement_band(row["agreement_rate"]),
        })
    plurality_df = pd.DataFrame(plurality_rows)
    plurality_df.sort_values(["agreement_band", "card_id"]).to_csv(
        OUTPUT_DIR / "card_sort_plurality_bands.csv", index=False
    )

    band_table = build_agreement_band_table(card_table)
    band_table.to_csv(OUTPUT_DIR / "card_sort_agreement_bands.csv", index=False)
    return band_table


def write_category_distribution(exports: list[dict], n_participants: int) -> pd.DataFrame:
    totals = Counter()
    for export_data in exports:
        placements, _, _, _ = collect_placements(export_data)
        totals.update(placements.values())

    rows = []
    for letter in ("A", "B", "C", "D"):
        count = totals.get(letter, 0)
        rows.append({
            "category": letter,
            "label": TOP_CATEGORY_LABELS[letter],
            "placement_count": count,
            "mean_per_participant": count / n_participants,
        })
    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR / "card_sort_category_distribution.csv", index=False)
    return df


def write_boundary_votes(card_table: pd.DataFrame) -> pd.DataFrame:
    ids = boundary_card_ids(card_table)
    boundary = card_table[card_table["card_id"].isin(ids)].copy()
    boundary["boundary_reason"] = f"plurality < {BOUNDARY_AGREEMENT_THRESHOLD:.0%}"
    boundary.to_csv(OUTPUT_DIR / "card_sort_boundary_votes.csv", index=False)
    return boundary


def build_plurality_vote_matrix(card_table: pd.DataFrame) -> pd.DataFrame:
    vote_columns = {f"{letter}_votes": letter for letter in CATEGORY_CODES}
    return (
        card_table.set_index("card_id")
        .rename(columns=vote_columns)[list(CATEGORY_CODES)]
        .reindex(CARD_IDS)
    )


def write_plurality_vote_heatmap(card_table: pd.DataFrame) -> pd.DataFrame:
    vote_matrix = build_plurality_vote_matrix(card_table)
    vote_matrix.to_csv(OUTPUT_DIR / "plurality_vote_heatmap.csv")
    return vote_matrix


def plot_plurality_vote_heatmap(
    vote_matrix: pd.DataFrame,
    n_participants: int,
) -> None:
    norm = mcolors.Normalize(vmin=0, vmax=n_participants)

    fig, ax = plt.subplots(figsize=(14, 14))
    sns.heatmap(
        vote_matrix,
        ax=ax,
        norm=norm,
        cmap="Blues",
        annot=True,
        fmt="d",
        linewidths=0.5,
        linecolor="white",
        cbar_kws={
            "label": "Participants placing card in category",
            "shrink": 0.5,
            "ticks": np.arange(0, n_participants + 1),
        },
        annot_kws={"size": 9},
    )

    for text, value in zip(ax.texts, vote_matrix.values.flatten(), strict=True):
        text.set_color("white" if value > n_participants / 2 else "black")

    ax.set_xlabel("Category")
    ax.set_ylabel("Card ID")
    ax.tick_params(axis="x", labelsize=9)
    ax.tick_params(axis="y", labelsize=7, rotation=0)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "plurality_vote_heatmap.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def _style_card_ticks(ax: plt.Axes, card_order: list[str], majors: pd.Series) -> None:
    for tick_label, card_id in zip(ax.get_xticklabels(), card_order, strict=True):
        tick_label.set_color(CATEGORY_COLORS.get(majors[card_id], "#333333"))
        tick_label.set_fontsize(6.5)
    for tick_label, card_id in zip(ax.get_yticklabels(), card_order, strict=True):
        tick_label.set_color(CATEGORY_COLORS.get(majors[card_id], "#333333"))
        tick_label.set_fontsize(6.5)


def _draw_category_dividers(ax: plt.Axes, blocks: list[tuple[str, int]]) -> None:
    total = sum(size for _, size in blocks)
    offset = 0
    for letter, count in blocks:
        midpoint = offset + count / 2
        ax.text(
            -0.12,
            midpoint,
            letter,
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
            color=CATEGORY_COLORS[letter],
            transform=ax.get_yaxis_transform(),
            clip_on=False,
        )
        offset += count
        if offset < total:
            ax.axhline(offset, color="#333333", linewidth=1.2)
            ax.axvline(offset, color="#333333", linewidth=1.2)


def plot_cooccurrence_matrix(
    cooccurrence: pd.DataFrame,
    card_table: pd.DataFrame,
    n_participants: int,
) -> pd.DataFrame:
    card_order = ordered_cards_by_majority(card_table)
    ordered = cooccurrence.loc[card_order, card_order]
    majors = majority_by_card(card_table)
    blocks = category_block_sizes(card_order, card_table)

    fig, ax = plt.subplots(figsize=(15, 13))
    mask = np.eye(len(ordered), dtype=bool)
    norm = mcolors.Normalize(vmin=0, vmax=n_participants)
    sns.heatmap(
        ordered,
        ax=ax,
        mask=mask,
        norm=norm,
        cmap="Blues",
        linewidths=0.15,
        linecolor="white",
        square=True,
        cbar_kws={
            "label": f"Participants (out of {n_participants}) who placed both cards in the same category",
            "shrink": 0.55,
            "ticks": np.arange(0, n_participants + 1),
        },
    )
    _draw_category_dividers(ax, blocks)
    _style_card_ticks(ax, card_order, majors)

    ax.set_xlabel("Card (coloured by plurality category: A reference · B corpus · C task · D criteria)")
    ax.set_ylabel("Card")
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "cooccurrence_matrix.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    return ordered


def plot_category_group_cooccurrence(
    group_matrix: pd.DataFrame,
    n_participants: int,
) -> None:
    labels = {
        "A": "A\nReference",
        "B": "B\nCorpus",
        "C": "C\nTask",
        "D": "D\nCriteria",
    }
    tick_labels = [labels[letter] for letter in CATEGORY_CODES]
    fig, ax = plt.subplots(figsize=(8, 6))
    norm = mcolors.Normalize(vmin=0, vmax=n_participants)
    sns.heatmap(
        group_matrix,
        ax=ax,
        norm=norm,
        cmap="Blues",
        annot=True,
        fmt=".1f",
        linewidths=1,
        linecolor="white",
        square=True,
        xticklabels=tick_labels,
        yticklabels=tick_labels,
        cbar_kws={
            "label": f"Mean co-occurrence (out of {n_participants})",
            "ticks": np.arange(0, n_participants + 1),
        },
        annot_kws={"size": 11},
    )
    for text, value in zip(ax.texts, group_matrix.values.flatten(), strict=True):
        if np.isnan(value):
            text.set_text("")
        else:
            text.set_color("white" if value > n_participants / 2 else "black")

    ax.tick_params(axis="both", labelsize=9)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "cooccurrence_by_category_groups.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def write_cooccurrence_outputs(
    cooccurrence: pd.DataFrame,
    card_table: pd.DataFrame,
    n_participants: int,
) -> None:
    cooccurrence.to_csv(OUTPUT_DIR / "cooccurrence_matrix.csv")
    ordered = plot_cooccurrence_matrix(cooccurrence, card_table, n_participants)
    ordered.to_csv(OUTPUT_DIR / "cooccurrence_matrix_ordered.csv")

    group_matrix = build_category_group_cooccurrence(cooccurrence, card_table)
    group_matrix.to_csv(OUTPUT_DIR / "cooccurrence_by_category_groups.csv")
    plot_category_group_cooccurrence(group_matrix, n_participants)

    top_pairs = build_cooccurrence_top_pairs(cooccurrence)
    top_pairs.to_csv(OUTPUT_DIR / "cooccurrence_top_pairs.csv", index=False)


def plot_participant_card_heatmap(df: pd.DataFrame) -> None:
    code_to_num = {code: idx for idx, code in enumerate(HEATMAP_CATEGORY_CODES)}
    numeric = df.map(lambda value: code_to_num.get(value, np.nan))

    cmap = sns.color_palette(["#4C78A8", "#F58518", "#54A24B", "#E45756", "#B279A2", "#E0E0E0"], 6)
    fig, ax = plt.subplots(figsize=(18, 6))
    sns.heatmap(
        numeric,
        ax=ax,
        cmap=cmap,
        vmin=0,
        vmax=len(HEATMAP_CATEGORY_CODES) - 1,
        cbar=False,
        linewidths=0.2,
        linecolor="white",
    )
    legend_handles = [
        plt.matplotlib.patches.Patch(color=cmap[code_to_num[code]], label=code)
        for code in HEATMAP_CATEGORY_CODES
    ]
    legend_handles.append(plt.matplotlib.patches.Patch(color="#E0E0E0", label="MISSING"))
    ax.legend(handles=legend_handles, bbox_to_anchor=(1.02, 1), loc="upper left", frameon=False)
    ax.set_xlabel("Card ID")
    ax.set_ylabel("Participant")
    ax.tick_params(axis="x", labelsize=7, rotation=90)
    ax.tick_params(axis="y", labelsize=8, rotation=0)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "participant_card_heatmap.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_pairwise_rater_agreement(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(
        df,
        ax=ax,
        vmin=0,
        vmax=1,
        cmap="YlGn",
        annot=True,
        fmt=".2f",
        square=True,
        cbar_kws={"label": "Proportion of comparable cards with matching category"},
    )
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "pairwise_rater_agreement.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_cooccurrence_dendrogram(
    cooccurrence: pd.DataFrame,
    card_table: pd.DataFrame,
    n_participants: int,
) -> None:
    card_order = ordered_cards_by_majority(card_table)
    ordered = cooccurrence.loc[card_order, card_order]
    majors = majority_by_card(card_table)

    similarity = ordered.values / n_participants
    np.fill_diagonal(similarity, 1.0)
    distance = 1.0 - similarity
    condensed = squareform(distance, checks=False)
    linkage_matrix = linkage(condensed, method="average")

    fig, ax = plt.subplots(figsize=(16, 6))
    dendrogram(
        linkage_matrix,
        labels=ordered.index.tolist(),
        leaf_rotation=90,
        leaf_font_size=7,
        ax=ax,
        color_threshold=0,
    )
    for tick_label, card_id in zip(ax.get_xticklabels(), ordered.index, strict=True):
        tick_label.set_color(CATEGORY_COLORS.get(majors[card_id], "#333333"))

    ax.set_ylabel(f"Distance (0 = always same category · 1 = never same category, N={n_participants})")
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "cooccurrence_dendrogram.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def format_duration_range(summary_df: pd.DataFrame) -> str:
    min_row = summary_df.loc[summary_df["duration_seconds"].idxmin()]
    max_row = summary_df.loc[summary_df["duration_seconds"].idxmax()]
    return f"{min_row['duration_hms']} – {max_row['duration_hms']} ({int(min_row['duration_seconds'])}–{int(max_row['duration_seconds'])} s)"


def write_summary_report(
    n_participants: int,
    summary_df: pd.DataFrame,
    card_table: pd.DataFrame,
    band_table: pd.DataFrame,
    category_df: pd.DataFrame,
    boundary_df: pd.DataFrame,
    alpha: float,
    d_o: float,
    d_e: float,
    set_aside_stats: dict,
    quality_stats: dict,
) -> None:
    mean_agreement = card_table["agreement_rate"].mean()
    cards_ge_80 = int((card_table["agreement_rate"] >= 0.80).sum())

    lines = [
        "Phase 1 — Card Sort Analysis Summary",
        "=" * 42,
        "",
        f"N = {n_participants}",
        f"Duration range = {format_duration_range(summary_df)}",
        f"Krippendorff's α = {alpha:.4f}",
        f"D_o = {d_o:.4f}, D_e = {d_e:.4f}",
        "",
        "Per-card majority category and agreement rate",
        "-" * 42,
    ]

    for _, row in card_table.iterrows():
        lines.append(
            f"{row['card_id']}: {row['majority_category']} "
            f"({int(row['majority_count'])}/{int(row['plurality_denominator'])} = {row['agreement_rate']:.1%}; "
            f"SA={int(row['SA_votes'])})"
        )

    lines.extend([
        "",
        f"Mean agreement rate (majority / (N − set-aside)) = {mean_agreement:.1%}",
        f"Cards at ≥80% agreement = {cards_ge_80}",
        f"Boundary cards (plurality < {BOUNDARY_AGREEMENT_THRESHOLD:.0%}) = {len(boundary_df)}",
        "",
        "Agreement band table",
        "-" * 42,
    ])
    for _, row in band_table.iterrows():
        lines.append(f"{row['agreement_band']}: {int(row['card_count'])} cards")

    cat_map = {row["category"]: int(row["placement_count"]) for _, row in category_df.iterrows()}
    lines.extend([
        "",
        "Category distribution (total placements across all participants)",
        "-" * 42,
        f"A = {cat_map.get('A', 0)}, B = {cat_map.get('B', 0)}, "
        f"C = {cat_map.get('C', 0)}, D = {cat_map.get('D', 0)}",
        "",
        "Set-aside",
        "-" * 42,
        f"Events (total set-aside actions) = {set_aside_stats['events']}",
        f"Distinct cards set aside = {set_aside_stats['distinct_cards']}",
        f"Participants using set-aside = {set_aside_stats['participants']}",
        "",
        "Participant means",
        "-" * 42,
        f"placed = {summary_df['placed_cards'].mean():.1f}",
        f"A = {summary_df['A_count'].mean():.1f}",
        f"B = {summary_df['B_count'].mean():.1f}",
        f"C = {summary_df['C_count'].mean():.1f}",
        f"D = {summary_df['D_count'].mean():.1f}",
        f"SA = {summary_df['set_aside_count'].mean():.1f}",
        "",
        "Quality dimensions (subcategory / quality-concern use)",
        "-" * 42,
        f"Participants who used any quality concern = {quality_stats['used_any']}",
        f"Participants who used the suggested Q01–Q14 set = {quality_stats['used_suggested']}",
        f"Total suggested-criteria instances created = {quality_stats['suggested_instances']}",
        f"Participants who did not use quality concerns = {quality_stats['unused']}",
        "",
        "Boundary card vote counts",
        f"(plurality < {BOUNDARY_AGREEMENT_THRESHOLD:.0%}; set-aside excluded from denominator)",
        "-" * 42,
    ])

    for _, row in boundary_df.iterrows():
        lines.append(
            f"{row['card_id']}: A={int(row['A_votes'])}, B={int(row['B_votes'])}, "
            f"C={int(row['C_votes'])}, D={int(row['D_votes'])}, SA={int(row['SA_votes'])} "
            f"(majority {row['majority_category']} at {row['agreement_rate']:.1%})"
        )

    lines.extend([
        "",
        "Generated artifacts",
        "-" * 42,
        "cooccurrence_matrix.csv / cooccurrence_matrix_ordered.csv / .png",
        "cooccurrence_by_category_groups.csv / .png",
        "cooccurrence_top_pairs.csv",
        "plurality_vote_heatmap.csv / .png",
        "participant_card_heatmap.csv / .png",
        "pairwise_rater_agreement.csv / .png",
        "cooccurrence_dendrogram.png",
    ])

    report_path = OUTPUT_DIR / "phase1_summary.txt"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def collect_set_aside_stats(exports: list[dict]) -> dict:
    events = 0
    distinct_cards: set[str] = set()
    participants = 0
    for export_data in exports:
        _, _, _, set_aside_cards = collect_placements(export_data)
        if set_aside_cards:
            participants += 1
        events += len(set_aside_cards)
        distinct_cards.update(set_aside_cards)
    return {
        "events": events,
        "distinct_cards": len(distinct_cards),
        "participants": participants,
    }


def collect_quality_summary(summary_df: pd.DataFrame) -> dict:
    return {
        "used_any": int(summary_df["used_any_quality_concern"].sum()),
        "used_suggested": int(summary_df["used_suggested_set"].sum()),
        "suggested_instances": int(summary_df["suggested_instances"].sum()),
        "unused": int((~summary_df["used_any_quality_concern"]).sum()),
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    exports = load_exports(EXPORT_DIR)
    n_participants = len(exports)

    participants, participant_matrix = build_participant_matrix(exports)
    summary_df = write_per_export_tables(exports)
    card_table = build_card_vote_table(exports, n_participants)
    band_table = write_card_tables(card_table)
    category_df = write_category_distribution(exports, n_participants)
    boundary_df = write_boundary_votes(card_table)

    alpha, d_o, d_e = krippendorff_alpha_nominal(participants, participant_matrix)

    cooccurrence = build_cooccurrence_matrix(participants, participant_matrix)
    write_cooccurrence_outputs(cooccurrence, card_table, n_participants)

    participant_heatmap = build_participant_card_heatmap(participants, participant_matrix)
    participant_heatmap.to_csv(OUTPUT_DIR / "participant_card_heatmap.csv")

    pairwise = build_pairwise_rater_agreement(participants, participant_matrix)
    pairwise.to_csv(OUTPUT_DIR / "pairwise_rater_agreement.csv")

    plurality_votes = write_plurality_vote_heatmap(card_table)
    plot_plurality_vote_heatmap(plurality_votes, n_participants)
    plot_participant_card_heatmap(participant_heatmap)
    plot_pairwise_rater_agreement(pairwise)
    plot_cooccurrence_dendrogram(cooccurrence, card_table, n_participants)

    write_summary_report(
        n_participants=n_participants,
        summary_df=summary_df,
        card_table=card_table,
        band_table=band_table,
        category_df=category_df,
        boundary_df=boundary_df,
        alpha=alpha,
        d_o=d_o,
        d_e=d_e,
        set_aside_stats=collect_set_aside_stats(exports),
        quality_stats=collect_quality_summary(summary_df),
    )

    print(f"Wrote Phase 1 analysis to {OUTPUT_DIR}")
    print(f"  N = {n_participants}")
    print(f"  Krippendorff's alpha = {alpha:.4f}")
    print(f"  Mean agreement = {card_table['agreement_rate'].mean():.1%}")
    print(f"  Summary report: {OUTPUT_DIR / 'phase1_summary.txt'}")


if __name__ == "__main__":
    main()
