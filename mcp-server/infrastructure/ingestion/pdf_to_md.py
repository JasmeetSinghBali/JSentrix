# infrastructure/pdf_to_md

from docling.document_converter import DocumentConverter
import re


def reformat_clauses_markdown(md_path):
    """
    Post-processes a Markdown file to standardize clause formatting and metadata.

    Args:
        md_path (str): Path to the Markdown file to reformat.

    Returns:
        None. The file is overwritten in place.
    """
    # raw markdown
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    clauses = []
    current = []
    for line in lines:
        if line.startswith("## Clause"):
            if current:
                clauses.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        clauses.append(current)

    output_lines = ["## Sample Compliance Clauses Document\n\n"]
    for clause_lines in clauses:
        header = clause_lines[0]
        body = "".join(clause_lines[1:]).strip()
        m = re.match(r"## Clause (C\d+) - (.+)", header)
        if not m:
            continue
        cid, title = m.groups()
        # Extract relationships
        text = []
        refs = amends = overrides = ""
        for l in body.splitlines():
            l = l.strip()
            if l.startswith("References:"):
                refs = l.replace("References:", "").strip()
            elif l.startswith("Amends:"):
                amends = l.replace("Amends:", "").strip()
            elif l.startswith("Overrides:"):
                overrides = l.replace("Overrides:", "").strip()
            elif l and not l.startswith("##"):
                text.append(l)
        clause_text = " ".join(text).strip()
        # Write in the desired format
        output_lines.append(f"## Clause {cid} - {title}\n\n")
        output_lines.append(f"**ID:** {cid}  \n")
        output_lines.append(f"**Text:** {clause_text}\n\n")
        output_lines.append(f"**References:** {refs}  \n")
        output_lines.append(f"**Amends:** {amends}  \n")
        output_lines.append(f"**Overrides:** {overrides}  \n\n")
    # Overwrite the markdown file with the reformatted content
    with open(md_path, "w", encoding="utf-8") as f:
        f.writelines(output_lines)


def pdf_to_markdown(pdf_path, md_path):
    """
    Converts a PDF file to Markdown format and reformats it for clause extraction.

    Args:
        pdf_path (str): Path to the source PDF file.
        md_path (str): Path to save the output Markdown file.

    Returns:
        str: Path to the reformatted Markdown file.
    """
    converter = DocumentConverter()
    docling_doc = converter.convert(pdf_path)
    md_text = docling_doc.document.export_to_markdown()
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text)
    # post processing to ensure correct clause formatting and bolded fields
    reformat_clauses_markdown(md_path)
    return md_path
