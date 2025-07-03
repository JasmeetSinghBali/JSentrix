'use client';
// mcp-client/src/custom-components/RootWrapper.tsx
import React, { useEffect, useRef, useState } from 'react';
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { useWsAuthStore } from '@/shared/store';
import { useStreamingesIdStore } from '@/shared/store';
import LogTerminal from './LogTerminal';
import { Button } from '@/components/ui/button';

// interface for a single tool object
interface Tool {
    name: string;
    description: string;
    inputSchema: object; 
    annotations: any; 
}

// interface for the shape of the 'tools' state
interface ToolsState {
    tools: Tool[];
}

export default React.memo((props: any) => {

    const [at, setAt] = useState<string>();
    const [tools, setTools] = useState<ToolsState>();
    const [logs, setLogs] = useState<string[]>([]);
    const wsRef = useRef<WebSocket | null>(null);

    const streamStartedRef = useRef<boolean>(false)

    const [streamCountdown, setStreamCountdown] = useState<number | null>(null);
    
    const [intakeLogs, setIntakeLogs] = useState<string[]>([]);
    const [assessmentLogs, setAssessmentLogs] = useState<string[]>([]);
    const [actionLogs, setActionLogs] = useState<string[]>([]);

    const shouldScrollToTop = streamCountdown === 0;


    const whoami = async (token: string) => {
        try {
            const response = await fetch("http://localhost:8080/auth/me", {
                headers: { Authorization: `Bearer ${token}` },
            });
            const data: ToolsState = await response.json(); // Cast to ToolsState
            setTools(data);
            return data;
        } catch (error) {
            console.error("Error in whoami:", error);
        }
    };

    const login = async (username: string, password: string) => {
        try {
            // abort previous stream if any (before changing token)
            const currentToken = at;
            const existingStreamId = streamId;
            if (currentToken && existingStreamId) {
                await invokeTool(currentToken, "abortinges", {
                    arguments: { stream_id: existingStreamId }
                });
                clearStreamId();
            }
            const response2 = await fetch("http://localhost:8080/auth/token", {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: new URLSearchParams({ username, password }),
            });
            const data = await response2.json();
            setAt(data.access_token);
            return data.access_token;
        } catch (error) {
            console.error("Error in login:", error);
        }
    };

    const listTools = async (token: string) => {
        try {
            const response3 = await fetch("http://localhost:8080/api/v1/listtools", {
                headers: { Authorization: `Bearer ${token}` },
            });
            const data: ToolsState = await response3.json(); // Cast to ToolsState
            setTools(data); // Set the entire object with the 'tools' array
            return data;
        } catch (error) {
            console.error("Error in listTools:", error);
            
        }
    };

    const invokeTool = async (token: string, toolName: string, params = {}) => {
        try {
            const response4 = await fetch(`http://localhost:8080/api/v1/tools/${toolName}/invoke`, {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(params),
            });
            return response4.json();
        } catch (error) {
            console.error(`Error invoking tool ${toolName}:`, error);
            
        }
    };

    // Replace with actual streaming-hub endpoint in production
    const STREAMING_HUB_URL = "http://localhost";
    // Login to streaming-hub and get client_id/token
    const loginToStreamingHub = async () => {
        try {
            const response = await fetch(`${STREAMING_HUB_URL}/login`, {
                method: "POST",
            });
            const data = await response.json();
            useWsAuthStore.getState().setAuth(data.client_id,data.token);
            return data;
        } catch (error) {
            console.error("Error logging in to streaming-hub:", error);
        }
    };

    const {clientId, token} = useWsAuthStore();

    const { streamId, setStreamId, clearStreamId } = useStreamingesIdStore();

    // --- Start streaming and schedule abort after 4 seconds ---
    const startAndAbortStreaming = async (accessToken: string) => {
        if (streamStartedRef.current) {
            console.log("Stream already starting or active, skipping.");
            return;
        }

        streamStartedRef.current = true;

        // If streamId exists, abort first
        if (streamId) {
            console.log("Existing stream found, aborting...");
            await invokeTool(accessToken, "abortinges", {
                arguments: { stream_id: streamId }
            });
            clearStreamId();
        }

        try {
            const res = await invokeTool(accessToken, "streaminges", {
                arguments: { source: "faker" }
            });

            if (res?.result?.stream_id) {
                setStreamId(res.result.stream_id);
                setStreamCountdown(150); // trigger stream countdown useEffect
                setTimeout(async () => {
                    await invokeTool(accessToken, "abortinges", {
                        arguments: { stream_id: res.result.stream_id }
                    });
                    clearStreamId();
                    streamStartedRef.current = false;
                    setStreamCountdown(null);
                }, 150000); // 150 seconds = 2.5min
            } else {
                console.error("No stream_id returned from streaminges!", res);
                streamStartedRef.current = false;
            }
        } catch (err) {
            console.error("Error in startAndAbortStreaming:", err);
            streamStartedRef.current = false;
        }
    };


    

    // Connect to Go fiber websocket and handle incoming messages
    // also reconnects settimeout minimalistic logic if ws connection drops due to any reason
    useEffect(() => {
        let ws: WebSocket | null = null;
        let reconnectTimeout: NodeJS.Timeout | null = null;
        let shouldReconnect = true;
        const RECONNECT_INTERVAL = 3000; // ms

        function connect() {
            if(clientId && token && streamId){
                ws = new WebSocket(
                    `ws://localhost/ws?client_id=${encodeURIComponent(clientId)}&token=${encodeURIComponent(token)}&stream_id=${encodeURIComponent(streamId)}`);
                wsRef.current = ws;

                ws.onopen = () => {
                    console.log('WebSocket connected to Go Fiber');
                };

                ws.onmessage = (event) => {
                    try {
                        const parsed = JSON.parse(event.data);
                        // pretty print stringify
                        const fullMessage = JSON.stringify(parsed, null, 2);

                        if (parsed.agent === "intake-agent") {
                            setIntakeLogs(prev => [...prev, `🟢 IntakeAgent:\n${fullMessage}`]);
                        } else if (parsed.agent === "assessment-agent") {
                            setAssessmentLogs(prev => [...prev, `🟣 AssessmentAgent:\n${fullMessage}`]);
                        } else if (parsed.agent === "action-agent") {
                            setActionLogs(prev => [...prev, `🔴 ActionAgent:\n${fullMessage}`]);
                        } else {
                            setIntakeLogs(prev => [...prev, `🟡 UnknownAgent:\n${fullMessage}`]);
                        }
                    } catch (err) {
                        setIntakeLogs(prev => [...prev, `⚠️ Malformed event:\n${event.data}`]);
                    }
                };

                ws.onerror = (err) => {
                    console.error('WebSocket error:', err);
                };

                ws.onclose = (event) => {
                    console.log('WebSocket closed', event.reason, event.code);
                    // if server closes due to auth error then clear credentials from zustand
                    if(event.code === 4001){ // invalid token/session
                        useWsAuthStore.getState().clearAuth();
                        shouldReconnect = false;
                        return;
                    }
                    if (shouldReconnect) {
                        reconnectTimeout = setTimeout(connect, RECONNECT_INTERVAL);
                        console.log(`Attempting to reconnect in ${RECONNECT_INTERVAL / 1000}s...`);
                    }
                };    
            }
        }

        // 📌 wait for streamId, token, clientId then connect make a websocket connect to streaming-hub
        // NOTE- the streamId only becomes available when the end user calls the streaminges tool
        if (clientId && token && streamId){
            connect();
        }

        // Cleanup on unmount
        return () => {
            shouldReconnect = false;
            if (reconnectTimeout) clearTimeout(reconnectTimeout);
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
            // Abort any running stream on unmount
            if (streamId && at) {
                invokeTool(at, "abortinges", { arguments: { stream_id: streamId } });
                clearStreamId();
            }
        };
    }, [clientId, token, streamId]);

    useEffect(() => {
        if (at) {
            whoami(at);
            listTools(at);
            invokeTool(at, 'ping');
            invokeTool(at, 'add', {
                arguments: {
                    a: 2,
                    b: 3
                }
            });
            startAndAbortStreaming(at);
        }
    }, [at]); 

    useEffect(() => {
        // login to mcp_server via gateway
        login('admin@example.com', 'ChangeThisSecurePassword123!');
        // login('user@example.com', 'testpassword');

        // login to streaming-hub for /ws websocket connection establisment
        loginToStreamingHub()
    }, []);

    
    useEffect(() => {
        if (streamCountdown === null) return;

        if (streamCountdown <= 0) {
            setStreamCountdown(null);
            return;
        }

        const interval = setInterval(() => {
            setStreamCountdown((prev) => (prev !== null ? prev - 1 : null));
        }, 1000);

        return () => clearInterval(interval);
    }, [streamCountdown]);


    return (
        <div className='h-[100vh] w-[100%]'>
            <ResizablePanelGroup direction="horizontal">
                <ResizablePanel minSize={25} defaultSize={30}>
                    <p>Connected to gateway-server with MCP tools:</p>
                    <br/>
                    <ul style={{
                        listStyle: 'inside'
                    }}>
                        {tools?.tools && tools.tools.map((tool: Tool) => (
                            <React.Fragment>
                                <li key={tool.name}>{tool.name}-({tool.description})</li>
                            </React.Fragment>
                        ))}
                    </ul>
                    {streamId && (
                        <div>
                            <b>Active stream_id:</b> <code>{streamId}</code>
                            {streamCountdown !== null && (
                                <div style={{ marginTop: '0.5em' }}>
                                    ⏳ Stream ends in <b>{streamCountdown}s</b>
                                </div>
                            )}
                        </div>
                    )}
                </ResizablePanel>
                <ResizableHandle />
                <ResizablePanel minSize={30}>
                    <div className="grid grid-cols-3 gap-6 p-2">
                        <LogTerminal
                        title="IntakeAgent Logs"
                        emoji="🟢"
                        logs={intakeLogs}
                        onClear={() => setIntakeLogs([])}
                        bgColor="#102010"
                        textColor="#aaffaa"
                        limit={150}
                        clearable
                        />
                        <LogTerminal
                        title="AssessmentAgent Logs"
                        emoji="🟣"
                        logs={assessmentLogs}
                        onClear={() => setAssessmentLogs([])}
                        bgColor="#201020"
                        textColor="#ddaaff"
                        limit={150}
                        clearable
                        />
                        <LogTerminal
                        title="ActionAgent Logs"
                        emoji="🔴"
                        logs={actionLogs}
                        onClear={()=>setActionLogs([])}
                        bgColor="#200010"
                        textColor="#ffaaaa"
                        limit={150}
                        clearable
                        />
                    </div>
                </ResizablePanel>

            </ResizablePanelGroup>
        </div>
    );
});