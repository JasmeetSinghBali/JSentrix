"""
mcp_server/application/run_pipeline.py

Batch ingestion pipeline for compliance clauses:
- Converts PDFs to Markdown.
- Extracts clauses from Markdown.
- Enriches clauses with NLP metadata.
- Loads enriched clauses and relationships into Neo4j.

Dependency:
    - Neo4j must be up & running.

Usage:
    - Run standalone (sync):
        python -m application.run_pipeline --data-dir ./custom_data
    - Run standalone (async):
        python -m application.run_pipeline --async --data-dir ./custom_data
    - Run as part of MCP server startup (async):
        The pipeline will automatically run during MCP server startup lifecycle.
"""

import os
import asyncio
from glob import glob
from dotenv import load_dotenv
from typing import List, Optional
from utils.logger import get_logger

# Sync imports
from infrastructure.ingestion.pdf_to_md import pdf_to_markdown
from infrastructure.ingestion.unstructured_md import extract_clauses_from_md
from infrastructure.ingestion.enrich import enrich_clause
from infrastructure.ingestion.load import (
    load_to_neo4j,
    async_load_to_neo4j,
    async_get_clause_count,
    get_clause_count,
)

logger = get_logger("jsentrix")
load_dotenv()
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# --- Core Processing Functions ---
async def process_pdf_async(pdf_path: str, sem: asyncio.Semaphore) -> List[dict]:
    """Async version of PDF processing pipeline with concurrency control"""
    async with sem:  # This limits parallel PDF processing
        md_path = pdf_path.replace(".pdf", ".md")

        # Process PDF -> Markdown (async I/O if supported)
        await asyncio.to_thread(pdf_to_markdown, pdf_path, md_path)
        logger.debug(f"Converted {os.path.basename(pdf_path)} to Markdown")

        # Process Markdown -> Clauses (CPU-bound, keep in thread)
        raw_clauses = await asyncio.to_thread(extract_clauses_from_md, md_path)

        # Parallel enrichment (I/O-bound)
        enrichment_tasks = [asyncio.to_thread(enrich_clause, c) for c in raw_clauses]
        enriched = await asyncio.gather(*enrichment_tasks)

        return enriched


def process_pdf_sync(pdf_path: str) -> List[dict]:
    """Original sync version"""
    md_path = pdf_path.replace(".pdf", ".md")
    pdf_to_markdown(pdf_path, md_path)
    logger.debug(f"Converted {os.path.basename(pdf_path)} to Markdown")
    raw_clauses = extract_clauses_from_md(md_path)
    return [enrich_clause(c) for c in raw_clauses]


# --- Pipeline Controllers ---
async def async_process_pdfs(data_dir: Optional[str] = None) -> None:
    """Async pipeline controller with concurrency control"""
    clause_count = await async_get_clause_count()
    if clause_count > 1:
        logger.info(f"Neo4j already has {clause_count} clauses. Skipping ingestion.")
        return
    data_dir = data_dir or os.path.join(SCRIPT_DIR, "../data")
    pdf_files = glob(os.path.join(os.path.abspath(data_dir), "*.pdf"))

    # Limit to 4 parallel PDFs at a time (adjust based on CPU cores)
    sem = asyncio.Semaphore(4)
    processing_tasks = [process_pdf_async(pdf, sem) for pdf in pdf_files]
    results = await asyncio.gather(*processing_tasks)

    # Flatten results and load
    all_clauses = [clause for sublist in results for clause in sublist]
    if all_clauses:
        await async_load_to_neo4j(all_clauses)
        logger.info(f"Async loaded {len(all_clauses)} clauses into Neo4j")
    else:
        logger.warning("No clauses found in async processing")


def sync_process_pdfs(data_dir: Optional[str] = None) -> None:
    """Original sync pipeline controller"""
    clause_count = get_clause_count()
    if clause_count > 1:
        logger.info(f"Neo4j already has {clause_count} clauses. Skipping ingestion.")
        return
    data_dir = data_dir or os.path.join(SCRIPT_DIR, "../data")
    data_dir = os.path.abspath(data_dir)
    pdf_files = glob(os.path.join(data_dir, "*.pdf"))
    all_clauses = []

    for pdf in pdf_files:
        all_clauses.extend(process_pdf_sync(pdf))

    if all_clauses:
        load_to_neo4j(all_clauses)
        logger.info(f"Sync loaded {len(all_clauses)} clauses into Neo4j")
    else:
        logger.warning("No clauses found in sync processing")


# --- CLI Entry Point ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    # 'async' is a reserved keyword, use dest='async_' to avoid conflict
    parser.add_argument(
        "--async", dest="async_", action="store_true", help="Use async pipeline"
    )
    parser.add_argument("--data-dir", type=str, help="Custom data directory")
    args = parser.parse_args()

    if args.async_:
        asyncio.run(async_process_pdfs(args.data_dir))
    else:
        sync_process_pdfs(args.data_dir)
