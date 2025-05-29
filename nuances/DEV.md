> Setting up React with Typescript in Electron
https://www.electronforge.io/guides/framework-integration/react-with-typescript
---
> Setting up ShadcnUI
https://ui.shadcn.com/docs/installation/manual
```bash
npm install tailwindcss @tailwindcss/postcss postcss
# 💡 make sure to install postcss-loader as well and 
```
> For custom alias to work for tailwind it must be configured inside the webpack.renderer.config make sure to add path.resolve for the same and postcss-loader in rules

> 💀 always do --legacy-peer-deps when adding shadcn components

> Start electron app
```bash
# navigate to mcp-client
npm run start
```
> Starts only mcp-server 
```bash
# navigate to mcp-server
uv run mcp_server.py
```

> Start gateway & mcp-server as subprocess on tool invocations
```bash
# navigate to gateway/
uv run main.py
```

> recap basic flow scaffolded
```bash
Electron app logs in, gets JWT.

Electron app calls /tools/add/invoke with:

json
{ "arguments": { "a": 2, "b": 3 } }

FastAPI receives the request, spawns MCP server as subprocess, calls add(a=2, b=3).

MCP server returns 5.

FastAPI returns {"result": 5} to Electron app.

Electron app displays the result.
```

> 💀 make sure to go through "devContentSecurityPolicy" in package.json and forge.config.ts and setup a/c to requirement and best practices based on use case

>>>>>>>>>> from here

- optim langchain and llamaindex retriever with new metadata filter for langchain and custom cypher query utils
for llamaindex results. ✅
```bash
relationship traversal capability so you can, for example:

Given a retrieved clause, find all clauses it REFERENCES, AMENDS, or OVERRIDES.

Given a clause, find all clauses that reference/amend/override it (reverse traversal).

Traverse multi-hop relationships for advanced compliance impact/explainability.
```

- mem0 inspired updates and custom setup for :
```bash
scoring & decay ✅
SETUP test for compliance voilations for some actual malformed transaction stream from faker ✅
SETUP TEST CHECK that the score and decay and reranking actually is working right ✅
summarization diff branch ✅ misc: added lifecycle callback shutdown centralized setup


clean architecture  make sure test_jsentrix_core and test_lifecycle test passes ✅
pre-commit hooks setup ✅

- memory-aware querying diff branch
```bash
Current retrieval (LangChain/LlamaIndex/Neo4j):
These layers are focused on retrieving relevant information (clauses, documents, facts) to answer a query, using metadata filters, vector search, or scoring/decay logic. They are not designed to "remember" the results of past analyses, decisions, or user interactions across sessions unless you explicitly store that information.

Memory-aware querying (Mem0-style):
This is an extension layer. After you analyze a transaction (e.g., using LlamaIndex retrieval and Qwen3/Ollama inference), you can store the entire "experience"—including the initial prompt, the LLM's answer, relevant clauses, scores, and any other context—into a memory store. This memory can then be:

Queried later to provide context for future transactions or conversations.

Used for audit trails, self-improvement, or personalization.

Accessed by agents to recall past actions, decisions, or user preferences.

No Redundancy—It’s Complementary:
This setup does not overwrite or duplicate your existing retrieval, scoring, or filtering logic. Instead, it adds a new dimension: the ability to persist and retrieve the "history" of interactions, decisions, and context, which is not covered by standard retrieval pipelines.

🕊️ in Practice
After analysis:
Store the prompt, LLM response, relevant clause IDs, agent metadata, and any other context as a “memory event” in Qdrant.

For future queries:
Retrieve the most relevant memories (by vector similarity and/or metadata) in qdrant local docker instance and inject them as context for the agent or LLM.

For audit/self-improvement:
Query the memory store for all events related to a user, session, or decision, reconstructing history or enabling learning.

Repository/Adapter + Event Sourcing + Context Provider

AIM: to support advanced agent features, auditability, and contextual intelligence with this approach.

```


- diff branch async setup using _async query from the rewarding wrapper and downstream pipeline including llm, neo4j, retrievers everything basically then write a mock test end to end after this async setup to make sure everything works
```bash
How Would This Look?
define main transaction analysis function as async def.

Use await for all LLM, database, and network calls that support async.

Use async-compatible libraries for Neo4j (see ), HTTP/LLM calls, and any other I/O.

