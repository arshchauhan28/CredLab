"use client";

import { useCallback, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import type { UserResponse } from "@/types/auth";
import {
  Play,
  RotateCcw,
  Trash2,
  Terminal,
  Code2,
  History,
  Clock,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  FileCode,
  Sparkles,
} from "lucide-react";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[460px] flex-col items-center justify-center gap-3 text-xs text-[#A5A29C] bg-[#1a1a1a]">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#FF6B2C] border-t-transparent" />
      <span>Loading Code Editor...</span>
    </div>
  ),
});

export type SupportedLanguage = "python" | "c" | "cpp" | "java";

export interface LanguageOption {
  value: SupportedLanguage;
  label: string;
  monacoLang: string;
  version: string;
  starter: string;
}

export const PRACTICE_LANGUAGES: LanguageOption[] = [
  {
    value: "python",
    label: "Python",
    monacoLang: "python",
    version: "3.8+",
    starter: 'print("Hello, World!")\n',
  },
  {
    value: "c",
    label: "C",
    monacoLang: "c",
    version: "GCC 9.2",
    starter: `#include <stdio.h>

int main(void) {
    printf("Hello, World!\\n");
    return 0;
}
`,
  },
  {
    value: "cpp",
    label: "C++",
    monacoLang: "cpp",
    version: "GCC 9.2",
    starter: `#include <iostream>
using namespace std;

int main() {
    cout << "Hello, World!" << endl;
    return 0;
}
`,
  },
  {
    value: "java",
    label: "Java",
    monacoLang: "java",
    version: "OpenJDK 13",
    starter: `public class Main {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
`,
  },
];

export interface ExecutionResult {
  status: string;
  status_id?: number;
  status_description?: string;
  stdout?: string;
  stderr?: string;
  compile_output?: string;
  time_ms?: number;
  memory_kb?: number;
  time?: string;
  memory?: number;
  exit_code?: number;
}

export interface PracticeHistoryItem {
  id: string;
  timestamp: string;
  language: SupportedLanguage;
  source_code: string;
  stdin: string;
  status: string;
  status_id?: number;
  time_ms?: number;
  memory_kb?: number;
  stdout?: string;
  stderr?: string;
  compile_output?: string;
  exit_code?: number;
}

interface PracticeArenaProps {
  user?: UserResponse | null;
  api: <T>(path: string, init?: RequestInit) => Promise<T>;
}

