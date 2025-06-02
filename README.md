# JSentrix
# Autonomous Transaction Monitoring & Fraud Response System (Local-Only, Multi-Agent, MCP&A2A-Compliant)

## Overview

This project is a fully local, privacy-preserving, multi-agent system for real-time transaction monitoring and fraud response, built for bank/fintech IT teams.  
It leverages the **Model Context Protocol (MCP)** for modular integrations, runs all AI models and data stores locally, and features an **Electron desktop app** (for IT staff) for monitoring.

---

## Architecture

- **Electron App(MCP-client):** Local desktop app for IT staff, with embedded MCP client for analysis and tasking dashboard for monitoring transactions, alerts, and agent actions.
- **MCP Server(s):** Python backend for now single MCP-server that exposes tools and agents via MCP and A2A compliance agent-to-agent comms; handles transaction ingestion, agent orchestration, and local AI Triage Agent flow.
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
| 5    | ~~custom flow setup including relevance decay score sort, summarization,memory aware querying~~                                                                                                   |
| 6    | Setup reusable BaseAgent class interface with mcp+a2a compatibility for across all agent in system|
| 7    | Setup streminges and abortinges tool for mcp server and fdagent with notification intake and analysis capacity
| 8    | Add A2A workflow (investigation, notification, action)                                            |
| 9    | Build dashboard screen in electron for monitoring, polish Electron UI, add logging/audit, Dockerize setup.   |

---

## Tech Stack

- **Electron** (React/TypeScript) - Desktop app & MCP client
- **Python** - MCP server, agent orchestration via Langchain
- **Ollama** - Local LLMs for analysis
- **neo4j** - Local graph database 
- **customMemory Event via Qdrant** - Local agent memory wired with custom configs and setup
- **Docker** - Deployment and local orchestration

---

## References

- [MCP Protocol](https://github.com/anthropics/mcp)
- [Ollama](https://ollama.com/)
- [Langchain](https://python.langchain.com/docs/introduction/)
- [LlamaIndex](https://docs.llamaindex.ai/en/stable/#introduction)
- [Neo4j](https://neo4j.com/docs/operations-manual/current/docker/introduction/)
- [Qdrant](https://qdrant.tech/documentation/)
- [Electron](https://www.electronjs.org/)
---

## Getting Started

1. **Clone the repo and follow setup instructions for each component.**
2. **Start the MCP server and supporting services (Ollama, neo4j) via Docker or local a/c to instructions.**
3. **Run the Electron app locally for IT staff dashboard for monitoring.**


---

## License

[![GPL V3](https://img.shields.io/badge/License-GPL-purple.svg)](https://choosealicense.com/licenses/gpl-3.0/)


