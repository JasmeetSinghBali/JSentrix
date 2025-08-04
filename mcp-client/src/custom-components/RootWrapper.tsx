'use client';

// mcp-client/src/custom-components/RootWrapper.tsx
import React, { useEffect, useRef, useState } from 'react';
import { 
    useGatewayAuthStore, 
    useStreamingesConfigStore, 
    useWsAuthStore, 
    useStreamingStore, 
    useRouterStore,
    AppRoute
} from '@/shared/store';
import { DropdownOption } from "./Dropdown";
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"
import { AppSidebar } from './AppSidebar';
import { SidebarProvider } from '@/components/ui/sidebar';
import JsentrixDashboard from '@/routes/JsentrixDashboard';


// interface for a single tool object
export interface Tool {
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

    // Auth and Config Store
    const accessToken = useGatewayAuthStore(state=>state.accessToken);
    const setAccessToken = useGatewayAuthStore(state => state.setAccessToken);
    const assessmentType = useStreamingesConfigStore(state => state.assessmentType);
    const setAssessmentType = useStreamingesConfigStore(state => state.setAssessmentType);
    const cachingEnabled = useStreamingesConfigStore(state => state.cachingEnabled);
    const setCachingEnabled = useStreamingesConfigStore(state => state.setCachingEnabled);

    // Route store
    const currentAppRoute = useRouterStore(state=>state.currentRoute);

    // Ws auth store
    const {clientId, token} = useWsAuthStore();
    
    // streaming store manages streamId, websocketActive, streamCountdown, and abortController
    const streamId = useStreamingStore((state)=>state.streamId);
    const setStreamId = useStreamingStore((state) => state.setStreamId);
    const clearStreamId = useStreamingStore((state) => state.clearStreamId);
    const websocketActive = useStreamingStore((state) => state.websocketActive);
    const setWebsocketActive = useStreamingStore((state) => state.setWebsocketActive);

    const streamCountdown = useStreamingStore((state)=>state.streamCountdown);
    const setStreamCountdown = useStreamingStore((state) => state.setStreamCountdown);
  
    const abortController = useStreamingStore((state) => state.abortController);
    const setAbortController = useStreamingStore((state) => state.setAbortController);

    // Local States
    const [currentAppRouteLocal, setCurrentAppRouteLocal] = useState<AppRoute>(currentAppRoute);

    const [tools, setTools] = useState<ToolsState>();
    const [toolsLoading, setToolsLoading] = useState<boolean>(false);
    const [toolsError, setToolsError] = useState<boolean>(false);
    const [toolActive, setToolActive] = useState<boolean>(false);
    const [pendingTxnAnalysisCount, setPendingTxnAnalysisCount] = useState<number>(0);
 
    const [intakeLogs, setIntakeLogs] = useState<string[]>([]);
    const [assessmentLogs, setAssessmentLogs] = useState<string[]>([]);
    const [actionLogs, setActionLogs] = useState<string[]>([]);    
    const [globalLogs, setGlobalLogs] = useState<string[]>([]); // in case of redistream single global log terminal

    const [whoamiAccess, setWhoAmIAccess] = useState<boolean>(false);
    const [whoamiAccessLoading, setWhoAmIAccessLoading] = useState<boolean>(false);
    const [whoamiAccessError, setWhoAmIAccessError] = useState<boolean>(false);
    const [loginGateway, setLoginGateway] = useState<boolean>(false);
    const [loginGatewayLoading, setLoginGatewayLoading] = useState<boolean>(false)
    const [loginGatewayError, setLoginGatewayError] = useState<boolean>(false);

    const [toolId, setToolId] = useState<string>("ping");
    const availableTools: Tool[] = tools?.tools || [];

    // Refs to hold timers, so that can be cleared on demand
    const abortTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const countdownIntervalRef = useRef<NodeJS.Timeout | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const websocketRef = useRef<WebSocket | null>(null);
    // 📌 native WebSocket.prototype.close(code, reason)
    // the reason string passed is only accessible on the server side (if supported) 
    // and as event.reason on the client where the connection closes. 
    // The problem is that browsers will not fire event.reason if call .close() from the same client — 
    // it gets eaten silently by most browser implementations (esp. in Chrome)
    const closeReasonRef = useRef<string | null>(null);



