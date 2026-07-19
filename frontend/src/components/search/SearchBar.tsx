"use client";

import React, { useState } from "react";
import { SearchMode } from "../../types/search";
import { ArrowUp, Sparkles } from "lucide-react";
import SearchModeSelector from "./SearchModeSelector";

interface SearchBarProps {
  initialValue?: string;
  initialMode?: SearchMode;
  onSearch: (query: string, mode: SearchMode) => void;
  placeholder?: string;
  isCompact?: boolean;
}

export default function SearchBar({
  initialValue = "",
  initialMode = "web",
  onSearch,
  placeholder = "Ask anything. We'll search, crawl, and verify...",
  isCompact = false
}: SearchBarProps) {
  const [query, setQuery] = useState(initialValue);
  const [mode, setMode] = useState<SearchMode>(initialMode);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim(), mode);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
      <div className="relative flex flex-col p-2 bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 focus-within:border-violet-500 focus-within:ring-2 focus-within:ring-violet-500/20 rounded-2xl shadow-md transition-all">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={isCompact ? 1 : 2}
          className="w-full px-3 pt-2 text-base text-zinc-900 dark:text-zinc-50 placeholder-zinc-400 bg-transparent border-0 resize-none outline-none focus:ring-0"
        />

        <div className="flex items-center justify-between border-t border-zinc-100 dark:border-zinc-900 mt-2 pt-2 px-1">
          {/* Left Side: Mode Indicator / Selector */}
          <div className="flex items-center gap-1.5 bg-zinc-50 dark:bg-zinc-900 py-1 px-2.5 rounded-xl border border-zinc-200/50 dark:border-zinc-800/50">
            <Sparkles className="w-3.5 h-3.5 text-violet-500" />
            <span className="text-xs font-semibold text-zinc-600 dark:text-zinc-400 capitalize">
              {mode} Mode
            </span>
          </div>

          {/* Right Side: Submit */}
          <button
            type="submit"
            disabled={!query.trim()}
            className={`p-2 rounded-xl text-white transition-all ${
              query.trim()
                ? "bg-violet-600 hover:bg-violet-700 hover:scale-105"
                : "bg-zinc-100 text-zinc-400 dark:bg-zinc-900 dark:text-zinc-600 cursor-not-allowed"
            }`}
          >
            <ArrowUp className="w-4 h-4" />
          </button>
        </div>
      </div>

      {!isCompact && (
        <SearchModeSelector selectedMode={mode} onChange={(m) => setMode(m)} />
      )}
    </form>
  );
}
