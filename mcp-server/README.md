```bash
# flow
knowledge base builder, using:

Docling for PDF → Markdown (and NLP enrichment)

Unstructured.io for Markdown parsing

LangChain + MiniLM for embedding

Neo4j for vector storage
# steps
Each PDF is converted to Markdown by Docling.

Unstructured.io parses Markdown into clause blocks.

Each clause is enriched with NLP features (entities, type, etc).

Each clause is embedded with MiniLM and stored in Neo4j as a vector node.

#example
--- Clause ---
Cross-border transfers between Country A and Country B must not exceed $10,000 per calendar month.
Metadata:
{
  "category": "NarrativeText",
  "page_number": 3,
  "clause_type": "Limit",
  "num_sentences": 1,
  "num_nouns": 6,
  "entities": ["Country A", "Country B", "$10,000", "month"],
  "source": "compliance_rules.pdf"
}
```

```bash
# batch processing pipeline related project files
mcp-server/
├── data/                  # Raw PDFs go here
├── infrastructure/
│   ├── __init__.py
│   ├── pdf_to_md.py       # Docling: PDF → Markdown
│   ├── unstructured_md.py # Unstructured<depracated>: direct block parsing Markdown → Clauses
│   ├── enrich.py          # Docling/regex: NLP enrichment
│   └── load.py            # LangChain+Neo4j: Embedding & storage
│   
|── domain/
│   ├── __init__.py
|   └── models.py           # Clause and ClauseMetaData pydantic validator model
|
|── application/
│   ├── __init__.py
|   └── run_pipeline.py           # Main batch script to prep knowledge base
|
├── memory/
│   ├── __init__.py
│   └── langchain_retriever.py     # For LangChain agents
│   └── llamaindex_retriever.py    # For LlamaIndex agents
├── utils/
│   ├── __init__.py
│   └── neo4j_utils.py          # Shared Neo4j config and connection helpers
│   └── neo4j_cypher_utils.py   # Shared Neo4j cypher query retrieval utils for graph context
|   └── logger.py               # Default logger singleton instance and custom logger get_logger new instance file/module level deep logging
└── tests/
|    ├── __init__.py
|    ├── test_mockagents.py       # Tests mock LangChain & LlamaIndex agent with retriever and cypher utils
|    └── test_neo4j_cypher_utls.py # Tests cypher retrieval utils custom setup and methods
| 
├── generate_sample.py     # generate sample clauses of 3 types- prohibited, limit and reporting
├── .env                   # Neo4j credentials

# deps 
unstructured[md]
docling
langchain
langchain-community
fpdf
neo4j
sentence-transformers
python-dotenv
```

> Run model and neo4j locally
```bash
# to run qwen3 1.7B model instance locally
ollama pull qwen3:1.7b
ollama run qwen3:1.7b
# http://localhost:11434 local api qwen3
# to run neo4j docker instance locally
docker-compose up -d
```

> 🚀 To run pipeline and prep knowledge base with ./data compliance/rules pdfs to extract clause+metadata and store embeddings in neo4j
```bash
# start the neo4j local instance
docker-compose up -d
# navigate to mcp-server
# to generate sample compliance pdf
python generate_sample.py
# to run and test the end-to-end pipeline
python run_pipeline.py

# How the Pipeline Flows Works
#PDF → Markdown:
#Each clause is clearly marked and annotated.

#Markdown → Clause dicts:
#Each clause is parsed with all fields (including #relationships).

#Enrichment:
#Each clause gets more metadata, but nothing is lost.

#Load:
#Everything (including relationships) is available for Neo4j ingestion.

# inspect stored clause+metadata in neo4j instance
http://localhost:7474
# use cypher query to check the stored embeddings node
# syntax
# CREATE NODE AND DEFINE PROPS
CREATE (NODENAME:TYPE {...PROPERTIES})
# CREATE RELATIONSHIPS
CREATE (NODENAME)-[:RELATIONTYPE]->(NODENAME)
# MATCH TO RETRIEVE DATA, assign custom variable name to that part of the cypher query which needs to be known
# example person who likes spongebob
MATCH (person)-[:LIKES]->(c:CARTOON {title: "Spongebob"})
RETURN person.name
# list 5 compliance clauses text and entities
MATCH (n:ComplianceClause) 
RETURN n.text AS text, n.entities AS entities 
LIMIT 5
# list 5 compliance clauses as text,entities,clause_type, num_sentences and source
MATCH (n:ComplianceClause) 
RETURN n.text, n.entities, n.clause_type, n.num_sentences, n.source 
LIMIT 5
# metadata structure
MATCH (c:ComplianceClause) 
RETURN keys(c) AS properties 
LIMIT 1
# visual graph
MATCH (n) 
RETURN n

# List all clause IDs and titles
MATCH (c:ComplianceClause) RETURN c.clause_id, c.title;

# Show all relationships for a given clause
MATCH (a:ComplianceClause {clause_id: 'C4'})-[r]->(b)
RETURN a.clause_id, type(r), b.clause_id;

# Find all clauses that override any other clause
MATCH (a)-[:OVERRIDES]->(b) RETURN a.clause_id AS Overrider, b.clause_id AS Overridden;

# to stop and remove volume persistent inside docker container dont use -v if want to persist data in docker container also
docker-compose down -v
```

> To run test

```bash
pytest ./tests/___.py
```