    const assessmentOptions: DropdownOption[] = [
        { label: "Default (A2A) Mode", value: "default" },
        { label: "Async RediStream Mode", value: "redistream" },
    ];

    // system inital render combine loading state for progress bar
    const [hideProgressBar, setHideProgressBar] = useState(false);
    const loadingStates = [
        whoamiAccessLoading,
        loginGatewayLoading,
        toolsLoading,
    ];
    const totalStates = loadingStates.length;
    const completedStates = loadingStates.filter((v) => !v).length;
    const progressPercent = (completedStates / totalStates) * 100;

    // appsidebar open/setopen local state
    const [openAppBar, setOpenAppBar] = React.useState(false);

    // General purpose invocation utility reused by start/abort etc.
    const invokeTool = async (token: string, toolName: string, params = {}) => {
        try {
        const response = await fetch(
            `http://localhost:8080/api/v1/tools/${toolName}/invoke`,
            {
            method: "POST",
            headers: {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify(params),
            }
        );
        if (response && toolName === "ping") {
            setToolActive(true);
        }
            return response.json();
        } catch (error) {
            toast.error(
                `[error-invoking-tool]-${toolName}`,
                {
                    description: `error: \n${JSON.stringify(error?.message || error ,null,2)}`,
                    position: 'top-center'
                }
            );
        }
    };

    // Reset all logs
    const resetAllLogs = () => {
        setIntakeLogs([]);
        setAssessmentLogs([]);
        setActionLogs([]);
        setGlobalLogs([]);
    };
    
    // Reset entire system (close web socket etc.)
    const resetSystem = (terminalLogs = false) => {
        clearStreamId();
        setStreamCountdown(null);
        setWebsocketActive(false);
        const controller = useStreamingStore.getState().abortController;
        console.log(`[resetSystem-triggered] Aborting websocket connection:`, controller);

        if (controller) {
            controller.abort();
            setAbortController(null);
        }
        if (websocketRef.current) {
            closeReasonRef.current = "[Reset-System-Triggered]-websocketRef.close()"
            websocketRef.current.close(1000, closeReasonRef.current);
            websocketRef.current = null;
        }
        if (abortTimeoutRef.current) {
            clearTimeout(abortTimeoutRef.current);
            abortTimeoutRef.current = null;
        }
        if (countdownIntervalRef.current) {
            clearInterval(countdownIntervalRef.current);
            countdownIntervalRef.current = null;
        }
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }
        if (terminalLogs) {
            resetAllLogs();
        }
    };
    
