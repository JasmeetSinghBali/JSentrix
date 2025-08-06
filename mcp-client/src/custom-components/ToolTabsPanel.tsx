'use client'

import React, { useState, useEffect } from "react";
import {
  useGatewayAuthStore,
  useStreamingStore,
} from "@/shared/store";
import Dropdown, { DropdownOption } from "./Dropdown";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Hourglass, SquareTerminal, Wand2 } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { toast } from "sonner"

import hammerGif from '../assets/loading-tool-animation.gif';

export interface Tool {
  name: string;
  description: string;
  inputSchema?: {
    properties?: Record<string, { title: string; type: string }>;
    required?: string[];
  };
}

interface ToolTabsPanelProps {
  tools: Tool[];
  currentTool: string;
  onToolChange: (tool: string) => void;

  // 📌 handlers and props to delegate stream control to RootWrapper
  startStreaming: (duration: number | "infinite") => Promise<void>;
  abortStreaming: () => Promise<void>;
}

const HIDE_INPUTS_FOR = ["streaminges", "abortinges"];
const streamDurationOptions: DropdownOption[] = [
  { label: "2 minutes", value: "120" },
  { label: "5 minutes", value: "300" },
  { label: "Indefinite", value: "infinite" },
];

// Helper function to format seconds into mm:ss
const formatSeconds = (seconds: number) => {
  const m = Math.floor(seconds / 60).toString().padStart(2, "0");
  const s = (seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
};

const ToolTabsPanel: React.FC<ToolTabsPanelProps> = ({
  tools,
  currentTool,
  onToolChange,
  startStreaming,
  abortStreaming,
}) => {
  const accessToken = useGatewayAuthStore((state)=>state.accessToken);
  const streamId = useStreamingStore((state)=>state.streamId);
  const streamCountdown = useStreamingStore((state)=>state.streamCountdown);

  const [inputValues, setInputValues] = useState<Record<string, Record<string, any>>>({});
  const [streamDuration, setStreamDuration] = useState<number | "infinite">(120);

  const [loadingTools, setLoadingTools] = useState<Record<string, boolean>>({});


  const handleInputChange = (toolName: string, key: string, value: any) => {
    setInputValues((prev) => ({
      ...prev,
      [toolName]: {
        ...prev[toolName],
        [key]: value,
      },
    }));
  };

  // handleInvoke to delegate streaming control
  const handleInvoke = async (toolName: string) => {
    console.log("Invoking tool:", toolName);
    if (!accessToken) {
      toast.warning(
        "No gateway access token set.",
        {
          position: 'top-center'
        }
      );
      return;
    }

    setLoadingTools((prev) => ({ ...prev, [toolName]: true }));

    try{
      if (toolName === "streaminges") {
        // Delegate starting stream to RootWrapper's handler
        await startStreaming(streamDuration);
        return;
      }

      if (toolName === "abortinges") {
        if (!streamId) {
          toast.warning(
            "No streamId available for aborting.",
            {
              position: 'top-center'
            }
          );
          return;
        }

        // Delegate abort streaming to RootWrapper's handler
        await abortStreaming();
        // Do NOT clearStreamId here; RootWrapper handles that when final post-abort event arrives.
        return;
      }

      // For Generic other tools invoke normally from tooltabspanel with stored inputs
      const inputs = inputValues[toolName] || {};
      const params = { arguments: inputs };

      // 🎈 cud be shifted to "use server" seprate data fetch component and similarly for other fetch calls inside other "use client" components
      const response = await fetch(`http://localhost:8080/api/v1/tools/${toolName}/invoke`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(params),
      });
      if(!response.ok){
        // Throw raw response
        const errorBody = await response.text();
        throw new Error(errorBody || `HTTP error ${response.status}`);
      }
      const result = await response.json();
      toast.success(
        `[tool-invoked-success]-${toolName}`,
        {
          description: `result: \n${JSON.stringify(result,null,2)}`,
          position: 'top-center',
        }
      );
    } catch (error: any) {
      toast.error(
        `[tool-invocation-error]-${toolName}`,
        {
          description: `error: \n${JSON.stringify(error?.message || error ,null,2)}`,
          position: 'top-center',
        } 
      );
    } finally {
      setLoadingTools((prev) => ({ ...prev, [toolName]: false }));
    }
  };
  

  // Clear stream duration from UI when streamId disappears
  useEffect(() => {
    if (!streamId) {
      setStreamDuration(120);
    }
  }, [streamId]);

  // misc: logs debug 
  useEffect(()=>{
    console.log("[Inside-ToolTabsPanel] streamCountdown updated:", streamCountdown);
  },[streamCountdown])


  return (
    <Tabs value={currentTool} onValueChange={onToolChange} className="w-full">
      <TabsList className="w-full justify-start gap-2 flex-wrap">
        {tools.map((tool: Tool) => (
          <TabsTrigger
            key={tool.name}
            value={tool.name}
            className={
              cn(
                "px-3 py-1 text-xs", 
                currentTool === tool.name && "bg-muted border",
              )
            }
            style={{
              cursor: 'pointer'
            }}
          >
            <Wand2 className="w-3 h-3 mr-1" />
            {tool.name}
          </TabsTrigger>
        ))}
      </TabsList>

      {tools.map((tool: Tool) => {
        const properties = tool.inputSchema?.properties ?? {};
        const required = tool.inputSchema?.required ?? [];
        const hasInputs = Object.keys(properties).length > 0;

        return (
          <TabsContent key={tool.name} value={tool.name} className="w-full mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <SquareTerminal className="w-4 h-4" />
                  {tool.name}
                </CardTitle>
                <CardDescription className="text-sm text-muted-foreground">
                  {tool.description || "No description available."}
                </CardDescription>
              </CardHeader>

              {hasInputs && !HIDE_INPUTS_FOR.includes(tool.name) && (
                <CardContent className="grid gap-4">
                  {Object.entries(properties).map(([key, schema]) => (
                    <div className="grid gap-2" key={key}>
                      <Label htmlFor={`${tool.name}-${key}`}>
                        {schema.title} {required.includes(key) && "*"}
                      </Label>
                      <Input
                        id={`${tool.name}-${key}`}
                        type={schema.type === "integer" ? "number" : "text"}
                        placeholder={`Enter ${schema.title}`}
                        value={inputValues[tool.name]?.[key] ?? ""}
                        onChange={(e) =>
                          handleInputChange(
                            tool.name,
                            key,
                            schema.type === "integer"
                              ? parseInt(e.target.value || "0", 10)
                              : e.target.value
                          )
                        }
                      />
                    </div>
                  ))}
                </CardContent>
              )}

              {(!hasInputs || HIDE_INPUTS_FOR.includes(tool.name)) && (
                <CardContent className="text-muted-foreground text-sm">No input required for this tool.</CardContent>
              )}

              {/* Show stream duration selector only for streaminges */}
              {(tool.name === "streaminges" && typeof streamCountdown !== 'number' ) && (
                <div className="ml-6 mb-2">
                  <Dropdown
                    label="Stream duration"
                    options={streamDurationOptions}
                    value={streamDuration.toString()}
                    onChange={(val: string) => {
                      const parsed = val === "infinite" ? "infinite" : Number(val);
                      setStreamDuration(parsed);
                    }}
                  />
                </div>
              )}

              {/* Show countdown timer from RootWrapper */}
              {tool.name === "streaminges" && typeof streamCountdown === 'number' && (
                <div className='text-muted-foreground text-sm'>
                    <div className="flex flex-col items-center gap-2 mt-2 text-base p-3 rounded-md bg-muted/80 border border-muted">
                        <div className='flex items-center gap-2 font-mono text-yellow-700'>
                            <Hourglass className='w-4 h-4'/>
                            Streaming stops in: {formatSeconds(streamCountdown)}
                        </div>
                        <div className="mt-1 text-xs text-muted-foreground leading-snug">
                            <b>NOTE:</b> New transactions are <span className="text-destructive">no longer ingested</span> after the stream ends.<br />
                            However, post-abort-stream analysis events (already in progress <br/>before abort) may still arrive until the <b>final post-abort event</b> <br/> is emitted by <code>mcp server</code>.
                        </div>
                    </div>
                </div>
              )}

              {/* Show current streamId for abortinges */}
              {tool.name === "abortinges" && streamId && (
                <div className="mb-4 ml-6 text-sm text-red-600 font-semibold">
                  Active stream: {streamId}
                </div>
              )}

              <CardFooter>
                <Button
                  onClick={() => handleInvoke(tool.name)}
                  disabled={
                    loadingTools[tool.name] ||
                    (!accessToken) || 
                    (tool.name === "abortinges" && !streamId) ||
                    (tool.name === "streaminges" && !!streamId)
                    }
                  className={cn('hammer-cursor')}
                  variant={
                    (
                      loadingTools[tool.name] ||
                      (!accessToken) || 
                      (tool.name === "abortinges" && !streamId) ||
                      (tool.name === "streaminges" && !!streamId)
                    ) ? 'ghost' : 'outline'
                  }
                >
                  {
                    loadingTools[tool.name] ? (
                      <span className="flex items-center gap-2 text-foreground">
                        <svg
                          className="animate-spin h-4 w-4 mr-1"
                          xmlns="http://www.w3.org/2000/svg"
                          fill="none"
                          viewBox="0 0 24 24"
                        >
                          <circle
                            className="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="4"
                          ></circle>
                          <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8v8z"
                          ></path>
                        </svg>
                        Invoking...
                      </span>
                    ) :
                    tool.name === "abortinges" && !streamId ? 
                    "No active stream" 
                    : tool.name === "streaminges" && !!streamId? 
                    "Stream already active" 
                    : "Invoke Tool"}
                </Button>
              </CardFooter>
            </Card>
          </TabsContent>
        );
      })}
    </Tabs>
  );
};

export default ToolTabsPanel;
