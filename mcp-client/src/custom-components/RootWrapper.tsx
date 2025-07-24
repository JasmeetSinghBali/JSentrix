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
import { TimerReset, BadgeInfo, BadgeCheck, BadgeX, Cog, Activity, HeartPulse, Podcast, Hourglass, Hammer } from "lucide-react";
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
import { Badge } from "@/components/ui/badge"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"

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

    const [whoamiAccess, setWhoAmIAccess] = useState<boolean>(false);
    const [loginGateway, setLoginGateway] = useState<boolean>(false);
    const [toolActive, setToolActive] = useState<boolean>(false);
    const [websocketActive, setWebsocketActive] = useState<boolean>(false);




    const whoami = async (token: string) => {
        try {
            const response = await fetch("http://localhost:8080/auth/me", {
                headers: { Authorization: `Bearer ${token}` },
            });
            const data: ToolsState = await response.json(); // Cast to ToolsState
            setTools(data);
            setWhoAmIAccess(true);
            return data;
        } catch (error) {
            console.error("Error in whoami:", error);
            setWhoAmIAccess(false);
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
            setLoginGateway(true);
            return data.access_token;
        } catch (error) {
            console.error("Error in login:", error);
            setLoginGateway(false);
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
            if(response4 && toolName === 'ping'){
                setToolActive(true)
            }
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
                        arguments: { 
                            stream_id: res.result.stream_id 
                        }
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

    const resetSystem = (terminalLogs: boolean = false) => {
        clearStreamId();
        streamStartedRef.current = false;
        setStreamCountdown(null);
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        setLoginGateway(false)
        setToolActive(false)
        if(terminalLogs){
            resetAllLogs()
        }
    }

    

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
                    setWebsocketActive(true);
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
                            // Reset System
                            resetSystem()
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
                    setWebsocketActive(false);
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
    // On assessmentType change, abort the stream and reset all logs
    if (streamId && at) {
        invokeTool(at, "abortinges", { arguments: { stream_id: streamId } });
        clearStreamId();
    }
    }, [assessmentType]);
   

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
            <div className='h-screen w-full'>
                {/* Outermost: vertical split */}
                <ResizablePanelGroup direction="vertical">

                    {/* Top-Panel: Left: Vitals, tools, configs section and Right: Log Terminal Section */}
                    <ResizablePanel minSize={40} defaultSize={70}> {/* 70%+ space */}
                        
                        <ResizablePanelGroup direction="horizontal">
                            {/* Vitals, tools, configs section */}

                            <ResizablePanel minSize={25} defaultSize={25}>
                                {/* CoreConfigs = Assessment Mode + Memory Caching Enabled/Disabled + Reset System */}
                                <div className='mb-6 ml-6 mt-6'>
                                    <div className="flex h-5 items-center space-x-4 text-sm">
                                        <Cog className='w-4 h-4'/>
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
                                                    <p>Enabling skips assessment and action agent pipeline if new txn's have similarity with prior assessed events.</p>
                                                </TooltipContent>
                                            </Tooltip>
                                            <label htmlFor="caching-toggle" className="text-sm font-medium">
                                                Cached
                                            </label>
                                        </div>
                                        <Separator orientation="vertical" />
                                        <div>
                                            {/* 📌 shud be used often before hardrefresh or starting new stream */}
                                            <Tooltip>
                                                <TooltipTrigger asChild>
                                                    <span>
                                                    <Button
                                                        variant="outline"
                                                        size="icon"
                                                        onClick={()=>{resetSystem(true)}}
                                                    >
                                                        <TimerReset className="w-5 h-5" />
                                                    </Button>
                                                    </span>
                                                </TooltipTrigger>
                                                <TooltipContent>
                                                    <p>Reset System</p>
                                                </TooltipContent>
                                            </Tooltip>
                                        </div>
                                    </div>
                                    <Separator className="my-4" />
                                </div>
                                {/* Dynamic System Vitals Section */}
                                <div className="ml-6 mb-2 p-3 rounded-md bg-muted/80 border border-muted">
                                    <div className="text-muted-foreground text-sm flex items-center gap-2">
                                        <div className='flex items-center gap-5 mt-2'>
                                            {
                                                (loginGateway && whoamiAccess) ?
                                                <HeartPulse className='w-4 h-4 text-green-500' />
                                                :    
                                                <Activity className='w-4 h-4 text-red-500'/>
                                                
                                            }
                                            Vitals :
                                            <div className="flex h-5 items-center space-x-4 text-sm">
                                                <Badge 
                                                    // variant="default |outline | secondary | destructive"
                                                    variant={(loginGateway && whoamiAccess) ? "secondary" : "destructive"}
                                                    className={(loginGateway && whoamiAccess) && "bg-blue-500 text-white dark:bg-blue-600"}
                                                    >
                                                        {(loginGateway && whoamiAccess) ? <BadgeCheck/>: <BadgeX/>}
                                                        Gateway
                                                </Badge>
                                                <Separator orientation="vertical" />
                                                <Badge 
                                                    // variant="default |outline | secondary | destructive"
                                                    variant={ toolActive ? "secondary" : "destructive"}
                                                    className={toolActive && "bg-blue-500 text-white dark:bg-blue-600"}
                                                    >
                                                        {
                                                            toolActive ? <BadgeCheck/> : <BadgeX/>
                                                        }
                                                        Tools
                                                </Badge>
                                                <Separator orientation="vertical" />
                                                <Badge 
                                                    // variant="default |outline | secondary | destructive"
                                                    variant={websocketActive ? "secondary" : "destructive"}
                                                    className={websocketActive && "bg-blue-500 text-white dark:bg-blue-600"}
                                                    >
                                                        {
                                                            websocketActive ? <BadgeCheck/> : <BadgeX/>
                                                        }
                                                        Events
                                                </Badge>
                                            </div>
                                        </div>
                                    </div>
                                    <div className='text-muted-foreground text-sm'>
                                        <div className='flex items-center gap-5 mt-2'>
                                            {
                                                streamId ?
                                                <Podcast className='w-4 h-4 text-green-500'/>
                                                :    
                                                <BadgeX className='w-4 h-4 text-red-500'/>
                                                
                                            }
                                            StreamID :
                                            <code className={streamId ? "px-2 py-0.5 rounded bg-blue-500 text-white text-xs" : "px-2 py-0.5 rounded bg-red-600 text-white text-xs" }>{streamId || 'no-active-stream-id'}</code>
                                        </div>
                                    </div>
                                </div>
                                <div className='flex ml-6 items-center gap-5 mt-2'>
                                    <Accordion
                                        type="single"
                                        collapsible
                                        className="w-full"
                                        defaultValue="item-1"
                                        >
                                        <AccordionItem value="item-1">
                                            
                                            <AccordionTrigger>
                                                <div className='flex justify-between items-center gap-2'>
                                                    <Podcast className='w-4 h-4'/>
                                                    Stream Vitals
                                                </div>
                                                
                                            </AccordionTrigger>

                                            <AccordionContent className="flex flex-col gap-4 text-balance">
                                                {
                                                    streamCountdown !== null ?
                                                    (
                                                        <div className='text-muted-foreground text-sm'>
                                                            <div className="flex-column items-center gap-2 mt-2 text-base p-3 rounded-md bg-muted/80 border border-muted">
                                                                <div className='flex items-center gap-2'>
                                                                    <Hourglass className='w-4 h-4'/>
                                                                    Stream ends in <b>{streamCountdown}s</b>
                                                                </div>
                                                                <div className="mt-1 text-xs text-muted-foreground leading-snug">
                                                                    <b>NOTE:</b> New transactions are <span className="text-destructive">no longer ingested</span> after the stream ends.<br />
                                                                    However, post-abort-stream analysis events (already in progress <br/>before abort) may still arrive until the <b>final post-abort event</b> <br/> is emitted by <code>mcp server</code>.
                                                                </div>
                                                            </div>
                                                        </div>
                                                    ) :
                                                    <div className='text-muted-foreground text-sm'>
                                                        <div className="flex items-center gap-2 mt-2 text-base p-3 rounded-md bg-muted/80 border border-muted">
                                                            <BadgeX className='w-4 h-4 text-red-500'/>
                                                            No stream is active at the moment.
                                                        </div>
                                                    </div>
                                                }
                                            </AccordionContent>
                                        </AccordionItem>
                                        <AccordionItem value="item-2">
                                            <AccordionTrigger>
                                                <div className='flex justify-between items-center gap-2'>
                                                    <Hammer className='w-4 h-4'/>
                                                    Available Tools
                                                </div>
                                            </AccordionTrigger>
                                            <AccordionContent className="flex flex-col gap-4 text-balance">
                                                {/* 🎈 for future this shud be tabs for each tool with description payload and action button to invoke it */}
                                                {
                                                    tools?.tools ? 
                                                    (
                                                        <ul style={{
                                                            listStyle: 'inside'
                                                        }}>
                                                            {tools?.tools && tools.tools.map((tool: Tool) => (
                                                                <React.Fragment>
                                                                    <li key={tool.name}>{tool.name}-({tool.description})</li>
                                                                </React.Fragment>
                                                            ))}
                                                        </ul>
                                                    ) 
                                                    :
                                                    (
                                                        <div className='text-muted-foreground text-sm'>
                                                            <div className="flex items-center gap-2 mt-2 text-base p-3 rounded-md bg-muted/80 border border-muted">
                                                                <BadgeX className='w-4 h-4 text-red-500'/>
                                                                No tools available at the moment.
                                                            </div>
                                                        </div>
                                                    )
                                                }
                                            </AccordionContent>
                                        </AccordionItem>
                                    </Accordion>
                                </div>
                                
                                
                                
                            </ResizablePanel>
                            
                            <ResizableHandle />

                            {/* Log section */}
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
                                        title="Intake-Events"
                                        emoji="🟢"
                                        logs={intakeLogs}
                                        onClear={() => setIntakeLogs([])}
                                        bgColor="#102010"
                                        textColor="#aaffaa"
                                        limit={150}
                                        clearable
                                    />
                                    <LogTerminal
                                        title="Assess-Events"
                                        emoji="🟣"
                                        logs={assessmentLogs}
                                        onClear={() => setAssessmentLogs([])}
                                        bgColor="#201020"
                                        textColor="#ddaaff"
                                        limit={150}
                                        clearable
                                    />
                                    <LogTerminal
                                        title="Action-Events"
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

                    </ResizablePanel>

                    {/* Middle handle (vertical drag between top and bottom) */}
                    <ResizableHandle />

                    {/* Bottom-Panel: XY React Flow Visual */}
                    <ResizablePanel minSize={10} defaultSize={30}>
                        <div className="h-full w-full bg-muted p-4 flex items-center justify-center">
                            {/* 🎈 Add xy react flow visualizing intake, assessment, judge agent working and shud be 2 flows 1 for default a2a mode and the 2nd one for Async Redis Stream mode */}
                            {/* For example */}
                            <div className="h-full w-full flex flex-col items-center justify-center">
                            <h2 className="mb-2 text-lg font-semibold">Agent Flows</h2>
                            {/* <YourXYReactFlowComponent mode={assessmentType}/> */}
                            <div className="border border-dashed border-gray-400 h-full w-full flex items-center justify-center text-muted-foreground">
                                XY React Flow Visuals go here
                            </div>
                            </div>
                        </div>
                    </ResizablePanel>
                
                </ResizablePanelGroup>
                {/* End main vertical split */}
            </div>
        </React.Fragment>
        
    );
});