// custom-components/AppSidebar.tsx
'use client';

import React, { useEffect, useState } from 'react';
import { BetweenHorizontalEnd, BetweenHorizontalStart, LayoutDashboard, Cog, LucideProps, BadgeInfo, SquareCode, FileChartLine, Moon, Sun } from "lucide-react"

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar"

import sidebarAnimation from '../assets/sidebar-animation.gif';
import { Separator } from "@/components/ui/separator";
import { AppRoute, useAppThemeStore, useRouterStore, useStreamingStore } from "@/shared/store";
import { DialogInfo } from './DialogInfo';
import Dropdown, { DropdownOption } from './Dropdown';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';

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
    title: "Docs",
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
  const streamId = useStreamingStore((state)=>state.streamId);
  
  const { open: isSidebarOpen } = useSidebar();

  const appThemeType = useAppThemeStore(state => state.appThemeType);
  const setAppThemeType = useAppThemeStore(state => state.setAppThemeType);
  const darkModeEnabled = useAppThemeStore(state => state.darkModeEnabled);
  const setDarkModeEnabled = useAppThemeStore(state => state.setDarkModeEnabled);

  const { currentRoute, navigate } = useRouterStore();
  // State to track which Help dialog is open
  const [openDialog, setOpenDialog] = useState<"Docs" | "Contact" | null>(null);
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
        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel>
              <div className="flex gap-2 items-center">
                  <img src={sidebarAnimation} className="h-10 w-10 sidebar-gif"  alt="https://www.flaticon.com/free-animated-icons/commercial-transaction" title="Commercial transaction animated icons created by Freepik - Flaticon"/>
                  JSentrix GPL-3.0 license
              </div>
            </SidebarGroupLabel>
            <Separator className="w-80 my-4" />
            {/* Main Menu Items Section */}
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
          </SidebarGroup>

          <SidebarGroup>
            <SidebarGroupLabel>
              <div className='flex justify-between items-center w-full'>
                <span>
                  Theme
                </span>
                <div className='flex items-center gap-2'>
                  {
                    darkModeEnabled ?
                    <Moon className='h-4 w-4' /> :
                    <Sun  className='h-4 w-4' />
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
                    <SidebarMenuButton disabled={!!streamId || false} onClick={() => setOpenDialog(item.title as "Docs" | "Contact")}>    
                      <item.icon />
                      <span>{item.title}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

        </SidebarContent>
      </Sidebar>
      
      {/* Docs Dialog */}
      <DialogInfo
        open={openDialog === "Docs"}
        onOpenChange={(open) => setOpenDialog(open ? "Docs" : null)}
        title="Documentation"
        description="All about JSentrix system."
        content={
          <>
            <p>This is the documentation section for JSentrix.</p>
            <ul className="list-disc list-inside text-sm text-muted-foreground">
              <li>Setup & Installation</li>
              <li>Agent API</li>
              <li>Usage with LangChain</li>
            </ul>
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
              <li>Email: support@jsentrix.dev</li>
              <li>Discord: #jsentrix-support</li>
            </ul>
          </>
        }
      />
    </React.Fragment>
  )
}