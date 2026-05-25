from rdflib import OWL
from .shared import SEP, short, get_declared_classes, get_declared_object_properties, get_declared_datatype_properties, write_dict_outputs


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
    print(f"METHOD 11 â€” CQ Coverage [{label}]")
    print(f"Paper: Gruninger & Fox (1995) IJCAI-95 Workshop")
    print(SEP)
    for cq_id, q, sat, c_ok, op_ok, dp_ok in results:
        mark = "[+]" if sat else "[-]"
        detail = f"[classes={'Y' if c_ok else 'N'} ops={'Y' if op_ok else 'N'} dps={'Y' if dp_ok else 'N'}]"
        print(f"  {mark} {cq_id:5s} {detail}  {q}")
    print(f"\n  Coverage: {satisfied}/{len(results)} = {coverage:.1%}")
    return {"satisfied": satisfied, "total": len(results),
            "coverage_pct": round(coverage * 100, 1)}

def write_cq_coverage_outputs(results_by_label, output_dir):
    write_dict_outputs(results_by_label, output_dir, 'cq_coverage_summary.csv')

