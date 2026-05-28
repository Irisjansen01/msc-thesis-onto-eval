from pathlib import Path
import csv

from rdflib import OWL

from .shared import (
    SEP,
    short,
    get_declared_classes,
    get_declared_object_properties,
    get_declared_datatype_properties,
    write_dict_outputs,
)


CQ_DIR = Path("data") / "CQs"


CQ_REQUIREMENTS = {
    "hospital": [
        ("CQ1", [["person"], ["degree", "medicaldegree"]], [["hasdegree", "medicaldegree", "degree"]], []),
        ("CQ2", [["person"], ["degree", "medicaldegree"], ["timeperiod", "studyperiod"]], [["studiedfor", "studied", "hasstudied"]], [["startdate", "enddate", "timeperiod"]]),
        ("CQ3", [["person"], ["hospital"], ["employment", "position"]], [["employedat", "worksat", "employed"]], [["startdate", "employeddate", "firstemployed"]]),
        ("CQ4", [["hospital"], ["city"]], [["locatedin", "islocatedin", "cityof"]], []),
        ("CQ5", [["city"], ["country"]], [["locatedin", "countryof", "islocatedin"]], []),
        ("CQ6", [["union"], ["person", "member"], ["membership", "unionmembership"]], [["hasmember", "memberof", "unionmember", "hasmembership"]], [["timeperiod", "eventdate", "pointintime"]]),
        ("CQ7", [["person"], ["union", "group"], ["role"]], [["hasrole", "rolein", "memberrole"]], [["timeperiod", "eventdate", "pointintime"]]),
        ("CQ8", [["doctor"], ["employee"], ["evaluation", "statement"]], [["hasstatement", "evaluationof", "givesstatement"]], []),
        ("CQ9", [["book", "cd"], ["article"]], [["containsarticle", "hasarticle", "composedof"]], []),
        ("CQ10", [["book"]], [["haspages", "pagecount"]], [["pages", "numberofpages", "npages"]]),
        ("CQ11", [["book", "cd"]], [["published", "haspublication"]], [["publicationdate", "publisheddate", "publicationyear"]]),
        ("CQ12", [["seminar"]], [], [["date", "eventdate", "seminardate"]]),
        ("CQ13", [["seminar"], ["article"]], [["presentedarticle", "hasarticle", "presents"]], []),
        ("CQ14", [["seminar"], ["location", "venue", "city"]], [["tookplaceat", "location", "venueof"]], []),
        ("CQ15", [["seminar"], ["article"]], [["hasarticle", "presentedarticle", "includesarticle"]], []),
    ],
    "music": [
        ("CQ1", [["person", "musician"], ["instrument"]], [["playsinstrument", "plays"]], []),
        ("CQ2", [["band", "musicgroup"], ["person", "musician"]], [["hasmember", "membership", "membershipof", "personmembership"]], []),
        ("CQ3", [["band", "musicgroup"], ["person", "musician"], ["role"]], [["hasrole"]], []),
        ("CQ4", [["album", "record"]], [], [["recordingstart", "startdate"], ["recordingend", "enddate"]]),
        ("CQ5", [["album", "record"], ["track"]], [["hastrack"]], []),
        ("CQ6", [["album", "record"]], [], [["releasedate"]]),
        ("CQ7", [["track"], ["song", "musicalwork"]], [["trackofsong", "recordingof", "issongof"]], []),
        ("CQ8", [["song", "musicalwork"]], [], [["composedat", "compositiondate"]]),
        ("CQ9", [["critic", "reviewer"], ["review", "critique"]], [["hasreview", "reviewof", "writesreview"]], []),
        ("CQ10", [["performance"]], [], [["performancedate", "eventdate", "performancetime"]]),
        ("CQ11", [["performance"], ["song", "musicalwork"]], [["featuredsong", "playedsong", "hassong", "includestrack"]], []),
        ("CQ12", [["performance"]], [["tookplaceat", "location", "venueof"]], []),
        ("CQ13", [["city"], ["region"]], [["locatedin"]], []),
        ("CQ14", [["region"], ["country"]], [["regionincountry", "incountry"]], []),
        ("CQ15", [["record", "album"], ["track"]], [["hastrack"]], []),
    ],
}


