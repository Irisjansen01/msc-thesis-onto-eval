from pathlib import Path
import argparse
import json
import logging

from rdflib import Graph

from metrics import basic_statistics as basic_statistics_metric
from metrics import cq_coverage as cq_coverage_metric
from metrics import oquare as oquare_metric
from metrics import vocabulary_profile_similarity as vocabulary_profile_metric
from metrics.maedche_staab_similarity import run_maedche_staab_evaluation


logging.getLogger("rdflib").setLevel(logging.ERROR)

SEP = "=" * 72
RESULTS_DIR = Path("results") / "phase2"

ONTOLOGIES = {
    "music": "data/phase2/ontologies/music-generated.ttl",
    "hospital": "data/phase2/ontologies/hospital-generated.ttl",
    "music_reference": "data/phase2/ontologies/music-reference.rdfs",
    "hospital_reference": "data/phase2/ontologies/hospital-reference.owl",
}

GENERATED_ONTOLOGY_KEYS = ("music", "hospital")

DOMAIN_STORY_COMPARISONS = [
    {
        "comparison": "music_final_vs_music_story",
        "ontology_key": "music",
        "story_path": "data/phase2/domain-stories/music-story.txt",
    },
    {
        "comparison": "hospital_final_vs_hospital_story",
        "ontology_key": "hospital",
        "story_path": "data/phase2/domain-stories/hospital-story.txt",
    },
]

RDF_FORMATS = {
    ".ttl": "turtle",
    ".turtle": "turtle",
    ".rdf": "xml",
    ".rdfs": "xml",
    ".owl": "xml",
    ".xml": "xml",
    ".nt": "nt",
    ".n3": "n3",
    ".jsonld": "json-ld",
    ".json": "json-ld",
}

METHODS = [
    ("basic", "Basic Ontology Statistics", None, basic_statistics_metric.method_basic_statistics),
    ("oquare", "OQuaRE Ontology Quality Model", None, oquare_metric.method_oquare),
    ("cq_coverage", "Competency Question Coverage", 11, cq_coverage_metric.method_cq_coverage),
]

VOCABULARY_PROFILE_METHOD_NAME = "Brewster-style vocabulary profile similarity to source text"


def wrap_method(result, name, number=None):
    return {
        "method_name": name,
        **({"method_number": number} if number is not None else {}),
        "result": result,
    }


def load_ontology(path):
    graph = Graph()
    path = Path(path)
    try:
        graph.parse(str(path), format=RDF_FORMATS.get(path.suffix.lower()))
        return {
            "path": path,
            "graph": graph,
            "loaded": True,
            "parse_error": None,
            "triple_count": len(graph),
        }
    except Exception as exc:
        return {
            "path": path,
            "graph": graph,
            "loaded": False,
            "parse_error": str(exc),
            "triple_count": 0,
        }


def run_maedche_reference_comparisons():
    comparisons = [
        ("music", ONTOLOGIES["music"], ONTOLOGIES["music_reference"], RESULTS_DIR / "maedche_staab_music"),
        ("hospital", ONTOLOGIES["hospital"], ONTOLOGIES["hospital_reference"], RESULTS_DIR / "maedche_staab_hospital"),
    ]
    for label, generated_path, reference_path, output_dir in comparisons:
        print(f"\n{SEP}")
        print(f"MAEDCHE AND STAAB REFERENCE COMPARISON [{label}]")
        print(SEP)
        run_maedche_staab_evaluation(generated_path, reference_path, output_dir)


def write_metric_outputs(results_by_metric):
    basic_statistics_metric.write_basic_statistics_outputs(results_by_metric["basic"], RESULTS_DIR / "basic_statistics")
    oquare_metric.write_oquare_outputs(results_by_metric["oquare"], RESULTS_DIR / "oquare")
    cq_coverage_metric.write_cq_coverage_outputs(results_by_metric["cq_coverage"], RESULTS_DIR / "cq_coverage")


