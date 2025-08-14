// custom-components/AppSidebar.tsx
'use client';

import React, { useEffect, useState } from 'react';
import { BetweenHorizontalEnd, BetweenHorizontalStart, LayoutDashboard, Cog, LucideProps, BadgeInfo, SquareCode, FileChartLine, Moon, Sun, ChevronsUpDown, LogOut, GitGraph, Scale, Copyright } from "lucide-react"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSubItem,
  useSidebar,
} from "@/components/ui/sidebar"

import indianFlag from '../assets/indian_flag.png';
import { Separator } from "@/components/ui/separator";
import { AppRoute, useAppThemeStore, useCurrentUserStore, useGatewayAuthStore, useRouterStore, useStreamingStore, useWsAuthStore } from "@/shared/store";
import { DialogInfo } from './DialogInfo';
import Dropdown, { DropdownOption } from './Dropdown';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import user1img from '../assets/user1_img.png';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import AccountSheet from './AccountSheet';
import { Badge } from '@/components/ui/badge';
import { stopTokenRotation } from '@/shared/tokenService';

interface CustomSidebarTriggerProps {
  disabled?: boolean;
}

interface MainMenuItemInterface {
  title: string;
  route: AppRoute;
  icon: React.ForwardRefExoticComponent<Omit<LucideProps, "ref"> & React.RefAttributes<SVGSVGElement>>;
}
// Main Menu items.
const MainMenuItems: MainMenuItemInterface[] = [
  {
    title: "Dashboard",
    route: "dashboard",
    icon: LayoutDashboard,
  },
  {
    title: "Analytics",
    route: "analytics",
    icon: FileChartLine,
  },
  {
    title: "Settings",
    route: "settings",
    icon: Cog,
  },
];

interface HelpMenuItemInterface {
  title: string;
  icon: React.ForwardRefExoticComponent<Omit<LucideProps, "ref"> & React.RefAttributes<SVGSVGElement>>;
}
// Help Menu items.
const HelpMenuitems: HelpMenuItemInterface[] = [
  {
    title: "Version Docs",
    icon: GitGraph,
  },
  {
    title: "Core Docs",
    icon: SquareCode,
  },
  {
    title: "Contact",
    icon: BadgeInfo,
  },
];

export function CustomSidebarTrigger({disabled}: CustomSidebarTriggerProps) {
  const { open, setOpen } = useSidebar();  // check your SidebarContext to ensure setOpen exists

  const handleClick = () => setOpen && setOpen(!open);

  return (
    <Button
      variant='outline'
      onClick={handleClick}
      aria-label={open ? "Collapse sidebar" : "Expand sidebar"}
      disabled={disabled || false}
    >
      {open ? <BetweenHorizontalEnd size={20} /> : <BetweenHorizontalStart size={20} />}
    </Button>
  );
}

