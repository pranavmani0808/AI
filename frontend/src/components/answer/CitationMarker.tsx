"use client";

import React, { useState } from "react";

interface CitationMarkerProps {
  id: number;
  onClick: (id: number) => void;
  evidence?: { content: string; relevanceScore: number } | null;
  source?: { title: string; url: string; domain: string } | null;
}

export default function CitationMarker({ id, onClick, evidence, source }: CitationMarkerProps) {
  const [hovered, setHovered] = useState(false);

  return (
    <span 
      className="relative inline-block"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <button
        type="button"
        onClick={() => onClick(id)}
        className="inline-flex items-center justify-center w-5 h-5 bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 border border-zinc-200 dark:border-zinc-700 text-zinc-800 dark:text-zinc-200 font-bold text-[10px] rounded-md mx-0.5 align-super transition-all shadow-2xs cursor-pointer hover:scale-105"
      >
        {id}
      </button>

      {hovered && (evidence || source) && (
        <span className="absolute bottom-6 left-1/2 -translate-x-1/2 z-30 w-72 p-3.5 peec-card bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 rounded-xl shadow-xl text-xs flex flex-col gap-1.5 pointer-events-none transition-all duration-150 border border-zinc-200 dark:border-zinc-800">
          {source && (
            <span className="font-bold text-[11px] text-zinc-900 dark:text-zinc-100 truncate block">
              {source.title} ({source.domain})
            </span>
          )}
          {evidence && (
            <span className="text-[11px] text-zinc-600 dark:text-zinc-300 italic line-clamp-3 block leading-relaxed">
              "{evidence.content}"
            </span>
          )}
          {evidence && (
            <span className="text-[10px] font-bold text-sky-600 dark:text-sky-400 text-right mt-1 block">
              Relevance: {evidence.relevanceScore}%
            </span>
          )}
        </span>
      )}
    </span>
  );
}
