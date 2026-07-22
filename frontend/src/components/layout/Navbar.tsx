"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { 
  Database, 
  Search, 
  Compass, 
  Sparkles, 
  Folder, 
  History, 
  Settings, 
  Plus, 
  Sun, 
  Moon, 
  Menu, 
  X 
} from "lucide-react";

interface NavbarProps {
  onNewSearch?: () => void;
}

export default function Navbar({ onNewSearch }: NavbarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const researchHref = `/search?${new URLSearchParams({ q: "Latest AI breakthroughs", mode: "research" }).toString()}`;

  const navLinks = [
    { label: "Search", href: "/", icon: <Search className="w-4 h-4" /> },
    { label: "Discover", href: "#", icon: <Compass className="w-4 h-4" /> },
    { label: "Research", href: researchHref, icon: <Sparkles className="w-4 h-4" /> },
    { label: "Workspaces", href: "/workspaces", icon: <Folder className="w-4 h-4" /> },
  ];

  const toggleTheme = () => {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
  };

  const handleNewSearchClick = () => {
    if (onNewSearch) {
      onNewSearch();
    } else {
      router.push("/");
    }
  };

  return (
    <header className="w-full sticky top-0 z-40 bg-[#faf9f6]/90 dark:bg-[#090d16]/90 backdrop-blur-md border-b border-zinc-200/80 dark:border-zinc-800/80">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        
        {/* LEFT: Logo + Brand Name */}
        <Link href="/" className="flex items-center gap-2.5 font-bold group">
          <div className="p-1.5 rounded-lg bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 group-hover:scale-105 transition-transform">
            <Database className="w-4 h-4" />
          </div>
          <span className="text-zinc-900 dark:text-zinc-50 tracking-tight text-base font-extrabold">
            IntelliSearch
          </span>
        </Link>

        {/* CENTER: Navigation Links (Desktop) */}
        <nav className="hidden md:flex items-center gap-1 bg-zinc-100/70 dark:bg-zinc-900/70 p-1 rounded-full border border-zinc-200/60 dark:border-zinc-800/60">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.label}
                href={link.href}
                className={`flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-semibold transition-all ${
                  isActive
                    ? "bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-50 shadow-xs"
                    : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-white/50 dark:hover:bg-zinc-800/50"
                }`}
              >
                {link.icon}
                <span>{link.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* RIGHT: History, Settings, Theme Toggle, New Search */}
        <div className="hidden md:flex items-center gap-2">
          <Link
            href="/history"
            className="p-2 rounded-lg text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-200/50 dark:hover:bg-zinc-800/50 transition-colors"
            title="History"
          >
            <History className="w-4 h-4" />
          </Link>

          <Link
            href="/settings"
            className="p-2 rounded-lg text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-200/50 dark:hover:bg-zinc-800/50 transition-colors"
            title="Settings"
          >
            <Settings className="w-4 h-4" />
          </Link>

          {mounted && (
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-200/50 dark:hover:bg-zinc-800/50 transition-colors"
              title={resolvedTheme === "dark" ? "Light Mode" : "Dark Mode"}
            >
              {resolvedTheme === "dark" ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-zinc-600" />}
            </button>
          )}

          <button
            onClick={handleNewSearchClick}
            className="flex items-center gap-1.5 py-2 px-3.5 bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-white text-white dark:text-zinc-900 rounded-lg text-xs font-bold transition-all shadow-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Search</span>
          </button>
        </div>

        {/* Mobile Hamburger Button */}
        <div className="flex md:hidden items-center gap-2">
          {mounted && (
            <button
              onClick={toggleTheme}
              className="p-2 text-zinc-600 dark:text-zinc-400"
            >
              {resolvedTheme === "dark" ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-zinc-600" />}
            </button>
          )}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200/50 dark:hover:bg-zinc-800/50 rounded-lg"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Navigation */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-zinc-200 dark:border-zinc-800 bg-[#faf9f6] dark:bg-[#090d16] p-4 flex flex-col gap-2">
          {navLinks.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center gap-3 p-2.5 rounded-lg text-sm font-semibold text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-900"
            >
              {link.icon}
              <span>{link.label}</span>
            </Link>
          ))}
          <div className="border-t border-zinc-200 dark:border-zinc-800 pt-2 flex flex-col gap-1">
            <Link
              href="/history"
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center gap-3 p-2.5 rounded-lg text-sm font-semibold text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-900"
            >
              <History className="w-4 h-4" />
              <span>History</span>
            </Link>
            <Link
              href="/settings"
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center gap-3 p-2.5 rounded-lg text-sm font-semibold text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-900"
            >
              <Settings className="w-4 h-4" />
              <span>Settings</span>
            </Link>
            <button
              onClick={() => {
                setMobileMenuOpen(false);
                handleNewSearchClick();
              }}
              className="w-full mt-2 flex items-center justify-center gap-2 py-2.5 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 rounded-lg text-sm font-bold"
            >
              <Plus className="w-4 h-4" />
              <span>New Search</span>
            </button>
          </div>
        </div>
      )}
    </header>
  );
}
