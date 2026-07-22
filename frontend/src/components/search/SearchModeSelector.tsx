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
      icon: <Globe className="w-3.5 h-3.5" />, 
      desc: "Fast AI web search" 
    },
    { 
      id: "research", 
      label: "Research", 
      icon: <Sparkles className="w-3.5 h-3.5" />, 
      desc: "Deep crawl & RAG fact-check" 
    },
    { 
      id: "academic", 
      label: "Academic", 
      icon: <GraduationCap className="w-3.5 h-3.5" />, 
      desc: "Academic papers & publications" 
    },
    { 
      id: "products", 
      label: "Products", 
      icon: <ShoppingBag className="w-3.5 h-3.5" />, 
      desc: "Compare product prices & specs" 
    }
  ];

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {modes.map((mode) => {
        const isActive = selectedMode === mode.id;
        return (
          <button
            key={mode.id}
            type="button"
            onClick={() => onChange(mode.id)}
            className={`flex items-center gap-1.5 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all ${
              isActive
                ? "bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 shadow-xs"
                : "text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800/80"
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
