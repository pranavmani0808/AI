"use client";

import React from "react";

interface PromptSuggestionsProps {
  onSelect: (prompt: string) => void;
}

export default function PromptSuggestions({ onSelect }: PromptSuggestionsProps) {
  const suggestions = [
    { text: "Latest AI news", desc: "Latest breakthroughs" },
    { text: "Best phones under ₹70,000", desc: "Compare specs & prices" },
    { text: "How does a vector database work?", desc: "Learn Qdrant & embeddings" },
    { text: "Explain quantum computing", desc: "Simple explanation" }
  ];

  return (
    <div className="w-full max-w-2xl mx-auto mt-6">
      <p className="text-xs font-medium text-zinc-400 dark:text-zinc-500 uppercase tracking-wider mb-2 text-center">
        Try asking
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {suggestions.map((sug, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => onSelect(sug.text)}
            className="flex flex-col text-left p-3 border border-zinc-200 hover:border-zinc-300 bg-white hover:bg-zinc-50 dark:border-zinc-800 dark:hover:border-zinc-700 dark:bg-zinc-950 dark:hover:bg-zinc-900 rounded-xl transition-all shadow-sm"
          >
            <span className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
              {sug.text}
            </span>
            <span className="text-xs text-zinc-400 dark:text-zinc-500 mt-0.5">
              {sug.desc}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
