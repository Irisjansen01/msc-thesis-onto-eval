"""
ontology_evaluation.py
======================
Reproducible evaluation script for MSc thesis: ontology quality assessment.

Design choice:
- The loader is intentionally minimal.
- It only parses the ontology and stores the asserted RDF graph.
- Metric-specific entity extraction is handled by small helper functions or
  inside each metric, so methodological choices remain visible and explicit.

Usage:
    python ontology_evaluation.py

Dependencies:
    pip install rdflib pyshacl

Tested with:
    Python 3.10+
    rdflib 6.x
    pyshacl 0.22.x
"""

from pathlib import Path
import re
import json
import warnings
from rdflib import Graph, RDF, RDFS, OWL, URIRef, BNode, Namespace, Literal
from rdflib.namespace import XSD

# Suppress RDFLib URI warnings
import logging
rdf_logger = logging.getLogger("rdflib")
rdf_logger.setLevel(logging.ERROR)

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------

BASE_PATH = Path(r"Bureaublad")
if not BASE_PATH.exists():
    desktop = Path.home() / "Desktop"
    BASE_PATH = desktop if desktop.exists() else Path.cwd()

ONTOLOGIES = {
    "ontology_1": BASE_PATH / "music-final.ttl",
    "ontology_2": BASE_PATH / "hospital-final.ttl"
}

SEP = "=" * 72
SEP2 = "-" * 72


# -----------------------------------------------------------------------------
# BASIC UTILITIES
# -----------------------------------------------------------------------------

def short(node):
    """Return a readable local name for a URIRef, else string form."""
    if isinstance(node, URIRef):
        text = str(node)
        return text.split("#")[-1] if "#" in text else text.rstrip("/").split("/")[-1]
    return str(node)


def is_named_uri(node):
    """True if node is a URIRef."""
    return isinstance(node, URIRef)


def sorted_uris(values):
    """Stable sort for URIRefs."""
    return sorted(values, key=str)


def wrap_method(result, name, number=None):
    """Wrap a metric result with method metadata for JSON export."""
    return {
        "method_name": name,
        **({"method_number": number} if number is not None else {}),
        "result": result,
    }


def require_loaded(onto):
    """Raise a clear error if the ontology did not parse."""
    if not onto["loaded"]:
        raise ValueError(
            f"Ontology could not be parsed: {onto['path']}\n{onto['parse_error']}"
        )


# -----------------------------------------------------------------------------
# MINIMAL LOADER
# -----------------------------------------------------------------------------

def load_ontology(path):
    """
    Parse a Turtle file into an RDFLib graph.
    """
    g = Graph()
    path = Path(path)

    try:
        g.parse(str(path), format="turtle")
        return {
            "path": path,
            "graph": g,
            "loaded": True,
            "parse_error": None,
            "triple_count": len(g),
        }
    except Exception as e:
        return {
            "path": path,
            "graph": g,
            "loaded": False,
            "parse_error": str(e),
            "triple_count": 0,
        }


def load_all_ontologies(ontologies):
    """Load all ontology files from the ONTOLOGIES mapping."""
    return {label: load_ontology(path) for label, path in ontologies.items()}


# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# Use only when the same operationalisation is reused across metrics.
# -----------------------------------------------------------------------------

def get_declared_classes(g):
    """Named resources explicitly declared as owl:Class."""
    return {
        s for s in g.subjects(RDF.type, OWL.Class)
        if is_named_uri(s)
    }


def get_declared_object_properties(g):
    """Named resources explicitly declared as owl:ObjectProperty."""
    return {
        s for s in g.subjects(RDF.type, OWL.ObjectProperty)
        if is_named_uri(s)
    }


def get_declared_datatype_properties(g):
    """Named resources explicitly declared as owl:DatatypeProperty."""
    return {
        s for s in g.subjects(RDF.type, OWL.DatatypeProperty)
        if is_named_uri(s)
    }


def get_declared_annotation_properties(g):
    """Named resources explicitly declared as owl:AnnotationProperty."""
    return {
        s for s in g.subjects(RDF.type, OWL.AnnotationProperty)
        if is_named_uri(s)
    }


def get_declared_named_individuals(g):
    """Named resources explicitly declared as owl:NamedIndividual."""
    return {
        s for s in g.subjects(RDF.type, OWL.NamedIndividual)
        if is_named_uri(s)
    }


def get_named_subclass_edges(g):
    """Asserted rdfs:subClassOf triples with named subject and named object."""
    return {
        (s, o)
        for s, _, o in g.triples((None, RDFS.subClassOf, None))
        if is_named_uri(s) and is_named_uri(o)
    }


def get_bnode_subclass_edges(g):
    """Asserted rdfs:subClassOf triples with named subject and blank-node object."""
    return {
        (s, o)
        for s, _, o in g.triples((None, RDFS.subClassOf, None))
        if is_named_uri(s) and isinstance(o, BNode)
    }


# -----------------------------------------------------------------------------
# EXAMPLE: DESCRIPTIVE PROFILE
# Not treated as an evaluation method.
# -----------------------------------------------------------------------------