agents (mock or Llama) would consume transactions from the stream and process them in parallel using asyncio.gather or similar
```

- diff branch direct mem0 import use mem0 as scratchpad storing logs,result,analyssis from agent of the transactions etc... for the agent setup with qdrant need more research https://qdrant.tech/documentation/frameworks/mem0/

- diff-brnch polish gateway main.py maybe segregate into different files and folders and python-dotenv setup for storing the jwt secret and setup dockerizing gateway to run gateway and mcp-server along with neo4j local with single docker-compose up be carefull so that the mcp-client electron can still interact with mcp-server via gateway.


- diff-branch setup reusable BaseAgent class that abstracts over LangChain and LlamaIndex agents to ensure consistency, modularity, and MCP + A2A compliance across all agents in the system.
example-agents fraud detection agent, investigation agent, notification agent, action agent extends these base class to initialize and setup agents in a custom way.
```bash
Agent	                     Responsibilities	                                          Suggested Agent Type
Fraud Detection	Scans incoming transactions using embeddings, rules, or heuristics	🧠 LlamaIndexAgent (for graph/vector querying)
Investigation	   Explores relationships, historical links, clause violations	         🧠 LlamaIndexAgent (Neo4j graph queries + context-aware)
Notification	   Sends alerts based on triggers from above agents	                  🔗 LangChainAgent (Tooling + APIs + Webhooks)
Action Agent	   Takes follow-up actions (e.g., block account, trigger audit)	      🔗 LangChainAgent (Multi-tool + Autonomous capability)
```

- diff-branch add and setup new "streaminges" and "abortinges" tool for the mcp-server these tools can be invoked by mcp-client by clicking a button in electron app. 
streaminges when invoked should send out notification to the (basic setup for now) minimal agent setup of Langchain Agent i.e fraud detection agent that on recieving this notification starts intaking a mock stream of transactions generated via https://github.com/joke2k/faker (a callable function that mocks transaction streams) for now.  

- diff branch polish frauddetectionagent now this agent will analyzes the stream of transactions in real time continuously by embedding them with all-MiniLM-L6-v2 and doing a similarity search or RAG against the stored compliance rules and clauses from neo4j 
**If fraud is suspected i.e a similar clause match with particular transaction condition met then:**
   - **A2A workflow:**  
     - Investigation agent gathers more context (looking into mem0 history) uses retreived data from fraud detection agent to qwen3 1.7B model runnning locally to return a analyzed report for that transaction.
     - Notification agent drafts alert or send alerts to electron app with analyzed report to mcp client via gateway fastapi.
     - Action agent autonomously performs freeze(freeze funds or transaction)/escalation(to human) actions.
 

> ## 🕊️ Streaming, MCP server tool invocation and FDA Agent Flow
```bash
MCP Client      MCP Server        Notification System       Agent
    |                |                     |                  |
    |---Invoke------>|                     |                  |
    |                |---Notify----------->|                  |
    |                |                     |---Push---------> |
    |                |                     |                  |---Connect--->(Streaming Tool)
    |                |                     |                  |<--Stream-----|

MCP Client Button Pressed:
User action triggers the "streaming" tool on the MCP server.

MCP Server Pushes Notification:
The MCP server sends a notification (via webhook, message queue, pub/sub, etc.) to the agent, indicating the stream is ready.

Agent Initiates Streaming Connection:
The agent, upon receiving the notification, connects to the streaming tool endpoint and processes the stream in real time.

Implementation Considerations
1. Notification Mechanism
Options: Webhooks, message queues (RabbitMQ, Kafka), Redis pub/sub, or cloud pub/sub (AWS SNS/SQS, Google Pub/Sub).

Security: Authenticate and authorize notifications to prevent spoofing.

Reliability: Ensure delivery guarantees (at-least-once or exactly-once) if the stream is critical.

2. Agent Streaming Logic
Use asynchronous programming (e.g., asyncio in Python) to handle the streaming connection.

Implement reconnection and error handling logic for robustness.

Make sure the agent can process and act on the streamed data efficiently.

3. MCP Server Streaming Tool
Ensure the tool endpoint supports streaming protocols (SSE, WebSockets, or gRPC streams).

Provide clear documentation or schema for the streaming data format.

4. Monitoring & Observability
Log notification delivery and streaming connection events.

Monitor for dropped connections, errors, or performance issues.
```

> ## 🕊️ Real-Time Processing Updates to MCP Client Flow

```bash
MCP Client      MCP Server       Agent
   |                |             |
1. |--start-------> |             |
2. |                |---notify--> |
3. |                |             |--connects to stream-->
4. |                |<---events---| (fraud, etc.)
5. |<---updates---- |             |
   |   (SSE/ws)     |             |
