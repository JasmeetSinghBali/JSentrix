import React, { useEffect, useState } from 'react';
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";


export default React.memo((props: any)=>{

    const [at,setAt] = useState<string>();
    const [tools,setTools] = useState<{tools: string[]}>();

    const login = async (username: string, password: string) => {
        const response = await fetch("http://localhost:8080/token", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({ username, password }),
        });
        const data = await response.json();
        setAt(data.access_token);
        return data.access_token;
    };

    const listTools = async (token: string) => {
        const response2 = await fetch("http://localhost:8080/listtools", {
            headers: { Authorization: `Bearer ${token}` },
        });
        const data = await response2.json();
        setTools(data);
        
        return data;
    };

    const invokeTool = async (token: string, toolName: string, params = {}) => {
        const response3 = await fetch(`http://localhost:8080/tools/${toolName}/invoke`, {
            method: "POST",
            headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
            },
            body: JSON.stringify(params),
        });
        return response3.json();
    };

    useEffect(() => {
        listTools(at);
        invokeTool(at,'ping');
        invokeTool(at,'add',{
            arguments: {
                a: 2,
                b: 3
            }
        })
    }, [at]);

    useEffect(()=>{
        login('admin','secret')
    },[]);

    

    return (
        <div className='h-[100vh] w-[100%]'>
            <ResizablePanelGroup direction="horizontal">
                <ResizablePanel minSize={25} defaultSize={30}>
                    <p>Connected to gateway-server with tools:</p>
                    <ul>
                        tools: {tools?.tools}
                    </ul>
                </ResizablePanel>
                <ResizableHandle />
                <ResizablePanel minSize={30}>
                    Transaction monitor
                </ResizablePanel>
            </ResizablePanelGroup>
        </div>
    )
})