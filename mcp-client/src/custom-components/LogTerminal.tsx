'use client'

import React, { useEffect, useRef, useState } from 'react'
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
  const searchInputRef = useRef<HTMLInputElement>(null);


  const handleCopy = async () => {
    const fullText = logs.join('\n\n' + '-'.repeat(30) + '\n\n')
    await navigator.clipboard.writeText(fullText)
  }

  const visibleLogs = logs.slice(-limit)
  const hasCacheHit = logs.some(log => log.includes("[CACHE-HIT]"));

  const getHighlightedText = (text:string, query: string)=>{
    if (!query) return text;
    const regex = new RegExp(`(${query})`,'gi');
    return text.split(regex).map((part,i)=>
      part.toLowerCase() === query.toLowerCase() ? (
        <mark key={i} className="bg-yellow-200 text-black rounded-sm">{part}</mark>
      ) : (
        part
      )
    );
  };

  const isMatch = (text: string, query: string) => query && text.toLowerCase().includes(query.toLowerCase());

  const scrollToMatch = () => {
    if (!searchQuery) return;
    const index = visibleLogs.findIndex((log) =>
      log.toLowerCase().includes(searchQuery.toLowerCase())
    );
    if (index !== -1) {
      const el = logRefs.current[index];
      const container = containerRef.current;
      if (el && container) {
        // Calculate scroll offset of the element *relative to viewport*
        const scrollTop = el.offsetTop - container.offsetTop - 100; // adjust for header
        container.scrollTo({ top: scrollTop, behavior: 'smooth' });
      }
    }
  };

  // Focus input with `/`, close with Esc
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === '/' && !showSearch) {
        e.preventDefault();
        setShowSearch(true);
        setTimeout(() => searchInputRef.current?.focus(), 0);
      }
      if (e.key === 'Escape' && showSearch) {
        setShowSearch(false);
        setSearchQuery('');
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showSearch]);


  // AUTO-SCROLL BOTTOM WHEN NEW LOGS WHEN SEARCH NOT OPEN
  useEffect(() => {
    if (!showSearch && containerRef.current) {
      setTimeout(() => {
        containerRef.current!.scrollTo({
          top: containerRef.current!.scrollHeight,
          behavior: "smooth",
        });
      }, 10);
    }
  }, [visibleLogs, showSearch]);

  // clear & populate with empty array on render
  logRefs.current = [];

  return (
    <div className="relative flex flex-col gap-2">
      {/* Header */}
      <div className="sticky top-0 z-20 bg-background p-2 flex justify-between items-center">
        <h3 className="text-sm font-semibold flex items-center gap-2">
          {emoji} {title}
          <span className="ml-2 text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
            {logs.length}
          </span>
        </h3>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setShowSearch(prev => !prev)}
          >
            {showSearch ? (
              <>
                <SearchX className={title === 'Assess-Events' ? 'w-1 h-1' : 'w-4 h-4'} /> Close
              </>
            ) : (
              <>
                <SearchIcon className={title === 'Assess-Events' ? 'w-1 h-1' : 'w-4 h-4'} /> Search
              </>
            )}
          </Button>
          {clearable && onClear && (
            <Button
              size="sm"
              variant="outline"
              onClick={onClear}
              className="text-red-300 hover:bg-red-300"
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


      

      <div className="relative">
        {/* Search bar floating over logs */}
        {showSearch && (
          <div className="absolute top-0 left-0 right-0 z-30 px-4 pointer-events-none">
            <Command className="bg-background shadow-lg border border-border rounded-md w-full pointer-events-auto">
              <CommandInput
                ref={searchInputRef}
                placeholder="Search by txnId, streamId, sender, receiver, amount..."
                value={searchQuery}
                onValueChange={setSearchQuery}
                className="w-full px-4 py-2"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    scrollToMatch();
                  }
                }}
              />
            </Command>
          </div>
        )}

        {/* Log display below */}
        <ScrollArea 
          ref={containerRef} 
          className="h-[80vh] rounded-md border border-muted/30 overflow-hidden shadow-inner"
        >
          <div
            className={cn('p-4 text-sm')}
            style={{
              minHeight: '78vh',
              background: bgColor,
              color: textColor,
              fontFamily: 'monospace',
              scrollPaddingTop: '3.5rem', // This ensures focused items aren't hidden under search bar
            }}
          >
            {visibleLogs.length === 0 ? (
              <div className="italic text-muted-foreground">No events yet.</div>
            ) : (
              visibleLogs.map((log, idx) => (
                <div
                  key={`${log}-${idx}`}
                  ref={(el) => {
                    logRefs.current[idx] = el
                  }}
                  className={cn(
                    'mb-4 border-b border-dashed border-white/10 pb-2',
                    isMatch(log, searchQuery) && 'bg-muted/10'
                  )}
                >
                  <pre className="whitespace-pre-wrap">
                    {getHighlightedText(log, searchQuery)}
                  </pre>
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