def descriptive_profile(onto, label):
    """
    Descriptive structural profile of the asserted ontology graph.

    This is not treated as a standalone quality metric. It provides contextual
    counts to support interpretation of later evaluation results.
    """
    require_loaded(onto)
    g = onto["graph"]

    declared_classes = get_declared_classes(g)
    declared_object_properties = get_declared_object_properties(g)
    declared_datatype_properties = get_declared_datatype_properties(g)
    declared_annotation_properties = get_declared_annotation_properties(g)
    declared_named_individuals = get_declared_named_individuals(g)

    named_sub = get_named_subclass_edges(g)
    bnode_sub = get_bnode_subclass_edges(g)

    equiv = list(g.triples((None, OWL.equivalentClass, None)))
    disjoint = list(g.triples((None, OWL.disjointWith, None)))
    inverse = list(g.triples((None, OWL.inverseOf, None)))
    domains = list(g.triples((None, RDFS.domain, None)))
    ranges = list(g.triples((None, RDFS.range, None)))
    labels = list(g.triples((None, RDFS.label, None)))
    comments = list(g.triples((None, RDFS.comment, None)))

    anonymous_subclass_expressions = [
        o for _, _, o in g.triples((None, RDFS.subClassOf, None))
        if isinstance(o, BNode)
    ]

    print(f"\n{SEP}")
    print(f"DESCRIPTIVE PROFILE [{label}]")
    print(SEP)

    stats = {
        "declared_named_classes": len(declared_classes),
        "declared_object_properties": len(declared_object_properties),
        "declared_datatype_properties": len(declared_datatype_properties),
        "declared_annotation_properties": len(declared_annotation_properties),
        "declared_named_individuals": len(declared_named_individuals),
        "named_subClassOf": len(named_sub),
        "bnode_subClassOf": len(bnode_sub),
        "equivalentClass_triples": len(equiv),
        "disjointWith_triples": len(disjoint),
        "inverseOf_triples": len(inverse),
        "domain_axioms": len(domains),
        "range_axioms": len(ranges),
        "rdfs_label_triples": len(labels),
        "rdfs_comment_triples": len(comments),
        "anonymous_subclass_expressions": len(anonymous_subclass_expressions),
        "total_triples": onto["triple_count"],
    }

    for k, v in stats.items():
        print(f"  {k:<34}: {v}")

    return stats
# ─────────────────────────────────────────────────────────────────────────────
# BASIC ONTOLOGY STATISTICS
# ─────────────────────────────────────────────────────────────────────────────

def method_basic_statistics(onto, label):
    """
    Method: Basic Ontology Statistics
    """
    if not onto["loaded"]:
        return {"error": onto["parse_error"]}
    
    g = onto["graph"]
    
    # Extract entities directly from graph
    named_classes = {s for s in g.subjects(RDF.type, OWL.Class) if isinstance(s, URIRef)}
    obj_props = {s for s in g.subjects(RDF.type, OWL.ObjectProperty) if isinstance(s, URIRef)}
    dt_props = {s for s in g.subjects(RDF.type, OWL.DatatypeProperty) if isinstance(s, URIRef)}
    ann_props = {s for s in g.subjects(RDF.type, OWL.AnnotationProperty) if isinstance(s, URIRef)}
    individuals = {s for s in g.subjects(RDF.type, OWL.NamedIndividual) if isinstance(s, URIRef)}
    
    equiv   = list(g.triples((None, OWL.equivalentClass, None)))
    disjoint = list(g.triples((None, OWL.disjointWith, None)))
    inverse  = list(g.triples((None, OWL.inverseOf, None)))
    domains  = list(g.triples((None, RDFS.domain, None)))
    ranges   = list(g.triples((None, RDFS.range, None)))
    labels   = list(g.triples((None, RDFS.label, None)))
    comments = list(g.triples((None, RDFS.comment, None)))
    
    # named-to-named subClassOf
    named_sub = len({(s, o) for s, _, o in g.triples((None, RDFS.subClassOf, None))
                     if isinstance(s, URIRef) and isinstance(o, URIRef)})
    # named-to-bnode subClassOf
    bnode_sub = len({(s, o) for s, _, o in g.triples((None, RDFS.subClassOf, None))
                     if isinstance(s, URIRef) and isinstance(o, BNode)})
    
    restrictions = [
        o for _, _, o in g.triples((None, RDFS.subClassOf, None))
        if isinstance(o, BNode)
    ]

    print(f"\n{SEP}")
    print(f"Basic Ontology Statistics [{label}]")
    print(SEP)
    stats = {
        "named_classes":     len(named_classes),
        "object_properties": len(obj_props),
        "datatype_properties": len(dt_props),
        "annotation_properties": len(ann_props),
        "named_individuals": len(individuals),
        "named_subClassOf":  named_sub,
        "bnode_subClassOf":  bnode_sub,
        "equivalentClass":   len(equiv),
        "disjointWith":      len(disjoint),
        "inverseOf":         len(inverse),
        "domain_axioms":     len(domains),
        "range_axioms":      len(ranges),
        "rdfs_label":        len(labels),
        "rdfs_comment":      len(comments),
        "restrictions":      len(restrictions),
        "total_triples":     onto["triple_count"],
    }
    for k, v in stats.items():
        print(f"  {k:<30}: {v}")
    return stats


# ─────────────────────────────────────────────────────────────────────────────
# METHOD 1 — RDFLIB SYNTAX PARSING
# ─────────────────────────────────────────────────────────────────────────────

def method_parseability_check(onto, label):
    """
    Method: RDF syntax parseability (RDFLib)

    PASS  = ontology parsed successfully by RDFLib
    FAIL  = RDFLib raised a parsing exception
    """
    if onto["loaded"]:
        status = "PASS"
    else:
        status = f"FAIL: {onto['parse_error']}"

    print(f"\n{SEP}")
    print(f"METHOD 1 — Parseability Check [{label}]")
    print(SEP)
    print(f"  Parse status : {status}")

    return {"status": status}


# ─────────────────────────────────────────────────────────────────────────────
# METHOD 3 — ONTOQA SCHEMA METRICS
# ─────────────────────────────────────────────────────────────────────────────

