"""
application/run_pipeline.py

Batch ingestion pipeline for compliance clauses:
- Converts PDFs to Markdown.
- Extracts clauses from Markdown.
- Enriches clauses with NLP metadata.
- Loads enriched clauses and relationship created into Neo4j.

Usage:
    python -m application.run_pipeline
"""

import os
from glob import glob
from dotenv import load_dotenv
from utils.logger import get_logger

from infrastructure.pdf_to_md import pdf_to_markdown
from infrastructure.unstructured_md import extract_clauses_from_md
from infrastructure.enrich import enrich_clause
from infrastructure.load import load_to_neo4j


logger = get_logger("jsentrix")

load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def process_pdfs(data_dir: str = None)->None:
    """
    Processes all PDF files in the specified directory and loads extracted clauses into Neo4j.

    Args:
        data_dir (str): Directory containing PDF files.

    Returns:
        None
    """
    if data_dir is None:
        data_dir = os.path.join(SCRIPT_DIR, "../data")
    data_dir = os.path.abspath(data_dir)
    pdf_files = glob(os.path.join(data_dir, "*.pdf"))
    all_clauses = []
    for pdf in pdf_files:
        print(f"Processing {pdf}...")
        md_path = pdf.replace(".pdf", ".md")
        pdf_to_markdown(pdf, md_path)
        logger.debug(f"converted and reformatted {pdf} to {md_path}")
        raw_clauses = extract_clauses_from_md(md_path)
        enriched = [enrich_clause(c) for c in raw_clauses]
        all_clauses.extend(enriched)
    if all_clauses:
        load_to_neo4j(all_clauses)
        logger.info(f"Successfully loaded {len(all_clauses)} clauses into Neo4j.")
    else:
        logger.warning("No clauses found to load.")

if __name__ == "__main__":
    process_pdfs()
