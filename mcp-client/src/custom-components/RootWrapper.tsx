'use client';

import React, { useEffect, useRef, useState } from 'react';
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { useWsAuthStore } from '@/shared/store';

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

    // Connect to Go fiber websocket and handle incoming messages
    // also reconnects settimeout minimalistic logic if ws connection drops due to any reason
    useEffect(() => {
        let ws: WebSocket | null = null;
        let reconnectTimeout: NodeJS.Timeout | null = null;
        let shouldReconnect = true;
        const RECONNECT_INTERVAL = 3000; // ms

        function connect() {
            if(clientId && token){
                ws = new WebSocket(
                    `ws://localhost/ws?client_id=${encodeURIComponent(clientId)}&token=${encodeURIComponent(token)}`);
                wsRef.current = ws;

                ws.onopen = () => {
                    console.log('WebSocket connected to Go Fiber');
                };

                ws.onmessage = (event) => {
                    setLogs(prev => [...prev, event.data]);
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

        connect();

        // Cleanup on unmount
        return () => {
            shouldReconnect = false;
            if (reconnectTimeout) clearTimeout(reconnectTimeout);
            if (ws) ws.close();
        };
    }, []);

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
        }
    }, [at]); 

    useEffect(() => {
        // login to mcp_server via gateway
        login('admin@example.com', 'ChangeThisSecurePassword123!');
        // login('user@example.com', 'testpassword');

        // login to streaming-hub for /ws websocket connection establisment
        loginToStreamingHub()
    }, []);


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
                </ResizablePanel>
                <ResizableHandle />
                <ResizablePanel minSize={30}>
                    <div>
                        <h3>Transaction Monitor (Real-Time Events)</h3>
                        <div style={{
                            height: '90vh',
                            overflowY: 'auto',
                            background: '#1a1a1a',
                            color: '#e0e0e0',
                            padding: '1em',
                            borderRadius: '8px'
                        }}>
                            {logs.length === 0 && <div>No events yet.</div>}
                            {logs.map((log, idx) => (
                                <div key={idx} style={{marginBottom: '0.5em'}}>{log}</div>
                            ))}
                        </div>
                    </div>
                </ResizablePanel>
            </ResizablePanelGroup>
        </div>
    );
});