def run_vocabulary_profile_story_comparisons(loaded_ontologies=None):
    loaded_ontologies = loaded_ontologies or {
        label: load_ontology(path)
        for label, path in ONTOLOGIES.items()
        if label in GENERATED_ONTOLOGY_KEYS
    }
    results = []
    for comparison in DOMAIN_STORY_COMPARISONS:
        label = comparison["ontology_key"]
        comparison_name = comparison["comparison"]
        story_path = comparison["story_path"]
        print(f"\n{SEP}")
        print(f"BREWSTER-STYLE VOCABULARY PROFILE SIMILARITY TO SOURCE TEXT [{comparison_name}]")
        print(SEP)
        result = vocabulary_profile_metric.compute_vocabulary_profile_similarity(
            loaded_ontologies[label],
            comparison_name,
            story_path,
        )
        result["summary"]["ontology_key"] = label
        summary = result["summary"]
        print(f"  Story: {story_path}")
        print(f"  Cosine similarity: {summary.get('cosine_similarity', 0):.4f}")
        print(f"  Weighted precision: {summary.get('weighted_precision_ontology_terms_in_source', 0):.4f}")
        print(f"  Weighted recall: {summary.get('weighted_recall_source_terms_in_ontology', 0):.4f}")
        print(f"  Weighted F1: {summary.get('weighted_f1', 0):.4f}")
        results.append(result)
    vocabulary_profile_metric.write_vocabulary_profile_outputs(
        results,
        RESULTS_DIR / "vocabulary_profile_similarity",
    )
    return results


def run_default_evaluation():
    all_results = {}
    results_by_metric = {key: {} for key, *_ in METHODS}
    loaded_ontologies = {}

    for ont_label in GENERATED_ONTOLOGY_KEYS:
        ont_path = ONTOLOGIES[ont_label]
        print(f"\n\n{'#' * 72}")
        print(f"  ONTOLOGY: {ont_label}")
        print(f"  Path: {ont_path}")
        print(f"{'#' * 72}")

        ontology = load_ontology(ont_path)
        loaded_ontologies[ont_label] = ontology
        ontology_results = {}
        for key, method_name, method_number, function in METHODS:
            result = function(ontology, ont_label)
            results_by_metric[key][ont_label] = result
            ontology_results[key] = wrap_method(result, method_name, method_number)
        all_results[ont_label] = ontology_results

    results_path = RESULTS_DIR / "evaluation_results.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)

    write_metric_outputs(results_by_metric)
    vocabulary_profile_results = run_vocabulary_profile_story_comparisons(loaded_ontologies)
    for result in vocabulary_profile_results:
        label = result["summary"]["ontology_key"]
        all_results[label]["vocabulary_profile_similarity"] = wrap_method(
            result["summary"],
            VOCABULARY_PROFILE_METHOD_NAME,
            31,
        )
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)
    run_maedche_reference_comparisons()
    print(f"\n\nResults saved to {results_path}")
    print("Per-metric CSV outputs saved to results/phase2/<metric_name>/")


def parse_args():
    parser = argparse.ArgumentParser(description="Ontology evaluation script.")
    parser.add_argument("--generated-ontology", help="Generated ontology path for Maedche and Staab comparison.")
    parser.add_argument("--reference-ontology", help="Reference ontology path for Maedche and Staab comparison.")
    parser.add_argument(
        "--maedche-output-dir",
        default=str(RESULTS_DIR / "maedche_staab"),
        help="Directory for Maedche and Staab CSV outputs.",
    )
    parser.add_argument(
        "--maedche-references",
        action="store_true",
        help="Run music-final vs music-ref and hospital-final vs hospital-ref.",
    )
    parser.add_argument(
        "--vocabulary-profile-stories",
        action="store_true",
        help="Run M31 vocabulary-profile similarity for final ontologies against domain stories.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.maedche_references:
        run_maedche_reference_comparisons()
    elif args.vocabulary_profile_stories:
        run_vocabulary_profile_story_comparisons()
    elif args.generated_ontology or args.reference_ontology:
        if not args.generated_ontology or not args.reference_ontology:
            raise SystemExit("Use both --generated-ontology and --reference-ontology.")
        run_maedche_staab_evaluation(
            args.generated_ontology,
            args.reference_ontology,
            args.maedche_output_dir,
        )
    else:
        run_default_evaluation()


if __name__ == "__main__":
    main()