    // --- WebSocket connect + reconnect logic ---
    const connectWebSocket = () => {
        if (!clientId || !token || !streamId) {
            return;
        }

        // Abort previous connection if any
        if (abortController) {
            abortController.abort();
        }

        closeReasonRef.current = null; // reset for next ws connection

        const controller = new AbortController();
        setAbortController(controller);
        const signal = controller.signal;

        const wsUrl = `ws://localhost/ws?client_id=${encodeURIComponent(clientId)}&token=${encodeURIComponent(token)}&stream_id=${encodeURIComponent(streamId)}`;

        const ws = new WebSocket(wsUrl);
        websocketRef.current = ws; // 📌 essential to use to for .close() explicitely as abort controller does not breaks of the websocket native connection automatically

        ws.onopen = () => {
            toast.success(
                "[ws.onopen]-Event",
                {
                    description: "connection established with streaming hub",
                    position: 'top-center'
                }
            );
            setWebsocketActive(true);
        };

        ws.onmessage = (event) => {
            try {
                const parsed = JSON.parse(event.data);
                const eventStreamId =
                parsed.stream_id || (parsed.data && parsed.data.stream_id);
                const fullMessage = JSON.stringify(parsed, null, 2);

                if (eventStreamId && eventStreamId !== streamId) {
                    return;
                }

                // Analysis counters to track pending txns after stream countdown ends
                if (
                    parsed.agent === "action-agent" &&
                    parsed.message?.includes("Compliance analysis in progress")
                ) {
                    setPendingTxnAnalysisCount((prev) => (prev === null ? 1 : prev + 1));
                }
                if (
                    parsed.agent === "action-agent" &&
                    parsed.message?.includes("Action Taken: DecisionLevel")
                ) {
                    setPendingTxnAnalysisCount((prev) => Math.max(0, (prev ?? 1) - 1));
                }

                // Final post-abort event -> Reset System
                if (
                parsed.agent === "action-agent" &&
                parsed.post_abort === true &&
                parsed.message &&
                parsed.message.includes("Final compliance decision")
                ) {
                    setActionLogs((prev) => [
                        ...prev,
                        `🔴 [POST-ABORT][FINAL] ActionAgent:\n${fullMessage}`,
                    ]);
                    toast.warning(
                        "[Manual-cutoff-ws]-Event",
                        {
                            description: `Reason: Final compliance decision event was recieved` ,
                            position: 'top-center'
                        }
                    );
                    resetSystem();
                    return;
                }

                // REDISTREAM global logs vs per-agent logs fallback
                if (assessmentType === "redistream") {
                    setGlobalLogs((prev) => [
                        ...prev,
                        `${parsed.agent ? `[${parsed.agent}] ` : ""}${fullMessage}`,
                    ]);
                    return;
                }

                if (parsed.agent === "action-agent") {
                const prefix = parsed.post_abort ? "[POST-ABORT] " : "";
                setActionLogs((prev) => [
                    ...prev,
                    `🔴 ${prefix}ActionAgent:\n${fullMessage}`,
                ]);
                } else if (parsed.agent === "intake-agent") {
                setIntakeLogs((prev) => [...prev, `🟢 IntakeAgent:\n${fullMessage}`]);
                } else if (parsed.agent === "assessment-agent") {
                setAssessmentLogs((prev) => [
                    ...prev,
                    `🟣 AssessmentAgent:\n${fullMessage}`,
                ]);
                } else if (parsed["cached-memory-hit"]) {
                setIntakeLogs((prev) => [
                    ...prev,
                    `🟡 [CACHE-HIT] Memory Event:\n${JSON.stringify(
                    parsed.memory_event,
                    null,
                    2
                    )}`,
                ]);
                } else {
                    setIntakeLogs((prev) => [...prev, `🟡 UnknownAgent:\n${fullMessage}`]);
                }
            } catch (err: any) {
                if (assessmentType === "redistream") {
                    setGlobalLogs((prev) => [...prev, `⚠️ Malformed event:\n${event.data}`]);
                } else {
                    setIntakeLogs((prev) => [...prev, `⚠️ Malformed event:\n${event.data}`]);
                }
            }
        };

        ws.onerror = (err: any) => {
            toast.error(
                "[error-websocket]-ws.onerror",
                {
                    description: `error: \n${JSON.stringify(err || err ,null,2)}`,
                    position: 'top-center'
                }
            );
        };

        ws.onclose = (event) => {
            const localReason = closeReasonRef.current;
            toast.warning(
                "[ws.onclose]-Event",
                {
                    description: `reason: ${localReason || event.reason || "No reason"} \ncode: ${event.code}` ,
                    position: 'top-center'
                }
            );
            setWebsocketActive(false);
            closeReasonRef.current = null; // reset for next ws connection

            if (event.code === 4001) {
                // invalid token/session
                useWsAuthStore.getState().clearAuth();
                return;
            }

            // Try reconnect if websocket was closed unexpectedly
            if (!signal.aborted) {
                reconnectTimeoutRef.current = setTimeout(() => {
                connectWebSocket();
                toast.info(
                    "[reconnect-ws]-Event",
                    {
                        description: "Attempting to reconnect websocket after 3s...",
                        position: 'top-center'
                    }
                );
                }, 3000);
            }
        };
    };



    const whoami = async (token: string) => {
        try {
            setWhoAmIAccessLoading(true)
            const response = await fetch("http://localhost:8080/auth/me", {
                headers: { Authorization: `Bearer ${token}` },
            });
            const data: any = await response.json(); // 🎈 shud Cast to UserState who is logged in
            setWhoAmIAccess(true);
            return data;
        } catch (error: any) {
            console.error("Error in whoami:", error);
            setWhoAmIAccessError(true)
            setWhoAmIAccess(false);
        }finally{
            setWhoAmIAccessLoading(false)
        }
    };

