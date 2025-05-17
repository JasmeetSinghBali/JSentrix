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

reff: un structured.io (for complex parsing) + nlp metadata docling + langchain document loader

- diff-branch add and setup new "streaminges" and "abortinges" tool for the mcp-server these tools can be invoked by mcp-client by clicking a button in electron app. 
streaminges when invoked should send out notification to the basic setup for now minimal agent setup of Langchain Agent as fraud detection agent that on recieving this notification starts intaking a mock stream of transactions using https://github.com/joke2k/faker to generate in realtime via reusable function and then this agent analyzes the transactions by embedding them with all-MiniLM-L6-v2 and doing a similarity search or RAG against the stored compliance rules and clauses from neo4j pass the retreived data to qwen3 1.7B model runnning locally to return a analyzed report for each transaction with ouput result as flagged or not and metadata for that transaction.

- diff-branch add mem0 local dynamic graph memory to the setup so that agent can utilize both neo4j and mem0 in the analysis process

- diff-brnch polish gateway main.py maybe segregate into different files and folders and python-dotenv setup for storing the jwt secret

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