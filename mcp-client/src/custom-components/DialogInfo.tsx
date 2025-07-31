// custom-components/DialogInfo.tsx
'use client';

import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

type DialogInfoProps = {
  open: boolean;
  onOpenChange: (value: boolean) => void;
  title?: string;
  description?: string;
  content: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
};

export function DialogInfo({
  open,
  onOpenChange,
  title,
  description,
  content,
  footer,
  className,
}: DialogInfoProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className={cn("max-h-[90vh] overflow-hidden sm:max-w-2xl", className)}
      >
        <DialogHeader>
          {title && <DialogTitle>{title}</DialogTitle>}
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>

        <ScrollArea className="max-h-[60vh] pr-2">
          <div className="space-y-4 py-2">{content}</div>
        </ScrollArea>

        <DialogFooter className="mt-4">
          {footer ?? (
            <DialogClose asChild>
              <Button variant="outline">Close</Button>
            </DialogClose>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
