'use client';

// src/routes/JsentrixDashboard.tsx
import React from 'react';
import {
  ResizablePanel,
  ResizablePanelGroup,
  ResizableHandle,
} from "@/components/ui/resizable";
import { BadgeInfo, Hammer, BadgeX, RefreshCcwDot } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Switch } from '@/components/ui/switch';
import { Separator } from "@/components/ui/separator"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { Progress } from "@/components/ui/progress";
import VitalsPanel from '@/custom-components/VitalsPanel';
import ToolTabsPanel from '@/custom-components/ToolTabsPanel';
import { SkeletonToolTabsPanel } from '@/custom-components/ToolTabsPanelSkelton';
import LogTerminal from '@/custom-components/LogTerminal';
import { CustomSidebarTrigger } from '@/custom-components/AppSidebar';
import Dropdown from '@/custom-components/Dropdown';
import { Tool } from '@/custom-components/RootWrapper';

interface JsentrixDashboardProps {
  assessmentOptions: any[];
  assessmentType: string;
  setAssessmentType: (v: any) => void;
  cachingEnabled: boolean;
  setCachingEnabled: (v: boolean) => void;
  resetSystem: (terminalLogs: boolean) => void;
  hideProgressBar: boolean;
  progressPercent: number;
  loginGateway: boolean;
  whoamiAccess: boolean;
  toolActive: boolean;
  websocketActive: boolean;
  streamId: string | null;
  toolsLoading: boolean;
  toolsError: boolean;
  tools: Tool[] | undefined;
  availableTools: Tool[];
  toolId: string;
  setToolId: (v: string) => void;
  startStreamingWithDuration: (duration: number | "infinite") => Promise<void>;
  abortStreaming: (cachedTrigger?: boolean) => Promise<void>;
  intakeLogs: string[];
  assessmentLogs: string[];
  actionLogs: string[];
  globalLogs: string[];
  setIntakeLogs: (logs: string[]) => void;
  setAssessmentLogs: (logs: string[]) => void;
  setActionLogs: (logs: string[]) => void;
  setGlobalLogs: (logs: string[]) => void;
}

