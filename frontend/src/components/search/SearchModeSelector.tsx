"use client";

import React from "react";
import { SearchMode } from "../../types/search";
import { Globe, Sparkles, GraduationCap, ShoppingBag } from "lucide-react";

interface SearchModeSelectorProps {
  selectedMode: SearchMode;
  onChange: (mode: SearchMode) => void;
}

export default function SearchModeSelector({ selectedMode, onChange }: SearchModeSelectorProps) {
  const modes: { id: SearchMode; label: string; icon: React.ReactNode; desc: string }[] = [
    { 
      id: "web", 
      label: "Web", 
      icon: <Globe className="w-4 h-4" />, 
      desc: "Fast AI web search" 
    },
    { 
      id: "research", 
      label: "Research", 
      icon: <Sparkles className="w-4 h-4" />, 
      desc: "Deep crawl & RAG fact-check" 
    },
    { 
      id: "academic", 
      label: "Academic", 
      icon: <GraduationCap className="w-4 h-4" />, 
      desc: "Academic papers & publications" 
    },
    { 
      id: "products", 
      label: "Products", 
      icon: <ShoppingBag className="w-4 h-4" />, 
      desc: "Compare product prices & specs" 
    }
  ];

  return (
    <div className="flex flex-wrap gap-2 justify-center my-4">
      {modes.map((mode) => {
        const isActive = selectedMode === mode.id;
        return (
          <button
            key={mode.id}
            type="button"
            onClick={() => onChange(mode.id)}
            className={`flex items-center gap-2 py-2 px-4 rounded-xl border text-sm font-medium transition-all ${
              isActive
                ? "bg-violet-50 border-violet-200 text-violet-700 dark:bg-violet-950/30 dark:border-violet-900 dark:text-violet-400 font-semibold"
                : "bg-white border-zinc-200 text-zinc-600 hover:bg-zinc-50 hover:border-zinc-300 dark:bg-zinc-950 dark:border-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-900/50"
            }`}
            title={mode.desc}
          >
            {mode.icon}
            <span>{mode.label}</span>
          </button>
        );
      })}
    </div>
  );
}
