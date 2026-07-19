"use client";

import React from "react";

interface CitationMarkerProps {
  id: number;
  onClick: (id: number) => void;
}

export default function CitationMarker({ id, onClick }: CitationMarkerProps) {
  return (
    <button
      type="button"
      onClick={() => onClick(id)}
      className="inline-flex items-center justify-center w-5 h-5 bg-violet-100 hover:bg-violet-200 dark:bg-violet-950/50 dark:hover:bg-violet-900 text-violet-700 dark:text-violet-400 font-bold text-[10px] rounded-md mx-0.5 align-super transition-colors cursor-pointer"
    >
      {id}
    </button>
  );
}
