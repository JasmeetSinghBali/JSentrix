'use client';

import { BadgeCheck, BadgeX, HeartPulse, Activity, Podcast } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import React from "react";

interface VitalsPanelProps {
  loginGateway: boolean;
  whoamiAccess: boolean;
  toolActive: boolean;
  websocketActive: boolean;
  streamId: string | null;
}

const VitalsPanel: React.FC<VitalsPanelProps> = ({
  loginGateway,
  whoamiAccess,
  toolActive,
  websocketActive,
  streamId,
}) => {
  return (
    <div className="ml-18 mb-2 p-3 rounded-md bg-muted/80 border border-muted">
      <div className="text-muted-foreground text-sm flex items-center gap-2">
        <div className='flex items-center gap-5 mt-2'>
          {
            (loginGateway && whoamiAccess) ?
              <HeartPulse className='w-4 h-4 text-green-500' />
              :
              <Activity className='w-4 h-4 text-red-500' />
          }
          Vitals :
          <div className="flex h-5 items-center space-x-4 text-sm">
            <Badge
              variant={(loginGateway && whoamiAccess) ? "secondary" : "destructive"}
              className={(loginGateway && whoamiAccess) ? "bg-blue-500 text-white dark:bg-blue-600" : ""}
            >
              {(loginGateway && whoamiAccess) ? <BadgeCheck /> : <BadgeX />}
              Gateway
            </Badge>
            <Separator orientation="vertical" />
            <Badge
              variant={toolActive ? "secondary" : "destructive"}
              className={toolActive ? "bg-blue-500 text-white dark:bg-blue-600" : ""}
            >
              {toolActive ? <BadgeCheck /> : <BadgeX />}
              Tools
            </Badge>
            <Separator orientation="vertical" />
            <Badge
              variant={websocketActive ? "secondary" : "destructive"}
              className={websocketActive ? "bg-blue-500 text-white dark:bg-blue-600" : ""}
            >
              {websocketActive ? <BadgeCheck /> : <BadgeX />}
              Events
            </Badge>
          </div>
        </div>
      </div>
      <div className='text-muted-foreground text-sm'>
        <div className='flex items-center gap-5 mt-2'>
          {
            streamId ?
              <Podcast className='w-4 h-4 text-green-500' />
              :
              <BadgeX className='w-4 h-4 text-red-500' />
          }
          StreamID :
          <code className={streamId ? "px-2 py-0.5 rounded bg-blue-500 text-white text-xs" : "px-2 py-0.5 rounded bg-red-600 text-white text-xs"}>
            {streamId || 'no-active-stream-id'}
          </code>
        </div>
      </div>
    </div>
  );
};

export default VitalsPanel;
