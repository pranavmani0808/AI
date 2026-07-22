"use client";

import React from "react";
import { Source } from "../../types/source";
import { ExternalLink, Globe, Calendar } from "lucide-react";

interface SourceCardProps {
  source: Source;
  index: number;
  isSelected?: boolean;
  onClick?: () => void;
}

export default function SourceCard({ source, index, isSelected = false, onClick }: SourceCardProps) {
  const formattedDate = source.crawledAt 
    ? new Date(source.crawledAt).toLocaleDateString(undefined, { 
        month: "short", 
        day: "numeric", 
        hour: "2-digit", 
        minute: "2-digit" 
      }) 
    : undefined;

  return (
    <div
      onClick={onClick}
      className={`peec-card peec-card-hover p-4 rounded-xl transition-all text-left flex flex-col gap-2 bg-white dark:bg-zinc-900 ${
        onClick ? "cursor-pointer" : ""
      } ${
        isSelected 
          ? "border-zinc-900 dark:border-zinc-100 ring-1 ring-zinc-900/10 dark:ring-zinc-100/10" 
          : "border-zinc-200/80 dark:border-zinc-800"
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {source.favicon ? (
            <img src={source.favicon} alt="" className="w-4 h-4 rounded-sm" onError={(e) => {
              (e.target as HTMLElement).style.display = "none";
            }} />
          ) : (
            <Globe className="w-3.5 h-3.5 text-zinc-400 dark:text-zinc-500" />
          )}
          <span className="text-xs font-bold text-zinc-600 dark:text-zinc-400">
            {source.domain}
          </span>
        </div>
        <span className="text-[10px] font-bold text-zinc-500 dark:text-zinc-400 bg-zinc-100 dark:bg-zinc-800 px-2 py-0.5 rounded-md">
          Source #{index + 1}
        </span>
      </div>

      <h4 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 leading-snug line-clamp-2">
        {source.title}
      </h4>

      <p className="text-xs text-zinc-500 dark:text-zinc-400 line-clamp-3 leading-relaxed">
        {source.excerpt}
      </p>

      <div className="flex items-center justify-between border-t border-zinc-100 dark:border-zinc-800/80 mt-1 pt-2">
        {formattedDate ? (
          <div className="flex items-center gap-1 text-[10px] text-zinc-400 dark:text-zinc-500">
            <Calendar className="w-3 h-3" />
            <span>Crawled: {formattedDate}</span>
          </div>
        ) : (
          <div />
        )}

        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()} // Avoid triggering parent click
          className="inline-flex items-center gap-1 text-[11px] font-bold text-sky-600 dark:text-sky-400 hover:underline"
        >
          <span>Open Source</span>
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    </div>
  );
}
