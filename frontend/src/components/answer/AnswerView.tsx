"use client";

import React from "react";
import { SearchResult } from "../../types/search";
import CitationMarker from "./CitationMarker";
import { Star, Check, Award, ArrowUpRight, Globe } from "lucide-react";

interface AnswerViewProps {
  result: SearchResult;
  onCitationClick: (id: number) => void;
  onSourceClick: (sourceId: string) => void;
}

export default function AnswerView({ result, onCitationClick, onSourceClick }: AnswerViewProps) {
  const { answer, recommendedProduct, sources } = result;

  // Helper to parse citations in text blocks
  const renderTextWithCitations = (text: string) => {
    const parts = text.split(/(\[\d+\])/g);
    return parts.map((part, idx) => {
      const match = part.match(/^\[(\d+)\]$/);
      if (match) {
        const citationId = parseInt(match[1], 10);
        return (
          <CitationMarker
            key={idx}
            id={citationId}
            onClick={onCitationClick}
          />
        );
      }
      return <span key={idx}>{part}</span>;
    });
  };

  const paragraphs = answer.split("\n");

  return (
    <div className="w-full max-w-3xl mx-auto py-6 flex flex-col gap-6">
      {/* Answer Body Section */}
      <section className="bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 p-6 rounded-2xl shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Award className="w-5 h-5 text-violet-500" />
          <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">Answer</h2>
        </div>
        
        <div className="prose prose-zinc dark:prose-invert max-w-none text-zinc-800 dark:text-zinc-200 leading-relaxed text-base space-y-4">
          {paragraphs.map((p, idx) => {
            if (!p.trim()) return null;
            return <p key={idx}>{renderTextWithCitations(p)}</p>;
          })}
        </div>
      </section>

      {/* Recommended Product Card Section (Optional) */}
      {recommendedProduct && (
        <section className="bg-gradient-to-br from-violet-50 to-white dark:from-violet-950/20 dark:to-zinc-950 border border-violet-100 dark:border-violet-900/50 p-6 rounded-2xl shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Star className="w-4 h-4 text-violet-500 fill-violet-500" />
            <span className="text-xs font-bold text-violet-700 dark:text-violet-400 uppercase tracking-wider">
              Recommended Option
            </span>
          </div>

          <h3 className="text-xl font-bold text-zinc-900 dark:text-zinc-50">
            {recommendedProduct.name}
          </h3>
          <p className="text-sm font-semibold text-zinc-600 dark:text-zinc-400 mt-1">
            Approximate Price: {recommendedProduct.price}
          </p>

          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <span className="text-xs font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider block mb-2">
                Specifications
              </span>
              <ul className="space-y-1.5">
                {recommendedProduct.specs.map((spec, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-zinc-700 dark:text-zinc-300">
                    <Check className="w-4 h-4 text-violet-500 mt-0.5 shrink-0" />
                    <span>{spec}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <span className="text-xs font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider block mb-2">
                Key Advantages
              </span>
              <ul className="space-y-1.5">
                {recommendedProduct.pros.map((pro, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-zinc-700 dark:text-zinc-300 font-medium">
                    <span className="text-violet-500 mr-1 shrink-0">•</span>
                    <span>{pro}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      )}

      {/* Sources References Grid */}
      <section>
        <div className="flex items-center justify-between mb-3 px-1">
          <h3 className="text-sm font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
            Sources
          </h3>
          <button 
            onClick={() => onSourceClick("")}
            className="text-xs font-semibold text-violet-600 dark:text-violet-400 hover:underline flex items-center gap-1"
          >
            <span>View All Details</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {sources.slice(0, 3).map((src, idx) => (
            <button
              key={src.id}
              onClick={() => onSourceClick(src.id)}
              className="flex flex-col text-left p-4 bg-white dark:bg-zinc-950 border border-zinc-200 hover:border-zinc-300 dark:border-zinc-800 dark:hover:border-zinc-700 rounded-xl transition-all shadow-sm group"
            >
              <div className="flex items-center gap-2 mb-2">
                {src.favicon ? (
                  <img src={src.favicon} alt="" className="w-4 h-4 rounded-sm" onError={(e) => {
                    // Fallback to Globe icon if image fails to load
                    (e.target as HTMLElement).style.display = "none";
                  }} />
                ) : (
                  <Globe className="w-4 h-4 text-zinc-400" />
                )}
                <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 truncate flex-1">
                  {src.domain}
                </span>
                <span className="text-[10px] font-bold text-violet-600 dark:text-violet-400 bg-violet-50 dark:bg-violet-950/40 px-1.5 py-0.5 rounded-md">
                  [{idx + 1}]
                </span>
              </div>
              <h4 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200 group-hover:text-violet-600 dark:group-hover:text-violet-400 transition-colors line-clamp-1">
                {src.title}
              </h4>
              <p className="text-xs text-zinc-400 dark:text-zinc-500 line-clamp-2 mt-1">
                {src.excerpt}
              </p>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
