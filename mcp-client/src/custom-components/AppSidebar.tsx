// custom-components/AppSidebar.tsx
'use client';

import React, { useState } from 'react';
import { BetweenHorizontalEnd, BetweenHorizontalStart, LayoutDashboard, Cog, LucideProps, BadgeInfo, SquareCode, MessageCircleQuestion, FileChartLine } from "lucide-react"

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
import { AppRoute, useRouterStore } from "@/shared/store";
import { DialogInfo } from './DialogInfo';

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
] as const;

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
] as const;

export function CustomSidebarTrigger() {
  const { open, setOpen } = useSidebar();  // check your SidebarContext to ensure setOpen exists

  const handleClick = () => setOpen && setOpen(!open);

  return (
    <button
      type="button"
      onClick={handleClick}
      className="p-2 rounded hover:bg-accent transition"
      aria-label={open ? "Collapse sidebar" : "Expand sidebar"}
    >
      {open ? <BetweenHorizontalEnd size={20} /> : <BetweenHorizontalStart size={20} />}
    </button>
  );
}

export function AppSidebar() {
  const { currentRoute, navigate } = useRouterStore();
  // State to track which Help dialog is open
  const [openDialog, setOpenDialog] = useState<"Docs" | "Contact" | null>(null);
  return (
    <React.Fragment>
      <Sidebar collapsible="icon">
        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel>
              <div className="flex gap-2 items-center">
                  <img src={sidebarAnimation} className="h-10 w-10"  alt="https://www.flaticon.com/free-animated-icons/commercial-transaction" title="Commercial transaction animated icons created by Freepik - Flaticon"/>
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
                            asChild
                            isActive={isActive}
                            onClick={() => navigate(item.route)}
                          >
                            <button className="flex items-center gap-2 w-full text-left">
                              <item.icon />
                              <span>{item.title}</span>
                            </button>
                          </SidebarMenuButton>
                        </SidebarMenuItem>
                      );
                  })
                }
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

          {/* Help MenuItem Section */}
          <SidebarGroup>
            <Separator className="w-60 my-1" />
            <SidebarGroupLabel>
              <div className="flex gap-2 items-center">
                <MessageCircleQuestion className="h-4 w-4 fill"/>
                Help
              </div>
            </SidebarGroupLabel>
            <Separator className="w-60 my-1" />
            <SidebarGroupContent>
              <SidebarMenu>
                {HelpMenuitems.map((item: HelpMenuItemInterface) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton asChild>
                      {
                        <button 
                          className="flex items-center gap-2 w-full text-left"
                          onClick={() => setOpenDialog(item.title as "Docs" | "Contact")}
                        >
                          <item.icon />
                          <span>{item.title}</span>
                        </button>
                      }
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