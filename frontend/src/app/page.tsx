"use client";

import React from "react";
import Sidebar from "../components/layout/Sidebar";
import SearchBar from "../components/search/SearchBar";
import PromptSuggestions from "../components/search/PromptSuggestions";
import { SearchMode } from "../types/search";
import { useRouter } from "next/navigation";
import { Sparkles } from "lucide-react";

export default function Home() {
  const router = useRouter();

  const handleSearch = (query: string, mode: SearchMode) => {
    router.push(`/search?q=${encodeURIComponent(query)}&mode=${mode}`);
  };

  return (
    <div className="flex w-full h-screen overflow-hidden bg-zinc-50 dark:bg-zinc-950 font-sans">
      {/* Sidebar Layout */}
      <Sidebar />

      {/* Main Home Container */}
      <main className="flex-1 flex flex-col justify-center items-center px-6 md:px-12 py-16 overflow-y-auto bg-zinc-50 dark:bg-zinc-950">
        <div className="w-full max-w-2xl flex flex-col items-center text-center mb-8">
          {/* Logo Badge */}
          <div className="flex items-center gap-1.5 py-1.5 px-3 bg-violet-50 dark:bg-violet-950/40 border border-violet-100 dark:border-violet-900/50 rounded-full mb-6 animate-fade-in">
            <Sparkles className="w-3.5 h-3.5 text-violet-500" />
            <span className="text-[11px] font-bold text-violet-700 dark:text-violet-400 uppercase tracking-wider">
              Autonomous Web Intelligence
            </span>
          </div>

          <h1 className="text-4xl md:text-5xl font-extrabold text-zinc-900 dark:text-zinc-50 tracking-tight leading-tight">
            Search beyond the surface.
          </h1>
          <p className="text-zinc-500 dark:text-zinc-400 mt-3 text-base md:text-lg max-w-lg">
            Ask any question. We will search the live web, crawl sources, index evidence, and verify claims.
          </p>
        </div>

        {/* Central Search Box */}
        <SearchBar onSearch={handleSearch} />

        {/* Prompt Suggestions */}
        <PromptSuggestions onSelect={(prompt) => handleSearch(prompt, "research")} />
      </main>
    </div>
  );
}
