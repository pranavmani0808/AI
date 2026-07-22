"use client";

import React, { useState } from "react";
import { SearchMode } from "../../types/search";
import { ArrowUp } from "lucide-react";
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
      <div className="peec-input relative flex flex-col p-3 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/90 dark:border-zinc-800">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={isCompact ? 1 : 2}
          className="w-full px-2 pt-1 text-base text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 bg-transparent border-0 resize-none outline-none focus:ring-0 leading-relaxed"
        />

        <div className="flex items-center justify-between border-t border-zinc-100 dark:border-zinc-800/80 mt-2 pt-2.5 px-1">
          {/* Left Side: Mode Selection Toolbar */}
          <SearchModeSelector selectedMode={mode} onChange={(m) => setMode(m)} />

          {/* Right Side: Submit Arrow */}
          <button
            type="submit"
            disabled={!query.trim()}
            className={`p-2.5 rounded-xl transition-all ${
              query.trim()
                ? "bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-white text-white dark:text-zinc-900 hover:scale-105 shadow-xs"
                : "bg-zinc-100 text-zinc-300 dark:bg-zinc-800 dark:text-zinc-600 cursor-not-allowed"
            }`}
          >
            <ArrowUp className="w-4 h-4" />
          </button>
        </div>
      </div>
    </form>
  );
}
