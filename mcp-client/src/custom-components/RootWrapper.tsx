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
import Dropdown, { DropdownOption } from "./Dropdown";
import { TimerReset, BadgeInfo } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Switch } from '@/components/ui/switch';
import { Separator } from "@/components/ui/separator"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"

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

    const [assessmentType, setAssessmentType] = useState<'default' | 'redistream'>('default');
    const [globalLogs, setGlobalLogs] = useState<string[]>([]); // in case of redistream single global log terminal

    const assessmentOptions: DropdownOption[] = [
        { label: "Default (A2A) Mode", value: "default" },
        { label: "Async RediStream Mode", value: "redistream" },
    ];

    const [cachingEnabled, setCachingEnabled] = useState<boolean>(false);
    const [pendingTxnAnalysisCount, setPendingTxnAnalysisCount] = useState<number>(0);




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


        // If streamId exists, abort first
        if (streamId) {
            console.log("Existing stream found, aborting...");
            await invokeTool(accessToken, "abortinges", {
                arguments: { stream_id: streamId }
            });
            clearStreamId();
            resetAllLogs();
            // 🎈 The WebSocket handler will handle cleanup after final event.
        }

        streamStartedRef.current = true;

        try {
            const res = await invokeTool(accessToken, "streaminges", {
                arguments: { 
                    source: "faker",
                    config: {
                        assessment_type: assessmentType,
                        caching: cachingEnabled
                    } 
                }
            });

            if (res?.result?.stream_id) {
                setStreamId(res.result.stream_id);
                setStreamCountdown(120); // trigger stream countdown useEffect
                setTimeout(async () => {
                    await invokeTool(accessToken, "abortinges", {
                        arguments: { stream_id: res.result.stream_id }
                    });
                    // 🎈 The WebSocket handler will handle cleanup after final event.
                    // clearStreamId();
                    streamStartedRef.current = false;
                    setStreamCountdown(null);
                }, 120000); // 120 seconds = 2min
            } else {
                console.error("No stream_id returned from streaminges!", res);
                streamStartedRef.current = false;
            }
        } catch (err) {
            console.error("Error in startAndAbortStreaming:", err);
            streamStartedRef.current = false;
        }
    };


    const resetAllLogs = () => {
        setIntakeLogs([]);
        setAssessmentLogs([]);
        setActionLogs([]);
        setGlobalLogs([]);
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
                        const eventStreamId = parsed.stream_id || (parsed.data && parsed.data.stream_id);
                        const fullMessage = JSON.stringify(parsed, null, 2);

                        // Only log events for the current streamId
                            if (eventStreamId && eventStreamId !== streamId) {
                            // Optionally: log or ignore
                            return;
                        }

                        // analysis counter sim to backend to keep track of pending txn post stream countdown ends
                        if (
                            parsed.agent === "action-agent" &&
                            parsed.message?.includes("Compliance analysis in progress")
                        ) {
                                setPendingTxnAnalysisCount(prev => (prev === null ? 1 : prev + 1));
                        }
                        if (
                            parsed.agent === "action-agent" &&
                            parsed.message?.includes("Action Taken: DecisionLevel")
                        ) {
                            setPendingTxnAnalysisCount(prev => Math.max(0, (prev ?? 1) - 1));
                        }



                        // 1. Check for ActionAgent final post-abort event
                        if (
                            parsed.agent === "action-agent" &&
                            parsed.post_abort === true &&
                            parsed.message &&
                            parsed.message.includes("Final compliance decision")
                        ) {
                            setActionLogs(prev => [
                                ...prev,
                                `🔴 [POST-ABORT][FINAL] ActionAgent:\n${fullMessage}`
                            ]);
                            // Cleanup: clear streamId, close ws, reset state
                            clearStreamId();
                            streamStartedRef.current = false;
                            setStreamCountdown(null);
                            if (wsRef.current) {
                                wsRef.current.close();
                                wsRef.current = null;
                            }
                            return;
                        }
                        // --- REDISTREAM: Push all events to global log ---
                        if (assessmentType === "redistream") {
                            setGlobalLogs(prev => [
                                ...prev,
                                `${parsed.agent ? `[${parsed.agent}] ` : ""}${fullMessage}`
                            ]);
                            return;
                        }

                        // --- DEFAULT: Per-agent logs ---
                        // 2. For all other ActionAgent events, mark post-abort if needed
                        if (parsed.agent === "action-agent") {
                            const prefix = parsed.post_abort ? "[POST-ABORT] " : "";
                            setActionLogs(prev => [
                                ...prev,
                                `🔴 ${prefix}ActionAgent:\n${fullMessage}`
                            ]);
                        } else if (parsed.agent === "intake-agent") {
                            setIntakeLogs(prev => [
                                ...prev,
                                `🟢 IntakeAgent:\n${fullMessage}`
                            ]);
                        } else if (parsed.agent === "assessment-agent") {
                            setAssessmentLogs(prev => [
                                ...prev,
                                `🟣 AssessmentAgent:\n${fullMessage}`
                            ]);
                        } else if (parsed["cached-memory-hit"]) {
                                setIntakeLogs(prev => [
                                    ...prev,
                                    `🟡 [CACHE-HIT] Memory Event:\n${JSON.stringify(parsed.memory_event, null, 2)}`
                                ]);
                                // Optionally: show a banner, toast, or highlight in your UI as well.
                                return;
                            } else {
                            setIntakeLogs(prev => [
                                ...prev,
                                `🟡 UnknownAgent:\n${fullMessage}`
                            ]);
                        }
                    } catch (err) {
                        if (assessmentType === "redistream") {
                            setGlobalLogs(prev => [
                                ...prev,
                                `⚠️ Malformed event:\n${event.data}`
                            ]);
                        } else {
                            setIntakeLogs(prev => [
                                ...prev,
                                `⚠️ Malformed event:\n${event.data}`
                            ]);
                        }
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
            resetAllLogs();
        };
    }, [clientId, token, streamId, assessmentType]);

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
    // On assessmentType change, abort stream and reset logs
    if (streamId && at) {
        invokeTool(at, "abortinges", { arguments: { stream_id: streamId } });
        clearStreamId();
        resetAllLogs();
    }
    }, [assessmentType]);

    // reset all logs when new stream starts or the current one ends all logs are cleared
    useEffect(() => {
       resetAllLogs();
    }, [streamId]);



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
            // let streamCountdown and cachingEnabled useEffect get triggered
            // setStreamCountdown(null);
            return;
        }

        const interval = setInterval(() => {
            setStreamCountdown((prev) => (prev !== null ? prev - 1 : null));
        }, 1000);

        return () => clearInterval(interval);
    }, [streamCountdown]);



    useEffect(() => {
        if (
            cachingEnabled &&
            streamCountdown === 0 &&
            pendingTxnAnalysisCount === 0
        ) {
            // 🎈 add toast like message here instead console.log here
            console.log("✅ [Caching-Enabled-trigger-Auto-close]: No pending txns + countdown expired");
            clearStreamId();
            streamStartedRef.current = false;
            setStreamCountdown(null);
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
        }
    }, [streamCountdown, cachingEnabled, pendingTxnAnalysisCount]);


    useEffect(() => {
        console.log(`[Pending Analysis Txns Count as per UI]: ${pendingTxnAnalysisCount}`);
    }, [pendingTxnAnalysisCount]);

    useEffect(()=>{
        if(cachingEnabled){
            toast("Quick Assessment Mode is active.")
        }
        if(!cachingEnabled){
            toast("Full Assessment Mode is active.")
        }
    },[cachingEnabled])



    return (
        <React.Fragment>
            <Toaster/>
            <div className='h-[70vh] w-[100%]'>
                <ResizablePanelGroup direction="horizontal">
                    <ResizablePanel minSize={25} defaultSize={25}>
                        {/* CoreConfigs = Assessment Mode + Memory Caching Enabled/Disabled + Reset System */}
                        <div className='mb-6 ml-6 mt-6'>
                            <div className="space-y-1">
                                <h3 className="scroll-m-20 text-2xl font-semibold tracking-tight">SYSTEM CONFIGS</h3>
                                <p className="text-muted-foreground text-sm">
                                Switch between Modes, Reset System and Quick Assessment 
                                </p>
                            </div>
                            <Separator className="my-4" />
                            <div className="flex h-5 items-center space-x-4 text-sm">
                                <div>
                                    <Dropdown
                                        label="Assessment Mode"
                                        options={assessmentOptions}
                                        value={assessmentType}
                                        onChange={(v) => setAssessmentType(v as "default" | "redistream")}
                                    />
                                </div>
                                <Separator orientation="vertical" />
                                <div className="flex items-center space-x-1">
                                    <Switch
                                        id="caching-toggle"
                                        checked={cachingEnabled}
                                        onCheckedChange={setCachingEnabled}
                                    />
                                    <Tooltip>
                                        <TooltipTrigger>
                                        <BadgeInfo className='w-4 h-4' />
                                        </TooltipTrigger>
                                        <TooltipContent>
                                            <p>When active assessment and action agent steps are short-circuited if new txn's have similarity with prior assessed events.</p>
                                        </TooltipContent>
                                    </Tooltip>
                                    <label htmlFor="caching-toggle" className="text-sm font-medium">
                                        Cached
                                    </label>
                                </div>
                                <Separator orientation="vertical" />
                                <div>
                                    {/* 📌 shud be used often before hardrefresh or starting new stream */}
                                    <Button
                                        variant="outline"
                                        size="icon"
                                        onClick={resetAllLogs}
                                        className="ml-1"
                                    >
                                        <Tooltip>
                                            <TooltipTrigger>
                                                <TimerReset className="w-5 h-5" />
                                            </TooltipTrigger>
                                            <TooltipContent>
                                                <p>Reset System</p>
                                            </TooltipContent>
                                        </Tooltip>    
                                    </Button>
                                </div>
                            </div>
                            <Separator className="my-4" />
                        </div>
                        {/* 🎈 for future this shud be tabs for each tool with description payload and action button to invoke it */}
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
                        <div className="mt-4 mb-2 p-3 rounded-md bg-muted/40 border border-muted">
                            <div className="flex items-center gap-2 text-sm">
                            <span className="font-semibold text-muted-foreground">Active stream_id:</span>
                            <code className="px-2 py-0.5 rounded bg-muted text-xs">{streamId}</code>
                            </div>
                            {streamCountdown !== null && (
                            <>
                                <div className="flex items-center gap-2 mt-2 text-base">
                                <span role="img" aria-label="hourglass">⏳</span>
                                <span>
                                    Stream ends in <b>{streamCountdown}s</b>
                                </span>
                                </div>
                                <div className="mt-1 text-xs text-muted-foreground leading-snug">
                                <b>NOTE:</b> New transactions are <span className="text-destructive">no longer ingested</span> after the stream ends.<br />
                                However, post-abort-stream analysis events (already in progress before abort) may still arrive until the <b>final post-abort event</b> is emitted by <code>mcp_server</code>.
                                </div>
                            </>
                            )}
                        </div>
                        )}
                    </ResizablePanel>
                    <ResizableHandle />
                    <ResizablePanel minSize={60}>
                        {/* Only use grid when showing multiple logs */}
                        {assessmentType === "redistream" ? (
                            <div className="p-2 h-full w-full">
                            <LogTerminal
                                title="Global Event Log"
                                emoji="🌐"
                                logs={globalLogs}
                                onClear={() => setGlobalLogs([])}
                                bgColor="#101020"
                                textColor="#ffffff"
                                limit={300}
                                clearable
                            />
                            </div>
                        ) : (
                            <div className="grid grid-cols-3 gap-6 p-2 h-full w-full">
                            <LogTerminal
                                title="Intake-Agent"
                                emoji="🟢"
                                logs={intakeLogs}
                                onClear={() => setIntakeLogs([])}
                                bgColor="#102010"
                                textColor="#aaffaa"
                                limit={150}
                                clearable
                            />
                            <LogTerminal
                                title="Assessment-Agent"
                                emoji="🟣"
                                logs={assessmentLogs}
                                onClear={() => setAssessmentLogs([])}
                                bgColor="#201020"
                                textColor="#ddaaff"
                                limit={150}
                                clearable
                            />
                            <LogTerminal
                                title="Action-Agent"
                                emoji="🔴"
                                logs={actionLogs}
                                onClear={()=>setActionLogs([])}
                                bgColor="#200010"
                                textColor="#ffaaaa"
                                limit={150}
                                clearable
                            />
                            </div>
                        )}
                        </ResizablePanel>


                </ResizablePanelGroup>
            </div>
            <Separator className="my-1" />
            {/* 🎈 Add xy react flow visualizing intake, assessment, judge agent working and shud be 2 flows 1 for default a2a mode and the 2nd one for Async Redis Stream mode */}

        </React.Fragment>
        
    );
});