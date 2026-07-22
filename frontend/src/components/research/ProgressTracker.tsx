"use client";

import React from "react";
import { StageStatus } from "../../types/search";
import { CheckCircle2, Loader2, Circle, AlertCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface ProgressTrackerProps {
  stages: StageStatus[];
}

export default function ProgressTracker({ stages }: ProgressTrackerProps) {
  return (
    <div className="w-full max-w-xl mx-auto peec-card p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/90 dark:border-zinc-800 my-8">
      <div className="text-center mb-6">
        <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 tracking-tight">
          Autonomous Research Progress
        </h3>
        <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
          Crawling live web sources, extracting chunks & indexing evidence
        </p>
      </div>

      <div className="flex flex-col gap-3.5">
        {stages.map((stage) => {
          const isCompleted = stage.status === "completed";
          const isRunning = stage.status === "running";
          const isFailed = stage.status === "failed";
          const isIdle = stage.status === "idle";

          return (
            <div 
              key={stage.id} 
              className={`flex items-start gap-3.5 transition-all duration-200 ${
                isIdle ? "opacity-40" : "opacity-100"
              }`}
            >
              {/* Icon Status */}
              <div className="mt-0.5 shrink-0">
                {isCompleted && (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                )}
                {isRunning && (
                  <Loader2 className="w-4 h-4 text-sky-600 dark:text-sky-400 animate-spin" />
                )}
                {isFailed && (
                  <AlertCircle className="w-4 h-4 text-rose-500" />
                )}
                {isIdle && (
                  <Circle className="w-4 h-4 text-zinc-300 dark:text-zinc-700" />
                )}
              </div>

              {/* Stage Content */}
              <div className="flex-1 flex flex-col min-w-0">
                <span className={`text-xs font-semibold ${
                  isRunning ? "text-sky-600 dark:text-sky-400 font-bold" : "text-zinc-800 dark:text-zinc-200"
                }`}>
                  {stage.label}
                </span>

                {/* Submessage details */}
                <AnimatePresence>
                  {isRunning && stage.message && (
                    <motion.span
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-0.5 overflow-hidden block truncate"
                    >
                      {stage.message}
                    </motion.span>
                  )}
                </AnimatePresence>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
