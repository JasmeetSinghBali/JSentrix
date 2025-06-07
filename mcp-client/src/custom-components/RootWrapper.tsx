'use client';

import React, { useEffect, useState } from 'react';
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";

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
        login('admin@example.com', 'ChangeThisSecurePassword123!');
        // login('user@example.com', 'testpassword');
    }, []);

    return (
        <div className='h-[100vh] w-[100%]'>
            <ResizablePanelGroup direction="horizontal">
                <ResizablePanel minSize={25} defaultSize={30}>
                    <p>Connected to gateway-server with tools:</p>
                    <ul>
                        {tools?.tools && tools.tools.map((tool: Tool) => (
                            <React.Fragment>
                                <li key={tool.name}>{tool.name}-({tool.description})</li>
                            </React.Fragment>
                        ))}
                    </ul>
                </ResizablePanel>
                <ResizableHandle />
                <ResizablePanel minSize={30}>
                    Transaction monitor
                </ResizablePanel>
            </ResizablePanelGroup>
        </div>
    );
});