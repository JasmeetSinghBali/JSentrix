// custom-components/AccountSheet.tsx
'use client';

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription
} from "@/components/ui/sheet";
import { useState } from "react";
import { SidebarMenuButton } from "@/components/ui/sidebar";
import { ChevronFirst, ChevronLast } from "lucide-react";

interface Props {
  username: string;
  email: string;
}

export default function AccountSheet({ username, email }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <SidebarMenuButton
        onClick={() => setOpen(true)}
        className="w-full flex items-center gap-2"
      >
        {open ? <ChevronLast/> : <ChevronFirst/>}
        <span>Account</span>
      </SidebarMenuButton>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="w-[400px] sm:w-[500px]">
          <SheetHeader>
            <SheetTitle>Account Settings</SheetTitle>
            <SheetDescription>
              Manage your account specific settings and account preferences.
            </SheetDescription>
          </SheetHeader>

          <div className="mt-6 space-y-4 p-4">
            <div className="space-y-1">
              <label htmlFor="username" className="text-sm font-medium">
                Username
              </label>
              <input
                id="username"
                type="text"
                defaultValue={username}
                className="w-full border rounded-md p-2 text-sm bg-background"
              />
            </div>

            <div className="space-y-1">
              <label htmlFor="email" className="text-sm font-medium">
                Email
              </label>
              <input
                id="email"
                type="text"
                value={email}
                disabled
                className="w-full border rounded-md p-2 text-sm text-muted-foreground bg-muted"
              />
            </div>

            <div className="pt-4 border-t mt-6">
              {/* not for superadmin other users deactivate account action */}
              <button
                className="text-red-500 text-sm underline"
                onClick={() => alert("Account Deactivation Triggered")}
              >
                Deactivate Account
              </button>
            </div>
            {/* KillSwitch Only for superadmin user Lock System will force log out all other logged in user if any and restrict any user to login until superadmin Unlocks the system again  */}
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
