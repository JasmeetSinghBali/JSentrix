# JSentrix
# Autonomous Transaction Monitoring & Fraud Response System (Local-Only, Multi-Agent, MCP-Based)

## Overview

This project is a fully local, privacy-preserving, multi-agent system for real-time transaction monitoring and fraud response, built for bank/fintech IT teams.  
It leverages the **Model Context Protocol (MCP)** for modular integrations, runs all AI models and data stores locally, and features both an **Electron desktop app** (for IT staff) and a **Next.js dashboard** for monitoring.

---

## Architecture

- **Electron App:** Local desktop app for IT staff, with embedded MCP client for analysis and tasking.
- **MCP Server(s):** Python backend exposing tools and agents via MCP; handles transaction ingestion, agent orchestration, and local AI.
- **Local Data/Models:** All LLMs (Ollama), vector DB (Qdrant), and agent memory (mem0) run locally-no cloud or API keys.
- **Next.js Dashboard:** Local/internal web dashboard for monitoring transactions, alerts, and agent actions.

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
8. **All actions, alerts, and transaction statuses** are visible in real time on the Next.js dashboard.

---

## Core Features

- **Local-Only Operation:** No third-party APIs or cloud dependencies; all data, models, and memory are local.
- **MCP-Based Integration:** Modular, protocol-driven access to data sources and tools.
- **Multi-Agent System:** Context- and memory-rich agents (fraud detection, investigation, notification, action) collaborating via A2A.
- **Electron Desktop App:** Cross-platform, user-friendly interface for IT staff, with embedded MCP client.
- **Next.js Monitoring Dashboard:** Real-time visualization of transactions, alerts, and agent actions.
- **Audit & Logging:** Full traceability of actions and agent decisions.
- **Dockerized Deployment:** One-command setup for all components.

---

## MVP Milestones Tracks

|Track | Milestone                                                                                         |  
|------|-------------------------------------------------------------------------------------------------- |  
| 1    | Scaffold Electron app (React/TypeScript), set up Python MCP server, connect via localhost.        |✅
| 2    | Implement transaction ingestion tool (local DB/CSV), basic fraud detection agent (local LLM).     |
| 3    | Add A2A workflow (investigation, notification, freeze), integrate vector DB (Qdrant), mem0.       |
| 4    | Build Next.js dashboard for monitoring, polish Electron UI, add logging/audit, Dockerize setup.   |

---

## Tech Stack

- **Electron** (React/TypeScript) - Desktop app & MCP client
- **Python** - MCP server, agent orchestration via Langchain
- **Ollama** - Local LLMs for analysis
- **Qdrant** - Local vector database for embeddings
- **mem0** - Local agent memory wired with qdrant configs
- **Next.js** (TypeScript) - Monitoring dashboard
- **Docker** - Deployment and local orchestration

---

## References

- [MCP Protocol](https://github.com/anthropics/mcp)
- [Ollama](https://ollama.com/)
- [Qdrant](https://qdrant.tech/)
- [mem0](https://github.com/mem0-ai/mem0)
- [Electron](https://www.electronjs.org/)
- [Next.js](https://nextjs.org/)

---

## Getting Started

1. **Clone the repo and follow setup instructions for each component.**
2. **Start the MCP server and supporting services (Ollama, Qdrant, mem0) via Docker.**
3. **Run the Electron app locally for IT staff.**
4. **Access the Next.js dashboard for monitoring.**

---



