# Analysis Code

This folder holds the reproducible analysis scripts that interpret the thesis study materials.

## Phase 1 card sort

Run the full Phase 1 analysis (all thesis metrics, tables, plots, and `phase1_summary.txt`):

```bash
python scripts/phase1/phase1_report.py
```

### Outputs (`results/phase1/`)

| Artifact | Description |
| --- | --- |
| `phase1_summary.txt` | Human-readable report: N, duration, α, per-card agreement, bands, set-aside, participant means, quality dimensions, boundary cards |
| `card_sort_per_card_agreement.csv` | Majority category and agreement rate for all 40 cards |
| `card_sort_plurality_bands.csv` | Per-card plurality share and agreement band |
| `card_sort_agreement_bands.csv` | Count of cards per agreement band |
| `card_sort_analysis_per_export.csv` | Per-participant placement counts and timing |
| `card_sort_set_aside_summary.csv` | Set-aside reasons per participant |
| `card_sort_quality_dimensions.csv` | Quality-concern (subcategory) use per participant |
| `card_sort_category_distribution.csv` | Total A/B/C/D placements |
| `card_sort_boundary_votes.csv` | Vote breakdown for cards with plurality &lt; 60% (auto-selected) |
| `cooccurrence_matrix.csv` | Full 40×40 matrix (M01–M40 order) |
| `cooccurrence_matrix_ordered.csv` / `.png` | Same matrix, cards grouped by plurality category (A→B→C→D) with dividers and colour-coded labels |
| `cooccurrence_by_category_groups.csv` / `.png` | 4×4 summary: mean co-occurrence between taxonomy groups |
| `cooccurrence_top_pairs.csv` | Top 20 card pairs most often sorted together |
| `plurality_vote_heatmap.csv` / `.png` | 40×4 vote counts per category (0–13) |
| `participant_card_heatmap.csv` / `.png` | 13×40 grid coloured by A/B/C/D/SA |
| `pairwise_rater_agreement.csv` / `.png` | 13×13 rater agreement matrix |
| `cooccurrence_dendrogram.png` | Hierarchical clustering on co-occurrence distance |

### Scripts

- `phase1_report.py` — main entry point (runs everything above)
- `card_sort_common.py` — shared loading and metric functions
- `card_sort_analysis.py` — per-export CSVs only (subset of the full report)
- `co-occurace.py`, `heatmap.py` — backward-compatible aliases for `phase1_report.py`

## Intended separation

- `data/` = raw study inputs and materials
- `scripts/` = code that transforms those inputs into evidence
- `results/` = generated tables, plots, and exported artifacts
