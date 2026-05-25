from pathlib import Path
import csv

from rdflib import RDF, RDFS, OWL, URIRef


def _declared_classes(g):
    classes = {s for s in g.subjects(RDF.type, OWL.Class) if isinstance(s, URIRef)}
    classes |= {s for s in g.subjects(RDF.type, RDFS.Class) if isinstance(s, URIRef)}
    for s, o in g.subject_objects(RDFS.subClassOf):
        if isinstance(s, URIRef):
            classes.add(s)
        if isinstance(o, URIRef):
            classes.add(o)
    return classes - {OWL.Thing, OWL.Nothing}


def _object_properties(g):
    return {s for s in g.subjects(RDF.type, OWL.ObjectProperty) if isinstance(s, URIRef)}


def _datatype_properties(g):
    return {s for s in g.subjects(RDF.type, OWL.DatatypeProperty) if isinstance(s, URIRef)}


def _annotation_properties(g):
    return {s for s in g.subjects(RDF.type, OWL.AnnotationProperty) if isinstance(s, URIRef)}


def _individuals(g):
    return {s for s in g.subjects(RDF.type, OWL.NamedIndividual) if isinstance(s, URIRef)}


def _subclass_edges(g):
    return {
        (s, o)
        for s, o in g.subject_objects(RDFS.subClassOf)
        if isinstance(s, URIRef) and isinstance(o, URIRef)
    }


def m_ANOnto(g, classes, ann_props):
    if not classes:
        return 0.0
    standard = {RDFS.label, RDFS.comment, RDFS.seeAlso, RDFS.isDefinedBy}
    return sum(1 for cls in classes for prop in ann_props | standard for _ in g.objects(cls, prop)) / len(classes)


def m_AROnto(g, classes, data_props):
    if not classes:
        return 0.0
    count = 0
    for prop in data_props:
        domains = [d for d in g.objects(prop, RDFS.domain) if isinstance(d, URIRef)]
        count += sum(1 for d in domains if d in classes) if domains else len(classes)
    return count / len(classes)


def m_CROnto(g, classes, individuals):
    if not classes:
        return 0.0
    populated = {typ for ind in individuals for typ in g.objects(ind, RDF.type) if typ in classes}
    return len(populated) / len(classes)


def m_DITOnto(classes, sc_edges):
    if not classes:
        return 0
    parents = {cls: set() for cls in classes}
    for child, parent in sc_edges:
        if child in parents and parent in classes:
            parents[child].add(parent)
    memo = {}

    def depth(cls):
        if cls in memo:
            return memo[cls]
        ps = parents.get(cls, set())
        memo[cls] = 1 + max(depth(p) for p in ps) if ps else 0
        return memo[cls]

    return max(depth(cls) for cls in classes)


def m_NOCOnto(classes, sc_edges):
    if not classes:
        return 0.0
    children = {cls: 0 for cls in classes}
    for child, parent in sc_edges:
        if parent in children and child in classes:
            children[parent] += 1
    return sum(children.values()) / len(classes)


def _ancestors(cls, parents, cache):
    if cls in cache:
        return cache[cls]
    result = set()
    for parent in parents.get(cls, set()):
        result.add(parent)
        result |= _ancestors(parent, parents, cache)
    cache[cls] = result
    return result


def m_NACOnto(classes, sc_edges):
    if not classes:
        return 0.0
    parents = {cls: set() for cls in classes}
    for child, parent in sc_edges:
        if child in parents and parent in classes:
            parents[child].add(parent)
    cache = {}
    return sum(len(_ancestors(cls, parents, cache)) for cls in classes) / len(classes)


def m_NOMOnto(obj_props, data_props):
    return float(len(obj_props) + len(data_props))


def m_WMCOnto(classes, obj_props, data_props):
    return (len(obj_props) + len(data_props)) / len(classes) if classes else 0.0


def m_TMOnto(classes, sc_edges):
    if not classes:
        return 0.0
    parents = {}
    for child, parent in sc_edges:
        if child in classes and parent in classes:
            parents.setdefault(child, set()).add(parent)
    return sum(1 for cls in classes if len(parents.get(cls, set())) > 1) / len(classes)


def m_LCOMOnto(classes, sc_edges, obj_props, g):
    cls_list = list(classes)
    if len(cls_list) < 2:
        return 0.0
    class_props = {cls: set() for cls in classes}
    for prop in obj_props:
        for domain in g.objects(prop, RDFS.domain):
            if domain in class_props:
                class_props[domain].add(prop)
        for rng in g.objects(prop, RDFS.range):
            if rng in class_props:
                class_props[rng].add(prop)
    total_pairs = len(cls_list) * (len(cls_list) - 1) / 2
    shared = sum(
        1 for i in range(len(cls_list))
        for j in range(i + 1, len(cls_list))
        if class_props[cls_list[i]] & class_props[cls_list[j]]
    )
    return 1.0 - (shared / total_pairs) if total_pairs else 0.0


