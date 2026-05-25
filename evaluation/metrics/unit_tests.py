import csv
from pathlib import Path
from rdflib import RDFS, OWL, URIRef, BNode
from .shared import SEP, short, get_declared_classes, get_declared_object_properties, get_declared_datatype_properties, get_named_subclass_edges


def method_unit_tests(onto, label):
    """
    Method: Unit Tests for Ontologies
    Source: Vrandecic D., Gangemi A. (2006).
            Unit Tests for Ontologies.
            Proc. OTM Workshops 2006, LNCS 4278, 1012-1020.
    Approach:
        Each test is a SPARQL ASK query encoding an expected entailment (positive)
        or expected non-entailment (negative).
        PASS iff bool(graph.query(ASK_query)) == expected_truth_value.
    Note on RDFLib ASK evaluation:
        g.query("ASK {...}") returns a Result object whose bool() value IS the
        answer (True/False). Do NOT use bool(list(result)) â€” that tests list
        non-emptiness, not the ASK answer, and always returns True.
    """
    if not onto["loaded"]:
        return {"error": onto["parse_error"]}
    g = onto["graph"]
    named_classes = get_declared_classes(g)
    obj_props = get_declared_object_properties(g)
    dt_props = get_declared_datatype_properties(g)
    named_sub = get_named_subclass_edges(g)
    nc_labels = {short(c).lower() for c in named_classes}
    op_labels = {short(p).lower() for p in obj_props}

    def term_uri(term):
        if isinstance(term, URIRef):
            return f"<{term}>"
        raise ValueError(f"Cannot convert non-URI term to SPARQL IRI: {term}")

    pfx = (
        "PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
        "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
        "PREFIX owl:  <http://www.w3.org/2002/07/owl#>\n"
        "PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>\n"
    )

    def ask(query, desc, expected=True):
        result = g.query(pfx + query)
        got    = bool(result)          # correct RDFLib ASK evaluation
        status = "PASS" if got == expected else "FAIL"
        return {"desc": desc, "expected": expected, "got": got, "status": status}

    tests = []

    # Dynamically build tests based on what's actually in the ontology
    # SubClassOf tests
    for (s, o) in named_sub:
        tests.append(ask(
            f"ASK {{ {term_uri(s)} rdfs:subClassOf {term_uri(o)} }}",
            f"{short(s)} subClassOf {short(o)}"
        ))

    # disjointWith tests (up to 3)
    dw_pairs = [(s, o) for s, _, o in
                g.triples((None, OWL.disjointWith, None))
                if isinstance(s, URIRef) and isinstance(o, URIRef)]
    for s, o in dw_pairs[:3]:
        tests.append(ask(
            f"ASK {{ {term_uri(s)} owl:disjointWith {term_uri(o)} }}",
            f"{short(s)} disjointWith {short(o)}"
        ))

    # Property constraints: first ObjectProperty domain + range
    for p in obj_props:
        for _, _, d in g.triples((p, RDFS.domain, None)):
            if isinstance(d, URIRef):
                tests.append(ask(
                    f"ASK {{ {term_uri(p)} rdfs:domain {term_uri(d)} }}",
                    f"{short(p)} domain = {short(d)}"
                ))
        for _, _, r in g.triples((p, RDFS.range, None)):
            if isinstance(r, URIRef):
                tests.append(ask(
                    f"ASK {{ {term_uri(p)} rdfs:range {term_uri(r)} }}",
                    f"{short(p)} range = {short(r)}"
                ))

    # inverseOf test
    for s, _, o in list(g.triples((None, OWL.inverseOf, None)))[:1]:
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            tests.append(ask(
                f"ASK {{ {term_uri(s)} owl:inverseOf {term_uri(o)} }}",
                f"{short(s)} inverseOf {short(o)}"
            ))

    # minCardinality restriction
    min_cards = [(s, o, list(g.objects(o, OWL.onProperty)), list(g.objects(o, OWL.minCardinality)))
                 for s, _, o in g.triples((None, RDFS.subClassOf, None))
                 if isinstance(s, URIRef) and isinstance(o, BNode)]
    for cls, bn, prop, card in min_cards[:1]:
        if prop and card:
            tests.append(ask(
                f"ASK {{ {term_uri(cls)} rdfs:subClassOf ?r . "
                f"?r owl:onProperty {term_uri(prop[0])} ; owl:minCardinality ?n . "
                f"FILTER(xsd:integer(?n) >= 1) }}",
                f"{short(cls)} has owl:minCardinality >= 1 on {short(prop[0])}"
            ))

    # Negative tests: pick 2 pairs that should NOT have subClassOf
    nc_list = list(named_classes)
    ns_set  = named_sub
    negatives_added = 0
    for i, c1 in enumerate(nc_list):
        for c2 in nc_list[i+1:]:
            if (c1, c2) not in ns_set and (c2, c1) not in ns_set and negatives_added < 2:
                tests.append(ask(
                    f"ASK {{ {term_uri(c1)} rdfs:subClassOf {term_uri(c2)} }}",
                    f"NEGATIVE: {short(c1)} NOT subClassOf {short(c2)}",
                    expected=False
                ))
                negatives_added += 1

    passed = sum(1 for t in tests if t["status"] == "PASS")
    total  = len(tests)

    print(f"\n{SEP}")
    print(f"METHOD 9 â€” Unit Tests for Ontologies [{label}]")
    print(f"Paper: Vrandecic & Gangemi (2006) OTM Workshops, LNCS 4278")
    print(SEP)
    print(f"  Results: {passed}/{total} PASS")
    for t in tests:
        mark = "[+]" if t["status"] == "PASS" else "[-]"
        print(f"  {mark} [{t['status']}] {t['desc']}")
    return {"passed": passed, "total": total, "tests": tests}

def write_unit_test_outputs(results_by_label, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    detail_rows = []
    for ontology, result in results_by_label.items():
        summary_rows.append({
            'ontology': ontology,
            'passed': result.get('passed'),
            'total': result.get('total'),
            'pass_rate': (result.get('passed', 0) / result.get('total', 1)) if result.get('total') else 0,
        })
        for test in result.get('tests', []):
            detail_rows.append({'ontology': ontology, **test})
    with open(output_dir / 'unit_tests_summary.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['ontology', 'passed', 'total', 'pass_rate'])
        writer.writeheader(); writer.writerows(summary_rows)
    fieldnames = ['ontology', 'desc', 'expected', 'got', 'status']
    with open(output_dir / 'unit_tests_details.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader(); writer.writerows(detail_rows)