6. |--stop--------> |             |
7. |                |---notify--> |
8. |                |             |--disconnects/cleanup-->

Goal:
When the agent detects an event (e.g., fraud transaction), this information should appear in the MCP client UI in real time.

Recommended Flow:

Streaming Tool Invocation:

MCP client starts the stream via the server.

Agent connects to the stream and begins processing data.

Agent Processing:

As the agent analyzes the stream, it detects notable events (e.g., fraud).

For each event, the agent sends an update back to the MCP server or directly to a notification endpoint. reff: https://python.langchain.com/docs/tutorials/agents/#streaming-messages

Real-Time UI Update:

The MCP server pushes these updates to the MCP client UI, typically using server-sent events (SSE), WebSockets, or another real-time transport.

The client UI displays the updates as they arrive.

Key Implementation Points:

Bidirectional Communication:

The agent should be able to send messages/events back to the MCP server or directly to the client, depending on your architecture.

The MCP server acts as a relay for these real-time updates to the client UI.

Session and Event Correlation:

Use unique session or stream IDs to ensure updates are routed to the correct client instance.

UI Handling:

The client UI should subscribe to the appropriate real-time endpoint and update the display as new events arrive.
```


---
> ## Score and Decay system

```bash
the score and lastAccessed attributes play pivotal roles in determining the relevance and retrieval priority of stored memories.

Significance of score
The score attribute quantifies the importance or relevance of a memory. Higher scores indicate that a memory is more significant and should be prioritized during retrieval operations. This scoring mechanism ensures that the most pertinent information is readily accessible, enhancing the AI's contextual understanding and response accuracy.

Significance of lastAccessed
The lastAccessed attribute records the timestamp of the most recent interaction with a memory. This temporal data is crucial for implementing decay strategies, where memories that haven't been accessed recently may be deprioritized or even removed to optimize memory usage. By tracking access patterns, Mem0 can maintain a dynamic and efficient memory store that reflects the current context and user interactions.

Role in Scoring and Decay System
Together, score and lastAccessed facilitate a sophisticated scoring and decay system.

Memory Prioritization: Memories with high scores and recent access timestamps are deemed highly relevant, ensuring they are retrieved promptly during AI operations.

Memory Decay: Memories that haven't been accessed for extended periods may experience a reduction in their score, leading to gradual deprioritization. This decay mechanism helps in managing the memory store's size and relevance.

Efficient Retrieval: By balancing score and recency, ensures that the AI retrieves information that is both important and contextually timely, enhancing the overall performance and user experience.

This dynamic interplay between score and lastAccessed allows to maintain a memory system that is both responsive and efficient, adapting to the evolving context and user interactions over time.
```
> The math
```bash
Formula
Let’s define:

S₀ = original relevance score (e.g., from cosine similarity, say 0.85)

t₀ = last accessed time (e.g., 2025-05-18 10:00:00)

t = current time (e.g., 2025-05-21 10:00:00)

Δt = t - t₀ = time passed since last access (in seconds/days)

λ = decay rate (e.g., λ = 0.05)

S(t) = S₀ × exp(-λ × Δt)

NOTE- Its exponential because the relevance drops at first fast then slows over time, the sensitivity can be controlled via λ for slower decay smaller valued of λ shud be used
Units
must pick a consistent unit for time difference:

If Δt is in days, λ should decay over days.

If Δt is in seconds, use a smaller λ.

Example (in days)
Let’s compute the decayed score step-by-step:

Original similarity: S₀ = 0.9

Last accessed: May 18, 2025

Current time: May 21, 2025

Δt = 3 days

Decay rate: λ = 0.1

Then:

cpp
Copy code
S(t) = 0.9 * exp(-0.1 × 3)
     = 0.9 * exp(-0.3)
     ≈ 0.9 * 0.7408
     ≈ 0.6667
The document's score decayed from 0.9 → 0.67 in 3 days.

here’s how S(t) changes over time for S₀ = 1.0:
Days since access	   Score (λ=0.1)	Score (λ=0.01)
0	                     1.0	         1.0
1	                     0.9048	      0.9900
3	                     0.7408	      0.9704
7	                     0.4966	      0.9324
14	                     0.2466	      0.8694
30	                     0.0498	      0.7408
So, with:

λ = 0.1, things decay fast — ideal for short-term memory

λ = 0.01, things decay slowly — ideal for long-term recall
```

> Self adjusting temporal aware memory with very low overhead
```bash
Initialize score = 0.8 for all docs

When retrieved, bump by +0.1 (up to 1.0) i.e reward