export function AppSidebar() {
  // 📌 Intentionally throw error to test ErrorBoundary
  // throw new Error("Test error from AppSidebar");
  const todayDate = new Date();
  const streamId = useStreamingStore((state)=>state.streamId);
  
  const { open: isSidebarOpen } = useSidebar();

  const appThemeType = useAppThemeStore(state => state.appThemeType);
  const setAppThemeType = useAppThemeStore(state => state.setAppThemeType);
  const darkModeEnabled = useAppThemeStore(state => state.darkModeEnabled);
  const setDarkModeEnabled = useAppThemeStore(state => state.setDarkModeEnabled);

  const { currentRoute, navigate } = useRouterStore();

  const currentUser = useCurrentUserStore(state => state.user);

  const clearUser = useCurrentUserStore(state => state.clearUser);
  const clearGatewayTokens = useGatewayAuthStore(state=>state.clearTokens);
  const clearStreamingToken = useWsAuthStore(state=>state.clearAuth);
  const clearStreamId = useStreamingStore((state) => state.clearStreamId);

  // State to track which Help dialog is open
  const [openDialog, setOpenDialog] = useState<"Core Docs" | "Version Docs" | "Contact" | null>(null);
  const themeOptions: DropdownOption[] = [
      { label: "Default", value: "default" },
      { label: "Indie", value: "indie" },
  ];
  // 💡 Apply or remove 'dark' class from <html> when darkModeEnabled changes
  useEffect(() => {
    if (darkModeEnabled) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    // Apply indie theme as a class
    if (appThemeType === "indie") {
      document.documentElement.classList.add("theme-indie");
    } else {
      document.documentElement.classList.remove("theme-indie");
    }
  }, [darkModeEnabled, appThemeType]);

  return (
    <React.Fragment>
      <Sidebar collapsible="icon">
        <SidebarContent className='overflow-y-auto'>

          {/* AppCopyright author + Main Menu Items Section */}
          <SidebarGroup>
            <SidebarGroupLabel>
              <div className="flex p-5 gap-2 mt-5 md:mt-2">
                  <img src={indianFlag} className="h-10 w-10 sidebar-gif"  alt="https://www.flaticon.com/free-icons/india" title="India icons created by Waveshade_Studios - Flaticon"/>
                  <div className='flex flex-col items-center mt-1'>
                      <div className='flex'>
                        <Copyright className='h-4 w-4' />
                        <span>2025-{todayDate.getFullYear()}</span>
                      </div>
                      <span> Jasmeet Singh Bali </span>
                  </div> 
              </div>
            </SidebarGroupLabel>
            <Separator className="w-80 my-4" />
            <SidebarGroupContent>
              <SidebarMenu>
                {
                  MainMenuItems.map((item: MainMenuItemInterface) => {
                      const isActive = currentRoute === item.route;

                      return (
                        <SidebarMenuItem 
                          key={item.title}
                        >
                          <SidebarMenuButton
                            isActive={isActive}
                            onClick={() => navigate(item.route)}
                            disabled={!!streamId || false}
                            className='flex items-center gap-2 md:gap-3 lg:gap-4'
                          >
                            <item.icon className='w-4 h-4 md:w-5 md:h-5 lg:w-6 lg:h-6'/>
                            <span className='text-sm md:text-base lg:text-lg'>{item.title}</span> 
                          </SidebarMenuButton>
                        </SidebarMenuItem>
                      );
                  })
                }
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
          
          {/* Theme Section */}
          <SidebarGroup>
            <SidebarGroupLabel>
              <div className='flex justify-between items-center w-full text-sm md:text-base lg:text-lg'>
                <span>
                  Theme
                </span>
                <div className='flex items-center gap-2'>
                  {
                    darkModeEnabled ?
                    <Moon className='h-4 w-4 md:h-5 md:w-5 lg:h-6 lg:w-6' /> :
                    <Sun  className='h-4 w-4 md:h-5 md:w-5 lg:h-6 lg:w-6' />
                  }
                  <Switch
                      id="app-light-dark-theme-toggle"
                      checked={darkModeEnabled}
                      onCheckedChange={setDarkModeEnabled}
                  />
                </div>
                
              </div>
            </SidebarGroupLabel>
            <Separator className="w-6- my-1"/>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  {
                    isSidebarOpen && (
                      <div className='flex items-center ml-4 mt-2'>
                        <Dropdown
                          label="JSentrix Theme"
                          options={themeOptions}
                          value={appThemeType}
                          onChange={(v) => setAppThemeType(v as "default" | "indie")}
                        />
                      </div>
                    )
                  }
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

          {/* Help MenuItem Section */}
          <SidebarGroup>
            <SidebarGroupLabel>
                Help
            </SidebarGroupLabel>
            <Separator className="w-60 my-1" />
            <SidebarGroupContent>
              <SidebarMenu>
                {HelpMenuitems.map((item: HelpMenuItemInterface) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton disabled={!!streamId || false} onClick={() => setOpenDialog(item.title as "Core Docs" | "Version Docs" | "Contact")}>    
                      <item.icon className='w-4 h-4 md:w-5 md:h-5 lg:w-6 lg:h-6'/>
                      <span className='text-sm md:text-base lg:text-lg'>{item.title}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

        </SidebarContent>
        
        {/* License + User logged in username and email + popup menu  */}
        <SidebarFooter>
          {
            isSidebarOpen &&
            <Badge
              variant={"secondary"}
              className={"bg-blue-800 text-white dark:bg-blue-600"}
            >
              <Scale className='h-4 w-4' />
              GPL-3.0 license
            </Badge>
          }
          <Separator className="w-60 my-1" />
          <SidebarMenu>
            <SidebarMenuItem>
              <Popover modal={false}>
                <PopoverTrigger asChild>
                  <SidebarMenuButton
                    disabled={!!streamId || false} 
                    className="w-full flex items-center gap-2 px-2">
                    <Avatar className="h-6 w-6">
                      <AvatarImage src={user1img} />
                      <AvatarFallback>CN</AvatarFallback>
                    </Avatar>
                    <div className="flex flex-col">
                      <span className="text-sm" >{currentUser?.full_name}</span>
                      <span className="text-xs text-muted-foreground">{currentUser?.email}</span>
                    </div>
                    <ChevronsUpDown className="ml-auto" />
                  </SidebarMenuButton>
                </PopoverTrigger>
                <PopoverContent
                  side="right"
                >
                    <SidebarMenuSubItem className="w-full flex items-center gap-2 px-2">
                      <Avatar className="h-6 w-6">
                        <AvatarImage src={user1img} />
                        <AvatarFallback>CN</AvatarFallback>
                      </Avatar>
                      <div className="flex flex-col gap-0.5">
                        <span>{currentUser?.full_name}</span>
                        <span className="text-xs text-muted-foreground">{currentUser?.email}</span>
                      </div>
                    </SidebarMenuSubItem>
                    <Separator className="w-80 my-1" />
                      <AccountSheet username={currentUser.full_name} email={currentUser.email} roles={currentUser?.roles} />
                    <Separator className="w-80 my-1" />
                    <SidebarGroupContent>
                    <SidebarMenu>
                      {
                        MainMenuItems.map((item: MainMenuItemInterface) => {
                            const isActive = currentRoute === item.route;

                            return (
                              <SidebarMenuItem 
                                key={item.title}
                              >
                                <SidebarMenuButton
                                  isActive={isActive}
                                  onClick={() => navigate(item.route)}
                                  disabled={!!streamId || false}
                                >
                                  <item.icon />
                                  <span>{item.title}</span> 
                                </SidebarMenuButton>
                              </SidebarMenuItem>
                            );
                        })
                      }
                    </SidebarMenu>
                  </SidebarGroupContent>
                  <Separator className="w-80 my-1" />
                  <SidebarMenuButton onClick={()=>{
                    
                    // core token access reset
                    clearGatewayTokens();
                    clearStreamingToken();
                    clearStreamId();

                    // stop token rotation interval
                    stopTokenRotation();

                    // core theme reset
                    setAppThemeType("default");
                    setDarkModeEnabled(false);

                    // core user and hard reset electron reload
                    setTimeout(() => {
                      clearUser();
                      window?.Electron?.ipcRenderer?.invoke('app:hard-reload');
                    }, 800);

                  }}>
                      <LogOut/>
                      <span>Log out</span>
                  </SidebarMenuButton>

                </PopoverContent>
              </Popover>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarFooter>

      </Sidebar>
      
      {/* Docs Dialog */}
      <DialogInfo
        open={openDialog === "Core Docs"}
        onOpenChange={(open) => setOpenDialog(open ? "Core Docs" : null)}
        title="JSentrix Core Documentation"
        description="Comprehensive guide to JSentrix system architecture, features, and operational modes."
        content={
          <>
            <section>
              <p>
                Welcome to the core documentation for <strong>JSentrix</strong>.  
                This section provides an in-depth overview of the system’s backend 
                architecture, supported agent modes, and major features from 
                <strong>v1.0.0</strong> onwards.
              </p>
            </section>

            <section>
              <h2>Core Backend Components</h2>
              <p>
                The JSentrix system consists of several modular backend services.  
                Each service exposes its own API documentation via Swagger UI:
              </p>
              <ol className="list-decimal list-inside text-sm text-muted-foreground space-y-1">
                <li>
                  <strong>MCP Server</strong> — Access Swagger docs at  
                  <code> http://localhost:9001/docs </code>
                </li>
                <li>
                  <strong>Gateway Service</strong> — Access Swagger docs at  
                  <code> http://localhost:8080/docs </code>
                </li>
                <li>
                  <strong>Streaming Hub</strong> — Access Swagger docs at  
                  <code> http://localhost/swagger </code>
                </li>
              </ol>
            </section>

            <section>
              <h2>Agent Modes & Graph-Flows</h2>
              <p>
                JSentrix agents can operate in multiple modes depending on caching 
                and streaming preferences:
              </p>
              <ol className="list-decimal list-inside text-sm text-muted-foreground space-y-1">
                <li>
                  <strong>Default Mode — A2A (Caching Disabled):</strong>  
                  Full Assessment Mode for thorough, fresh evaluations.
                </li>
                <li>
                  <strong>Default Mode — A2A (Caching Enabled):</strong>  
                  Quick Assessment Mode for faster responses using cached insights.
                </li>
                <li>
                  <strong>Async Redis Streams (Caching Disabled):</strong>  
                  Async stream txn's processing events without prior cache.
                </li>
                <li>
                  <strong>Async Redis Streams (Caching Enabled):</strong>  
                  Async stream txn's processing with stored event history.
                </li>
              </ol>
            </section>

            <section>
              <h2>Core Features</h2>
              <article>
                <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1">
                  <li>
                    <strong>Dedicated Triage Agents:</strong> Specialized agents for 
                    intake, assessment, and action — each operating within its own 
                    dedicated graph stream.
                  </li>
                  <li>
                    <strong>Configurable UI Controls:</strong> Adjust data sources, 
                    operation modes, stream settings, and ingestion durations directly 
                    from the UI.
                  </li>
                  <li>
                    <strong>Enhanced RAG Flows:</strong> Custom-tweaked LangChain and 
                    LlamaIndex retrievers with re-ranking, scoring, and decay 
                    mechanisms for robust retrieval-augmented generation.
                  </li>
                  <li>
                    <strong>Stream Lifecycle Management:</strong> Automatic stream 
                    timeouts post-analysis, with full end-to-end WebSocket connection 
                    handling.
                  </li>
                  <li>
                    <strong>Scalable Streaming Infrastructure:</strong> Multiple 
                    dockerized streaming hub instances for efficient real-time event 
                    dispatching and broadcasting to connected MCP clients.
                  </li>
                  <li>
                    <strong>Group Stream Broadcasting:</strong> Event broadcasting to 
                    all MCP clients subscribed under the same <code>stream-id</code>.
                  </li>
                  <li>
                    <strong>Event History Caching:</strong> Stores prior assessed 
                    events for comparative analysis in caching mode for future assessment txn's streams.
                  </li>
                </ul>
              </article>
            </section>
          </>
        }
      />


      {/* Contact Dialog */}
      <DialogInfo
        open={openDialog === "Contact"}
        onOpenChange={(open) => setOpenDialog(open ? "Contact" : null)}
        title="Contact Support"
        description="Reach out to the JSentrix team."
        content={
          <>
            <p>You can contact us via:</p>
            <ul className="list-disc list-inside text-sm text-muted-foreground">
              <li>Github: <a style={{
                textDecoration: 'underline',
                color: 'HighlightText'
              }} href='https://github.com/JasmeetSinghBali/JSentrix'>JSentrix Github GPL-3.0 license Source Code</a></li>
              <li>Email:<strong> jasmeetbali.dev.2021@gmail.com </strong></li>
            </ul>
          </>
        }
      />

      {/* 🎈delete account placeholder sheet confirmation modal shud be reusable component setup for future instead of this */}
      <Sheet>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Are you absolutely sure?</SheetTitle>
            <SheetDescription>
              This action cannot be undone. This will permanently delete your account
              and remove your data from our servers.
            </SheetDescription>
          </SheetHeader>
        </SheetContent>
      </Sheet>

    </React.Fragment>
  )
}