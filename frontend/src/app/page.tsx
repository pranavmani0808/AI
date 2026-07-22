"use client";

import React from "react";
import Navbar from "../components/layout/Navbar";
import SearchBar from "../components/search/SearchBar";
import CapabilityIndicators from "../components/search/CapabilityIndicators";
import PromptSuggestions from "../components/search/PromptSuggestions";
import { SearchMode } from "../types/search";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  const handleSearch = (query: string, mode: SearchMode) => {
    const params = new URLSearchParams({
      q: query.trim(),
      mode: mode,
    });
    router.push(`/search?${params.toString()}`);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#faf9f6] dark:bg-[#090d16] font-sans text-zinc-900 dark:text-zinc-50">
      {/* Peec-inspired Horizontal Top Navbar */}
      <Navbar onNewSearch={() => {}} />

      {/* Main Hero & Content Area */}
      <main className="flex-1 flex flex-col items-center px-4 sm:px-6 py-12 sm:py-16 max-w-4xl mx-auto w-full text-center">
        
        {/* HERO SECTION */}
        <div className="flex flex-col items-center mb-8 max-w-2xl">
          {/* Small Pill */}
          <div className="inline-flex items-center gap-1.5 py-1 px-3 bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800 rounded-full mb-6 shadow-2xs">
            <span className="text-[11px] font-bold text-zinc-700 dark:text-zinc-300 tracking-wider uppercase">
              ✦ AUTONOMOUS WEB INTELLIGENCE
            </span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold text-zinc-900 dark:text-zinc-50 tracking-tight leading-tight">
            Search beyond the{" "}
            <span className="text-sky-600 dark:text-sky-400">
              surface.
            </span>
          </h1>

          {/* Subtitle */}
          <p className="text-zinc-500 dark:text-zinc-400 mt-4 text-base sm:text-lg leading-relaxed font-normal max-w-xl">
            Ask any question. IntelliSearch searches the live web, crawls sources, extracts evidence, and generates grounded answers.
          </p>
        </div>

        {/* SEARCH BOX */}
        <div className="w-full">
          <SearchBar onSearch={handleSearch} />
        </div>

        {/* CAPABILITY INDICATORS */}
        <CapabilityIndicators />

        {/* SUGGESTED RESEARCH */}
        <PromptSuggestions onSelect={(prompt) => handleSearch(prompt, "research")} />

      </main>

      {/* Footer */}
      <footer className="w-full border-t border-zinc-200/60 dark:border-zinc-800/60 py-6 text-center text-xs text-zinc-400 dark:text-zinc-600">
        IntelliSearch Engine &copy; 2026 &bull; Grounded RAG & Autonomous Web Crawling
      </footer>
    </div>
  );
}
