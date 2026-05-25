from .shared import SEP, write_dict_outputs


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
    print(f"METHOD 1 â€” Parseability Check [{label}]")
    print(SEP)
    print(f"  Parse status : {status}")

    return {"status": status}

def write_parseability_outputs(results_by_label, output_dir):
    write_dict_outputs(results_by_label, output_dir, 'parseability_summary.csv')

