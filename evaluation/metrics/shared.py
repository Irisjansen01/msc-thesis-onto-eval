from pathlib import Path
import csv

from rdflib import RDF, RDFS, OWL, URIRef, BNode

SEP = "=" * 72
SEP2 = "-" * 72


def short(node):
    if isinstance(node, URIRef):
        text = str(node)
        return text.split("#")[-1] if "#" in text else text.rstrip("/").split("/")[-1]
    return str(node)


def is_named_uri(node):
    return isinstance(node, URIRef)


def get_declared_classes(g):
    return {s for s in g.subjects(RDF.type, OWL.Class) if is_named_uri(s)}


def get_declared_object_properties(g):
    return {s for s in g.subjects(RDF.type, OWL.ObjectProperty) if is_named_uri(s)}


def get_declared_datatype_properties(g):
    return {s for s in g.subjects(RDF.type, OWL.DatatypeProperty) if is_named_uri(s)}


def get_declared_annotation_properties(g):
    return {s for s in g.subjects(RDF.type, OWL.AnnotationProperty) if is_named_uri(s)}


def get_declared_named_individuals(g):
    return {s for s in g.subjects(RDF.type, OWL.NamedIndividual) if is_named_uri(s)}


def get_named_subclass_edges(g):
    return {
        (s, o)
        for s, _, o in g.triples((None, RDFS.subClassOf, None))
        if is_named_uri(s) and is_named_uri(o)
    }


def write_dict_outputs(results_by_label, output_dir, filename):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for ontology, result in results_by_label.items():
        if isinstance(result, dict):
            for key, value in result.items():
                if isinstance(value, (dict, list, set, tuple)):
                    continue
                rows.append({"ontology": ontology, "metric": key, "value": value})
        else:
            rows.append({"ontology": ontology, "metric": "value", "value": result})
    with open(output_dir / filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ontology", "metric", "value"])
        writer.writeheader()
        writer.writerows(rows)
