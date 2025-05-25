import re
from .model import Clause
from typing import List
from utils.logger import get_logger

logger = get_logger("jsentrix")

# Precompiled regex patterns for performance
ID_PATTERN = re.compile(r"\*\*ID:\*\*\s*(C\d+)")
TITLE_PATTERN = re.compile(r"^## Clause (C\d+) - (.+?)(?:\n|$)")
TEXT_PATTERN = re.compile(r"\*\*Text:\*\*\s*(.+?)(?=\n\*\*|\Z)", re.DOTALL)
REF_PATTERN = re.compile(r"\*\*References:\*\*\s*([C\d, ]*)")
AMENDS_PATTERN = re.compile(r"\*\*Amends:\*\*\s*([C\d, ]*)")
OVERRIDES_PATTERN = re.compile(r"\*\*Overrides:\*\*\s*([C\d, ]*)")

def _extract_relationships(text: str, pattern: re.Pattern) -> List[str]:
    match = pattern.search(text)
    return [c.strip() for c in match.group(1).split(",") if c.strip()] if match else []

def extract_clauses_from_md(md_path) -> List[Clause]:
    """
    Extracts clauses and builds metadata including relationships like amends, overrides, references.
    Also includes category and section_header as None (since not present in plain Markdown).
    """
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    # split by clause header block parsing
    clause_blocks = re.split(r"^## Clause ", text, flags=re.MULTILINE)
    clauses = []
    for block in clause_blocks:
        block = block.strip()
        if not block or block.startswith("Sample Compliance Clauses Document"):
            continue

        # Extract title and id from the header line
        title_match = TITLE_PATTERN.match("## Clause " + block)
        if not title_match:
            logger.debug(f"Skipped clause due to missing title. Raw: {block[:50]}")
            continue
        cid, title = title_match.groups()

        # Extract fields
        id_match = ID_PATTERN.search(block)
        text_match = TEXT_PATTERN.search(block)
        refs = _extract_relationships(block, REF_PATTERN)
        amends = _extract_relationships(block, AMENDS_PATTERN)
        overrides = _extract_relationships(block, OVERRIDES_PATTERN)

        clause_data = {
            "id": id_match.group(1) if id_match else None,
            "title": title.strip(),
            "text": text_match.group(1).strip() if text_match else None,
            "metadata": {
                "category": "NarrativeText",  # Default, since plain Markdown doesn't have this
                "section_header": None,       # Not available in plain Markdown
                "references": refs,
                "amends": amends,
                "overrides": overrides,
                "source": md_path
            }
        }
        if clause_data["id"] and clause_data["text"]:
            try:
                clause = Clause(**clause_data)
                clauses.append(clause)
            except Exception as e:
                logger.debug(f"Invalid clause skipped: {e}")
        else:
            logger.debug(
                f"Skipped clause due to missing fields. Raw: {block[:50]}"
            )
    return [clause.model_dump() for clause in clauses]
