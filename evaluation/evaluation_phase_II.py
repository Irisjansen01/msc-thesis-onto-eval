from pathlib import Path
import argparse
import json
import logging

from rdflib import Graph

from metrics import annotation_completeness as annotation_completeness_metric
from metrics import basic_statistics as basic_statistics_metric
from metrics import cq_coverage as cq_coverage_metric
from metrics import external_vocab as external_vocab_metric
from metrics import literal_validation as literal_validation_metric
from metrics import logical_consistency as logical_consistency_metric
from metrics import ontoqa as ontoqa_metric
from metrics import oquare as oquare_metric
from metrics import parseability as parseability_metric
from metrics import shacl_validation as shacl_validation_metric
from metrics import structural_constraints as structural_constraints_metric
from metrics import unit_tests as unit_tests_metric
from metrics import yang_complexity as yang_complexity_metric
from metrics.maedche_staab_similarity import run_maedche_staab_evaluation


logging.getLogger("rdflib").setLevel(logging.ERROR)

SEP = "=" * 72

ONTOLOGIES = {
    "ontology_1": "data/ontologies/music-final.ttl",
    "ontology_2": "data/ontologies/hospital-final.ttl",
    "ref_ontology_1": "data/ontologies/music-ref.rdfs",
    "ref_ontology_2": "data/ontologies/hospital-ref.owl",
}

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
    ("stats", "RDF syntax parseability (RDFLib)", 1, parseability_metric.method_parseability_check),
    ("ontoqa", "OntoQA Schema-level Metrics", 3, ontoqa_metric.method_ontoqa),
    ("yang", "Ontology Complexity Metrics", 4, yang_complexity_metric.method_yang_complexity),
    ("consistency", "Logical Consistency Check (placeholder)", None, logical_consistency_metric.method_logical_consistency),
    ("sparql", "SPARQL-Based Structural Constraint Checks", 7, structural_constraints_metric.method_sparql_constraints),
    ("shacl", "SHACL Shapes Constraint Language Validation", 8, shacl_validation_metric.method_shacl),
    ("unit_tests", "Unit Tests for Ontologies", 9, unit_tests_metric.method_unit_tests),
    ("cq_coverage", "Competency Question Coverage", 11, cq_coverage_metric.method_cq_coverage),
    ("oquare", "OQuaRE Ontology Quality Model", None, oquare_metric.method_oquare),
    ("completeness", "Column Completeness / Annotation Completeness", 12, annotation_completeness_metric.method_annotation_completeness),
    ("ext_vocab", "External Vocabulary Usage Rate", 13, external_vocab_metric.method_external_vocab),
    ("literals", "Syntactic Validity of Typed Literals", 14, literal_validation_metric.method_literal_validation),
]


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
        ("music", ONTOLOGIES["ontology_1"], ONTOLOGIES["ref_ontology_1"], Path("results") / "maedche_staab_music"),
        ("hospital", ONTOLOGIES["ontology_2"], ONTOLOGIES["ref_ontology_2"], Path("results") / "maedche_staab_hospital"),
    ]
    for label, generated_path, reference_path, output_dir in comparisons:
        print(f"\n{SEP}")
        print(f"MAEDCHE AND STAAB REFERENCE COMPARISON [{label}]")
        print(SEP)
        run_maedche_staab_evaluation(generated_path, reference_path, output_dir)


def write_metric_outputs(results_by_metric):
    basic_statistics_metric.write_basic_statistics_outputs(results_by_metric["basic"], Path("results") / "basic_statistics")
    parseability_metric.write_parseability_outputs(results_by_metric["stats"], Path("results") / "parseability")
    ontoqa_metric.write_ontoqa_outputs(results_by_metric["ontoqa"], Path("results") / "ontoqa")
    yang_complexity_metric.write_yang_complexity_outputs(results_by_metric["yang"], Path("results") / "yang_complexity")
    logical_consistency_metric.write_logical_consistency_outputs(results_by_metric["consistency"], Path("results") / "logical_consistency")
    structural_constraints_metric.write_structural_constraints_outputs(results_by_metric["sparql"], Path("results") / "structural_constraints")
    shacl_validation_metric.write_shacl_outputs(results_by_metric["shacl"], Path("results") / "shacl")
    unit_tests_metric.write_unit_test_outputs(results_by_metric["unit_tests"], Path("results") / "unit_tests")
    cq_coverage_metric.write_cq_coverage_outputs(results_by_metric["cq_coverage"], Path("results") / "cq_coverage")
    oquare_metric.write_oquare_outputs(results_by_metric["oquare"], Path("results") / "oquare")
    annotation_completeness_metric.write_annotation_completeness_outputs(results_by_metric["completeness"], Path("results") / "annotation_completeness")
    external_vocab_metric.write_external_vocab_outputs(results_by_metric["ext_vocab"], Path("results") / "external_vocab")
    literal_validation_metric.write_literal_validation_outputs(results_by_metric["literals"], Path("results") / "literal_validation")


def run_default_evaluation():
    all_results = {}
    results_by_metric = {key: {} for key, *_ in METHODS}

    for ont_label, ont_path in ONTOLOGIES.items():
        print(f"\n\n{'#' * 72}")
        print(f"  ONTOLOGY: {ont_label}")
        print(f"  Path: {ont_path}")
        print(f"{'#' * 72}")

        ontology = load_ontology(ont_path)
        ontology_results = {}
        for key, method_name, method_number, function in METHODS:
            result = function(ontology, ont_label)
            results_by_metric[key][ont_label] = result
            ontology_results[key] = wrap_method(result, method_name, method_number)
        all_results[ont_label] = ontology_results

    results_path = Path("results") / "evaluation_results.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)

    write_metric_outputs(results_by_metric)
    print(f"\n\nResults saved to {results_path}")
    print("Per-metric CSV outputs saved to results/<metric_name>/")


def parse_args():
    parser = argparse.ArgumentParser(description="Ontology evaluation script.")
    parser.add_argument("--generated-ontology", help="Generated ontology path for Maedche and Staab comparison.")
    parser.add_argument("--reference-ontology", help="Reference ontology path for Maedche and Staab comparison.")
    parser.add_argument(
        "--maedche-output-dir",
        default=str(Path("results") / "maedche_staab"),
        help="Directory for Maedche and Staab CSV outputs.",
    )
    parser.add_argument(
        "--maedche-references",
        action="store_true",
        help="Run music-final vs music-ref and hospital-final vs hospital-ref.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.maedche_references:
        run_maedche_reference_comparisons()
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