    const login = async (username: string, password: string) => {
        try {
        setLoginGatewayLoading(true)
        // Abort any existing stream before login
        if (accessToken && streamId) {
            await invokeTool(accessToken, "abortinges", {
            arguments: { stream_id: streamId },
            });
            clearStreamId();
        }
        const response = await fetch("http://localhost:8080/auth/token", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({ username, password }),
        });
        const data = await response.json();
        setAccessToken(data.access_token);
        setLoginGateway(true);
        return data.access_token;
        } catch (error: any) {
            console.error("Error in login:", error);
            setLoginGatewayError(true);
            setLoginGateway(false);
        }finally{
            setLoginGatewayLoading(false)
        }
    };

    const loginToStreamingHub = async () => {
        try {
        const response = await fetch(`http://localhost/login`, { method: "POST" });
        const data = await response.json();
        useWsAuthStore.getState().setAuth(data.client_id, data.token);
        return data;
        } catch (error: any) {
         console.error("Error logging in to streaming-hub:", error);
        }
    };

    const listTools = async (token: string) => {
        setToolsLoading(true);
        setToolsError(false);
        try {
        const response = await fetch("http://localhost:8080/api/v1/listtools", {
            headers: { Authorization: `Bearer ${token}` },
        });
        const data: ToolsState = await response.json();
        setTools(data);
        return data;
        } catch (error: any) {
            console.error("Error in listTools:", error);
            setToolsError(true);
            setTools(null)
        } finally {
            setToolsLoading(false);
        }
    };


    // --- Stream control functions, can be passed to ToolTabsPanel or exposed via Zustand actions ---

    // Start streaming with duration (seconds or 'infinite')
    const startStreamingWithDuration = async (
        duration: number | "infinite" = 120
    ) => {
        console.log("startStreamingWithDuration called", { duration })
        if (!accessToken) {
            toast.warning(
                "No access token for starting stream",
                {
                    position: 'top-center',
                }
            );
            return;
        }
        if (streamId) {
            toast.warning(
                "Stream already active",
                {
                    description: `Active: ${useStreamingStore.getState().streamId}`,
                    position: 'top-center',
                }
            );
            return;
        }

        try {
        const res = await invokeTool(accessToken, "streaminges", {
            arguments: {
            source: "faker",
            config: { assessment_type: assessmentType, caching: cachingEnabled },
            },
        });

        if (res?.result?.stream_id) {
            setStreamId(res.result.stream_id);
            setStreamCountdown(duration === "infinite" ? null : duration);

            // Clear previous timers if any
            if (abortTimeoutRef.current) {
                clearTimeout(abortTimeoutRef.current);
                abortTimeoutRef.current = null;
            }
            if (countdownIntervalRef.current) {
                clearInterval(countdownIntervalRef.current);
                countdownIntervalRef.current = null;
            }

                // Setup countdown timer and abort mechanism if not infinite
                if (duration !== "infinite") {
                    countdownIntervalRef.current = setInterval(() => {
                        // 📌 every tick, always update based on the most recent value of streamCountdown
                        const curr = useStreamingStore.getState().streamCountdown;
                        if (curr === null || curr <= 1) {
                            clearInterval(countdownIntervalRef.current!);
                            countdownIntervalRef.current = null;
                            setStreamCountdown(null);
                        } else {
                            setStreamCountdown(curr - 1);
                        }
                    }, 1000);

                    abortTimeoutRef.current = setTimeout(async () => {
                        toast.warning(
                            "[trigger-autoabort]-Event",
                            {
                                description: `Auto aborting stream after stream-duration: ${duration}s`,
                                position: 'top-center'
                            }
                        );
                        const currCachingMode = useStreamingesConfigStore.getState().cachingEnabled
                        await abortStreaming(currCachingMode || false); // Use abortStreaming handler to abort
                    }, duration * 1000);
                }
            } else {
                toast.error(
                    "[error-startStreamingWithDuration]-NoStreamIdReturned-streaminges",
                        {
                            position: 'top-center',
                        }
                );
            }
        } catch (err: any) {
            toast.error(
                "[error-startStreamingWithDuration]-Event",
                {
                    description: `error: \n${JSON.stringify(err?.message || err ,null,2)}`,
                    position: 'top-center'
                }
            );
        }
    };

    // Abort streaming but do NOT close websocket so post-abort events can be handled
    const abortStreaming = async (cachedTrigger: boolean = false) => {
        const currentStreamId = useStreamingStore.getState().streamId
        if (!useGatewayAuthStore.getState().accessToken || !currentStreamId) {
            console.warn("No active stream to abort");
            return;
        }

        // Clear timers, but DO NOT clear streamId or close websocket here yet
        if (abortTimeoutRef.current) {
            clearTimeout(abortTimeoutRef.current);
            abortTimeoutRef.current = null;
        }
        if (countdownIntervalRef.current) {
            clearInterval(countdownIntervalRef.current);
            countdownIntervalRef.current = null;
        }
        setStreamCountdown(null);

        try {
            const res = await invokeTool(accessToken, "abortinges", {
                arguments: { stream_id: currentStreamId },
            });
            toast.success(
                "[abort-success-abortStreaming]-Event",
                {
                    description: `result: \n${JSON.stringify(res,null,2)}`,
                    position: 'top-center'
                }
            );
            // for caching mode clearStreamId on abort success
            if(cachedTrigger){
                clearStreamId();
            }
            // Crucially: DO NOT clearStreamId or close websocket here for caching mode disabled case
            // Wait for final 'post_abort' event on websocket to cleanup
        } catch (err: any) {
            toast.error(
                "[abort-error-abortStreaming]-Event",
                {
                    description: `error: \n${JSON.stringify(err?.message || err ,null,2)}`,
                    position: 'top-center'
                }
            );
        }
    };


    // Login gateway & streaming hub on mount
    useEffect(() => {
        // login to mcp_server via gateway
        login('admin@example.com', 'ChangeThisSecurePassword123!');
        // login('user@example.com', 'testpassword');

        // login to streaming-hub for /ws websocket connection establishment
        loginToStreamingHub()
    }, []);

    // listing tools , whoami and check ping and add tool invoking
    useEffect(() => {
        if (!accessToken) return;
        (async () => {
            await whoami(accessToken);
            await listTools(accessToken);
            await invokeTool(accessToken, "ping");
            await invokeTool(accessToken, "add", { arguments: { a: 2, b: 3 } });
        })();
    }, [accessToken]);

    // Keep websocket connected when clientId, token, streamId, or assessmentType changes
    useEffect(() => {
        if (clientId && token && streamId) {
        connectWebSocket();
        }

        return () => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
        }
        if (abortController) {
            abortController.abort();
            setAbortController(null);
        }
        setWebsocketActive(false);
        };
    }, [clientId, token, streamId, assessmentType]);
 
   

    // NOTE- this effect triggers before the calling of abortStreaming
    // 📌 Case: Caching-Mode enabled 
    // WS connection and abortController cut off after all pending txns are done, streamCountdown resets to null and caching enabled
    useEffect(() => {
        if (cachingEnabled && pendingTxnAnalysisCount === 0 && streamCountdown === null) {
        console.log(
            "✅ [Caching-Enabled-trigger-Auto-close]: No pending txns + countdown expired"
        );
        // 📌 NOTE- Dont call clearStreamId() here as it will set streamId zustand state to null
        // and then abortStreaming will not be able to invoke abortinges 
        // instead clearStreamId inside abortStreaming func after abortinges success       
        const controller = useStreamingStore.getState().abortController;
        console.log(`[Caching-Enabled-triggered] Aborting websocket connection:`, controller);

        if (controller) {
            controller.abort();
            setAbortController(null);
        }
        if (websocketRef.current) {
            closeReasonRef.current = "[Caching-Enabled-Trigger]-websocketRef.close()"
            websocketRef.current.close(1000, closeReasonRef.current);
            websocketRef.current = null;
        }
        setWebsocketActive(false);
        }
    }, [cachingEnabled, pendingTxnAnalysisCount, streamCountdown]);


    // Logging pendingtxn analysis and caching enabled for debug
    useEffect(() => {
        toast.info(
            "[pending-txn-analysis-count]-Event",
            {
                description: `Pending: ${pendingTxnAnalysisCount}`,
                position: 'top-center'
            }
        );
    }, [pendingTxnAnalysisCount]);
    useEffect(() => {
        if (cachingEnabled) {
            toast.info(
                "Quick Assessment Mode is active.",
                {
                    position: 'top-center'
                }
            );
        } else {
            toast.info(
                "Full Assessment Mode is active.",
                {
                    position: 'top-center'
                }
            );
        }
    }, [cachingEnabled]);

    // hide initialization progress bar after 1.5s
    useEffect(() => {
    if (progressPercent === 100) {
        const timeout = setTimeout(() => {
        setHideProgressBar(true);
        }, 1500);
        return () => clearTimeout(timeout);
    } else {
        setHideProgressBar(false);
    }
    }, [progressPercent]);


    // currentAppRoute useEffect
    useEffect(()=>{
        console.log(`Current-App-Route: ${currentAppRoute}`)
        setCurrentAppRouteLocal(currentAppRoute);
    },[currentAppRoute])

    return (
        <React.Fragment>
            <Toaster/>
            <SidebarProvider open={openAppBar} onOpenChange={setOpenAppBar}>
                {/* never smaller than 1600px and mx-auto does not stretch past 1920px and center with max-w-[1920px] */}
                <div className="flex min-h-screen min-w-[1600px] max-w-[1920px] flex-col md:flex-row lg:gap-4 bg-background transition-all duration-200 ease-in-out">
                    <AppSidebar/>
                    {/* main content never streches wider than 2xl screen size and always centers max-w-screen-2xl mx-auto and h-[700px] min-h-screen ensures 700px tall but always streches if screen is taller */}
                    <main className="flex-1 overflow-y-auto p-2 md:p-4 lg:p-8 h-[700px] min-h-screen">
                        {
                            currentAppRoute === 'dashboard' ? (
                                <JsentrixDashboard
                                    assessmentOptions={assessmentOptions}
                                    assessmentType={assessmentType}
                                    setAssessmentType={setAssessmentType}
                                    cachingEnabled={cachingEnabled}
                                    setCachingEnabled={setCachingEnabled}
                                    resetSystem={resetSystem}
                                    hideProgressBar={hideProgressBar}
                                    progressPercent={progressPercent}
                                    loginGateway={loginGateway}
                                    whoamiAccess={whoamiAccess}
                                    toolActive={toolActive}
                                    websocketActive={websocketActive}
                                    streamId={streamId}
                                    toolsLoading={toolsLoading}
                                    toolsError={toolsError}
                                    tools={tools?.tools}
                                    availableTools={availableTools}
                                    toolId={toolId}
                                    setToolId={setToolId}
                                    startStreamingWithDuration={startStreamingWithDuration}
                                    abortStreaming={abortStreaming}
                                    intakeLogs={intakeLogs}
                                    assessmentLogs={assessmentLogs}
                                    actionLogs={actionLogs}
                                    globalLogs={globalLogs}
                                    setIntakeLogs={setIntakeLogs}
                                    setAssessmentLogs={setAssessmentLogs}
                                    setActionLogs={setActionLogs}
                                    setGlobalLogs={setGlobalLogs}
                                />
                            ) :
                            currentAppRoute === 'analytics' ? (
                                // 🎈 two split chat rag interface with ability to provide feedback and upd on the already stored prior events in qdrant, fetch ND txn or tnx forwarded by judge agent
                                <>Analytics Component 🚧 JSentrix v2.0</>
                            ) :
                            currentAppRoute === 'settings' ? (
                                // 🎈 This component shud only be visible to the super admin not other users shud have interface to add , edit lower user role, email and permission also shud show existing user login time, duration , currently logged in or not for superadmin
                                <>Settings Component 🚧 JSentrix v2.0</>
                            ) :
                            null
                        }    
                    </main>
                </div>
            </SidebarProvider>
        </React.Fragment>
        
    );
});