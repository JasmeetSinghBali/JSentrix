from docling.document_converter import DocumentConverter
import re
from utils.summarizer import T5Summarizer

summarizer = T5Summarizer()

def enrich_clause(clause):
    """
    Enriches a clause dict with additional metadata.
    - Adds num_sentences, entities, clause_type, summary to metadata.
    - Preserves all existing metadata (including relationships).

    Args:
        clause (List[Dict]): list of Dict of pydantic model Clause

    Returns:
        List[Clause]: the same list of Dict of pydantic model Clause with enriched metadata
    """
    # sentence splitting
    converter = DocumentConverter()
    doc = converter.convert_all(clause["text"])
    num_sentences = len(doc.sentences) if hasattr(doc, "sentences") else clause["text"].count('.') + 1
    entities = extract_basic_entities(clause["text"])
    clause_type = determine_clause_type(clause["text"])

    # --- summarize the clause text ---
    summary = summarizer.summarize(clause["text"])
    
    # merge and syn metadata
    enriched_metadata={
        **clause.get("metadata",{}),
        "num_sentences": num_sentences,
        "entities": entities,
        "clause_type": clause_type,
        "clause_id": clause["id"], # maps relationships in neo4j graph store
        "title": clause.get("title"),
        "summary": summary,
    }

    return {
        **clause,
        "metadata": enriched_metadata
    }

def extract_basic_entities(text):
    countries = re.findall(r'Country [A-Z]', text)
    amounts = re.findall(r'\$\d+(?:,\d{3})*(?:\.\d{2})?', text)
    months = re.findall(r'(month|year|quarter|calendar month)', text, re.I)
    return list(set(countries + amounts + months))

def determine_clause_type(text):
    t = text.lower()
    if "prohibit" in t or "prohibited" in t:
        return "Prohibition"
    elif "limit" in t or "exceed" in t:
        return "Limit"
    return "Rule"