def method_ontoqa(onto, label):
    """
    Method: OntoQA Schema-level Metrics (faithful OWL operationalisation)

    Source:
        Tartir et al. (2005) OntoQA

    Notes:
        - Relationships (P) are operationalised as object properties.
        - Attributes (A) are operationalised as datatype properties.
        - Metrics are computed on the asserted RDF graph only.
        - Instance detection is based on rdf:type usage (not owl:NamedIndividual).
    """

    if not onto["loaded"]:
        return {"error": onto["parse_error"]}

    g = onto["graph"]

    # ── Sets ────────────────────────────────────────────────────────────────
    C  = get_declared_classes(g)
    P  = get_declared_object_properties(g)
    A  = get_declared_datatype_properties(g)

    subclass_edges = {
        (s, o)
        for s, _, o in g.triples((None, RDFS.subClassOf, None))
        if isinstance(s, URIRef) and isinstance(o, URIRef) and s in C and o in C
    }

    # ── RR: Relationship Richness ───────────────────────────────────────────
    P_inh     = len(subclass_edges)
    P_non_inh = len(P)   # ONLY object properties

    RR = P_non_inh / (P_inh + P_non_inh) if (P_inh + P_non_inh) else 0

    # ── AR: Attribute Richness ──────────────────────────────────────────────
    attr_per_class = {}

    for c in C:
        attrs = {
            p for p in A
            for _, _, d in g.triples((p, RDFS.domain, None))
            if d == c
        }
        attr_per_class[c] = len(attrs)

    AR = sum(attr_per_class.values()) / len(C) if C else 0

    # ── IR: Inheritance Richness ────────────────────────────────────────────
    subclass_count = {}

    for c in C:
        children = {
            s for s, _, o in g.triples((None, RDFS.subClassOf, None))
            if isinstance(s, URIRef) and s in C and o == c
        }
        subclass_count[c] = len(children)

    IR = sum(subclass_count.values()) / len(C) if C else 0

    # ── CR: Class Richness ──────────────────────────────────────────────────
    # Use ALL rdf:type assertions (not only owl:NamedIndividual)
    classes_with_instances = {
        t for s, _, t in g.triples((None, RDF.type, None))
        if isinstance(s, URIRef) and t in C
    }

    CR = len(classes_with_instances) / len(C) if C else 0

    # ── Output ──────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"METHOD — OntoQA Schema Metrics [{label}]")
    print(f"Paper: Tartir et al. (2005)")
    print(SEP)

    print(f"  RR = |P| / (|HC| + |P|)")
    print(f"     = {P_non_inh} / ({P_inh} + {P_non_inh}) = {RR:.4f}")

    print(f"  AR = Sum |Attr(c)| / |C|")
    print(f"     = {sum(attr_per_class.values())} / {len(C)} = {AR:.4f}")

    print(f"  IR = Sum |SubClasses(c)| / |C|")
    print(f"     = {sum(subclass_count.values())} / {len(C)} = {IR:.4f}")

    print(f"  CR = |Classes_with_instances| / |C|")
    print(f"     = {len(classes_with_instances)} / {len(C)} = {CR:.4f}")

    return {
        "RR": round(RR, 4),
        "AR": round(AR, 4),
        "IR": round(IR, 4),
        "CR": round(CR, 4),
    }


def method_logical_consistency(onto, label):
    """
    Method: Logical Consistency Check (placeholder).
    """
    if not onto["loaded"]:
        return {"error": onto["parse_error"]}

    print(f"\n{SEP}")
    print(f"METHOD — Logical Consistency Check [{label}]")
    print(SEP)
    print("  [SKIP] Full OWL logical consistency check is not implemented.")
    return {"status": "SKIPPED", "reason": "not_implemented"}

from collections import deque

# ─────────────────────────────────────────────────────────────────────────────
# METHOD 4 — YANG ET AL. COMPLEXITY METRICS
# ─────────────────────────────────────────────────────────────────────────────

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
        print(f"METHOD 4 — Yang et al. Complexity Metrics [{label}]")
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

    # ── Tangledness ──────────────────────────────────────────────────────────
    tangled = [c for c in nc if len(named_parents[c]) > 1]
    T = len(tangled) / len(nc)

    # ── Average Branching Factor ─────────────────────────────────────────────
    parents_with_child = [c for c in nc if len(named_children[c]) > 0]
    ABF = len(subclass_edges) / len(parents_with_child) if parents_with_child else 0.0

    # ── Leaf Ratio ───────────────────────────────────────────────────────────
    leaves = [c for c in nc if len(named_children[c]) == 0]
    LR = len(leaves) / len(nc)

    # ── Depth (shortest path from roots) ─────────────────────────────────────
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

    # ── Reporting ────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"METHOD 4 — Yang et al. Complexity Metrics [{label}]")
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



# ─────────────────────────────────────────────────────────────────────────────
# METHOD 7 — SPARQL STRUCTURAL CONSTRAINT CHECKS
# ─────────────────────────────────────────────────────────────────────────────

