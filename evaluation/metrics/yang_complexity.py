from collections import deque
from rdflib import RDFS, URIRef
from .shared import SEP, short, get_declared_classes, write_dict_outputs


def method_yang_complexity(onto, label):
    """
    Method: Ontology Complexity Metrics
    Source: Yang Y., Calmet J. (2005). OntoBayes: An Ontology-Bayesian Based
            Uncertainty Reasoning Framework.

    Operationalisation for OWL/RDF:
        - C = declared named classes only
        - parent/child relations = asserted rdfs:subClassOf links between
          declared named classes only
        - anonymous superclass expressions (BNodes) are excluded
        - depth is computed as shortest-path depth from root classes
          (classes with no named declared parent)

    Metrics:
        Tangledness (T):
            T = |{c in C : |NamedParents(c)| > 1}| / |C|

        Average Branching Factor (ABF):
            ABF = |subClassOf_edges| / |{c in C : |NamedChildren(c)| >= 1}|

        Leaf Ratio (LR):
            LR = |{c in C : |NamedChildren(c)| = 0}| / |C|

        Max Depth / Average Depth:
            Computed on the asserted subclass graph using shortest-path BFS
            from root classes.
    """
    if not onto["loaded"]:
        return {
            "error": onto["parse_error"],
            "T": None,
            "ABF": None,
            "LR": None,
            "max_depth": None,
            "avg_depth": None,
        }

    g = onto["graph"]
    nc = get_declared_classes(g)

    if not nc:
        print(f"\n{SEP}")
        print(f"METHOD 4 â€” Yang et al. Complexity Metrics [{label}]")
        print(f"Paper: Yang & Calmet (2005)")
        print(SEP)
        print("  No declared classes found.")
        return {"T": 0.0, "ABF": 0.0, "LR": 0.0, "max_depth": 0, "avg_depth": 0.0}

    # Asserted subclass graph restricted to declared named classes only
    subclass_edges = {
        (s, o)
        for s, _, o in g.triples((None, RDFS.subClassOf, None))
        if isinstance(s, URIRef) and isinstance(o, URIRef) and s in nc and o in nc
    }

    # Parents per class
    named_parents = {c: set() for c in nc}
    # Children per class
    named_children = {c: set() for c in nc}

    for child, parent in subclass_edges:
        named_parents[child].add(parent)
        named_children[parent].add(child)

    # â”€â”€ Tangledness â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    tangled = [c for c in nc if len(named_parents[c]) > 1]
    T = len(tangled) / len(nc)

    # â”€â”€ Average Branching Factor â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    parents_with_child = [c for c in nc if len(named_children[c]) > 0]
    ABF = len(subclass_edges) / len(parents_with_child) if parents_with_child else 0.0

    # â”€â”€ Leaf Ratio â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    leaves = [c for c in nc if len(named_children[c]) == 0]
    LR = len(leaves) / len(nc)

    # â”€â”€ Depth (shortest path from roots) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    roots = [c for c in nc if len(named_parents[c]) == 0]

    # If no roots exist, the hierarchy may be cyclic or malformed.
    # In that case, depth values are not safely interpretable.
    if not roots:
        max_d = None
        avg_d = None
    else:
        depth = {c: float("inf") for c in nc}
        queue = deque()

        for r in roots:
            depth[r] = 0
            queue.append(r)

        while queue:
            cur = queue.popleft()
            for child in named_children[cur]:
                proposed_depth = depth[cur] + 1
                if proposed_depth < depth[child]:
                    depth[child] = proposed_depth
                    queue.append(child)

        finite_depths = [d for d in depth.values() if d != float("inf")]

        max_d = max(finite_depths) if finite_depths else None
        avg_d = (sum(finite_depths) / len(finite_depths)) if finite_depths else None

    # â”€â”€ Reporting â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print(f"\n{SEP}")
    print(f"METHOD 4 â€” Yang et al. Complexity Metrics [{label}]")
    print(f"Paper: Yang & Calmet (2005)")
    print(SEP)

    print("  T   = |tangled| / |C|")
    print(f"      = {len(tangled)} / {len(nc)} = {T:.4f}")

    print("  ABF = |subClassOf_edges| / |parents_with_child|")
    print(f"      = {len(subclass_edges)} / {len(parents_with_child)} = {ABF:.4f}")

    print("  LR  = |leaves| / |C|")
    print(f"      = {len(leaves)} / {len(nc)} = {LR:.4f}")

    if max_d is None or avg_d is None:
        print("  Max depth = not computable")
        print("  Avg depth = not computable")
        print("  Reason    = no root classes found in the asserted named-class hierarchy")
    else:
        print(f"  Max depth = {max_d}")
        print(f"  Avg depth = {avg_d:.4f}")

    return {
        "T": round(T, 4),
        "ABF": round(ABF, 4),
        "LR": round(LR, 4),
        "max_depth": max_d,
        "avg_depth": round(avg_d, 4) if avg_d is not None else None,
    }

def write_yang_complexity_outputs(results_by_label, output_dir):
    write_dict_outputs(results_by_label, output_dir, 'yang_complexity_summary.csv')