When rejected/irrelevant, decay by ×0.9 i.e penalize

Use decayed_score = score * exp(-λ * Δt) on every read, never store it

This gives a self-adjusting, temporal-aware memory with very low overhead.


# When to penalize and when to reward
1.) Implicit Feedback (Automatic)
Let the system infer reward/penalty based on agent behavior or pipeline results:

Reward When:
The document was used in generating a final output.

The document was repeatedly selected across different queries.

The output using that doc received a positive user response (e.g., high LLM confidence, no fallback to other tools).

Penalize When:
The document was retrieved but not referenced or used.

The agent overrode or ignored it (e.g., reran the query).

The agent explicitly flagged the result as irrelevant.

You can check LangChain’s trace or internal intermediate_steps, or hook into your custom chain/agent logic to inspect this.

2.) Explicit Feedback (Agent-Aware or User-Aware)
If you're building an interactive agent, let the agent or user explicitly give feedback:

"This is useful" → reward (+0.1)

"This is outdated" or "not relevant" → penalize (×0.9)

This can be done via:

An agent memory feedback tool

A UI thumbs-up/thumbs-down system

A system prompt that tells the LLM:
“Mark which context was most helpful.”

3.) Confidence-Based Feedback (LLM-Driven)
Let the LLM tell you how useful a document was:

"On a scale from 0 to 1, how helpful was this document for answering the question?"
Use that score to reward/penalize:

0.7 → reward

<0.3 → penalize

This works well with Tool-Calling, where the LLM can give a reason field and a score.

4.) Context-Use Tracking (Lightweight Heuristic)
In simple systems, just track if the retrieved doc made it into the final LLM context:

if doc in final_prompt:
    reward
else:
    penalize
This assumes if it was used in the final context, it was helpful — decent proxy for now.

```

> Example Interaction Flow Between Agents
```bash
LangChain receives a query from the user.

LangChain calls LlamaIndex agent with the query string.

LlamaIndex:

Retrieves nodes from Neo4j,

Applies decayed scoring + reranking,

Returns top-K ranked nodes with updated scores.

LangChain uses retrieved nodes to generate a final answer (maybe calling an LLM).

LangChain decides which documents were used in the answer.

LangChain tells LlamaIndex to reward or penalize those documents.

LlamaIndex updates Neo4j metadata accordingly.
```

> 🕊️💫 Flow Overview & Relevance
```bash
Score Decay: Every clause/document node in Neo4j tracks a score and last_accessed_at. The score decays over time unless the document is accessed/rewarded.

Reward/Penalty: When a node is used in a final answer (LLM output), it’s rewarded (score increases, timestamp updated); otherwise, it’s penalized (score decreases).

Integration:

LangChain: Uses the decayed score for reranking after retrieval.

LlamaIndex: Applies decay/reranking via a custom postprocessor, and uses a wrapper to reward/penalize nodes based on LLM output.

Persistence: All updates are persisted back to Neo4j, keeping the knowledge graph “freshness-aware.”

Testing: End-to-end tests validate the full flow, including metadata updates in Neo4j.

Alignment with Project Goals
Compliance RAG: This flow ensures that frequently accessed (and thus likely more relevant or up-to-date) clauses are prioritized, while stale or less useful ones fade in ranking.

Explainability: The scoring and decay logic is transparent and can be surfaced in audit logs or explanations.

Adaptability: The system can adapt over time to user behavior and LLM usage patterns.

---
# POSSIBLE IMPROVEMENTS
Improvements
Hybrid Scoring: Consider combining semantic similarity and decayed score, rather than replacing the original score. This would ensure that both recency and relevance are balanced.

Cypher-Level Decay: Move decay calculation into Cypher queries for efficiency (optional, as current approach is already modular and transparent).

Decay Rate Tuning: Make decay rate and reward/penalty amounts configurable per clause type or user.

Analytics: Track how often nodes are rewarded/penalized for dashboarding or further model fine-tuning.
```


> 🎈 Knowledge Graph Neo4j with llamaindex <often gets malformed via the openai error Settings.llm can help reff: llamaindex_retriever.py>
```bash
LlamaIndex’s Neo4jVectorStore (in many versions) does NOT actually use the custom_query argument, or it ignores metadata fields and only returns text and embedding.
# to make the ollama compatible with graph neo4j llamaindex
https://docs.llamaindex.ai/en/stable/api_reference/llms/openai_like/
https://docs.llamaindex.ai/en/stable/examples/index_structs/knowledge_graph/Neo4jKGIndexDemo/

```