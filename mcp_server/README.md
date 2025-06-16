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

mcp_server/
├── data/                  # Raw PDFs go here
├── infrastructure/
│     |
|     |── ingestion
|       ├── __init__.py
│       ├── pdf_to_md.py       # Docling: PDF → Markdown
│       ├── unstructured_md.py # Unstructured<depracated>: direct block parsing Markdown → Clauses
│       ├── enrich.py          # Docling/regex: NLP enrichment
│       └── load.py            # LangChain+Neo4j: Embedding & storage
│     |── qdrant_setup.py      # Create qdrant memory event collection [only to be run once as script]
│     |── memory_event_repository.py   # Handles low-level Qdrant persistence for MemoryEvent domain objects.
|
|── domain/
│   ├── __init__.py
|   └── models.py           # Clause and ClauseMetaData pydantic validator model
|── agents/
│   ├── __init__.py
|   └── message_a2aserializer.py           # Base class for robust agent-to-agent (A2A) message serialization
|   ├── base_agent.py 
|
|── application/
│   ├── __init__.py
|   └── run_pipeline.py 
|   |── postprocessors
│     ├── __init__.py
|     ├── llamaindex_postprocessors.py # LlamaIndex node postprocessors for advanced scoring & metadata injec.
|   |── query_engines
│     ├── __init__.py
|     └── llamaindex_rewarding_wrapper.py # Wraps a LlamaIndex QueryEngine to apply rew/pen to source nodes
|   ├── retrievers/
│   ├── __init__.py
│   └── langchain_retriever.py     # For LangChain agents
│   └── llamaindex_retriever.py    # For LlamaIndex agents
│   └── memory_event_retriever.py  # Supports audit/history for memory event queries+pagination+metadata+vector
|
├── interface/      # The interface layer adapting application to the outside world (API, CLI, etc.).
│   ├── __init__.py
│   └── mcp_server.py      # main entry point for mcp-server
|
├── utils/
│   ├── __init__.py
|   ├── lifecycle.py          # Lifecycle utility for registering and running shutdown callbacks. 
|   ├── retry.py              # Generic retry decorator for functions that may fail transiently.. 
│   └── neo4j_utils.py        # Shared Neo4j config and connection helpers 
│   └── neo4j_cypher_utils.py # Shared Neo4j cypher query retrieval utils for graph context 
|   └── logger.py             # logger singleton instance and custom logger get_logger new instance  
|   └── relevance_scorer.py   # Default logger singleton instance and custom logger get_logger new instance
|   └── summarizer.py         # Handles long texts via chunking and recursive summarization 
|   └── embedding_utils.py    # Centralized embedding utility for consistent model/config across the system 
|
└── tests/                    # test dir
|    ├── __init__.py
|
└── tracers/                    # tracers opentelemetry
|    ├── __init__.py
| 
├── generate_sample.py     # generate sample clauses of 3 types- prohibited, limit and reporting
├── docker-compose.yml     # startup neo4j docker continer
├── .env                   # Neo4j credentials

```

> Run model and neo4j locally
```bash
# to run qwen3 1.7B model instance locally
ollama pull qwen3:1.7b
ollama run qwen3:1.7b
# to run gemma 1.1B model instance locally
ollama pull gemma3:1b
ollama run gemma3:1b
# http://localhost:11434 local api qwen3
# to run neo4j docker instance locally
docker-compose up -d
```

> 🚀 To run pipeline and prep knowledge base with ./data compliance/rules pdfs to extract clause+metadata and store embeddings in neo4j
```bash
# start the neo4j local instance
docker-compose up -d
# navigate to mcp_server
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

# qdrant ui
http://localhost:6333/dashboard
```

> To run test

```bash
pytest ./tests/___.py
```