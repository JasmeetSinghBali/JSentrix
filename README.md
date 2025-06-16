# JSentrix
# Autonomous Transaction Monitoring & Fraud Response System (Local-Only, Multi-Agent, MCP&A2A-Compliant)

## Overview

This project is a fully local, privacy-preserving, multi-agent system for real-time transaction monitoring and fraud response, built for bank/fintech IT teams.  
It leverages the **Model Context Protocol (MCP)** for modular integrations, runs all AI models and data stores locally, and features an **Electron desktop app** (for IT staff) for monitoring.

---

## Architecture

- **Electron App(MCP-client):** Local desktop app for IT staff, with embedded MCP client for analysis and tasking dashboard for monitoring transactions, alerts, and agent actions.
- **MCP Server(s):** Python backend for now single MCP-server wrapped by fastapi http api that exposes tools and agents via MCP and A2A compliance agent-to-agent comms; handles transaction ingestion, agent orchestration, and local AI Triage Agent flow.
- **Gateway FastAPI:** Act a minimal proxy gateway service that enables interaction between MCP Server and Electron app.
- **Local Data/Models/LLM:** All LLMs (Ollama), vector DB (Qdrant), and graph clause memory (neo4j) run locally-no cloud or API keys.

---

## End-to-End Flow

1. **IT staff launches Electron app** on their workstation.
2. **Electron MCP client** connects to the local MCP server via localhost.
3. **User triggers transaction ingestion/analysis** from the Electron UI.
4. **MCP server** fetches transactions from a local data source (CSV, database, or direct feed).
5. **Fraud detection agent** (local LLM) analyzes transactions for suspicious patterns.
6. **If fraud is suspected:**
   - **A2A workflow:**  
     - Investigation agent gathers more context (customer profile, history).
     - Notification agent drafts alert for customer or compliance.
     - Action agent prepares freeze/escalation actions.
7. **User reviews and approves/denies actions** in the Electron app.
8. **All actions, alerts, and transaction statuses** are visible in real time on Electron app dashboard.

---

## Core Features

- **Local-Only Operation:** No third-party APIs or cloud dependencies; all data, models, and memory are local.
- **MCP-Based Integration:** Modular, protocol-driven access to data sources and tools.
- **Multi-Agent System:** Context- and memory-rich agents (fraud detection, investigation, notification, action) collaborating via A2A.
- **Electron Desktop App:** Cross-platform, user-friendly interface for IT staff, with embedded MCP client.
- **Electron Monitoring Dashboard:** Real-time visualization of transactions, alerts, and agent actions.
- **Audit & Logging:** Full traceability of actions and agent decisions.
- **Dockerized Deployment:** One-command setup for all components.

---

## MVP Milestones Tracks

|Track | Milestone                                                                                         |  
|------|-------------------------------------------------------------------------------------------------- |  
| 1    | ~~Scaffold Electron app (React/TypeScript), set up Python MCP server, connect via localhost.~~                                                                                                         |
| 2    | ~~Setup custom neo4j, retriever interface for both llamaindex and langchain agent support~~       |
| 3    | ~~Implement transaction ingestion tool (local DB/CSV/pdf) unstructure+langchain+docling~~                                                                                                 |
| 4    | ~~optimiz and expand retrieval interface with relationship traversal cypher utils~~               |
| 5    | ~~custom flow setup including relevance decay score sort, summarization,memory aware querying~~                                                                                                 |
| 6    | ~~add async support for retrievers, postprocessors, utils downstream pipelines~~                  |
| 7    | ~~sphinix doc and instrumentation with opentellemetry setup~~                                         |
| 8    | ~~Setup reusable BaseAgent class interface with mcp+a2a compatibility for across all agent in system~~|
| 9    | ~~Setup support jsonrpc2.0 for comm b/w gateway and mcp_server with rest backw compat~~               |
| 10    | Setup streminges and abortinges tool for mcp server and fdagent with notification intake and analysis capacity
| 11    | Add A2A workflow (investigation, notification, action)                                            |
| 12    | Build dashboard screen in electron for monitoring, polish Electron UI, add logging/audit, Dockerize setup.   |

---

## Tech Stack

- **Electron** (React/TypeScript) - Desktop app & MCP client
- **Python** - MCP server, agent orchestration via Langchain
- **Ollama** - Local LLMs for analysis(qwen3:1.7b) + summary(Gemma3:1b)
- **neo4j** - Local graph database 
- **customMemory Event via Qdrant** - Local agent memory event wired with custom configs and setup
- **Docker** - Deployment and local orchestration
- **Sphinix** - Docs
- **OpenTelemetry** Tracing and Instrumentation

---

## References

- [MCP Protocol](https://github.com/anthropics/mcp)
- [Ollama](https://ollama.com/)
- [Langchain](https://python.langchain.com/docs/introduction/)
- [LlamaIndex](https://docs.llamaindex.ai/en/stable/#introduction)
- [Neo4j](https://neo4j.com/docs/operations-manual/current/docker/introduction/)
- [Qdrant](https://qdrant.tech/documentation/)
- [Electron](https://www.electronjs.org/)
- [Sphinix](https://www.sphinx-doc.org/en/master/usage/installation.html#pypi-package)
- [OpenTelemetry](https://opentelemetry.io/docs/languages/python/)
---

## Getting Started

1. **Clone the repo and follow setup instructions for each component in the next step.**
2. **Start the MCP server and supporting services (Ollama, neo4j) via Docker or local a/c to instructions.**
```bash
# start up postgres,neo4j & qdrant docker instance from root jsentrix
docker-compose up -d

# startup ollama qwen3 model locally in terminal
ollama pull qwen3:1.7b # only the first time
ollama run qwen3:1.7b

# makes sure venv is activated and .env is set for each of the backend components
# mcp_server
python -m interface.mcp_server --http
# gateway (super user is auto created everytime the gateway fastapi service startsup with mcp_server health check and accessibility)
uv run ./src/main.py

# frontend electron app startup
# mcp-client
npm run start

#qwen3
http://localhost:11434 # local api qwen3

# neo4j
http://localhost:7474

# qdrant ui
http://localhost:6333/dashboard

# gateway
http://localhost:8080/docs

# mcp_server
http://localhost:9001

# to prep neo4j knowledge base with initial clauses
python generate_sample.py # generate data/sample_clause.pdf
python application/run_pipeline.py # generate sample_clause.md and prep and injest knowledge base neo4j

```


---

## License

[![GPL V3](https://img.shields.io/badge/License-GPL-purple.svg)](https://choosealicense.com/licenses/gpl-3.0/)


