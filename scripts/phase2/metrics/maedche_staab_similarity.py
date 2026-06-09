from collections import defaultdict, deque
from pathlib import Path
import csv
import math

from rdflib import Graph, RDF, RDFS, OWL, URIRef, Literal


def parse_rdf_any(path):
    path = Path(path)
    formats = {
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
    g = Graph()
    g.parse(str(path), format=formats.get(path.suffix.lower()))
    return g


def local_name(node):
    text = str(node)
    if "#" in text:
        return text.rsplit("#", 1)[-1]
    return text.rstrip("/").rsplit("/", 1)[-1]


def labels_or_local_name(g, uri):
    labels = {
        str(label)
        for label in g.objects(uri, RDFS.label)
        if isinstance(label, Literal) and str(label).strip()
    }
    return labels or {local_name(uri)}


def transitive_subclass_closure(edges):
    parents = defaultdict(set)
    for child, parent in edges:
        parents[child].add(parent)

    closure = defaultdict(set)
    for start in set(parents) | {p for values in parents.values() for p in values}:
        seen = set()
        queue = deque(parents.get(start, set()))
        while queue:
            current = queue.popleft()
            if current in seen:
                continue
            seen.add(current)
            queue.extend(parents.get(current, set()) - seen)
        closure[start] = seen
    return {k: set(v) for k, v in closure.items()}


def extract_maedche_staab_ontology(path, name):
    """Extract A, P, Lc, Lr, F, G, H, d(R), and r(R) from RDF/OWL."""
    g = parse_rdf_any(path)

    classes = {s for s in g.subjects(RDF.type, OWL.Class) if isinstance(s, URIRef)}
    classes |= {s for s in g.subjects(RDF.type, RDFS.Class) if isinstance(s, URIRef)}
    for s, o in g.subject_objects(RDFS.subClassOf):
        if isinstance(s, URIRef):
            classes.add(s)
        if isinstance(o, URIRef):
            classes.add(o)

    properties = {s for s in g.subjects(RDF.type, RDF.Property) if isinstance(s, URIRef)}
    properties |= {s for s in g.subjects(RDF.type, OWL.ObjectProperty) if isinstance(s, URIRef)}
    properties |= {s for s in g.subjects(RDF.type, OWL.DatatypeProperty) if isinstance(s, URIRef)}
    properties |= {s for s, _ in g.subject_objects(RDFS.domain) if isinstance(s, URIRef)}
    properties |= {s for s, _ in g.subject_objects(RDFS.range) if isinstance(s, URIRef)}

    F = defaultdict(set)
    class_uri_to_lex = defaultdict(set)
    for cls in classes:
        for label in labels_or_local_name(g, cls):
            F[label].add(cls)
            class_uri_to_lex[cls].add(label)

    G = defaultdict(set)
    property_uri_to_lex = defaultdict(set)
    for prop in properties:
        for label in labels_or_local_name(g, prop):
            G[label].add(prop)
            property_uri_to_lex[prop].add(label)

    subclass_edges = {
        (s, o)
        for s, o in g.subject_objects(RDFS.subClassOf)
        if isinstance(s, URIRef) and isinstance(o, URIRef)
        and s in classes and o in classes
    }

    return {
        "name": name,
        "path": str(path),
        "A": set(classes),
        "P": set(properties),
        "Lc": set(F),
        "Lr": set(G),
        "F": {k: set(v) for k, v in F.items()},
        "G": {k: set(v) for k, v in G.items()},
        "class_uri_to_lex": {k: set(v) for k, v in class_uri_to_lex.items()},
        "property_uri_to_lex": {k: set(v) for k, v in property_uri_to_lex.items()},
        "H": transitive_subclass_closure(subclass_edges),
        "domains": {p: {d for d in g.objects(p, RDFS.domain) if isinstance(d, URIRef)} for p in properties},
        "ranges": {p: {r for r in g.objects(p, RDFS.range) if isinstance(r, URIRef)} for p in properties},
    }


def levenshtein_ed(left, right):
    left, right = str(left), str(right)
    if left == right:
        return 0
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for i, c_left in enumerate(left, 1):
        current = [i]
        for j, c_right in enumerate(right, 1):
            current.append(min(
                current[j - 1] + 1,
                previous[j] + 1,
                previous[j - 1] + (c_left != c_right),
            ))
        previous = current
    return previous[-1]


def string_matching(left, right):
    min_len = min(len(str(left)), len(str(right)))
    if min_len == 0:
        return 0.0
    return max(0.0, (min_len - levenshtein_ed(left, right)) / min_len)


def asymmetric_string_matching(source_lex, target_lex):
    if not source_lex or not target_lex:
        return 0.0
    return sum(max(string_matching(a, b) for b in target_lex) for a in source_lex) / len(source_lex)


def relative_hit(source_lex, target_lex):
    return len(set(source_lex) & set(target_lex)) / len(source_lex) if source_lex else 0.0


def inverse_class_lex(onto, concepts):
    return {
        label
        for concept in concepts
        for label in onto["class_uri_to_lex"].get(concept, set())
    }


def semantic_cotopy(concepts, onto):
    result = set()
    for concept in concepts:
        result |= onto["H"].get(concept, set())
        result |= {child for child, parents in onto["H"].items() if concept in parents}
    return result & onto["A"]


def upwards_cotopy(concepts, onto):
    result = set()
    for concept in concepts:
        result |= onto["H"].get(concept, set())
    return result & onto["A"]


def jaccard(left, right):
    union = set(left) | set(right)
    return len(set(left) & set(right)) / len(union) if union else 0.0


def taxonomic_overlap_prime(label, source, target):
    source_lex = inverse_class_lex(source, semantic_cotopy(source["F"].get(label, set()), source))
    target_lex = inverse_class_lex(target, semantic_cotopy(target["F"].get(label, set()), target))
    return jaccard(source_lex, target_lex)


def taxonomic_overlap_double_prime(label, source, target):
    source_lex = inverse_class_lex(source, semantic_cotopy(source["F"].get(label, set()), source))
    if not target["A"]:
        return 0.0
    return max(
        jaccard(source_lex, inverse_class_lex(target, semantic_cotopy({candidate}, target)))
        for candidate in target["A"]
    )


def lexical_taxonomic_overlap(label, source, target):
    if label in target["Lc"]:
        return taxonomic_overlap_prime(label, source, target), "TO_prime"
    return taxonomic_overlap_double_prime(label, source, target), "TO_double_prime"


def average_taxonomic_overlap(source, target):
    if not source["Lc"]:
        return 0.0
    return sum(lexical_taxonomic_overlap(label, source, target)[0] for label in source["Lc"]) / len(source["Lc"])


def concept_match(source_concepts, source, target_concepts, target):
    return jaccard(
        inverse_class_lex(source, upwards_cotopy(source_concepts, source)),
        inverse_class_lex(target, upwards_cotopy(target_concepts, target)),
    )


def relation_overlap_prime(source_prop, source, target_prop, target):
    source_domains = source["domains"].get(source_prop, set()) & source["A"]
    source_ranges = source["ranges"].get(source_prop, set()) & source["A"]
    target_domains = target["domains"].get(target_prop, set()) & target["A"]
    target_ranges = target["ranges"].get(target_prop, set()) & target["A"]
    if not source_domains or not source_ranges or not target_domains or not target_ranges:
        return None
    return math.sqrt(
        concept_match(source_domains, source, target_domains, target)
        * concept_match(source_ranges, source, target_ranges, target)
    )


def ro_uncomputed_reason(source_prop, source, target_props, target):
    if not source["domains"].get(source_prop, set()):
        return "source_missing_domain"
    if not source["ranges"].get(source_prop, set()):
        return "source_missing_range"
    if not (source["domains"].get(source_prop, set()) & source["A"]):
        return "source_domain_not_class"
    if not (source["ranges"].get(source_prop, set()) & source["A"]):
        return "source_range_not_class"
    if not target_props:
        return "no_target_relation_candidates"
    if not any(
        (target["domains"].get(p, set()) & target["A"]) and (target["ranges"].get(p, set()) & target["A"])
        for p in target_props
    ):
        return "target_candidates_missing_domain_or_range"
    return "no_computable_relation_overlap"


def lexical_relation_overlap(label, source, target, blocked):
    target_props = target["G"].get(label, set()) if label in target["Lr"] else target["P"]
    formula = "RO_double_prime" if label in target["Lr"] else "RO_triple_prime"
    source_props = source["G"].get(label, set())
    if not source_props:
        return 0.0, formula

    total = 0.0
    for source_prop in source_props:
        scores = []
        for target_prop in target_props:
            score = relation_overlap_prime(source_prop, source, target_prop, target)
            if score is not None:
                scores.append(score)
        if not scores:
            scope = "shared_label_candidates" if label in target["Lr"] else "all_target_properties"
            blocked.append((label, source_prop, scope, ro_uncomputed_reason(source_prop, source, target_props, target)))
        total += max(scores) if scores else 0.0
    return total / len(source_props), formula


def best_lexical_matches(source_lex, target_lex, kind, direction):
    rows = []
    for label in sorted(source_lex):
        if target_lex:
            best = max(sorted(target_lex), key=lambda other: (string_matching(label, other), other))
            score = string_matching(label, best)
        else:
            best, score = "", 0.0
        rows.append({
            "direction": direction,
            "kind": kind,
            "source_label": label,
            "best_target_label": best,
            "string_matching": score,
            "exact_hit": label in target_lex,
        })
    return rows


def diagnostics(source, target, direction, blocked):
    missing_domain = sorted(str(p) for p in source["P"] if not source["domains"].get(p, set()))
    missing_range = sorted(str(p) for p in source["P"] if not source["ranges"].get(p, set()))
    nonclass_domain = sorted(str(p) for p in source["P"] if source["domains"].get(p, set()) and not (source["domains"].get(p, set()) & source["A"]))
    nonclass_range = sorted(str(p) for p in source["P"] if source["ranges"].get(p, set()) and not (source["ranges"].get(p, set()) & source["A"]))
    blocked_unique = sorted({(label, str(prop), scope, reason) for label, prop, scope, reason in blocked})
    return [
        {"direction": direction, "diagnostic": "source_class_lexical_entries", "value": len(source["Lc"]), "details": ""},
        {"direction": direction, "diagnostic": "source_property_lexical_entries", "value": len(source["Lr"]), "details": ""},
        {"direction": direction, "diagnostic": "exact_class_lexical_hits", "value": len(source["Lc"] & target["Lc"]), "details": "|".join(sorted(source["Lc"] & target["Lc"]))},
        {"direction": direction, "diagnostic": "exact_property_lexical_hits", "value": len(source["Lr"] & target["Lr"]), "details": "|".join(sorted(source["Lr"] & target["Lr"]))},
        {"direction": direction, "diagnostic": "class_lexical_entries_missing_in_target", "value": len(source["Lc"] - target["Lc"]), "details": "|".join(sorted(source["Lc"] - target["Lc"]))},
        {"direction": direction, "diagnostic": "property_lexical_entries_missing_in_target", "value": len(source["Lr"] - target["Lr"]), "details": "|".join(sorted(source["Lr"] - target["Lr"]))},
        {"direction": direction, "diagnostic": "source_properties_missing_domain", "value": len(missing_domain), "details": "|".join(missing_domain)},
        {"direction": direction, "diagnostic": "source_properties_missing_range", "value": len(missing_range), "details": "|".join(missing_range)},
        {"direction": direction, "diagnostic": "source_properties_domain_not_class", "value": len(nonclass_domain), "details": "|".join(nonclass_domain)},
        {"direction": direction, "diagnostic": "source_properties_range_not_class", "value": len(nonclass_range), "details": "|".join(nonclass_range)},
        {"direction": direction, "diagnostic": "relations_where_ro_could_not_be_computed", "value": len(blocked_unique), "details": "|".join(f"{l}: {p} against {s} ({r})" for l, p, s, r in blocked_unique)},
    ]


def compute_direction(source, target, direction):
    blocked = []
    to_rows = []
    for label in sorted(source["Lc"]):
        score, formula = lexical_taxonomic_overlap(label, source, target)
        to_rows.append({
            "direction": direction,
            "class_label": label,
            "formula": formula,
            "taxonomic_overlap": score,
            "exact_hit": label in target["Lc"],
            "source_uris": "|".join(sorted(str(uri) for uri in source["F"].get(label, set()))),
            "target_uris": "|".join(sorted(str(uri) for uri in target["F"].get(label, set()))),
        })

    ro_rows = []
    for label in sorted(source["Lr"]):
        score, formula = lexical_relation_overlap(label, source, target, blocked)
        ro_rows.append({
            "direction": direction,
            "relation_label": label,
            "formula": formula,
            "relation_overlap": score,
            "exact_hit": label in target["Lr"],
            "source_uris": "|".join(sorted(str(uri) for uri in source["G"].get(label, set()))),
            "target_uris": "|".join(sorted(str(uri) for uri in target["G"].get(label, set()))),
        })

    return {
        "summary": {
            "direction": direction,
            "source": source["name"],
            "target": target["name"],
            "source_path": source["path"],
            "target_path": target["path"],
            "class_string_matching": asymmetric_string_matching(source["Lc"], target["Lc"]),
            "property_string_matching": asymmetric_string_matching(source["Lr"], target["Lr"]),
            "class_relative_hit": relative_hit(source["Lc"], target["Lc"]),
            "property_relative_hit": relative_hit(source["Lr"], target["Lr"]),
            "taxonomic_overlap": average_taxonomic_overlap(source, target),
            "relation_overlap": sum(row["relation_overlap"] for row in ro_rows) / len(source["Lr"]) if source["Lr"] else 0.0,
            "source_class_lexical_entries": len(source["Lc"]),
            "target_class_lexical_entries": len(target["Lc"]),
            "source_property_lexical_entries": len(source["Lr"]),
            "target_property_lexical_entries": len(target["Lr"]),
            "exact_class_lexical_hits": len(source["Lc"] & target["Lc"]),
            "exact_property_lexical_hits": len(source["Lr"] & target["Lr"]),
        },
        "class_matching": best_lexical_matches(source["Lc"], target["Lc"], "class", direction),
        "property_matching": best_lexical_matches(source["Lr"], target["Lr"], "property", direction),
        "to_rows": to_rows,
        "ro_rows": ro_rows,
        "diagnostics": diagnostics(source, target, direction, blocked),
    }


def write_csv(path, rows, fieldnames):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_maedche_staab_evaluation(generated_path, reference_path, output_dir):
    generated = extract_maedche_staab_ontology(generated_path, "generated")
    reference = extract_maedche_staab_ontology(reference_path, "reference")
    directions = [
        compute_direction(generated, reference, "generated_to_reference"),
        compute_direction(reference, generated, "reference_to_generated"),
    ]

    summary = [d["summary"] for d in directions]
    class_matching = [r for d in directions for r in d["class_matching"]]
    property_matching = [r for d in directions for r in d["property_matching"]]
    to_rows = [r for d in directions for r in d["to_rows"]]
    ro_rows = [r for d in directions for r in d["ro_rows"]]
    diag_rows = [r for d in directions for r in d["diagnostics"]]

    output_dir = Path(output_dir)
    write_csv(output_dir / "maedche_staab_summary.csv", summary, list(summary[0].keys()))
    write_csv(output_dir / "maedche_staab_class_lexical_matching.csv", class_matching,
              ["direction", "kind", "source_label", "best_target_label", "string_matching", "exact_hit"])
    write_csv(output_dir / "maedche_staab_property_lexical_matching.csv", property_matching,
              ["direction", "kind", "source_label", "best_target_label", "string_matching", "exact_hit"])
    write_csv(output_dir / "maedche_staab_per_class_taxonomic_overlap.csv", to_rows,
              ["direction", "class_label", "formula", "taxonomic_overlap", "exact_hit", "source_uris", "target_uris"])
    write_csv(output_dir / "maedche_staab_per_relation_overlap.csv", ro_rows,
              ["direction", "relation_label", "formula", "relation_overlap", "exact_hit", "source_uris", "target_uris"])
    write_csv(output_dir / "maedche_staab_diagnostics.csv", diag_rows,
              ["direction", "diagnostic", "value", "details"])

    for row in summary:
        print(
            f"{row['direction']}: "
            f"class SM={row['class_string_matching']:.4f}, "
            f"property SM={row['property_string_matching']:.4f}, "
            f"TO={row['taxonomic_overlap']:.4f}, "
            f"RO={row['relation_overlap']:.4f}"
        )
    print(f"CSV outputs: {output_dir}")