def m_RFCOnto(g, classes, obj_props):
    if not classes:
        return 0.0
    total = 0
    for cls in classes:
        own = {prop for prop in obj_props if cls in g.objects(prop, RDFS.domain)}
        reached = {rng for prop in own for rng in g.objects(prop, RDFS.range) if rng in classes}
        total += len(own) + len(reached)
    return total / len(classes)


def m_CBOOnto(g, classes, obj_props):
    if not classes:
        return 0.0
    coupled = {cls: set() for cls in classes}
    for prop in obj_props:
        domains = [d for d in g.objects(prop, RDFS.domain) if d in classes]
        ranges = [r for r in g.objects(prop, RDFS.range) if r in classes]
        for domain in domains:
            for rng in ranges:
                if domain != rng:
                    coupled[domain].add(rng)
                    coupled[rng].add(domain)
    return sum(len(values) for values in coupled.values()) / len(classes)


def m_INROnto(individuals, obj_props):
    return len(individuals) / (len(obj_props) or 1)


def m_PROnto(g, obj_props, data_props):
    all_props = obj_props | data_props
    if not all_props:
        return 0.0
    defined = sum(1 for prop in all_props if list(g.objects(prop, RDFS.domain)) or list(g.objects(prop, RDFS.range)))
    return defined / len(all_props)


def m_POnto(classes, sc_edges, obj_props, g):
    if not classes:
        return 0.0
    class_props = {cls: {prop for prop in obj_props if cls in g.objects(prop, RDFS.domain)} for cls in classes}
    child_parents = {}
    for child, parent in sc_edges:
        if child in classes and parent in classes:
            child_parents.setdefault(child, set()).add(parent)
    parent_classes = {p for ps in child_parents.values() for p in ps}
    if not parent_classes:
        return 0.0
    overrides = 0
    for parent in parent_classes:
        children = [cls for cls in classes if parent in child_parents.get(cls, set())]
        overrides += sum(1 for cls in children if class_props.get(cls, set()) & class_props.get(parent, set()))
    return overrides / len(parent_classes)


THRESHOLDS = {
    "ANOnto": ((0, 0.04, 0.08, 0.20), "asc"),
    "AROnto": ((0, 0.02, 0.04, 0.08), "asc"),
    "CROnto": ((0, 0.17, 0.33, 0.50), "asc"),
    "DITOnto": ((1, 2, 3, 4), "asc"),
    "INROnto": ((0, 1, 5, 10), "asc"),
    "LCOMOnto": ((0.90, 0.75, 0.50, 0.25), "desc"),
    "NACOnto": ((0, 1, 3, 5), "asc"),
    "NOCOnto": ((0, 0.50, 1, 2), "asc"),
    "NOMOnto": ((0, 5, 10, 20), "asc"),
    "PROnto": ((0, 0.25, 0.50, 0.75), "asc"),
    "RFCOnto": ((0, 0.50, 1, 2), "asc"),
    "TMOnto": ((0.50, 0.30, 0.20, 0.05), "desc"),
    "WMCOnto": ((0, 0.20, 0.50, 1), "asc"),
    "CBOOnto": ((3, 2, 1, 0.50), "desc"),
    "POnto": ((0, 0.10, 0.25, 0.50), "asc"),
}


def scale(name, raw):
    t1, t2, t3, t4 = THRESHOLDS[name][0]
    direction = THRESHOLDS[name][1]
    if direction == "asc":
        if raw < t1:
            return 1
        if raw < t2:
            return 2
        if raw < t3:
            return 3
        if raw < t4:
            return 4
        return 5
    if raw >= t1:
        return 1
    if raw >= t2:
        return 2
    if raw >= t3:
        return 3
    if raw >= t4:
        return 4
    return 5


SUBCHAR_METRICS = {
    "Formal adequacy": ["ANOnto", "NOMOnto", "WMCOnto", "PROnto"],
    "Domain adequacy": ["CROnto", "AROnto", "INROnto"],
    "Formal correctness": ["DITOnto", "NACOnto", "NOCOnto"],
    "Consistency": ["LCOMOnto", "TMOnto", "CBOOnto"],
    "Modularity": ["CBOOnto", "NOCOnto", "RFCOnto"],
    "Reusability": ["PROnto", "NOMOnto", "CBOOnto"],
    "Understandability": ["ANOnto", "CROnto", "NOCOnto"],
    "Operability": ["INROnto", "CROnto"],
    "Adaptability": ["DITOnto", "NOCOnto", "NACOnto"],
    "Replaceability": ["POnto", "NOCOnto"],
}