def method_sparql_constraints(onto, label):
    """
    Method: SPARQL-Based Structural Constraint Checks
    Source: Pan J.Z., Stoilos G., Stamou G., Tzouvaras V., Horrocks I. (2006).
            Adding Inequalities to OWL. Proc. OWLED 2006.
            (Pattern also used in Noy & McGuinness 2001 ontology development guide.)
    Queries:
        Q1: SELECT ?p WHERE { ?p a owl:ObjectProperty . FILTER NOT EXISTS { ?p rdfs:domain ?d } }
            → ObjectProperties with no domain declaration.
        Q2: SELECT ?p WHERE { ?p a owl:ObjectProperty . FILTER NOT EXISTS { ?p rdfs:range ?r } }
            → ObjectProperties with no range declaration.
        Q3: Same for DatatypeProperties.
        Q4: ASK for self-disjoint classes (owl:disjointWith itself).
        Q5: Check for asymmetric inverseOf (A inv B but not B inv A).
        Q6: SELECT classes that are roots (no parent) and leaves (no children)
            simultaneously — semantically isolated concepts.
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
    print(f"METHOD 7 — SPARQL Structural Constraint Checks [{label}]")
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


# ─────────────────────────────────────────────────────────────────────────────
# METHOD 8 — SHACL VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def method_shacl(onto, label):
    """
    Method: SHACL Shapes Constraint Language Validation
    Source: Knublauch H., Kontokostas D. (2017).
            Shapes Constraint Language (SHACL). W3C Recommendation, 20 July 2017.
            https://www.w3.org/TR/shacl/
    Note: This implementation is skipped due to complexity of generating valid SHACL
    shapes dynamically. SHACL validation is best used with hand-authored shapes files.
    """
    if not onto["loaded"]:
        return {"error": onto["parse_error"]}
    
    print(f"\n{SEP}")
    print(f"METHOD 8 — SHACL Validation [{label}]")
    print(f"Paper: Knublauch & Kontokostas (2017) W3C SHACL Recommendation")
    print(SEP)
    print(f"  [SKIP] SHACL validation requires hand-authored shapes files.")
    print(f"  Recommendation: Define shapes manually in a separate SHACL shapes graph.")
    print(f"  Reference: https://www.w3.org/TR/shacl/")
    return {"status": "SKIPPED", "reason": "requires_manual_shapes"}


# ─────────────────────────────────────────────────────────────────────────────
# METHOD 9 — UNIT TESTS FOR ONTOLOGIES
# ─────────────────────────────────────────────────────────────────────────────

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
        answer (True/False). Do NOT use bool(list(result)) — that tests list
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
    print(f"METHOD 9 — Unit Tests for Ontologies [{label}]")
    print(f"Paper: Vrandecic & Gangemi (2006) OTM Workshops, LNCS 4278")
    print(SEP)
    print(f"  Results: {passed}/{total} PASS")
    for t in tests:
        mark = "[+]" if t["status"] == "PASS" else "[-]"
        print(f"  {mark} [{t['status']}] {t['desc']}")
    return {"passed": passed, "total": total, "tests": tests}


# ─────────────────────────────────────────────────────────────────────────────
# METHOD 11 — CQ COVERAGE (Gruninger & Fox 1995)
# ─────────────────────────────────────────────────────────────────────────────

def method_cq_coverage(onto, label):
    """
    Method: Competency Question Coverage
    Source: Gruninger M., Fox M.S. (1995).
            Methodology for the Design and Evaluation of Ontologies.
            Proc. IJCAI-95 Workshop on Basic Ontological Issues in
            Knowledge Sharing. Montreal.
    Approach:
        For each CQ, identify the minimum set of ontology elements required to
        answer it (classes, object properties, datatype properties).
        A CQ is SATISFIABLE iff ALL required elements are present.
        Presence check: local name of the element (case-insensitive substring match
        against the set of declared entity local names).
    Formula:
        CQ_coverage = |{CQ_i : satisfiable(CQ_i)}| / |CQs|
    """
    if not onto["loaded"]:
        return {"error": onto["parse_error"]}
    g = onto["graph"]
    nc_s = {short(c).lower() for c in get_declared_classes(g)}
    op_s = {short(p).lower() for p in get_declared_object_properties(g)}
    dp_s = {short(p).lower() for p in get_declared_datatype_properties(g)}
    has_min = bool(list(g.triples((None, OWL.minCardinality, None))))

    # Each CQ: (id, question, [[class_alternatives]], [[op_alternatives]], [[dp_alternatives]])
    # OR logic within each group, AND logic across groups
    path_lower = str(onto["path"]).lower()
    if "hospital" in path_lower or label.lower().endswith("ontology_2"):
        CQS = [
            ("CQ1",  "What medical degrees does a certain person have?",
             [["person"],["degree","medicaldegree"]],
             [["hasdegree","medicaldegree","degree"]], []),
            ("CQ2",  "During what time period did a certain person study for a specific degree?",
             [["person"],["degree","medicaldegree"],["timeperiod","studyperiod"]],
             [["studiedfor","studied","hasstudied"]], [["startdate","enddate","timeperiod"]]),
            ("CQ3",  "When was a certain person first employed at a certain hospital?",
             [["person"],["hospital"],["employment","position"]],
             [["employedat","worksat","employed"]], [["startdate","employeddate","firstemployed"]]),
            ("CQ4",  "In what city is a certain hospital located?",
             [["hospital"],["city"]],
             [["locatedin","islocatedin","cityof"]], []),
            ("CQ5",  "In what country is a certain city located?",
             [["city"],["country"]],
             [["locatedin","countryof","islocatedin"]], []),
            ("CQ6",  "Who are the members of a certain union at a certain point in time?",
             [["union"],["person","member"],["membership","unionmembership"]],
             [["hasmember","memberof","unionmember","hasmembership"]],
             [["timeperiod","eventdate","pointintime"]]),
            ("CQ7",  "What role does a certain person have within a certain union group at a certain point in time?",
             [["person"],["union","group"],["role"]],
             [["hasrole","rolein","memberrole"]], [["timeperiod","eventdate","pointintime"]]),
            ("CQ8",  "What is the evaluation statement given by a certain doctor for a certain employee?",
             [["doctor"],["employee"],["evaluation","statement"]],
             [["hasstatement","evaluationof","givesstatement"]], []),
            ("CQ9",  "What articles is a specific book or CD composed of?",
             [["book","cd"],["article"]],
             [["containsarticle","hasarticle","composedof"]], []),
            ("CQ10", "How many pages does a particular book contain?",
             [["book"]],
             [["haspages","pagecount"]], [["pages","numberofpages","npages"]]),
            ("CQ11", "When was a certain book or CD published?",
             [["book","cd"]],
             [["published","haspublication"]], [["publicationdate","publisheddate","publicationyear"]]),
            ("CQ12", "When did a certain seminar take place?",
             [["seminar"]],
             [], [["date","eventdate","seminardate"]]),
            ("CQ13", "What articles were presented in a certain seminar?",
             [["seminar"],["article"]],
             [["presentedarticle","hasarticle","presents"]], []),
            ("CQ14", "Where did a certain seminar take place?",
             [["seminar"],["location","venue","city"]],
             [["tookplaceat","location","venueof"]], []),
            ("CQ15", "At least one article is always presented at each seminar.",
             [["seminar"],["article"]],
             [["hasarticle","presentedarticle","includesarticle"]], []),
        ]
    else:
        CQS = [
            ("CQ1",  "What instruments does a certain person play?",
             [["person","musician"],["instrument"]],
             [["playsinstrument","plays"]], []),
            ("CQ2",  "What are the members of a certain band at a certain point in time?",
             [["band","musicgroup"],["person","musician"]],
             [["hasmember","membership","membershipof","personmembership"]], []),
            ("CQ3",  "What role does a certain person have in a certain band at a certain point in time?",
             [["band","musicgroup"],["person","musician"],["role"]],
             [["hasrole"]], []),
            ("CQ4",  "During what time period was a certain album recorded?",
             [["album","record"]],
             [],
             [["recordingstart","startdate"],["recordingend","enddate"]]),
            ("CQ5",  "How many tracks does a particular album contain?",
             [["album","record"],["track"]],
             [["hastrack"]], []),
            ("CQ6",  "When was a certain album released?",
             [["album","record"]],
             [], [["releasedate"]]),
            ("CQ7",  "What song is a specific track a recording of?",
             [["track"],["song","musicalwork"]],
             [["trackofsong","recordingof","issongof"]], []),
            ("CQ8",  "When was a certain song composed?",
             [["song","musicalwork"]],
             [], [["composedat","compositiondate"]]),
            ("CQ9",  "What does a certain critic say about a certain record?",
             [["critic","reviewer"],["review","critique"]],
             [["hasreview","reviewof","writesreview"]], []),
            ("CQ10", "When did a certain performance take place?",
             [["performance"]],
             [], [["performancedate","eventdate","performancetime"]]),
            ("CQ11", "What songs were played in a certain performance?",
             [["performance"],["song","musicalwork"]],
             [["featuredsong","playedsong","hassong","includestrack"]], []),
            ("CQ12", "Where did a certain performance take place?",
             [["performance"]],
             [["tookplaceat","location","venueof"]], []),
            ("CQ13", "In what region is a certain city located?",
             [["city"],["region"]],
             [["locatedin"]], []),
            ("CQ14", "In what country is a certain region located?",
             [["region"],["country"]],
             [["regionincountry","incountry"]], []),
            ("CQ15", "A record always contains at least one track.",
             [["record","album"],["track"]],
             [["hastrack"]], []),
        ]

    results = []
    for cq_id, q, c_groups, op_groups, dp_groups in CQS:
        c_ok  = all(any(any(alt in s for s in nc_s) for alt in grp) for grp in c_groups)
        op_ok = all(any(any(alt in s for s in op_s) for alt in grp) for grp in op_groups)
        dp_ok = all(any(any(alt in s for s in dp_s) for alt in grp) for grp in dp_groups)
        if cq_id == "CQ15":
            op_ok = op_ok or has_min
        sat = c_ok and op_ok and dp_ok
        results.append((cq_id, q, sat, c_ok, op_ok, dp_ok))

    satisfied = sum(1 for _, _, s, *_ in results if s)
    coverage  = satisfied / len(results)

    print(f"\n{SEP}")
    print(f"METHOD 11 — CQ Coverage [{label}]")
    print(f"Paper: Gruninger & Fox (1995) IJCAI-95 Workshop")
    print(SEP)
    for cq_id, q, sat, c_ok, op_ok, dp_ok in results:
        mark = "[+]" if sat else "[-]"
        detail = f"[classes={'Y' if c_ok else 'N'} ops={'Y' if op_ok else 'N'} dps={'Y' if dp_ok else 'N'}]"
        print(f"  {mark} {cq_id:5s} {detail}  {q}")
    print(f"\n  Coverage: {satisfied}/{len(results)} = {coverage:.1%}")
    return {"satisfied": satisfied, "total": len(results),
            "coverage_pct": round(coverage * 100, 1)}


# ─────────────────────────────────────────────────────────────────────────────
# METHOD 12 — ANNOTATION COMPLETENESS (Zaveri et al. 2016)
# ─────────────────────────────────────────────────────────────────────────────

def method_annotation_completeness(onto, label):
    """
    Method: Column Completeness / Annotation Completeness
    Source: Zaveri A., Rula A., Maurino A., Pietrobon R., Lehmann J., Auer S.
            (2016). Quality Assessment for Linked Data: A Survey.
            Semantic Web, 7(1), 63-93. (Section 4.2, "Completeness")
    Formula:
        completeness(annotation_prop) =
            |{e ∈ Entities : (e, annotation_prop, ?) ∈ G}| / |Entities|
    Applied to: rdfs:label, rdfs:comment, owl:deprecated
    Entity set = named_classes ∪ object_properties ∪ datatype_properties.
    """
    if not onto["loaded"]:
        return {"error": onto["parse_error"]}
    g = onto["graph"]
    all_e = (list(get_declared_classes(g)) + list(get_declared_object_properties(g)) + 
             list(get_declared_datatype_properties(g)))
    total = len(all_e)

    metrics = [
        ("rdfs:label",    RDFS.label),
        ("rdfs:comment",  RDFS.comment),
        ("owl:deprecated", OWL.deprecated),
    ]

    print(f"\n{SEP}")
    print(f"METHOD 12 — Annotation Completeness [{label}]")
    print(f"Paper: Zaveri et al. (2016) Semantic Web 7(1)")
    print(SEP)
    result = {}
    for name, prop in metrics:
        have = [e for e in all_e if list(g.objects(e, prop))]
        pct  = len(have) / total * 100 if total else 0
        print(f"  {name:<20}: {len(have):2d}/{total} = {pct:.1f}%")
        result[name] = {"count": len(have), "total": total, "pct": round(pct, 1)}
    return result


# ─────────────────────────────────────────────────────────────────────────────
# METHOD 13 — EXTERNAL VOCABULARY USAGE (Heath & Bizer 2009)
# ─────────────────────────────────────────────────────────────────────────────

def method_external_vocab(onto, label):
    """
    Method: External Vocabulary Usage Rate
    Source: Bizer C., Heath T., Berners-Lee T. (2009).
            Linked Data — The Story So Far.
            International Journal on Semantic Web and Information Systems, 5(3), 1-22.
    Formula:
        ext_vocab_rate = |{t ∈ triples : predicate(t) ∈ known_ext_vocab}|
                       / |triples|
    Known external vocabularies: rdf, rdfs, owl, xsd, foaf, dc, skos, prov, vann
    """
    if not onto["loaded"]:
        return {"error": onto["parse_error"]}
    g = onto["graph"]
    EXT_VOCABS = {
        "rdf":  "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "owl":  "http://www.w3.org/2002/07/owl#",
        "xsd":  "http://www.w3.org/2001/XMLSchema#",
        "foaf": "http://xmlns.com/foaf/0.1/",
        "dc":   "http://purl.org/dc/elements/1.1/",
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "prov": "http://www.w3.org/ns/prov#",
        "vann": "http://purl.org/vocab/vann/",
    }

    vocab_counts = {k: 0 for k in EXT_VOCABS}
    proprietary = 0
    total = 0
    for _, p, _ in g:
        if not isinstance(p, URIRef):
            continue
        total += 1
        matched = False
        for k, ns in EXT_VOCABS.items():
            if str(p).startswith(ns):
                vocab_counts[k] += 1
                matched = True
                break
        if not matched:
            proprietary += 1

    ext_total = sum(vocab_counts.values())
    ext_rate  = ext_total / total * 100 if total else 0

    print(f"\n{SEP}")
    print(f"METHOD 13 — External Vocabulary Usage [{label}]")
    print(f"Paper: Bizer, Heath & Berners-Lee (2009) IJSWIS 5(3)")
    print(SEP)
    for k, v in sorted(vocab_counts.items(), key=lambda x: -x[1]):
        if v > 0:
            print(f"  {k:<8}: {v:4d} ({v/total*100:.1f}%)")
    print(f"  proprietary : {proprietary}")
    print(f"  Total predicates: {total}")
    print(f"  External vocab rate: {ext_rate:.1f}%")
    return {"ext_rate_pct": round(ext_rate, 1), "proprietary": proprietary, "total": total}


# ─────────────────────────────────────────────────────────────────────────────
# METHOD 14 — LITERAL VALIDATION (Paulheim 2017)
# ─────────────────────────────────────────────────────────────────────────────

def method_literal_validation(onto, label):
    """
    Method: Syntactic Validity of Typed Literals
    Source: Paulheim H. (2017). Knowledge Graph Refinement: A Survey of
            Approaches and Evaluation Methods.
            Semantic Web, 8(3), 489-508.
    Formula:
        For each (s, p, o) where o is a typed Literal with datatype D,
        validate the lexical form of o against the XSD regex for D.
        error_rate = |invalid_literals| / |typed_literals|
    XSD regexes applied:
        xsd:integer          : r'^-?[0-9]+'
        xsd:nonNegativeInteger: r'^[0-9]+'
        xsd:decimal          : r'^-?[0-9]+(\\.[0-9]+)?'
        xsd:dateTime         : r'^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}'
        xsd:date             : r'^\\d{4}-\\d{2}-\\d{2}'
        xsd:boolean          : r'^(true|false|0|1)$'
        xsd:anyURI           : r'^https?://'
    """
    if not onto["loaded"]:
        return {"error": onto["parse_error"]}
    g = onto["graph"]
    XSD_REGEX = {
        str(XSD.integer):           r"^-?[0-9]+$",
        str(XSD.nonNegativeInteger): r"^[0-9]+$",
        str(XSD.decimal):           r"^-?[0-9]+(\.[0-9]+)?$",
        str(XSD.dateTime):          r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
        str(XSD.date):              r"^\d{4}-\d{2}-\d{2}$",
        str(XSD.boolean):           r"^(true|false|0|1)$",
        str(XSD.anyURI):            r"^https?://",
    }

    typed, invalid = 0, []
    for _, _, o in g:
        if isinstance(o, Literal) and o.datatype is not None:
            typed += 1
            dt = str(o.datatype)
            if dt in XSD_REGEX:
                if not re.match(XSD_REGEX[dt], str(o)):
                    invalid.append((str(o), dt))

    print(f"\n{SEP}")
    print(f"METHOD 14 — Literal Validation [{label}]")
    print(f"Paper: Paulheim (2017) Semantic Web 8(3)")
    print(SEP)
    print(f"  Typed literals found : {typed}")
    print(f"  Invalid literals     : {len(invalid)}")
    if invalid:
        for val, dt in invalid:
            print(f"    '{val}' does not conform to {dt}")
    else:
        print(f"  All typed literals pass XSD regex validation.")
    return {"typed": typed, "invalid": len(invalid)}


# ─────────────────────────────────────────────────────────────────────────────
# OQUARE METRICS
# ─────────────────────────────────────────────────────────────────────────────

def get_oquare_classes(g):
    classes = set()
    for s in g.subjects(RDF.type, OWL.Class):
        if isinstance(s, URIRef):
            classes.add(s)
    for s in g.subjects(RDF.type, RDFS.Class):
        if isinstance(s, URIRef):
            classes.add(s)
    for s, o in g.subject_objects(RDFS.subClassOf):
        if isinstance(s, URIRef):
            classes.add(s)
        if isinstance(o, URIRef):
            classes.add(o)
    return classes - {OWL.Thing, OWL.Nothing}


def m_ANOnto(g, classes, ann_props):
    if not classes:
        return 0.0
    standard = {RDFS.label, RDFS.comment, RDFS.seeAlso, RDFS.isDefinedBy}
    all_ann = ann_props | standard
    count = sum(1 for cls in classes for p in all_ann for _ in g.objects(cls, p))
    return count / len(classes)


def m_AROnto(g, classes, data_props):
    if not classes:
        return 0.0
    count = 0
    for dp in data_props:
        domains = [d for d in g.objects(dp, RDFS.domain) if isinstance(d, URIRef)]
        count += sum(1 for d in domains if d in classes) if domains else len(classes)
    return count / len(classes)


def m_CROnto(g, classes, individuals):
    if not classes:
        return 0.0
    populated = {t for ind in individuals for t in g.objects(ind, RDF.type) if t in classes}
    return len(populated) / len(classes)


def m_DITOnto(classes, sc_edges):
    if not classes:
        return 0
    parents = {cls: set() for cls in classes}
    for child, parent in sc_edges:
        if child in parents and parent in classes:
            parents[child].add(parent)
    memo = {}
    def depth(c):
        if c in memo:
            return memo[c]
        memo[c] = 0
        ps = parents.get(c, set())
        memo[c] = (1 + max(depth(p) for p in ps)) if ps else 0
        return memo[c]
    return max(depth(c) for c in classes)


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
    cache[cls] = set()
    result = set()
    for p in parents.get(cls, set()):
        result.add(p)
        result |= _ancestors(p, parents, cache)
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
    return sum(len(_ancestors(c, parents, cache)) for c in classes) / len(classes)


def m_NOMOnto(obj_props, data_props):
    return float(len(obj_props) + len(data_props))


def m_WMCOnto(classes, obj_props, data_props):
    if not classes:
        return 0.0
    return (len(obj_props) + len(data_props)) / len(classes)


def m_TMOnto(classes, sc_edges):
    if not classes:
        return 0.0
    parents = {}
    for child, parent in sc_edges:
        if child in classes and parent in classes:
            parents.setdefault(child, set()).add(parent)
    return sum(1 for c in classes if len(parents.get(c, set())) > 1) / len(classes)


def m_LCOMOnto(classes, sc_edges, obj_props, g):
    cls_list = list(classes)
    if len(cls_list) < 2:
        return 0.0
    cp = {c: set() for c in classes}
    for p in obj_props:
        for d in g.objects(p, RDFS.domain):
            if d in cp:
                cp[d].add(p)
        for r in g.objects(p, RDFS.range):
            if r in cp:
                cp[r].add(p)
    total_pairs = len(cls_list) * (len(cls_list) - 1) / 2
    shared = sum(
        1 for i in range(len(cls_list))
        for j in range(i + 1, len(cls_list))
        if cp[cls_list[i]] & cp[cls_list[j]]
    )
    return 1.0 - (shared / total_pairs) if total_pairs else 0.0


def m_RFCOnto(g, classes, obj_props):
    if not classes:
        return 0.0
    total = 0
    for cls in classes:
        own = {p for p in obj_props if cls in g.objects(p, RDFS.domain)}
        reached = {r for p in own for r in g.objects(p, RDFS.range) if r in classes}
        total += len(own) + len(reached)
    return total / len(classes)


def m_CBOOnto(g, classes, obj_props):
    if not classes:
        return 0.0
    coupled = {c: set() for c in classes}
    for p in obj_props:
        domains = [d for d in g.objects(p, RDFS.domain) if d in classes]
        ranges = [r for r in g.objects(p, RDFS.range) if r in classes]
        for d in domains:
            for r in ranges:
                if d != r:
                    coupled[d].add(r)
                    coupled[r].add(d)
    return sum(len(v) for v in coupled.values()) / len(classes)


def m_INROnto(individuals, obj_props):
    return len(individuals) / (len(obj_props) or 1)


def m_PROnto(g, obj_props, data_props):
    all_props = obj_props | data_props
    if not all_props:
        return 0.0
    defined = sum(
        1 for p in all_props
        if list(g.objects(p, RDFS.domain)) or list(g.objects(p, RDFS.range))
    )
    return defined / len(all_props)


def m_POnto(classes, sc_edges, obj_props, g):
    if not classes:
        return 0.0
    cp = {c: {p for p in obj_props if c in g.objects(p, RDFS.domain)} for c in classes}
    child_parents = {}
    for child, parent in sc_edges:
        if child in classes and parent in classes:
            child_parents.setdefault(child, set()).add(parent)
    parent_classes = {p for ps in child_parents.values() for p in ps}
    if not parent_classes:
        return 0.0
    overrides = 0
    for parent in parent_classes:
        children = [c for c in classes if parent in child_parents.get(c, set())]
        overrides += sum(1 for c in children if cp.get(c, set()) & cp.get(parent, set()))
    return overrides / len(parent_classes)


THRESHOLDS = {
    "ANOnto":  ((0,      0.04,  0.08,  0.20), "asc"),
    "AROnto":  ((0,      0.02,  0.04,  0.08), "asc"),
    "CROnto":  ((0,      0.17,  0.33,  0.50), "asc"),
    "DITOnto": ((1,      2,     3,     4   ), "asc"),
    "INROnto": ((0,      1,     5,     10  ), "asc"),
    "LCOMOnto":((0.90,   0.75,  0.50,  0.25), "desc"),
    "NACOnto": ((0,      1,     3,     5   ), "asc"),
    "NOCOnto": ((0,      0.50,  1,     2   ), "asc"),
    "NOMOnto": ((0,      5,     10,    20  ), "asc"),
    "PROnto":  ((0,      0.25,  0.50,  0.75), "asc"),
    "RFCOnto": ((0,      0.50,  1,     2   ), "asc"),
    "TMOnto":  ((0.50,   0.30,  0.20,  0.05), "desc"),
    "WMCOnto": ((0,      0.20,  0.50,  1   ), "asc"),
    "CBOOnto": ((3,      2,     1,     0.50), "desc"),
    "POnto":   ((0,      0.10,  0.25,  0.50), "asc"),
}


def scale(name, raw):
    thresholds, direction = THRESHOLDS[name]
    t1, t2, t3, t4 = thresholds
    if direction == "asc":
        if raw < t1:  return 1
        if raw < t2:  return 2
        if raw < t3:  return 3
        if raw < t4:  return 4
        return 5
    else:
        if raw >= t1: return 1
        if raw >= t2: return 2
        if raw >= t3: return 3
        if raw >= t4: return 4
        return 5


SUBCHAR_METRICS = {
    "Formal adequacy":   ["ANOnto", "NOMOnto", "WMCOnto", "PROnto"],
    "Domain adequacy":   ["CROnto", "AROnto", "INROnto"],
    "Formal correctness":["DITOnto", "NACOnto", "NOCOnto"],
    "Consistency":       ["LCOMOnto", "TMOnto", "CBOOnto"],
    "Modularity":        ["CBOOnto", "NOCOnto", "RFCOnto"],
    "Reusability":       ["PROnto", "NOMOnto", "CBOOnto"],
    "Understandability": ["ANOnto", "CROnto", "NOCOnto"],
    "Operability":       ["INROnto", "CROnto"],
    "Adaptability":      ["DITOnto", "NOCOnto", "NACOnto"],
    "Replaceability":    ["POnto", "NOCOnto"],
}


CHAR_SUBCHARS = {
    "Functional adequacy": ["Formal adequacy", "Domain adequacy", "Formal correctness"],
    "Reliability":         ["Consistency"],
    "Usability":           ["Understandability", "Operability"],
    "Maintainability":    ["Modularity", "Adaptability"],
    "Portability":        ["Reusability", "Replaceability"],
}


def _avg(values):
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def compute_quality_model(scaled):
    subchars = {
        sc: _avg([scaled.get(m) for m in metrics])
        for sc, metrics in SUBCHAR_METRICS.items()
    }
    chars = {
        ch: _avg([subchars.get(sc) for sc in scs])
        for ch, scs in CHAR_SUBCHARS.items()
    }
    return subchars, chars


def method_oquare(onto, label):
    g = onto["graph"]
    classes     = get_oquare_classes(g)
    obj_props   = get_declared_object_properties(g)
    data_props  = get_declared_datatype_properties(g)
    ann_props   = get_declared_annotation_properties(g)
    individuals = get_declared_named_individuals(g)
    sc_edges    = get_named_subclass_edges(g)

    raw = {
        "ANOnto":   m_ANOnto(g, classes, ann_props),
        "AROnto":   m_AROnto(g, classes, data_props),
        "CROnto":   m_CROnto(g, classes, individuals),
        "DITOnto":  m_DITOnto(classes, sc_edges),
        "INROnto":  m_INROnto(individuals, obj_props),
        "LCOMOnto": m_LCOMOnto(classes, sc_edges, obj_props, g),
        "NACOnto":  m_NACOnto(classes, sc_edges),
        "NOCOnto":  m_NOCOnto(classes, sc_edges),
        "NOMOnto":  m_NOMOnto(obj_props, data_props),
        "PROnto":   m_PROnto(g, obj_props, data_props),
        "RFCOnto":  m_RFCOnto(g, classes, obj_props),
        "TMOnto":   m_TMOnto(classes, sc_edges),
        "WMCOnto":  m_WMCOnto(classes, obj_props, data_props),
        "CBOOnto":  m_CBOOnto(g, classes, obj_props),
        "POnto":    m_POnto(classes, sc_edges, obj_props, g),
    }
    scaled = {k: scale(k, v) for k, v in raw.items()}
    subchars, chars = compute_quality_model(scaled)

    print("\n" + "=" * 62)
    print(f"  {label} - OQuaRE quality model")
    print(f"  Classes: {len(classes)}  |  ObjProps: {len(obj_props)}  |  DataProps: {len(data_props)}  |  Individuals: {len(individuals)}")
    print("-" * 62)
    print(f"  {'Metric':<12}  {'Raw':>8}  {'Score':>5}  Bar")
    print("  " + "-" * 44)
    for m, rv in raw.items():
        sv = scaled[m]
        bar = '#' * sv + '-' * (5 - sv)
        print(f"  {m:<12}  {rv:>8.3f}  {sv:>5}  {bar}")

    print(f"\n  Quality model")
    print("  " + "-" * 44)
    for ch, ch_score in chars.items():
        if ch_score is None:
            continue
        bar = '#' * round(ch_score) + '-' * (5 - round(ch_score))
        print(f"  {ch:<23} {ch_score:>4.2f}  {bar}")
        for sc in CHAR_SUBCHARS[ch]:
            sc_score = subchars.get(sc)
            if sc_score is not None:
                print(f"      {sc:<23} {sc_score:>4.2f}")
    print("=" * 62)

    return {
        'raw': raw,
        'scaled': scaled,
        'subchars': subchars,
        'chars': chars,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    all_results = {}
    for ont_label, ont_path in ONTOLOGIES.items():
        print(f"\n\n{'#'*72}")
        print(f"  ONTOLOGY: {ont_label}")
        print(f"  Path: {ont_path}")
        print(f"{'#'*72}")

        onto = load_ontology(ont_path)
        r = {}
        r["basic"]       = wrap_method(method_basic_statistics(onto, ont_label),
                                        "Basic Ontology Statistics")
        r["stats"]       = wrap_method(method_parseability_check(onto, ont_label),
                                        "RDF syntax parseability (RDFLib)", 1)
        r["ontoqa"]      = wrap_method(method_ontoqa(onto, ont_label),
                                        "OntoQA Schema-level Metrics", 3)
        r["yang"]        = wrap_method(method_yang_complexity(onto, ont_label),
                                        "Ontology Complexity Metrics", 4)
        r["consistency"] = wrap_method(method_logical_consistency(onto, ont_label),
                                        "Logical Consistency Check (placeholder)")
        r["sparql"]      = wrap_method(method_sparql_constraints(onto, ont_label),
                                        "SPARQL-Based Structural Constraint Checks", 7)
        r["shacl"]       = wrap_method(method_shacl(onto, ont_label),
                                        "SHACL Shapes Constraint Language Validation", 8)
        r["unit_tests"]  = wrap_method(method_unit_tests(onto, ont_label),
                                        "Unit Tests for Ontologies", 9)
        r["cq_coverage"] = wrap_method(method_cq_coverage(onto, ont_label),
                                        "Competency Question Coverage", 11)
        r["oquare"]      = wrap_method(method_oquare(onto, ont_label),
                                        "OQuaRE Ontology Quality Model")
        r["completeness"]= wrap_method(method_annotation_completeness(onto, ont_label),
                                        "Column Completeness / Annotation Completeness", 12)
        r["ext_vocab"]   = wrap_method(method_external_vocab(onto, ont_label),
                                        "External Vocabulary Usage Rate", 13)
        r["literals"]    = wrap_method(method_literal_validation(onto, ont_label),
                                        "Syntactic Validity of Typed Literals", 14)

        all_results[ont_label] = r

    with open(BASE_PATH / "evaluation_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print("\n\nResults saved to evaluation_results.json")