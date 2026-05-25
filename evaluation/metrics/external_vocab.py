from rdflib import URIRef
from .shared import SEP, write_dict_outputs


def method_external_vocab(onto, label):
    """
    Method: External Vocabulary Usage Rate
    Source: Bizer C., Heath T., Berners-Lee T. (2009).
            Linked Data â€” The Story So Far.
            International Journal on Semantic Web and Information Systems, 5(3), 1-22.
    Formula:
        ext_vocab_rate = |{t âˆˆ triples : predicate(t) âˆˆ known_ext_vocab}|
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
    print(f"METHOD 13 â€” External Vocabulary Usage [{label}]")
    print(f"Paper: Bizer, Heath & Berners-Lee (2009) IJSWIS 5(3)")
    print(SEP)
    for k, v in sorted(vocab_counts.items(), key=lambda x: -x[1]):
        if v > 0:
            print(f"  {k:<8}: {v:4d} ({v/total*100:.1f}%)")
    print(f"  proprietary : {proprietary}")
    print(f"  Total predicates: {total}")
    print(f"  External vocab rate: {ext_rate:.1f}%")
    return {"ext_rate_pct": round(ext_rate, 1), "proprietary": proprietary, "total": total}

def write_external_vocab_outputs(results_by_label, output_dir):
    write_dict_outputs(results_by_label, output_dir, 'external_vocab_summary.csv')

