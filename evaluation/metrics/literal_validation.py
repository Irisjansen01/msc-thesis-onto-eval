import re
from rdflib import Literal
from rdflib.namespace import XSD
from .shared import SEP, write_dict_outputs


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
    print(f"METHOD 14 â€” Literal Validation [{label}]")
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

def write_literal_validation_outputs(results_by_label, output_dir):
    write_dict_outputs(results_by_label, output_dir, 'literal_validation_summary.csv')

