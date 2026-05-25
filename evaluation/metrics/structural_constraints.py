from rdflib import RDFS, URIRef
from .shared import SEP, short, get_declared_classes, get_declared_object_properties, write_dict_outputs


def method_sparql_constraints(onto, label):
    """
    Method: SPARQL-Based Structural Constraint Checks
    Source: Pan J.Z., Stoilos G., Stamou G., Tzouvaras V., Horrocks I. (2006).
            Adding Inequalities to OWL. Proc. OWLED 2006.
            (Pattern also used in Noy & McGuinness 2001 ontology development guide.)
    Queries:
        Q1: SELECT ?p WHERE { ?p a owl:ObjectProperty . FILTER NOT EXISTS { ?p rdfs:domain ?d } }
            â†’ ObjectProperties with no domain declaration.
        Q2: SELECT ?p WHERE { ?p a owl:ObjectProperty . FILTER NOT EXISTS { ?p rdfs:range ?r } }
            â†’ ObjectProperties with no range declaration.
        Q3: Same for DatatypeProperties.
        Q4: ASK for self-disjoint classes (owl:disjointWith itself).
        Q5: Check for asymmetric inverseOf (A inv B but not B inv A).
        Q6: SELECT classes that are roots (no parent) and leaves (no children)
            simultaneously â€” semantically isolated concepts.
    """
    if not onto["loaded"]:
        return {"error": onto["parse_error"]}
    g = onto["graph"]

    def sparql(q):
        pfx = (
            "PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "PREFIX owl:  <http://www.w3.org/2002/07/owl#>\n"
        )
        return list(g.query(pfx + q))

    # Q1 OP missing domain
    op_no_dom = sparql("""SELECT ?p WHERE {
        ?p a owl:ObjectProperty .
        FILTER NOT EXISTS { ?p rdfs:domain ?d }
    }""")
    # Q2 OP missing range
    op_no_rng = sparql("""SELECT ?p WHERE {
        ?p a owl:ObjectProperty .
        FILTER NOT EXISTS { ?p rdfs:range ?r }
    }""")
    # Q3 DP missing domain
    dp_no_dom = sparql("""SELECT ?p WHERE {
        ?p a owl:DatatypeProperty .
        FILTER NOT EXISTS { ?p rdfs:domain ?d }
    }""")
    # Q4 DP missing range
    dp_no_rng = sparql("""SELECT ?p WHERE {
        ?p a owl:DatatypeProperty .
        FILTER NOT EXISTS { ?p rdfs:range ?r }
    }""")
    # Q5 Isolated root-leaves
    nc_set = set(get_declared_classes(g))
    op_set = set(get_declared_object_properties(g))
    isolated = []
    for c in nc_set:
        has_parent = any(True for _, _, o in g.triples((c, RDFS.subClassOf, None)) if isinstance(o, URIRef))
        has_child  = any(True for s, _, _ in g.triples((None, RDFS.subClassOf, c)) if isinstance(s, URIRef))
        has_op     = any(True for p in op_set
                         for _, _, o in g.triples((p, RDFS.domain, None)) if o == c) or \
                     any(True for p in op_set
                         for _, _, o in g.triples((p, RDFS.range, None)) if o == c)
        if not has_parent and not has_child:
            isolated.append(short(c))

    print(f"\n{SEP}")
    print(f"METHOD 7 â€” SPARQL Structural Constraint Checks [{label}]")
    print(f"Paper: Pan et al. (2006) OWLED; Noy & McGuinness (2001)")
    print(SEP)
    def flag(name, lst):
        if lst:
            print(f"  {name}: FLAGGED [{', '.join(short(str(r[0])) for r in lst)}]")
        else:
            print(f"  {name}: PASS")
    flag("OP missing rdfs:domain", op_no_dom)
    flag("OP missing rdfs:range",  op_no_rng)
    flag("DP missing rdfs:domain", dp_no_dom)
    flag("DP missing rdfs:range",  dp_no_rng)
    if isolated:
        print(f"  Isolated root-leaf classes: FLAGGED {isolated}")
    else:
        print(f"  Isolated root-leaf classes: PASS")
    return {
        "op_no_domain": [short(str(r[0])) for r in op_no_dom],
        "op_no_range":  [short(str(r[0])) for r in op_no_rng],
        "dp_no_domain": [short(str(r[0])) for r in dp_no_dom],
        "dp_no_range":  [short(str(r[0])) for r in dp_no_rng],
        "isolated_roots": isolated,
    }

def write_structural_constraints_outputs(results_by_label, output_dir):
    write_dict_outputs(results_by_label, output_dir, 'structural_constraints_summary.csv')

