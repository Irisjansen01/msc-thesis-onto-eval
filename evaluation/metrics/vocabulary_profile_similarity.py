from collections import Counter
from pathlib import Path
import csv
import math
import re
import unicodedata

from rdflib import RDF, RDFS, OWL, URIRef, Literal


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "for",
    "from", "has", "have", "he", "her", "his", "in", "is", "it", "its",
    "of", "on", "or", "that", "the", "their", "there", "they", "this",
    "to", "was", "were", "what", "when", "where", "which", "who", "with",
    "within", "years", "certain", "specific", "particular", "usually",
    "regularly", "future", "total", "different", "current",
}


def _normalize_text(text):
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.replace("_", " ").replace("-", " ").replace("/", " ")


def _split_identifier(text):
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(text))
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)
    text = re.sub(r"\b[Cc]l\s+", " ", text)
    return text


def _singularize(token):
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("ses"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize(text):
    text = _normalize_text(_split_identifier(text)).lower()
    tokens = re.findall(r"[a-z][a-z0-9]+", text)
    return [
        _singularize(token)
        for token in tokens
        if token not in STOPWORDS and len(token) > 2
    ]


def _local_name(node):
    text = str(node)
    if "#" in text:
        return text.rsplit("#", 1)[-1]
    return text.rstrip("/").rsplit("/", 1)[-1]


def _labels_or_local_name(g, uri):
    labels = [
        str(label)
        for label in g.objects(uri, RDFS.label)
        if isinstance(label, Literal) and str(label).strip()
    ]
    return labels or [_local_name(uri)]


def extract_ontology_vocabulary(g):
    classes = {s for s in g.subjects(RDF.type, OWL.Class) if isinstance(s, URIRef)}
    classes |= {s for s in g.subjects(RDF.type, RDFS.Class) if isinstance(s, URIRef)}
    for s, o in g.subject_objects(RDFS.subClassOf):
        if isinstance(s, URIRef):
            classes.add(s)
        if isinstance(o, URIRef):
            classes.add(o)

    properties = {s for s in g.subjects(RDF.type, RDF.Property) if isinstance(s, URIRef)}
    properties |= {s for s in g.subjects(RDF.type, OWL.ObjectProperty) if isinstance(s, URIRef)}
    properties |= {s for s in g.subjects(RDF.type, OWL.DatatypeProperty) if isinstance(s, URIRef)}
    properties |= {s for s, _ in g.subject_objects(RDFS.domain) if isinstance(s, URIRef)}
    properties |= {s for s, _ in g.subject_objects(RDFS.range) if isinstance(s, URIRef)}

    labels = []
    for entity in classes | properties:
        labels.extend(_labels_or_local_name(g, entity))
    return labels, classes, properties


def profile_from_labels(labels):
    profile = Counter()
    for label in labels:
        profile.update(tokenize(label))
    return profile


def profile_from_story(story_path):
    text = Path(story_path).read_text(encoding="utf-8", errors="replace")
    return Counter(tokenize(text)), text


def cosine_similarity(left, right):
    keys = set(left) | set(right)
    if not keys:
        return 0.0
    dot = sum(left.get(k, 0) * right.get(k, 0) for k in keys)
    left_norm = math.sqrt(sum(v * v for v in left.values()))
    right_norm = math.sqrt(sum(v * v for v in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def weighted_overlap(source, target):
    return sum(min(source.get(term, 0), target.get(term, 0)) for term in set(source) & set(target))


def compute_vocabulary_profile_similarity(onto, comparison_label, story_path):
    if not onto["loaded"]:
        return {
            "summary": {
                "comparison": comparison_label,
                "ontology": comparison_label,
                "story_path": str(story_path),
                "error": onto["parse_error"],
            },
            "terms": [],
        }

    ontology_labels, classes, properties = extract_ontology_vocabulary(onto["graph"])
    ontology_profile = profile_from_labels(ontology_labels)
    story_profile, story_text = profile_from_story(story_path)

    overlap_terms = set(ontology_profile) & set(story_profile)
    overlap_weight = weighted_overlap(ontology_profile, story_profile)
    ontology_total = sum(ontology_profile.values())
    story_total = sum(story_profile.values())
    precision = overlap_weight / ontology_total if ontology_total else 0.0
    recall = overlap_weight / story_total if story_total else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    unique_union = set(ontology_profile) | set(story_profile)
    unique_jaccard = len(overlap_terms) / len(unique_union) if unique_union else 0.0

    term_rows = []
    for term in sorted(unique_union):
        term_rows.append({
            "comparison": comparison_label,
            "term": term,
            "ontology_count": ontology_profile.get(term, 0),
            "source_text_count": story_profile.get(term, 0),
            "in_both": term in overlap_terms,
        })

    summary = {
        "comparison": comparison_label,
        "ontology_path": str(onto["path"]),
        "story_path": str(story_path),
        "classes": len(classes),
        "properties": len(properties),
        "ontology_labels": len(ontology_labels),
        "ontology_profile_terms": len(ontology_profile),
        "source_profile_terms": len(story_profile),
        "overlap_terms": len(overlap_terms),
        "ontology_token_total": ontology_total,
        "source_token_total": story_total,
        "cosine_similarity": cosine_similarity(ontology_profile, story_profile),
        "weighted_precision_ontology_terms_in_source": precision,
        "weighted_recall_source_terms_in_ontology": recall,
        "weighted_f1": f1,
        "unique_term_jaccard": unique_jaccard,
        "top_missing_source_terms": "|".join(term for term, _ in story_profile.most_common() if term not in ontology_profile)[:500],
        "top_ontology_only_terms": "|".join(term for term, _ in ontology_profile.most_common() if term not in story_profile)[:500],
        "source_character_count": len(story_text),
    }
    return {"summary": summary, "terms": term_rows}


def write_vocabulary_profile_outputs(results, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = [result["summary"] for result in results]
    term_rows = [row for result in results for row in result["terms"]]

    with open(output_dir / "vocabulary_profile_summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    with open(output_dir / "vocabulary_profile_terms.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["comparison", "term", "ontology_count", "source_text_count", "in_both"],
        )
        writer.writeheader()
        writer.writerows(term_rows)

    for result in results:
        comparison = result["summary"]["comparison"]
        comparison_dir = output_dir / comparison
        comparison_dir.mkdir(parents=True, exist_ok=True)

        with open(comparison_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(result["summary"].keys()))
            writer.writeheader()
            writer.writerow(result["summary"])

        with open(comparison_dir / "terms.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["comparison", "term", "ontology_count", "source_text_count", "in_both"],
            )
            writer.writeheader()
            writer.writerows(result["terms"])
