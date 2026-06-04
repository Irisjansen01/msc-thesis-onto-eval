from pathlib import Path
import csv

from rdflib import URIRef

from .shared import (
    SEP,
    short,
    write_dict_outputs,
)


CQ_DIR = Path("data") / "CQs"


DOMAIN_PREFIXES = {
    "hospital": "http://www.example.org/ontology/hospital#",
    "music": "http://www.example.org/ontology/music#",
}


CQ_SPARQL = {
    "hospital": [
        ("CQ1", """
            SELECT ?person ?degree WHERE {
              ?person a :Cl_Person ; :hasDegree ?degree .
            }
        """),
        ("CQ2", """
            SELECT ?person ?degree ?startDate ?endDate WHERE {
              ?person a :Cl_Person .
              {
                ?association a :Cl_PersonDegree ;
                  :heldBy ?person ;
                  :hasDegree ?degree .
                OPTIONAL { ?association :degreeDate ?startDate . }
              }
              UNION {
                ?person :hasDegree ?degree .
              }
              OPTIONAL { ?association :startDate ?startDate . }
              OPTIONAL { ?association :endDate ?endDate . }
            }
        """),
        ("CQ3", """
            SELECT DISTINCT ?person ?hospital ?startDate WHERE {
              {
                ?event a :Cl_EmploymentEvent ;
                  :hasEmployee ?person ;
                  :hasEmployer ?hospital ;
                  :startDate ?startDate .
              }
              UNION {
                ?person a :Cl_Person ;
                  :employedAt ?hospital .
                OPTIONAL {
                  ?event a :Cl_EmploymentEvent ;
                    :hasEmployee ?person ;
                    :hasEmployer ?hospital ;
                    :startDate ?startDate .
                }
              }
            }
        """),
        ("CQ4", """
            SELECT ?hospital ?city WHERE {
              ?hospital a :Cl_Hospital ; :locatedInCity ?city .
            }
        """),
        ("CQ5", """
            SELECT ?city ?country WHERE {
              {
                ?city a :Cl_City ; :op_isLocatedInCountry ?country .
              }
              UNION {
                ?country a :Cl_Country ; :op_hasCity ?city .
              }
            }
        """),
        ("CQ6", """
            SELECT DISTINCT ?union ?member ?startDate ?endDate WHERE {
              ?membership a :Cl_UnionMembership ;
                :hasUnion ?union ;
                :hasMember ?member .
              OPTIONAL { ?membership :membershipStartDate ?startDate . }
              OPTIONAL { ?membership :membershipEndDate ?endDate . }
            }
        """),
        ("CQ7", """
            SELECT DISTINCT ?person ?union ?role ?startDate ?endDate WHERE {
              ?membership a :Cl_UnionMembership ;
                :hasMember ?person ;
                :hasUnion ?union ;
                :hasRole ?role .
              OPTIONAL { ?membership :membershipStartDate ?startDate . }
              OPTIONAL { ?membership :membershipEndDate ?endDate . }
            }
        """),
        ("CQ8", """
            SELECT ?doctor ?employee ?statement WHERE {
              ?evaluation a :Cl_EvaluationStatement ;
                :hasEvaluator ?doctor ;
                :hasEvaluatee ?employee ;
                :hasStatement ?statement .
            }
        """),
        ("CQ9", """
            SELECT ?collection ?article WHERE {
              ?collection a ?collectionType .
              VALUES ?collectionType { :Cl_Book :Cl_CD :Cl_ArticleCollection }
              {
                ?collection :containsArticle ?article .
              }
              UNION {
                ?collection :hasArticle ?article .
              }
            }
        """),
        ("CQ10", """
            SELECT ?book ?pageCount WHERE {
              ?book a :Cl_Book .
              {
                ?book :hasPageCount ?pageCount .
              }
              UNION {
                ?book :dp_pageCount ?pageCount .
              }
              UNION {
                ?book :pageCount ?pageCount .
              }
            }
        """),
        ("CQ11", """
            SELECT ?publication ?published WHERE {
              ?publication a ?publicationType .
              VALUES ?publicationType { :Cl_Book :Cl_CD :Cl_Publication }
              {
                ?publication :hasPublicationDate ?published .
              }
              UNION {
                ?publication :publicationYear ?published .
              }
            }
        """),
        ("CQ12", """
            SELECT DISTINCT ?seminar ?date WHERE {
              ?seminar a :Cl_Seminar .
              {
                ?seminar :seminarDate ?date .
              }
              UNION {
                ?seminar :dp_hasDate ?date .
              }
              UNION {
                ?seminar :hasStartDate ?date .
              }
              UNION {
                ?seminar :hasOccurrence ?occurrence .
                ?occurrence :occurrenceDate ?date .
              }
            }
        """),
        ("CQ13", """
            SELECT DISTINCT ?seminar ?article WHERE {
              {
                ?presentation :hasPresentationVenue ?seminar ;
                  :hasPresentedArticle ?article .
              }
              UNION {
                ?article :presentedAtSeminar ?seminar .
              }
            }
        """),
        ("CQ14", """
            SELECT DISTINCT ?seminar ?location WHERE {
              ?seminar a :Cl_Seminar .
              {
                ?seminar :heldAtHospital ?location .
              }
              UNION {
                ?seminar :op_heldAt ?location .
              }
              UNION {
                ?seminar :hasOccurrence ?occurrence .
                ?occurrence :occurrenceAtLocation ?location .
              }
            }
        """),
        ("CQ15", """
            SELECT DISTINCT ?seminar ?article WHERE {
              {
                ?presentation :hasPresentationVenue ?seminar ;
                  :hasPresentedArticle ?article .
              }
              UNION {
                ?article :presentedAtSeminar ?seminar .
              }
            }
        """),
    ],
    "music": [
        ("CQ1", """
            SELECT ?person ?instrument WHERE {
              ?person a :Cl_Musician ; :playsInstrument ?instrument .
            }
        """),
        ("CQ2", """
            SELECT DISTINCT ?band ?member ?startDate ?endDate WHERE {
              {
                ?membership a :Cl_Membership ;
                  :hasBand ?band ;
                  :hasMember ?member .
                OPTIONAL {
                  ?membership :hasTimeInterval ?interval .
                  OPTIONAL { ?interval :startDate ?startDate . }
                  OPTIONAL { ?interval :endDate ?endDate . }
                }
              }
              UNION {
                ?band a :Cl_Band ; :hasMember ?member .
              }
            }
        """),
        ("CQ3", """
            SELECT ?band ?person ?role ?startDate ?endDate WHERE {
              ?membership a :Cl_Membership ;
                :hasBand ?band ;
                :hasMember ?person ;
                :hasRole ?role .
              OPTIONAL {
                ?membership :hasTimeInterval ?interval .
                OPTIONAL { ?interval :startDate ?startDate . }
                OPTIONAL { ?interval :endDate ?endDate . }
              }
            }
        """),
        ("CQ4", """
            SELECT ?album ?startDate ?endDate WHERE {
              ?album a :Cl_Album ; :hasRecordingEvent ?recording .
              ?recording :recordingStartDate ?startDate ;
                :recordingEndDate ?endDate .
            }
        """),
        ("CQ5", """
            SELECT ?album (COUNT(?track) AS ?trackCount) WHERE {
              ?album a :Cl_Album ; :hasTrack ?track .
            }
            GROUP BY ?album
        """),
        ("CQ6", """
            SELECT DISTINCT ?album ?releaseDate WHERE {
              ?album a :Cl_Album .
              {
                ?album :releaseDate ?releaseDate .
              }
              UNION {
                ?album :albumReleaseDate ?releaseDate .
              }
            }
        """),
        ("CQ7", """
            SELECT DISTINCT ?track ?song WHERE {
              {
                ?track a :Cl_Track ; :trackOfSong ?song .
              }
              UNION {
                ?track a :Cl_Track ; :recordingOf ?song .
              }
              UNION {
                ?track a :Cl_Track ; :isSongOf ?song .
              }
              UNION {
                ?track a :Cl_Track, :Cl_Song .
                BIND(?track AS ?song)
              }
            }
        """),
        ("CQ8", """
            SELECT DISTINCT ?song ?compositionDate WHERE {
              ?song a :Cl_Song .
              {
                ?song :composedDate ?compositionDate .
              }
              UNION {
                ?song :trackCompositionDate ?compositionDate .
              }
              UNION {
                ?song :hasCompositionEvent ?event .
                ?event :hasCompositionDate ?compositionDate .
              }
            }
        """),
        ("CQ9", """
            SELECT ?critic ?record ?statement WHERE {
              ?review a :Cl_CriticRecordStatement ;
                :hasCritic ?critic ;
                :hasRecord ?record ;
                :statementText ?statement .
            }
        """),
        ("CQ10", """
            SELECT ?performance ?date WHERE {
              ?performance a :Cl_Performance ; :performanceDate ?date .
            }
        """),
        ("CQ11", """
            SELECT DISTINCT ?performance ?song WHERE {
              {
                ?performance a :Cl_Performance ; :performedSong ?song .
              }
              UNION {
                ?event a :Cl_SongInPerformance ;
                  :hasPerformance ?performance ;
                  :hasSong ?song .
              }
            }
        """),
        ("CQ12", """
            SELECT ?performance ?location WHERE {
              ?performance a :Cl_Performance .
              {
                ?performance :performanceLocation ?location .
              }
              UNION {
                ?performance :hasLocation ?location .
              }
            }
        """),
        ("CQ13", """
            SELECT ?city ?region WHERE {
              ?city a :Cl_City .
              {
                ?city :locatedIn ?region .
              }
              UNION {
                ?city :hasState ?region .
              }
            }
        """),
        ("CQ14", """
            SELECT ?region ?country WHERE {
              ?region a :Cl_Region .
              {
                ?region :locatedInCountry ?country .
              }
              UNION {
                ?region :inCountry ?country .
              }
            }
        """),
        ("CQ15", """
            SELECT ?record (COUNT(DISTINCT ?track) AS ?trackCount) WHERE {
              ?record a ?recordType ; :hasTrack ?track .
              VALUES ?recordType { :Cl_Record :Cl_Album }
            }
            GROUP BY ?record
        """),
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
    for index, (cq_id, sparql) in enumerate(CQ_SPARQL[domain]):
        question = questions[index] if index < len(questions) else ""
        cqs.append((cq_id, question, _with_prefixes(domain, sparql)))
    return cqs


def _with_prefixes(domain, sparql):
    return "\n".join(
        [
            f"PREFIX : <{DOMAIN_PREFIXES[domain]}>",
            "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>",
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>",
            "PREFIX owl: <http://www.w3.org/2002/07/owl#>",
            "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>",
            sparql.strip(),
        ]
    )


def _node_to_text(node):
    if node is None:
        return ""
    if isinstance(node, URIRef):
        return short(node)
    return str(node)


def _format_answers(query_result, max_answers=25):
    answers = []
    variables = [str(var) for var in query_result.vars]
    for row in query_result:
        values = []
        for variable in variables:
            value = _node_to_text(row.get(variable))
            if value:
                values.append(f"{variable}={value}")
        if values:
            answers.append("; ".join(values))
    answer_count = len(answers)
    if answer_count > max_answers:
        answers = answers[:max_answers] + [f"... {answer_count - max_answers} more"]
    return answer_count, " | ".join(answers)


def _run_cq_query(graph, sparql):
    try:
        query_result = graph.query(sparql)
        query_type = getattr(query_result, "type", "SELECT")
        if query_type == "ASK":
            ask_answer = bool(getattr(query_result, "askAnswer", False))
            return {
                "answerable": ask_answer,
                "result_count": 1 if ask_answer else 0,
                "answers": str(ask_answer),
                "query_error": "",
            }
        result_count, answers = _format_answers(query_result)
        return {
            "answerable": result_count > 0,
            "result_count": result_count,
            "answers": answers,
            "query_error": "",
        }
    except Exception as exc:
        return {
            "answerable": False,
            "result_count": 0,
            "answers": "",
            "query_error": str(exc),
        }


def method_cq_coverage(onto, label):
    """
    Method: Competency Question Coverage
    Source: Gruninger M., Fox M.S. (1995).
            Methodology for the Design and Evaluation of Ontologies.
            Proc. IJCAI-95 Workshop on Basic Ontological Issues in
            Knowledge Sharing. Montreal.
    Approach:
        Each CQ is represented as a SPARQL query over the ontology graph.
        A CQ is answerable iff its SPARQL query returns at least one row, or
        an ASK query returns true.
    Formula:
        CQ_coverage = |{CQ_i : answerable(CQ_i)}| / |CQs|
    """
    if not onto["loaded"]:
        return {"error": onto["parse_error"]}

    graph = onto["graph"]
    domain = _domain_for(onto, label)
    cqs = _build_cqs(domain)

    results = []
    for cq_id, question, sparql in cqs:
        query_result = _run_cq_query(graph, sparql)
        answerable = query_result["answerable"]
        results.append(
            {
                "cq_id": cq_id,
                "question": question,
                "answerable": answerable,
                "satisfied": answerable,
                "result_count": query_result["result_count"],
                "answers": query_result["answers"],
                "query_error": query_result["query_error"],
                "sparql": sparql,
            }
        )

    satisfied_count = sum(1 for row in results if row["answerable"])
    coverage = satisfied_count / len(results)
    cq_source = CQ_DIR / f"{domain}-cq.txt"

    print(f"\n{SEP}")
    print(f"METHOD 11 - CQ Coverage [{label}]")
    print("Paper: Gruninger & Fox (1995) IJCAI-95 Workshop")
    print(f"CQs: {cq_source}")
    print(SEP)
    for row in results:
        mark = "[+]" if row["answerable"] else "[-]"
        detail = f"[rows={row['result_count']}]"
        print(f"  {mark} {row['cq_id']:5s} {detail}  {row['question']}")
        if row["query_error"]:
            print(f"        SPARQL error: {row['query_error']}")
        elif row["answers"]:
            print(f"        Answers: {row['answers']}")
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
                "answerable",
                "result_count",
                "answers",
                "query_error",
                "sparql",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
