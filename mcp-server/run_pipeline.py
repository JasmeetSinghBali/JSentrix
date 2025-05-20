import os
from glob import glob
from pipeline.pdf_to_md import pdf_to_markdown
from pipeline.unstructured_md import extract_clauses_from_md
from pipeline.enrich import enrich_clause
from pipeline.load import load_to_neo4j
from dotenv import load_dotenv
from utils.logger import default_logger

load_dotenv()

def process_pdfs():
    pdf_files = glob("./data/*.pdf")
    all_clauses = []
    for pdf in pdf_files:
        print(f"Processing {pdf}...")
        md_path = pdf.replace(".pdf", ".md")
        pdf_to_markdown(pdf, md_path)
        default_logger.debug(f"converted and reformatted {pdf} to {md_path}")
        raw_clauses = extract_clauses_from_md(md_path)
        enriched = [enrich_clause(c) for c in raw_clauses]
        all_clauses.extend(enriched)
    load_to_neo4j(all_clauses)

if __name__ == "__main__":
    process_pdfs()
