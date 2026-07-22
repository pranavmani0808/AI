"use client";

import React from "react";
import { ArrowRight } from "lucide-react";

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
    <div className="w-full max-w-2xl mx-auto mt-8">
      <h3 className="text-xs font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider mb-3 text-left">
        Suggested research questions
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {suggestions.map((sug, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => onSelect(sug.text)}
            className="peec-card peec-card-hover p-4 rounded-xl text-left flex items-center justify-between group cursor-pointer bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800"
          >
            <div className="flex flex-col pr-2">
              <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 group-hover:text-sky-600 dark:group-hover:text-sky-400 transition-colors">
                {sug.text}
              </span>
              <span className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                {sug.desc}
              </span>
            </div>
            <ArrowRight className="w-4 h-4 text-zinc-400 dark:text-zinc-600 group-hover:text-zinc-900 dark:group-hover:text-zinc-100 group-hover:translate-x-0.5 transition-all shrink-0" />
          </button>
        ))}
      </div>
    </div>
  );
}
