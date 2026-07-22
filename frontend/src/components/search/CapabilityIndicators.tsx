"use client";

import React from "react";
import { Globe, Database, ShieldCheck } from "lucide-react";

export default function CapabilityIndicators() {
  const capabilities = [
    {
      title: "Live Crawling",
      subtitle: "SearXNG + BeautifulSoup",
      icon: <Globe className="w-4 h-4 text-zinc-700 dark:text-zinc-300" />
    },
    {
      title: "Local RAG",
      subtitle: "Qdrant Vector Store",
      icon: <Database className="w-4 h-4 text-zinc-700 dark:text-zinc-300" />
    },
    {
      title: "Grounded LLM",
      subtitle: "Inline Citation Check",
      icon: <ShieldCheck className="w-4 h-4 text-zinc-700 dark:text-zinc-300" />
    }
  ];

  return (
    <div className="w-full max-w-2xl mx-auto grid grid-cols-1 sm:grid-cols-3 gap-3 my-6">
      {capabilities.map((item, idx) => (
        <div 
          key={idx}
          className="peec-card p-3 rounded-xl flex items-center gap-3 bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800"
        >
          <div className="p-2 rounded-lg bg-zinc-100 dark:bg-zinc-800/80 shrink-0">
            {item.icon}
          </div>
          <div className="text-left min-w-0">
            <h4 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 truncate">
              {item.title}
            </h4>
            <p className="text-[11px] text-zinc-500 dark:text-zinc-400 truncate mt-0.5">
              {item.subtitle}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
