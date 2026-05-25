from .shared import SEP, write_dict_outputs


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
    print(f"METHOD 8 â€” SHACL Validation [{label}]")
    print(f"Paper: Knublauch & Kontokostas (2017) W3C SHACL Recommendation")
    print(SEP)
    print(f"  [SKIP] SHACL validation requires hand-authored shapes files.")
    print(f"  Recommendation: Define shapes manually in a separate SHACL shapes graph.")
    print(f"  Reference: https://www.w3.org/TR/shacl/")
    return {"status": "SKIPPED", "reason": "requires_manual_shapes"}

def write_shacl_outputs(results_by_label, output_dir):
    write_dict_outputs(results_by_label, output_dir, 'shacl_summary.csv')