def _domain_for(onto, label):
    text = f"{onto['path']} {label}".lower()
    if "hospital" in text or label.lower().endswith("ontology_2"):
        return "hospital"
    return "music"


def _load_cq_questions(domain):
    cq_path = CQ_DIR / f"{domain}-cq.txt"
    if not cq_path.exists():
        return []
    return [
        line.strip()
        for line in cq_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _build_cqs(domain):
    questions = _load_cq_questions(domain)
    cqs = []
    for index, (cq_id, class_groups, object_property_groups, datatype_property_groups) in enumerate(CQ_REQUIREMENTS[domain]):
        question = questions[index] if index < len(questions) else ""
        cqs.append((cq_id, question, class_groups, object_property_groups, datatype_property_groups))
    return cqs


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
        A CQ is satisfiable iff all required elements are present.
        Presence check: local name of the element (case-insensitive substring
        match against the set of declared entity local names).
    Formula:
        CQ_coverage = |{CQ_i : satisfiable(CQ_i)}| / |CQs|
    """
    if not onto["loaded"]:
        return {"error": onto["parse_error"]}

    graph = onto["graph"]
    declared_classes = {short(c).lower() for c in get_declared_classes(graph)}
    object_properties = {short(p).lower() for p in get_declared_object_properties(graph)}
    datatype_properties = {short(p).lower() for p in get_declared_datatype_properties(graph)}
    has_min_cardinality = bool(list(graph.triples((None, OWL.minCardinality, None))))

    domain = _domain_for(onto, label)
    cqs = _build_cqs(domain)

    results = []
    for cq_id, question, class_groups, object_property_groups, datatype_property_groups in cqs:
        classes_present = all(
            any(any(alternative in declared for declared in declared_classes) for alternative in group)
            for group in class_groups
        )
        object_properties_present = all(
            any(any(alternative in declared for declared in object_properties) for alternative in group)
            for group in object_property_groups
        )
        datatype_properties_present = all(
            any(any(alternative in declared for declared in datatype_properties) for alternative in group)
            for group in datatype_property_groups
        )
        if cq_id == "CQ15":
            object_properties_present = object_properties_present or has_min_cardinality
        satisfied = classes_present and object_properties_present and datatype_properties_present
        results.append(
            {
                "cq_id": cq_id,
                "question": question,
                "satisfied": satisfied,
                "classes_present": classes_present,
                "object_properties_present": object_properties_present,
                "datatype_properties_present": datatype_properties_present,
            }
        )

    satisfied_count = sum(1 for row in results if row["satisfied"])
    coverage = satisfied_count / len(results)
    cq_source = CQ_DIR / f"{domain}-cq.txt"

    print(f"\n{SEP}")
    print(f"METHOD 11 - CQ Coverage [{label}]")
    print("Paper: Gruninger & Fox (1995) IJCAI-95 Workshop")
    print(f"CQs: {cq_source}")
    print(SEP)
    for row in results:
        mark = "[+]" if row["satisfied"] else "[-]"
        detail = (
            f"[classes={'Y' if row['classes_present'] else 'N'} "
            f"ops={'Y' if row['object_properties_present'] else 'N'} "
            f"dps={'Y' if row['datatype_properties_present'] else 'N'}]"
        )
        print(f"  {mark} {row['cq_id']:5s} {detail}  {row['question']}")
    print(f"\n  Coverage: {satisfied_count}/{len(results)} = {coverage:.1%}")

    return {
        "satisfied": satisfied_count,
        "total": len(results),
        "coverage_pct": round(coverage * 100, 1),
        "cq_source": str(cq_source),
        "details": results,
    }


def write_cq_coverage_outputs(results_by_label, output_dir):
    output_dir = Path(output_dir)
    write_dict_outputs(results_by_label, output_dir, "cq_coverage_summary.csv")

    rows = []
    for ontology, result in results_by_label.items():
        for detail in result.get("details", []):
            rows.append({"ontology": ontology, **detail})

    if not rows:
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "cq_coverage_details.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "ontology",
                "cq_id",
                "question",
                "satisfied",
                "classes_present",
                "object_properties_present",
                "datatype_properties_present",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
