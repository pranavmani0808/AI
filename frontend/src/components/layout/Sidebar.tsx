"use client";

import React, { useState } from "react";
import { useTheme } from "next-themes";
import { 
  Search, 
  Compass, 
  History, 
  Settings, 
  Sun, 
  Moon, 
  Plus, 
  ChevronLeft, 
  ChevronRight,
  Database
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

interface SidebarProps {
  onNewSearch?: () => void;
}

export default function Sidebar({ onNewSearch }: SidebarProps) {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const router = useRouter();

  // useEffect to avoid hydration mismatch
  React.useEffect(() => {
    setMounted(true);
  }, []);

  const toggleTheme = () => {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
  };

  const recentSearches = [
    { label: "Best iPhone under ₹70,000", query: "Best phones under ₹70,000" },
    { label: "AI news today", query: "Latest AI news" },
    { label: "React vs Next.js", query: "React vs Next.js" }
  ];

  return (
    <aside 
      className={`border-r border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 flex flex-col h-screen transition-all duration-300 ${
        collapsed ? "w-16" : "w-64"
      }`}
    >
      {/* Brand Header */}
      <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
        {!collapsed && (
          <Link href="/" className="flex items-center gap-2 font-semibold text-violet-600 dark:text-violet-400">
            <Database className="w-5 h-5 animate-pulse" />
            <span className="text-zinc-900 dark:text-zinc-50 tracking-tight">IntelliSearch</span>
          </Link>
        )}
        {collapsed && (
          <Link href="/" className="mx-auto text-violet-600 dark:text-violet-400">
            <Database className="w-5 h-5" />
          </Link>
        )}
        <button 
          onClick={() => setCollapsed(!collapsed)}
          className="p-1 hover:bg-zinc-100 dark:hover:bg-zinc-900 rounded-md text-zinc-500 hidden md:block"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Primary Actions */}
      <div className="p-3 flex flex-col gap-2">
        <button
          onClick={() => {
            if (onNewSearch) {
              onNewSearch();
            } else {
              router.push("/");
            }
          }}
          className="flex items-center justify-center gap-2 w-full py-2.5 px-4 bg-violet-600 hover:bg-violet-700 text-white rounded-xl font-medium text-sm transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" />
          {!collapsed && <span>New Search</span>}
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="px-3 flex-1 flex flex-col gap-1 overflow-y-auto">
        <Link 
          href="/" 
          className="flex items-center gap-3 py-2 px-3 hover:bg-zinc-100 dark:hover:bg-zinc-900 rounded-xl text-sm font-medium text-zinc-700 dark:text-zinc-300 transition-colors"
        >
          <Search className="w-4 h-4 text-zinc-500" />
          {!collapsed && <span>Search</span>}
        </Link>
        <Link 
          href="#" 
          className="flex items-center gap-3 py-2 px-3 hover:bg-zinc-100 dark:hover:bg-zinc-900 rounded-xl text-sm font-medium text-zinc-700 dark:text-zinc-300 transition-colors"
        >
          <Compass className="w-4 h-4 text-zinc-500" />
          {!collapsed && <span>Discover</span>}
        </Link>
        <Link 
          href="/history" 
          className="flex items-center gap-3 py-2 px-3 hover:bg-zinc-100 dark:hover:bg-zinc-900 rounded-xl text-sm font-medium text-zinc-700 dark:text-zinc-300 transition-colors"
        >
          <History className="w-4 h-4 text-zinc-500" />
          {!collapsed && <span>History</span>}
        </Link>

        {/* Recent Section */}
        {!collapsed && (
          <div className="mt-6">
            <span className="px-3 text-xs font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider block">
              Recent
            </span>
            <div className="mt-2 flex flex-col gap-0.5">
              {recentSearches.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => router.push(`/search?q=${encodeURIComponent(item.query)}&mode=web`)}
                  className="w-full text-left py-1.5 px-3 hover:bg-zinc-100 dark:hover:bg-zinc-900 rounded-lg text-sm text-zinc-600 dark:text-zinc-400 truncate transition-colors"
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </nav>

      {/* Footer Settings & Theme Toggle */}
      <div className="p-3 border-t border-zinc-200 dark:border-zinc-800 flex flex-col gap-1">
        <Link 
          href="/settings"
          className="flex items-center gap-3 py-2 px-3 hover:bg-zinc-100 dark:hover:bg-zinc-900 rounded-xl text-sm font-medium text-zinc-700 dark:text-zinc-300 transition-colors"
        >
          <Settings className="w-4 h-4 text-zinc-500" />
          {!collapsed && <span>Settings</span>}
        </Link>

        {mounted && (
          <button
            onClick={toggleTheme}
            className="flex items-center gap-3 py-2 px-3 w-full text-left hover:bg-zinc-100 dark:hover:bg-zinc-900 rounded-xl text-sm font-medium text-zinc-700 dark:text-zinc-300 transition-colors"
          >
            {resolvedTheme === "dark" ? (
              <>
                <Sun className="w-4 h-4 text-zinc-500" />
                {!collapsed && <span>Light Mode</span>}
              </>
            ) : (
              <>
                <Moon className="w-4 h-4 text-zinc-500" />
                {!collapsed && <span>Dark Mode</span>}
              </>
            )}
          </button>
        )}
      </div>
    </aside>
  );
}
