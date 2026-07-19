"use client";

import React from "react";
import { StageStatus } from "../../types/search";
import { CheckCircle2, Loader2, Circle, AlertCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface ProgressTrackerProps {
  stages: StageStatus[];
}

export default function ProgressTracker({ stages }: ProgressTrackerProps) {
  // Get currently active stage, if any
  const activeStage = stages.find((s) => s.status === "running");

  return (
    <div className="w-full max-w-xl mx-auto bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 p-6 rounded-2xl shadow-md my-8">
      <div className="text-center mb-6">
        <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50 tracking-tight">
          Researching your question...
        </h3>
        <p className="text-sm text-zinc-400 dark:text-zinc-500 mt-1">
          Running autonomous web intelligence flow
        </p>
      </div>

      <div className="flex flex-col gap-4">
        {stages.map((stage, idx) => {
          const isCompleted = stage.status === "completed";
          const isRunning = stage.status === "running";
          const isFailed = stage.status === "failed";
          const isIdle = stage.status === "idle";

          return (
            <div 
              key={stage.id} 
              className={`flex items-start gap-4 transition-all duration-300 ${
                isIdle ? "opacity-30" : "opacity-100"
              }`}
            >
              {/* Icon Status */}
              <div className="mt-0.5">
                {isCompleted && (
                  <CheckCircle2 className="w-5 h-5 text-emerald-500 dark:text-emerald-400" />
                )}
                {isRunning && (
                  <Loader2 className="w-5 h-5 text-violet-500 animate-spin" />
                )}
                {isFailed && (
                  <AlertCircle className="w-5 h-5 text-rose-500 dark:text-rose-400" />
                )}
                {isIdle && (
                  <Circle className="w-5 h-5 text-zinc-300 dark:text-zinc-700" />
                )}
              </div>

              {/* Stage Content */}
              <div className="flex-1 flex flex-col">
                <span className={`text-sm font-medium ${
                  isRunning ? "text-violet-600 dark:text-violet-400 font-semibold" : "text-zinc-800 dark:text-zinc-200"
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
                      className="text-xs text-zinc-400 dark:text-zinc-500 mt-0.5 overflow-hidden"
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
