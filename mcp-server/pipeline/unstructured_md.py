from unstructured.partition.md import partition_md

def extract_clauses_from_md(md_path):
    elements=partition_md(filename=md_path)
    clauses=[]
    for elm in elements:
        if elm.category == "NarrativeText" and elm.text:
            clauses.append({
                "text": elm.text,
                "metadata": {
                    "category": elm.category,
                    "section_header": getattr(elm.metadata,"section_header",None),
                    "source": md_path
                }
            })
    return clauses