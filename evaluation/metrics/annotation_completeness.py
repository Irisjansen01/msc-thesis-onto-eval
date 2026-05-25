from rdflib import RDFS, OWL
from .shared import SEP, get_declared_classes, get_declared_object_properties, get_declared_datatype_properties, write_dict_outputs


def method_annotation_completeness(onto, label):
    """
    Method: Column Completeness / Annotation Completeness
    Source: Zaveri A., Rula A., Maurino A., Pietrobon R., Lehmann J., Auer S.
            (2016). Quality Assessment for Linked Data: A Survey.
            Semantic Web, 7(1), 63-93. (Section 4.2, "Completeness")
    Formula:
        completeness(annotation_prop) =
            |{e âˆˆ Entities : (e, annotation_prop, ?) âˆˆ G}| / |Entities|
    Applied to: rdfs:label, rdfs:comment, owl:deprecated
    Entity set = named_classes âˆª object_properties âˆª datatype_properties.
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
    print(f"METHOD 12 â€” Annotation Completeness [{label}]")
    print(f"Paper: Zaveri et al. (2016) Semantic Web 7(1)")
    print(SEP)
    result = {}
    for name, prop in metrics:
        have = [e for e in all_e if list(g.objects(e, prop))]
        pct  = len(have) / total * 100 if total else 0
        print(f"  {name:<20}: {len(have):2d}/{total} = {pct:.1f}%")
        result[name] = {"count": len(have), "total": total, "pct": round(pct, 1)}
    return result

def write_annotation_completeness_outputs(results_by_label, output_dir):
    write_dict_outputs(results_by_label, output_dir, 'annotation_completeness_summary.csv')

