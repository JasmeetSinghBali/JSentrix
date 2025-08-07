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
  const clearAccessToken = useGatewayAuthStore(state=>state.clearAccessToken);
  const clearRefreshToken = useGatewayAuthStore(state=>state.clearRefreshToken);
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
                    clearAccessToken();
                    clearRefreshToken();
                    clearStreamingToken();
                    clearStreamId();

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
      {/* 🎈 for docs expandable accordion like seprate sections with links to the appropriate sphinx/swagger docs shud be mentioned reff to Readme.md core 
      also if possible giphy or demo videos of every flow like default + caching, default+non-caching, asyncredis+caching, 
      which section does what, sitemap section  */}
      <DialogInfo
        open={openDialog === "Core Docs"}
        onOpenChange={(open) => setOpenDialog(open ? "Core Docs" : null)}
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
            <p>
              What is Lorem Ipsum?
              Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum.

              Why do we use it?
              It is a long established fact that a reader will be distracted by the readable content of a page when looking at its layout. The point of using Lorem Ipsum is that it has a more-or-less normal distribution of letters, as opposed to using 'Content here, content here', making it look like readable English. Many desktop publishing packages and web page editors now use Lorem Ipsum as their default model text, and a search for 'lorem ipsum' will uncover many web sites still in their infancy. Various versions have evolved over the years, sometimes by accident, sometimes on purpose (injected humour and the like).


              Where does it come from?
              Contrary to popular belief, Lorem Ipsum is not simply random text. It has roots in a piece of classical Latin literature from 45 BC, making it over 2000 years old. Richard McClintock, a Latin professor at Hampden-Sydney College in Virginia, looked up one of the more obscure Latin words, consectetur, from a Lorem Ipsum passage, and going through the cites of the word in classical literature, discovered the undoubtable source. Lorem Ipsum comes from sections 1.10.32 and 1.10.33 of "de Finibus Bonorum et Malorum" (The Extremes of Good and Evil) by Cicero, written in 45 BC. This book is a treatise on the theory of ethics, very popular during the Renaissance. The first line of Lorem Ipsum, "Lorem ipsum dolor sit amet..", comes from a line in section 1.10.32.
            </p>
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