CHAR_SUBCHARS = {
    "Functional adequacy": ["Formal adequacy", "Domain adequacy", "Formal correctness"],
    "Reliability": ["Consistency"],
    "Usability": ["Understandability", "Operability"],
    "Maintainability": ["Modularity", "Adaptability"],
    "Portability": ["Reusability", "Replaceability"],
}


def _avg(values):
    vals = [value for value in values if value is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def compute_quality_model(scaled):
    subchars = {
        subchar: _avg([scaled.get(metric) for metric in metrics])
        for subchar, metrics in SUBCHAR_METRICS.items()
    }
    chars = {
        char: _avg([subchars.get(subchar) for subchar in subchars_for_char])
        for char, subchars_for_char in CHAR_SUBCHARS.items()
    }
    return subchars, chars


def method_oquare(onto, label):
    if not onto["loaded"]:
        return {"error": onto["parse_error"]}

    g = onto["graph"]
    classes = _declared_classes(g)
    obj_props = _object_properties(g)
    data_props = _datatype_properties(g)
    ann_props = _annotation_properties(g)
    individuals = _individuals(g)
    sc_edges = _subclass_edges(g)

    raw = {
        "ANOnto": m_ANOnto(g, classes, ann_props),
        "AROnto": m_AROnto(g, classes, data_props),
        "CROnto": m_CROnto(g, classes, individuals),
        "DITOnto": m_DITOnto(classes, sc_edges),
        "INROnto": m_INROnto(individuals, obj_props),
        "LCOMOnto": m_LCOMOnto(classes, sc_edges, obj_props, g),
        "NACOnto": m_NACOnto(classes, sc_edges),
        "NOCOnto": m_NOCOnto(classes, sc_edges),
        "NOMOnto": m_NOMOnto(obj_props, data_props),
        "PROnto": m_PROnto(g, obj_props, data_props),
        "RFCOnto": m_RFCOnto(g, classes, obj_props),
        "TMOnto": m_TMOnto(classes, sc_edges),
        "WMCOnto": m_WMCOnto(classes, obj_props, data_props),
        "CBOOnto": m_CBOOnto(g, classes, obj_props),
        "POnto": m_POnto(classes, sc_edges, obj_props, g),
    }
    scaled = {metric: scale(metric, value) for metric, value in raw.items()}
    subchars, chars = compute_quality_model(scaled)

    print("\n" + "=" * 62)
    print(f"  {label} - OQuaRE quality model")
    print(f"  Classes: {len(classes)}  |  ObjProps: {len(obj_props)}  |  DataProps: {len(data_props)}  |  Individuals: {len(individuals)}")
    print("-" * 62)
    for metric, value in raw.items():
        print(f"  {metric:<12}  {value:>8.3f}  score={scaled[metric]}")

    return {
        "raw": raw,
        "scaled": scaled,
        "subchars": subchars,
        "chars": chars,
    }


def write_oquare_outputs(results_by_label, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_rows = []
    scaled_rows = []
    subchar_rows = []
    char_rows = []
    for label, result in results_by_label.items():
        if "error" in result:
            raw_rows.append({"ontology": label, "metric": "error", "value": result["error"]})
            continue
        raw_rows.extend({"ontology": label, "metric": metric, "value": value} for metric, value in result["raw"].items())
        scaled_rows.extend({"ontology": label, "metric": metric, "score": value} for metric, value in result["scaled"].items())
        subchar_rows.extend({"ontology": label, "subcharacteristic": name, "score": value} for name, value in result["subchars"].items())
        char_rows.extend({"ontology": label, "characteristic": name, "score": value} for name, value in result["chars"].items())

    outputs = [
        (output_dir / "oquare_raw_metrics.csv", raw_rows, ["ontology", "metric", "value"]),
        (output_dir / "oquare_scaled_metrics.csv", scaled_rows, ["ontology", "metric", "score"]),
        (output_dir / "oquare_subcharacteristics.csv", subchar_rows, ["ontology", "subcharacteristic", "score"]),
        (output_dir / "oquare_characteristics.csv", char_rows, ["ontology", "characteristic", "score"]),
    ]
    for path, rows, fieldnames in outputs:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

