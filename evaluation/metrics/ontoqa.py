from pathlib import Path
import csv

from rdflib import RDF, RDFS, OWL, URIRef


def _require_loaded(onto):
    if not onto["loaded"]:
        return {"error": onto["parse_error"]}
    return None


def _declared_classes(g):
    return {s for s in g.subjects(RDF.type, OWL.Class) if isinstance(s, URIRef)}


def _object_properties(g):
    return {s for s in g.subjects(RDF.type, OWL.ObjectProperty) if isinstance(s, URIRef)}


def _datatype_properties(g):
    return {s for s in g.subjects(RDF.type, OWL.DatatypeProperty) if isinstance(s, URIRef)}


def method_ontoqa(onto, label):
    """
    OntoQA schema-level metrics.

    RR: relationship richness
    AR: attribute richness
    IR: inheritance richness
    CR: class richness
    """
    error = _require_loaded(onto)
    if error:
        return error

    g = onto["graph"]
    classes = _declared_classes(g)
    object_properties = _object_properties(g)
    datatype_properties = _datatype_properties(g)

    subclass_edges = {
        (s, o)
        for s, _, o in g.triples((None, RDFS.subClassOf, None))
        if isinstance(s, URIRef) and isinstance(o, URIRef)
        and s in classes and o in classes
    }

    inherited_relations = len(subclass_edges)
    non_inherited_relations = len(object_properties)
    relationship_richness = (
        non_inherited_relations / (inherited_relations + non_inherited_relations)
        if inherited_relations + non_inherited_relations
        else 0.0
    )

    attr_per_class = {}
    for cls in classes:
        attrs = {
            prop for prop in datatype_properties
            for _, _, domain in g.triples((prop, RDFS.domain, None))
            if domain == cls
        }
        attr_per_class[cls] = len(attrs)
    attribute_richness = sum(attr_per_class.values()) / len(classes) if classes else 0.0

    subclass_count = {}
    for cls in classes:
        children = {
            s for s, _, o in g.triples((None, RDFS.subClassOf, None))
            if isinstance(s, URIRef) and s in classes and o == cls
        }
        subclass_count[cls] = len(children)
    inheritance_richness = sum(subclass_count.values()) / len(classes) if classes else 0.0

    classes_with_instances = {
        typ for _, _, typ in g.triples((None, RDF.type, None))
        if isinstance(typ, URIRef) and typ in classes
    }
    class_richness = len(classes_with_instances) / len(classes) if classes else 0.0

    print("\n" + "=" * 72)
    print(f"METHOD - OntoQA Schema Metrics [{label}]")
    print("=" * 72)
    print(f"  RR = {relationship_richness:.4f}")
    print(f"  AR = {attribute_richness:.4f}")
    print(f"  IR = {inheritance_richness:.4f}")
    print(f"  CR = {class_richness:.4f}")

    return {
        "classes": len(classes),
        "object_properties": len(object_properties),
        "datatype_properties": len(datatype_properties),
        "subclass_edges": len(subclass_edges),
        "relationship_richness": relationship_richness,
        "attribute_richness": attribute_richness,
        "inheritance_richness": inheritance_richness,
        "class_richness": class_richness,
    }


def write_ontoqa_outputs(results_by_label, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for label, result in results_by_label.items():
        if "error" in result:
            rows.append({"ontology": label, "metric": "error", "value": result["error"]})
            continue
        for metric, value in result.items():
            rows.append({"ontology": label, "metric": metric, "value": value})

    with open(output_dir / "ontoqa_summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ontology", "metric", "value"])
        writer.writeheader()
        writer.writerows(rows)

