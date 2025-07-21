'use client'

import React, { useRef, useState } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { CopyIcon, Trash2Icon, SearchIcon, SearchX } from 'lucide-react'
import { Command, CommandInput } from '@/components/ui/command'
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

  const logRefs = useRef<(HTMLDivElement | null)[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [showSearch, setShowSearch] = useState(false)

  const handleCopy = async () => {
    const fullText = logs.join('\n\n' + '-'.repeat(30) + '\n\n')
    await navigator.clipboard.writeText(fullText)
  }

  const visibleLogs = logs.slice(-limit)
  const hasCacheHit = logs.some(log => log.includes("[CACHE-HIT]"));


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
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setShowSearch(prev => !prev)}
          >
            {showSearch ? (
              <>
                <SearchX className={title === 'Assessment-Agent' ? 'w-1 h-1' : 'w-4 h-4'} /> Close
              </>
            ) : (
              <>
                <SearchIcon className={title === 'Assessment-Agent' ? 'w-1 h-1' : 'w-4 h-4'} /> Search
              </>
            )}
          </Button>
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


      {/* Banner for cache hit */}
      {hasCacheHit && (
        <div className="mb-2 py-2 px-3 rounded bg-yellow-100 text-yellow-900 border border-yellow-400 flex items-center gap-2 animate-pulse">
          <span role="img" aria-label="rocket" className="text-yellow-600 text-lg">🚀</span>
          <span>
            <b>Memory cache hit:</b> This transaction was short-circuited and served from prior LLM memory—no new LLM analysis was run.
          </span>
        </div>
      )}

      {/* Floating search bar overlayed on top of logs */}
      <div className="relative">
        {showSearch && (
          <div className="absolute top-2 right-2 left-2 z-30">
            <Command className="bg-background shadow-lg border border-border rounded-md">
              <CommandInput
                placeholder="Search by txnId, streamId, sender, reciever, amount..."
                value={searchQuery}
                onValueChange={setSearchQuery}
                onKeyDown={(e) => {
                  // if (e.key === 'Enter') {
                  //   e.preventDefault()
                  //   handleSearch(searchQuery)
                  // }
                }}
              />
            </Command>
          </div>
        )}
      </div>


      {/* Logs */}
      <div className="relative">
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
      
    </div>
  )
}

export default LogTerminal
