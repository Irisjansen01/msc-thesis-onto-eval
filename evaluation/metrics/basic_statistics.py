from rdflib import RDF, RDFS, OWL, URIRef, BNode
from .shared import SEP, write_dict_outputs


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

def write_basic_statistics_outputs(results_by_label, output_dir):
    write_dict_outputs(results_by_label, output_dir, 'basic_statistics_summary.csv')