export function PracticeArena({ user, api }: PracticeArenaProps) {
  const [language, setLanguage] = useState<SupportedLanguage>("python");
  const [codePerLang, setCodePerLang] = useState<Record<SupportedLanguage, string>>(() => {
    return {
      python: PRACTICE_LANGUAGES.find((l) => l.value === "python")!.starter,
      c: PRACTICE_LANGUAGES.find((l) => l.value === "c")!.starter,
      cpp: PRACTICE_LANGUAGES.find((l) => l.value === "cpp")!.starter,
      java: PRACTICE_LANGUAGES.find((l) => l.value === "java")!.starter,
    };
  });
  const [stdin, setStdin] = useState("");
  const [showStdin, setShowStdin] = useState(true);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ExecutionResult | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [copiedOutput, setCopiedOutput] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);
  const [activeOutputTab, setActiveOutputTab] = useState<"stdout" | "stderr" | "compiler">("stdout");

  // Practice Run History State (Client-Side Storage)
  const historyStorageKey = useMemo(
    () => `credlab_practice_history_${user?.id || "default"}`,
    [user?.id],
  );
  const [history, setHistory] = useState<PracticeHistoryItem[]>(() => {
    if (typeof window !== "undefined") {
      try {
        const stored = localStorage.getItem(`credlab_practice_history_${user?.id || "default"}`);
        if (stored) {
          const parsed = JSON.parse(stored);
          if (Array.isArray(parsed)) {
            return parsed.slice(0, 25);
          }
        }
      } catch (err) {
        console.warn("Failed to load practice history:", err);
      }
    }
    return [];
  });
  const [showHistory, setShowHistory] = useState(false);

  // Save history to localStorage
  const saveHistoryItem = useCallback(
    (item: PracticeHistoryItem) => {
      setHistory((prev) => {
        const updated = [item, ...prev].slice(0, 25);
        if (typeof window !== "undefined") {
          try {
            localStorage.setItem(historyStorageKey, JSON.stringify(updated));
          } catch (err) {
            console.warn("Failed to save practice history:", err);
          }
        }
        return updated;
      });
    },
    [historyStorageKey],
  );

  const clearHistory = useCallback(() => {
    setHistory([]);
    if (typeof window !== "undefined") {
      try {
        localStorage.removeItem(historyStorageKey);
      } catch (err) {
        console.warn("Failed to clear practice history:", err);
      }
    }
  }, [historyStorageKey]);

  const currentLangConfig = useMemo(
    () => PRACTICE_LANGUAGES.find((l) => l.value === language) || PRACTICE_LANGUAGES[0],
    [language],
  );

  const currentSourceCode = codePerLang[language] ?? currentLangConfig.starter;

  const isCodeModified = useMemo(() => {
    return currentSourceCode.trim() !== currentLangConfig.starter.trim();
  }, [currentSourceCode, currentLangConfig]);

  const handleLanguageChange = (newLang: SupportedLanguage) => {
    if (newLang === language) return;
    setConfirmReset(false);
    setLanguage(newLang);
  };

  const handleCodeChange = (newCode: string) => {
    setCodePerLang((prev) => ({
      ...prev,
      [language]: newCode,
    }));
  };

  const handleResetRequest = () => {
    if (isCodeModified) {
      setConfirmReset(true);
    } else {
      doResetCode();
    }
  };

  const doResetCode = () => {
    setCodePerLang((prev) => ({
      ...prev,
      [language]: currentLangConfig.starter,
    }));
    setConfirmReset(false);
  };

  const clearOutput = () => {
    setResult(null);
    setErrorMessage("");
  };

  const handleCopyOutput = () => {
    if (!result) return;
    const textToCopy =
      activeOutputTab === "stdout"
        ? result.stdout || ""
        : activeOutputTab === "stderr"
          ? result.stderr || ""
          : result.compile_output || "";
    if (textToCopy) {
      navigator.clipboard.writeText(textToCopy);
      setCopiedOutput(true);
      setTimeout(() => setCopiedOutput(false), 2000);
    }
  };

  const runCode = async () => {
    if (running) return;
    if (!currentSourceCode.trim()) {
      setErrorMessage("Source code cannot be empty. Please write some code before running.");
      return;
    }

    setRunning(true);
    setErrorMessage("");
    setConfirmReset(false);

    try {
      // Reusing existing secure backend execution infrastructure
      const data = await api<ExecutionResult>("execute", {
        method: "POST",
        body: JSON.stringify({
          language,
          source_code: currentSourceCode,
          stdin: stdin || "",
        }),
      });

      setResult(data);

      // Auto-select tab with most relevant output
      if (data.compile_output && data.compile_output.trim()) {
        setActiveOutputTab("compiler");
      } else if (data.stderr && data.stderr.trim() && !data.stdout?.trim()) {
        setActiveOutputTab("stderr");
      } else {
        setActiveOutputTab("stdout");
      }

      // Add to practice run history
      const historyEntry: PracticeHistoryItem = {
        id: `${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
        language,
        source_code: currentSourceCode,
        stdin,
        status: data.status || "Completed",
        status_id: data.status_id,
        time_ms: data.time_ms ?? (data.time ? Math.round(parseFloat(data.time) * 1000) : undefined),
        memory_kb: data.memory_kb ?? data.memory,
        stdout: data.stdout,
        stderr: data.stderr,
        compile_output: data.compile_output,
        exit_code: data.exit_code,
      };
      saveHistoryItem(historyEntry);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to execute code in sandbox.";
      setErrorMessage(msg);
      setResult({
        status: "Sandbox Error",
        stderr: msg,
      });
      setActiveOutputTab("stderr");
    } finally {
      setRunning(false);
    }
  };

  const restoreHistoryItem = (item: PracticeHistoryItem) => {
    setLanguage(item.language);
    setCodePerLang((prev) => ({
      ...prev,
      [item.language]: item.source_code,
    }));
    setStdin(item.stdin || "");
    setResult({
      status: item.status,
      status_id: item.status_id,
      stdout: item.stdout,
      stderr: item.stderr,
      compile_output: item.compile_output,
      time_ms: item.time_ms,
      memory_kb: item.memory_kb,
      exit_code: item.exit_code,
    });
    setShowHistory(false);
  };

  // Determine status color styling
  const getStatusBadge = (status: string, statusId?: number) => {
    const isAccepted = status === "Accepted" || statusId === 3;
    const isCompileError = status === "Compilation Error" || statusId === 6;
    const isTimeout = status === "Time Limit Exceeded" || statusId === 5;
    const isMemoryLimit = status === "Memory Limit Exceeded" || statusId === 12;

    if (isAccepted) {
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-bold text-emerald-400">
          <CheckCircle2 className="h-3.5 w-3.5" />
          Accepted
        </span>
      );
    }
    if (isCompileError) {
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs font-bold text-amber-400">
          <AlertTriangle className="h-3.5 w-3.5" />
          Compilation Error
        </span>
      );
    }
    if (isTimeout) {
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-purple-500/30 bg-purple-500/10 px-2.5 py-1 text-xs font-bold text-purple-400">
          <Clock className="h-3.5 w-3.5" />
          Time Limit Exceeded
        </span>
      );
    }
    if (isMemoryLimit) {
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-rose-500/30 bg-rose-500/10 px-2.5 py-1 text-xs font-bold text-rose-400">
          <Cpu className="h-3.5 w-3.5" />
          Memory Limit Exceeded
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-rose-500/30 bg-rose-500/10 px-2.5 py-1 text-xs font-bold text-rose-400">
        <XCircle className="h-3.5 w-3.5" />
        {status || "Runtime Error"}
      </span>
    );
  };

  const runtimeDisplay = useMemo(() => {
    if (!result) return null;
    if (result.time) return `${result.time}s`;
    if (typeof result.time_ms === "number") return `${(result.time_ms / 1000).toFixed(3)}s`;
    return null;
  }, [result]);

  const memoryDisplay = useMemo(() => {
    if (!result) return null;
    const kb = typeof result.memory === "number" ? result.memory : result.memory_kb;
    if (typeof kb === "number") {
      if (kb > 1024) return `${(kb / 1024).toFixed(1)} MB`;
      return `${kb} KB`;
    }
    return null;
  }, [result]);

  return (
    <div className="space-y-6">
      {/* ────── Practice Arena Header Bar ────── */}
      <section className="lux-card relative overflow-hidden p-5 sm:p-6 bg-[#181818] border border-[#353535]">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#FF6B2C]/10 text-[#FF6B2C] border border-[#FF6B2C]/30">
                <Code2 className="h-4 w-4" />
              </div>
              <h1 className="text-xl font-extrabold tracking-tight text-[#F7F4EF] sm:text-2xl">
                Practice Arena
              </h1>
              <span className="inline-flex items-center gap-1 rounded-full border border-[#FF6B2C]/30 bg-[#FF6B2C]/10 px-2.5 py-0.5 text-[11px] font-bold text-[#FF8A3D]">
                <Sparkles className="h-3 w-3" />
                Independent Sandbox
              </span>
            </div>
            <p className="text-xs text-[#A5A29C]">
              Practice programming and experiment with code independently without academic constraints.
            </p>
          </div>

          {/* Action Toolbar */}
          <div className="flex flex-wrap items-center gap-2.5">
            {/* Language Selector */}
            <div className="relative">
              <label htmlFor="practice-language-select" className="sr-only">
                Select Programming Language
              </label>
              <select
                id="practice-language-select"
                value={language}
                onChange={(e) => handleLanguageChange(e.target.value as SupportedLanguage)}
                className="appearance-none rounded-xl border border-[#353535] bg-[#141414] py-2 pl-3.5 pr-8 text-xs font-bold text-[#F7F4EF] transition-all hover:border-[#4F4F4F] focus:border-[#FF6B2C] focus:outline-none"
              >
                {PRACTICE_LANGUAGES.map((lang) => (
                  <option key={lang.value} value={lang.value} className="bg-[#1B1B1B] text-[#F7F4EF]">
                    {lang.label} ({lang.version})
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#A5A29C]" />
            </div>

            {/* Run Code Button */}
            <button
              onClick={runCode}
              disabled={running}
              className="btn-primary !py-2 !px-4 !text-xs font-bold flex items-center gap-2 shadow-sm"
              title="Run code in secure sandbox (Ctrl + Enter)"
            >
              {running ? (
                <>
                  <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  <span>Executing...</span>
                </>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5 fill-current" />
                  <span>Run Code</span>
                </>
              )}
            </button>

            {/* Reset Code Button */}
            <button
              onClick={handleResetRequest}
              disabled={running}
              className="btn-secondary !py-2 !px-3.5 !text-xs font-bold flex items-center gap-1.5"
              title="Reset code to default template"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Reset</span>
            </button>

            {/* Clear Output Button */}
            {result && (
              <button
                onClick={clearOutput}
                className="btn-secondary !py-2 !px-3 !text-xs font-bold flex items-center gap-1 text-[#A5A29C] hover:text-[#F87171]"
                title="Clear console output"
              >
                <Trash2 className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Clear</span>
              </button>
            )}

            {/* History Toggle Button */}
            <button
              onClick={() => setShowHistory((prev) => !prev)}
              className={`rounded-xl px-3 py-2 text-xs font-bold border transition-all flex items-center gap-1.5 ${
                showHistory
                  ? "bg-[#FF6B2C]/15 border-[#FF6B2C] text-[#FF8A3D]"
                  : "bg-[#141414] border-[#353535] text-[#A5A29C] hover:text-[#F7F4EF] hover:border-[#4F4F4F]"
              }`}
              title="View previous practice runs"
            >
              <History className="h-3.5 w-3.5" />
              <span>History</span>
              {history.length > 0 && (
                <span className="ml-0.5 rounded-full bg-[#2A2A2A] px-1.5 py-0.2 text-[10px] font-mono text-[#F7F4EF]">
                  {history.length}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Confirmation Banner for Reset */}
        {confirmReset && (
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300 animate-fade-in">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
              <span>
                Reset <strong>{currentLangConfig.label}</strong> code to starter template? Your modified code will be discarded.
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={doResetCode}
                className="rounded-lg bg-amber-500 px-3 py-1 font-bold text-black hover:bg-amber-400 transition-colors"
              >
                Confirm Reset
              </button>
              <button
                onClick={() => setConfirmReset(false)}
                className="rounded-lg bg-[#242424] px-3 py-1 font-bold text-[#F7F4EF] hover:bg-[#303030] transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Error Notification */}
        {errorMessage && (
          <div className="mt-4 flex items-center justify-between rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300 animate-fade-in">
            <div className="flex items-center gap-2">
              <XCircle className="h-4 w-4 shrink-0 text-rose-400" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage("")}
              className="text-xs text-rose-400 hover:text-rose-200 underline"
            >
              Dismiss
            </button>
          </div>
        )}
      </section>

      {/* ────── History Drawer / Dropdown ────── */}
      {showHistory && (
        <section className="lux-card p-5 bg-[#161616] border border-[#353535] animate-fade-in">
          <div className="flex items-center justify-between border-b border-[#2A2A2A] pb-3">
            <div className="flex items-center gap-2">
              <History className="h-4 w-4 text-[#FF8A3D]" />
              <h2 className="text-sm font-bold text-[#F7F4EF]">Practice Run History</h2>
              <span className="text-xs text-[#A5A29C]">({history.length} runs stored locally)</span>
            </div>
            <div className="flex items-center gap-2">
              {history.length > 0 && (
                <button
                  onClick={clearHistory}
                  className="text-xs font-semibold text-[#A5A29C] hover:text-[#F87171] transition-colors"
                >
                  Clear History
                </button>
              )}
              <button
                onClick={() => setShowHistory(false)}
                className="text-xs font-semibold text-[#A5A29C] hover:text-[#F7F4EF]"
              >
                Close
              </button>
            </div>
          </div>

          {history.length === 0 ? (
            <div className="py-8 text-center text-xs text-[#A5A29C]">
              No practice runs recorded yet. Write some code and click &ldquo;Run Code&rdquo; to test your programs.
            </div>
          ) : (
            <div className="mt-3 grid gap-2.5 max-h-72 overflow-y-auto pr-1">
              {history.map((item) => (
                <div
                  key={item.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#2D2D2D] bg-[#1D1D1D] p-3 text-xs transition-all hover:border-[#3D3D3D]"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-[11px] font-bold uppercase rounded-md bg-[#282828] px-2 py-0.5 text-[#FF8A3D]">
                      {item.language}
                    </span>
                    {getStatusBadge(item.status, item.status_id)}
                    <span className="text-[11px] text-[#A5A29C]">{item.timestamp}</span>
                    {item.time_ms !== undefined && (
                      <span className="text-[11px] font-mono text-[#A5A29C] hidden sm:inline">
                        {item.time_ms}ms
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => restoreHistoryItem(item)}
                      className="rounded-lg border border-[#353535] bg-[#222222] px-2.5 py-1 text-[11px] font-bold text-[#F7F4EF] hover:border-[#FF6B2C] hover:text-[#FF8A3D] transition-all"
                    >
                      Reopen Code
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* ────── Main Workspace: Editor + Input/Output ────── */}
      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left Column: Monaco Code Editor & Stdin (lg:col-span-7) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="lux-card overflow-hidden border border-[#353535] bg-[#181818] shadow-md">
            {/* Editor Status Bar */}
            <div className="flex items-center justify-between border-b border-[#2D2D2D] bg-[#141414] px-4 py-2.5 text-xs">
              <div className="flex items-center gap-2.5">
                <FileCode className="h-3.5 w-3.5 text-[#FF8A3D]" />
                <span className="font-bold text-[#F7F4EF] uppercase tracking-wide text-[11px]">
                  {currentLangConfig.label} Workspace
                </span>
                <span className="rounded-full bg-[#242424] px-2 py-0.5 font-mono text-[10px] text-[#A5A29C]">
                  {currentLangConfig.version}
                </span>
              </div>
              <div className="flex items-center gap-3 text-[11px] text-[#A5A29C]">
                <span className="hidden sm:inline font-mono">
                  {currentSourceCode.split("\n").length} lines
                </span>
                <span className="flex items-center gap-1.5">
                  <span className={`h-2 w-2 rounded-full ${running ? "bg-[#FF6B2C] animate-pulse" : "bg-emerald-500"}`} />
                  <span>{running ? "Executing..." : "Sandbox Ready"}</span>
                </span>
              </div>
            </div>

            {/* Monaco Editor Container */}
            <div className="relative">
              <MonacoEditor
                height="480px"
                language={currentLangConfig.monacoLang}
                theme="vs-dark"
                value={currentSourceCode}
                onChange={(val) => handleCodeChange(val || "")}
                onMount={(editor) => {
                  // Bind Ctrl+Enter or Cmd+Enter to execute
                  editor.addCommand(
                    // monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter
                    2048 | 3,
                    () => {
                      runCode();
                    },
                  );
                }}
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  lineNumbers: "on",
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                  tabSize: 4,
                  fontFamily: "JetBrains Mono, monospace",
                  contextmenu: true,
                  wordWrap: "on",
                  padding: { top: 12, bottom: 12 },
                  renderLineHighlight: "all",
                  cursorBlinking: "smooth",
                }}
              />
            </div>

            {/* Standard Input (stdin) Panel */}
            <div className="border-t border-[#2D2D2D] bg-[#141414] p-3.5">
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => setShowStdin((prev) => !prev)}
                  className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-[#A5A29C] hover:text-[#F7F4EF] transition-colors"
                >
                  <Terminal className="h-3.5 w-3.5 text-[#FF8A3D]" />
                  <span>Custom Standard Input (stdin)</span>
                  {showStdin ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                </button>
                {stdin && (
                  <button
                    type="button"
                    onClick={() => setStdin("")}
                    className="text-[11px] text-[#A5A29C] hover:text-[#F87171] transition-colors"
                  >
                    Clear stdin
                  </button>
                )}
              </div>

              {showStdin && (
                <div className="mt-2 animate-fade-in">
                  <textarea
                    rows={3}
                    value={stdin}
                    onChange={(e) => setStdin(e.target.value)}
                    placeholder="Enter input to pass to program stdin when running (e.g., numbers, text, lines)..."
                    className="w-full rounded-lg border border-[#353535] bg-[#191919] p-2.5 font-mono text-xs text-[#F7F4EF] placeholder:text-[#77736D] outline-none transition-all focus:border-[#FF6B2C]"
                  />
                  <p className="mt-1 text-[10px] text-[#77736D]">
                    Input provided here will be piped into standard input (e.g., sys.stdin, scanf, cin, Scanner).
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Console & Execution Output (lg:col-span-5) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="lux-card overflow-hidden border border-[#353535] bg-[#181818] shadow-md flex flex-col h-full min-h-[580px]">
            {/* Output Panel Header */}
            <div className="flex items-center justify-between border-b border-[#2D2D2D] bg-[#141414] px-4 py-2.5 text-xs">
              <div className="flex items-center gap-2">
                <Terminal className="h-3.5 w-3.5 text-[#FF8A3D]" />
                <span className="font-bold text-[#F7F4EF] uppercase tracking-wide text-[11px]">
                  Execution Output
                </span>
              </div>
              {result && (
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleCopyOutput}
                    className="flex items-center gap-1 rounded-md bg-[#242424] px-2 py-0.5 text-[10px] font-semibold text-[#A5A29C] hover:text-[#F7F4EF] transition-colors"
                    title="Copy output to clipboard"
                  >
                    {copiedOutput ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                    <span>{copiedOutput ? "Copied" : "Copy"}</span>
                  </button>
                </div>
              )}
            </div>

            {/* Output Body */}
            <div className="flex-1 p-4 flex flex-col">
              {!result && !running && (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-6 text-[#A5A29C]">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#222222] border border-[#333333] text-[#A5A29C] mb-3">
                    <Terminal className="h-6 w-6" />
                  </div>
                  <h3 className="text-sm font-bold text-[#F7F4EF]">No Execution Output</h3>
                  <p className="mt-1 text-xs max-w-xs text-[#8A8680]">
                    Click <strong className="text-[#FF8A3D]">&ldquo;Run Code&rdquo;</strong> or press{" "}
                    <kbd className="rounded border border-[#444] bg-[#222] px-1.5 py-0.5 font-mono text-[10px] text-[#F7F4EF]">
                      Ctrl + Enter
                    </kbd>{" "}
                    to compile and execute in the secure sandbox.
                  </p>
                </div>
              )}

              {running && (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-6">
                  <div className="h-10 w-10 animate-spin rounded-full border-3 border-[#FF6B2C] border-t-transparent mb-4" />
                  <h3 className="text-sm font-bold text-[#F7F4EF]">Running Program...</h3>
                  <p className="mt-1 text-xs text-[#A5A29C]">
                    Transmitting code to Judge0 sandbox container for isolated execution...
                  </p>
                </div>
              )}

              {result && !running && (
                <div className="space-y-4 animate-fade-in flex flex-col flex-1">
                  {/* Status & Metrics Bar */}
                  <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[#2D2D2D] bg-[#141414] p-3">
                    <div className="flex items-center gap-2">
                      {getStatusBadge(result.status, result.status_id)}
                    </div>

                    <div className="flex items-center gap-3 text-[11px] font-mono text-[#A5A29C]">
                      {runtimeDisplay && (
                        <span className="flex items-center gap-1" title="Execution Time">
                          <Clock className="h-3 w-3 text-[#FF8A3D]" />
                          <span>{runtimeDisplay}</span>
                        </span>
                      )}
                      {memoryDisplay && (
                        <span className="flex items-center gap-1" title="Memory Consumption">
                          <Cpu className="h-3 w-3 text-[#FF8A3D]" />
                          <span>{memoryDisplay}</span>
                        </span>
                      )}
                      {result.exit_code !== undefined && result.exit_code !== null && (
                        <span className="text-[10px] text-[#77736D]">
                          Exit: {result.exit_code}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Output Category Tabs */}
                  <div className="flex gap-1.5 border-b border-[#2D2D2D] pb-2 text-xs">
                    <button
                      onClick={() => setActiveOutputTab("stdout")}
                      className={`rounded-lg px-3 py-1 font-bold transition-all ${
                        activeOutputTab === "stdout"
                          ? "bg-[#252525] text-[#FF8A3D] border border-[#3A3A3A]"
                          : "text-[#A5A29C] hover:text-[#F7F4EF]"
                      }`}
                    >
                      Stdout {result.stdout ? `(${result.stdout.length}B)` : ""}
                    </button>
                    {result.stderr && (
                      <button
                        onClick={() => setActiveOutputTab("stderr")}
                        className={`rounded-lg px-3 py-1 font-bold transition-all ${
                          activeOutputTab === "stderr"
                            ? "bg-rose-500/15 text-rose-300 border border-rose-500/30"
                            : "text-rose-400 hover:text-rose-300"
                        }`}
                      >
                        Stderr
                      </button>
                    )}
                    {result.compile_output && (
                      <button
                        onClick={() => setActiveOutputTab("compiler")}
                        className={`rounded-lg px-3 py-1 font-bold transition-all ${
                          activeOutputTab === "compiler"
                            ? "bg-amber-500/15 text-amber-300 border border-amber-500/30"
                            : "text-amber-400 hover:text-amber-300"
                        }`}
                      >
                        Compiler Diagnostics
                      </button>
                    )}
                  </div>

                  {/* Terminal Output Display Area */}
                  <div className="flex-1 rounded-xl border border-[#2D2D2D] bg-[#111111] p-3.5 overflow-auto max-h-[400px]">
                    {activeOutputTab === "stdout" && (
                      <pre className="font-mono text-xs leading-5 text-[#E0DDD5] whitespace-pre-wrap select-text">
                        {result.stdout
                          ? result.stdout
                          : result.status === "Accepted"
                            ? "Code executed successfully with return code 0 (no stdout produced)."
                            : "No standard output produced."}
                      </pre>
                    )}

                    {activeOutputTab === "stderr" && (
                      <pre className="font-mono text-xs leading-5 text-rose-300 whitespace-pre-wrap select-text">
                        {result.stderr || "No standard error."}
                      </pre>
                    )}

                    {activeOutputTab === "compiler" && (
                      <pre className="font-mono text-xs leading-5 text-amber-300 whitespace-pre-wrap select-text">
                        {result.compile_output || "No compilation errors reported."}
                      </pre>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