const JsentrixDashboard: React.FC<JsentrixDashboardProps> = ({
  assessmentOptions,
  assessmentType,
  setAssessmentType,
  cachingEnabled,
  setCachingEnabled,
  resetSystem,
  hideProgressBar,
  progressPercent,
  loginGateway,
  whoamiAccess,
  toolActive,
  websocketActive,
  streamId,
  toolsLoading,
  toolsError,
  tools,
  availableTools,
  toolId,
  setToolId,
  startStreamingWithDuration,
  abortStreaming,
  intakeLogs,
  assessmentLogs,
  actionLogs,
  globalLogs,
  setIntakeLogs,
  setAssessmentLogs,
  setActionLogs,
  setGlobalLogs,
}) => {
  return (
    <div className="flex-1 h-full">
        {/* Outermost: vertical split */}
        <ResizablePanelGroup direction="vertical">

            {/* Top-Panel: Left: Vitals, tools, configs section and Right: Log Terminal Section */}
            <ResizablePanel minSize={40} defaultSize={70}> {/* 70%+ space */}
                
                <ResizablePanelGroup direction="horizontal">
                    
                    {/* Vitals, tools, configs section */}
                    <ResizablePanel minSize={25} defaultSize={25}>
                        {/* CoreConfigs = Assessment Mode + Memory Caching Enabled/Disabled + Reset System */}
                        <div className='mb-6 ml-3 mt-6'>
                            <div className="flex h-5 items-center space-x-4 text-sm">
                                <CustomSidebarTrigger disabled={!!streamId}/>
                                <div>
                                    <Dropdown
                                        label="Assessment Mode"
                                        options={assessmentOptions}
                                        value={assessmentType}
                                        onChange={(v) => setAssessmentType(v as "default" | "redistream")}
                                        disabled={!!streamId}
                                    />
                                </div>
                                <Separator orientation="vertical" />
                                <div className="flex items-center space-x-1">
                                    <Switch
                                        id="caching-toggle"
                                        checked={cachingEnabled}
                                        onCheckedChange={setCachingEnabled}
                                        disabled={!!streamId}
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
                                                <RefreshCcwDot className="w-5 h-5" />
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
                            <div className="w-100 ml-6 items-center transition-opacity duration-500 ease-in-out" style={{ opacity: hideProgressBar ? 0 : 1 }}>
                                <Progress value={progressPercent} />
                            </div>
                        </div>
                        {/* Dynamic System Vitals Section */}
                        <VitalsPanel
                            loginGateway={loginGateway}
                            whoamiAccess={whoamiAccess}
                            toolActive={toolActive}
                            websocketActive={websocketActive}
                            streamId={streamId}
                        />
                        <div className='flex ml-4 mr-2 items-center gap-5 mt-2'>
                            <Accordion
                                type="single"
                                collapsible
                                className="w-full"
                                defaultValue="item-1"
                                >
                                <AccordionItem value="item-1">
                                    <AccordionTrigger>
                                        <div className='flex items-center gap-2' style={{
                                            cursor: 'pointer'
                                        }}>
                                            <Hammer className='w-4 h-4'/>
                                            Available Tools
                                        </div>
                                    </AccordionTrigger>
                                    <AccordionContent className="flex flex-col gap-4 text-balance">
                                        {
                                            toolsLoading ? (
                                                <SkeletonToolTabsPanel />
                                            ) : toolsError ? (
                                                <div className="text-muted-foreground text-sm">
                                                    <div className="flex items-center gap-2 mt-2 text-base p-3 rounded-md bg-muted/80 border border-muted">
                                                        <BadgeX className="w-4 h-4 text-red-500" />
                                                        Failed to load tools. Please try again.
                                                    </div>
                                                </div>
                                            ) 
                                            : 
                                            (tools && availableTools?.length === 0) ?
                                            (
                                                <div className="text-muted-foreground text-sm">
                                                    <div className="flex items-center gap-2 mt-2 text-base p-3 rounded-md bg-muted/80 border border-muted">
                                                    <BadgeX className="w-4 h-4 text-red-500" />
                                                    No tools are available at the moment.
                                                    </div>
                                                </div>
                                            ) :
                                            (
                                                <ToolTabsPanel
                                                    tools={availableTools}
                                                    currentTool={toolId}
                                                    onToolChange={setToolId}
                                                    startStreaming={startStreamingWithDuration}
                                                    abortStreaming={abortStreaming}
                                                />
                                            )
                                        }
                                    </AccordionContent>
                                </AccordionItem>
                            </Accordion>
                        </div>
                        
                    </ResizablePanel>
                    
                    <ResizableHandle />

                    {/* Log section */}
                    <ResizablePanel minSize={68} maxSize={74} defaultSize={70}>
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
            <ResizablePanel minSize={10} defaultSize={10}>
                <div className="h-full w-full bg-muted p-4 flex items-center justify-center">
                    {/* 🎈 Add xy react flow visualizing intake, assessment, judge agent working and shud be 2 flows 1 for default a2a mode and the 2nd one for Async Redis Stream mode */}
                    {/* 🎈 The approach shud be the  new tool call ex- agentrace with payload as logs of all agents-intake, assessment, action that actually uses gemini llm/other relevant model under the hood recieves the payload agent based logs and then generates node strucutred data accordingly gives it back to the ui and then ui can generate visual graph with this node structured data from the tool via xy react flow  */}
                    {/* For example */}
                    <div className="h-full w-full flex flex-col items-center justify-center">
                    <h2 className="mb-2 text-lg font-semibold">Agent Flows</h2>
                    {/* <YourXYReactFlowComponent mode={assessmentType}/> */}
                    <div className="border border-dashed border-gray-400 h-full w-full flex items-center justify-center text-muted-foreground">
                        🚧 For Future JSentrix v2.0 XY Flow Visuals go here
                    </div>
                    </div>
                </div>
            </ResizablePanel>
        
        </ResizablePanelGroup>
        {/* End main vertical split */}
    </div>
  );
};

export default JsentrixDashboard;
