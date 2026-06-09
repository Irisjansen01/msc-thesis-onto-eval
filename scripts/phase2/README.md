# Evaluation Code

`evaluation_phase_II.py` is the main runner. It currently executes only the active evaluation approaches:

1. Basic statistics
2. OQuaRE
3. Competency question coverage
4. Brewster-style vocabulary profile similarity
5. Maedche-Staab reference similarity

The active metric modules are:

- `metrics/basic_statistics.py`
- `metrics/oquare.py`
- `metrics/cq_coverage.py`
- `metrics/vocabulary_profile_similarity.py`
- `metrics/maedche_staab_similarity.py`

Other metric modules are legacy exploratory code unless they are explicitly re-added to `evaluation_phase_II.py`.
