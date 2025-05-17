from docling.document_converter import DocumentConverter
import re

def enrich_clause(clause):
    # sentence splitting
    converter = DocumentConverter()
    doc = converter.convert_all(clause["text"])
    num_sentences = len(doc.sentences) if hasattr(doc, "sentences") else clause["text"].count('.') + 1
    entities = extract_basic_entities(clause["text"])
    clause_type = determine_clause_type(clause["text"])
    return {
        **clause,
        "metadata": {
            **clause["metadata"],
            "num_sentences": num_sentences,
            "entities": entities,
            "clause_type": clause_type
        }
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
