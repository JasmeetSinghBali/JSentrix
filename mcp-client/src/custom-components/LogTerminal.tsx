'use client'

import React, { useRef } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { CopyIcon, Trash2Icon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface LogTerminalProps {
  title: string
  emoji?: string
  logs: string[]
  bgColor?: string
  textColor?: string
  limit?: number
  autoScroll?: boolean
  clearable?: boolean
  onClear?: () => void
}

const LogTerminal: React.FC<LogTerminalProps> = ({
  title,
  emoji,
  logs,
  bgColor = '#111',
  textColor = '#fff',
  limit = 100,
  clearable = false,
  onClear,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null)

  const handleCopy = async () => {
    const fullText = logs.join('\n\n' + '-'.repeat(30) + '\n\n')
    await navigator.clipboard.writeText(fullText)
  }

  const visibleLogs = logs.slice(-limit)

  return (
    <div className="flex flex-col gap-2">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h3 className="text-md font-semibold flex items-center gap-2">
          {emoji} {title}
          <span className="ml-2 text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
            {logs.length}
          </span>
        </h3>
        <div className="flex gap-2">
          {clearable && onClear && (
            <Button
              size="sm"
              variant="ghost"
              onClick={onClear}
              className="text-red-500 hover:text-red-600"
            >
              <Trash2Icon className="w-4 h-4" />
              Clear
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={handleCopy}>
            <CopyIcon className="w-4 h-4" />
            Copy
          </Button>
        </div>
      </div>


      {/* Logs */}
      <ScrollArea className="h-[80vh] rounded-md border border-muted/30 overflow-hidden shadow-inner">
        <div
          ref={containerRef}
          className={cn('p-4 text-sm')}
          style={{
            minHeight: '78vh',
            background: bgColor,
            color: textColor,
            fontFamily: 'monospace',
          }}
        >
          {visibleLogs.length === 0 ? (
            <div className="italic text-muted-foreground">No events yet.</div>
          ) : (
            visibleLogs.map((log, idx) => (
              <div
                key={idx}
                className="mb-4 border-b border-dashed border-white/10 pb-2"
              >
                <pre className="whitespace-pre-wrap">{log}</pre>
              </div>
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  )
}

export default LogTerminal
