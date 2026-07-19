"use client";

import React, { useRef, useEffect } from "react";
import { Source } from "../../types/source";
import SourceCard from "./SourceCard";
import { X, Search } from "lucide-react";

interface SourcesPanelProps {
  sources: Source[];
  selectedSourceId: string | null;
  onSelectSource: (sourceId: string | null) => void;
  onClose: () => void;
}

export default function SourcesPanel({
  sources,
  selectedSourceId,
  onSelectSource,
  onClose
}: SourcesPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  // Close panel on clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        // Only close if not clicking on elements that trigger the panel open (like inline markers or source buttons)
        const target = event.target as HTMLElement;
        if (!target.closest("button") && !target.closest("a")) {
          onClose();
        }
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [onClose]);

  return (
    <div 
      ref={panelRef}
      className="w-full md:w-96 border-l border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 flex flex-col h-screen shadow-2xl relative"
    >
      {/* Header */}
      <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between bg-white dark:bg-zinc-950">
        <div className="flex items-center gap-2">
          <Search className="w-4 h-4 text-violet-500" />
          <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-50 tracking-tight">
            Sources Analyzed
          </h3>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-zinc-100 dark:hover:bg-zinc-900 rounded-md text-zinc-500"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Excerpt Summary */}
      <div className="p-4 bg-white dark:bg-zinc-950 border-b border-zinc-200 dark:border-zinc-800">
        <p className="text-xs text-zinc-500 dark:text-zinc-400">
          The autonomous search pipeline crawled and extracted text from **{sources.length} sources** across **{Array.from(new Set(sources.map(s => s.domain))).length} unique domains** to answer your query.
        </p>
      </div>

      {/* Sources list */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
        {sources.map((src, index) => (
          <SourceCard
            key={src.id}
            source={src}
            index={index}
            isSelected={selectedSourceId === src.id}
            onClick={() => onSelectSource(selectedSourceId === src.id ? null : src.id)}
          />
        ))}
      </div>
    </div>
  );
}
