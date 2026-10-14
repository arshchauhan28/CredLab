"use client";
/* eslint react-hooks/set-state-in-effect: off */

import { useCallback, useEffect, useMemo, useState, useRef } from "react";
import type { FormEvent } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import type { UserResponse } from "@/types/auth";
import { PROGRAM_OPTIONS } from "@/lib/academic-options";

type Course = {
  id: number;
  name: string;
  code?: string | null;
  program: string;
  year_of_study: string;
  semester: string;
  academic_year?: string | null;
  faculty_names?: string[];
  lab_count?: number;
};

type Lab = {
  id: number;
  course_id: number;
  title: string;
  description?: string | null;
  is_published: boolean;
  practical_count: number;
  courseName?: string;
  program?: string;
};

type Practical = {
  id: number;
  lab_id: number;
  question_id: number;
  question_title?: string | null;
  effective_title: string;
  sequence_number: number;
  status: "LOCKED" | "AVAILABLE" | "COMPLETED";
  is_unlocked: boolean;
  best_score?: number | null;
  lock_reason?: string | null;
  instructions?: string | null;
};

type Question = {
  id: number;
  title: string;
  description: string;
  input_format?: string | null;
  output_format?: string | null;
  constraints?: string | null;
  status?: string;
  allowed_languages: string[];
  examples: { input: string; output: string; explanation?: string | null }[];
};

type Submission = {
  id: number;
  question_id: number;
  practical_id?: number | null;
  language: string;
  status: string;
  total_test_cases: number;
  passed_test_cases: number;
  score: number;
  created_at: string;
};

type CertificateData = {
  certificates: {
    id: string;
    status: string;
    lab_title: string;
    practical_title: string;
    issued_at: string;
    payload_digest: string;
  }[];
  requests: {
    id: number;
    lab_id: number;
    lab_title: string;
    status: string;
    review_note?: string | null;
    requested_at: string;
  }[];
};

type StudentProgressItem = {
  course_id: number;
  course_name: string;
  course_code: string;
  total_required: number;
  completed_required: number;
  remaining_required: number;
  completion_percentage: number;
  badges_earned: number;
  certificate_status: "NOT_ELIGIBLE" | "ELIGIBLE" | "PENDING_APPROVAL" | "REJECTED" | "ISSUED";
  certificate_id?: string | null;
  rejection_note?: string | null;
};

type BadgeItem = {
  id: number;
  name: string;
  description?: string;
  icon: string;
  earned_at: string;
  practical_id: number;
  course_id?: number | null;
  meta?: Record<string, unknown> | null;
};

type Tab = "Overview" | "My Labs" | "Submissions" | "Statistics" | "Achievements" | "Profile";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[420px] flex-col items-center justify-center gap-3 text-xs text-[#806777] bg-[#1e1e1e]">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#BE5678] border-t-transparent" />
      <span>Loading code editor...</span>
    </div>
  ),
});

const DEFAULT_LANGUAGES = [
  {
    value: "python",
    label: "Python 3",
    starter: "# Write your solution below\nimport sys\n\ndef main():\n    lines = sys.stdin.read().splitlines()\n    if not lines:\n        return\n    # Process input here\n\nif __name__ == '__main__':\n    main()\n",
  },
  {
    value: "cpp",
    label: "C++ (GCC)",
    starter: "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios_base::sync_with_stdio(false);\n    cin.tie(NULL);\n    // Write your solution here\n    return 0;\n}\n",
  },
  {
    value: "c",
    label: "C (GCC)",
    starter: "#include <stdio.h>\n#include <stdlib.h>\n\nint main(void) {\n    // Write your solution here\n    return 0;\n}\n",
  },
  {
    value: "java",
    label: "Java 17",
    starter: "import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner scanner = new Scanner(System.in);\n        // Write your solution here\n    }\n}\n",
  },
  {
    value: "javascript",
    label: "JavaScript (Node.js)",
    starter: '"use strict";\nconst fs = require("fs");\n\nfunction main() {\n    const input = fs.readFileSync(0, "utf-8");\n    // Write your solution here\n}\nmain();\n',
  },
  {
    value: "typescript",
    label: "TypeScript",
    starter: 'import * as fs from "fs";\n\nfunction main(): void {\n    const input = fs.readFileSync(0, "utf-8");\n    // Write your solution here\n}\nmain();\n',
  },
  {
    value: "go",
    label: "Go",
    starter: "package main\n\nimport (\n\t\"bufio\"\n\t\"fmt\"\n\t\"os\"\n)\n\nfunc main() {\n\tscanner := bufio.NewScanner(os.Stdin)\n\t_ = scanner\n\t// Write your solution here\n}\n",
  },
  {
    value: "rust",
    label: "Rust",
    starter: "use std::io::{self, Read};\n\nfn main() {\n    let mut input = String::new();\n    io::stdin().read_to_string(&mut input).unwrap();\n    // Write your solution here\n}\n",
  },
];

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(`/api/proxy/${path.replace(/^\/+/, "")}`, {
    ...init,
    cache: "no-store",
    headers,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    let errorMessage = `Request failed (${response.status})`;
    if (typeof body.detail === "string") {
      errorMessage = body.detail;
    } else if (Array.isArray(body.detail)) {
      errorMessage = body.detail.map((err: { msg?: string }) => err.msg || JSON.stringify(err)).join(", ");
    } else if (typeof body.message === "string") {
      errorMessage = body.message;
    }
    throw new Error(errorMessage);
  }
  return body as T;
}

export default function StudentDashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserResponse | null>(null);
  const [tab, setTab] = useState<Tab>("Overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Academic Course & Lab Data
  const [courses, setCourses] = useState<Course[]>([]);
  const [labsByCourse, setLabsByCourse] = useState<Record<number, Lab[]>>({});
  const [practicalsByLab, setPracticalsByLab] = useState<Record<number, Practical[]>>({});
  const [, setPracticalLoadStates] = useState<Record<number, string>>({});

  // Submissions & Certificates
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [certificateData, setCertificateData] = useState<CertificateData>({
    certificates: [],
    requests: [],
  });

  // Profile Form
  const [profileOpen, setProfileOpen] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileMessage, setProfileMessage] = useState("");
  const [profileError, setProfileError] = useState("");
  const [profile, setProfile] = useState({
    student_id_number: "",
    academic_course: "B.Tech (AI & DS)",
    year_of_study: "1st Year",
    semester: "Semester 1",
    academic_year: "2026-2027",
  });

  // Active Lab & Practical Workspace
  const [selectedLab, setSelectedLab] = useState<number | null>(null);
  const [selectedPractical, setSelectedPractical] = useState<Practical | null>(null);
  const [question, setQuestion] = useState<Question | null>(null);
  const [questionLoading, setQuestionLoading] = useState(false);
  const [questionError, setQuestionError] = useState("");
  const [language, setLanguage] = useState("python");
  const [sourceCode, setSourceCode] = useState(DEFAULT_LANGUAGES[0].starter);
  const [stdin, setStdin] = useState("");
  const [running, setRunning] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [consoleResult, setConsoleResult] = useState<{
    title: string;
    body: string;
    tone: "ok" | "bad" | "neutral";
  } | null>(null);
  const [lastSubmissionId, setLastSubmissionId] = useState<number | null>(null);
  const [aiFeedback, setAiFeedback] = useState("");
  const [feedbackBusy, setFeedbackBusy] = useState(false);
  const [logoutBusy, setLogoutBusy] = useState(false);
  const [pasteBlocked, setPasteBlocked] = useState(false);
  const [studentProgress, setStudentProgress] = useState<StudentProgressItem[]>([]);
  const [earnedBadges, setEarnedBadges] = useState<BadgeItem[]>([]);
  const [requestingCertCourseId, setRequestingCertCourseId] = useState<number | null>(null);
  const [certRequestMessage, setCertRequestMessage] = useState("");

  // Editor mode: Monaco vs Native Textarea Fallback
  const [useFallbackEditor, setUseFallbackEditor] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const handleTextareaKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Tab") {
      e.preventDefault();
      const target = e.currentTarget;
      const start = target.selectionStart;
      const end = target.selectionEnd;
      const val = target.value;
      const nextVal = val.substring(0, start) + "    " + val.substring(end);
      setSourceCode(nextVal);
      setTimeout(() => {
        target.selectionStart = target.selectionEnd = start + 4;
      }, 0);
    }
  };

  const loadPracticals = useCallback(async (labId: number) => {
    setPracticalLoadStates((states) => ({ ...states, [labId]: "loading" }));
    try {
      const practicals = await api<Practical[]>(`labs/${labId}/practicals`);
      setPracticalsByLab((current) => ({ ...current, [labId]: practicals }));
      setPracticalLoadStates((states) => ({ ...states, [labId]: "loaded" }));
    } catch {
      setPracticalLoadStates((states) => ({ ...states, [labId]: "error" }));
    }
  }, []);

  const refreshWorkspace = useCallback(async () => {
    try {
      const courseList = await api<Course[]>("courses");
      setCourses(courseList);

      const labEntries = await Promise.all(
        courseList.map(async (course) => {
          try {
            const list = await api<Lab[]>(`courses/${course.id}/labs`);
            return [course.id, list] as const;
          } catch {
            return [course.id, []] as const;
          }
        }),
      );
      const labMap: Record<number, Lab[]> = Object.fromEntries(labEntries);
      setLabsByCourse(labMap);

      const allLabs = Object.values(labMap).flat();
      allLabs.forEach((lab) => {
        void loadPracticals(lab.id);
      });

      const [submissionData, certificates, progressData] = await Promise.all([
        api<{ items: Submission[]; total: number }>("submissions?page=1&page_size=100").catch(
          () => ({ items: [], total: 0 }),
        ),
        api<CertificateData>("certificates/mine").catch(() => ({
          certificates: [],
          requests: [],
        })),
        api<{ subjects: StudentProgressItem[]; badges: BadgeItem[] }>(
          "certificates/student-progress",
        ).catch(() => ({
          subjects: [],
          badges: [],
        })),
      ]);
      setSubmissions(submissionData.items ?? []);
      setCertificateData(certificates);
      setStudentProgress(progressData.subjects ?? []);
      setEarnedBadges(progressData.badges ?? []);
    } catch (err) {
      console.error("Workspace refresh error:", err);
    }
  }, [loadPracticals]);

  const handleRequestSubjectCert = async (targetCourseId: number) => {
    setRequestingCertCourseId(targetCourseId);
    setCertRequestMessage("");
    try {
      await api("certificates/subject-requests", {
        method: "POST",
        body: JSON.stringify({ course_id: targetCourseId }),
      });
      setCertRequestMessage(
        "Subject certificate request submitted successfully to faculty for review!",
      );
      await refreshWorkspace();
    } catch (cause) {
      setCertRequestMessage(
        cause instanceof Error ? cause.message : "Failed to request subject certificate.",
      );
    } finally {
      setRequestingCertCourseId(null);
    }
  };

  useEffect(() => {
    let cancelled = false;
    async function init() {
      try {
        const response = await fetch("/api/auth/session", { cache: "no-store" });
        if (response.status === 401) {
          router.replace("/login");
          return;
        }
        if (!response.ok) throw new Error("Unable to verify account session.");
        const session = (await response.json()) as { user: UserResponse };
        if (session.user.role !== "STUDENT") {
          router.replace(
            session.user.role === "FACULTY" ? "/faculty/dashboard" : "/admin/dashboard",
          );
          return;
        }
        if (cancelled) return;
        setUser(session.user);
        setProfile({
          student_id_number: session.user.student_id_number || "",
          academic_course: session.user.academic_course || PROGRAM_OPTIONS[2],
          year_of_study: session.user.year_of_study || "1st Year",
          semester: session.user.semester || "Semester 1",
          academic_year: session.user.academic_year || "2026-2027",
        });
        setProfileOpen(!session.user.profile_completed);
        await refreshWorkspace();
      } catch (cause) {
        if (!cancelled)
          setError(
            cause instanceof Error ? cause.message : "Unable to load student workspace.",
          );
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void init();
    return () => {
      cancelled = true;
    };
  }, [refreshWorkspace, router]);

  const allLabs = useMemo(() => {
    const list: (Lab & { courseName: string })[] = [];
    courses.forEach((course) => {
      (labsByCourse[course.id] || []).forEach((lab) => {
        list.push({
          ...lab,
          courseName: course.name,
          program: course.program,
        });
      });
    });
    return list;
  }, [courses, labsByCourse]);

  const selectLab = (labId: number) => {
    setSelectedLab(labId);
    void loadPracticals(labId);
    const existing = practicalsByLab[labId];
    if (existing && existing.length > 0) {
      const available = existing.find((p) => p.is_unlocked) || existing[0];
      selectPractical(available);
    } else {
      setSelectedPractical(null);
      setQuestion(null);
    }
  };

  const selectPractical = async (p: Practical) => {
    setSelectedPractical(p);
    setQuestionLoading(true);
    setQuestionError("");
    setConsoleResult(null);
    setAiFeedback("");
    setLastSubmissionId(null);
    try {
      if (!p.question_id) {
        throw new Error("This practical does not have an assigned question.");
      }
      const q = await api<Question>(`questions/${p.question_id}`);
      if (!q || q.status !== "PUBLISHED") {
        throw new Error(
          `Practical challenge content is not yet published (status: ${q?.status || "unpublished"}). Please contact your instructor.`,
        );
      }
      setQuestion(q);
      const chosenLang = q.allowed_languages?.includes(language)
        ? language
        : q.allowed_languages?.[0] || "python";
      setLanguage(chosenLang);
      const starter =
        DEFAULT_LANGUAGES.find((l) => l.value === chosenLang)?.starter ||
        `# Solution for ${p.effective_title}\n`;
      setSourceCode(starter);
    } catch (cause) {
      setQuestion(null);
      setQuestionError(cause instanceof Error ? cause.message : "Unable to load problem details.");
    } finally {
      setQuestionLoading(false);
    }
  };

  const handleLanguageChange = (newLang: string) => {
    setLanguage(newLang);
    const starter = DEFAULT_LANGUAGES.find((l) => l.value === newLang)?.starter || "";
    if (
      !sourceCode.trim() ||
      DEFAULT_LANGUAGES.some((l) => l.starter.trim() === sourceCode.trim())
    ) {
      setSourceCode(starter);
    }
  };

  const resetCode = () => {
    const starter = DEFAULT_LANGUAGES.find((l) => l.value === language)?.starter || "";
    setSourceCode(starter);
  };

  const runCode = async () => {
    if (!question) return;
    setRunning(true);
    setConsoleResult(null);
    try {
      const result = await api<{
        stdout?: string;
        stderr?: string;
        compile_output?: string;
        status?: { description: string };
        time?: string;
        memory?: number;
      }>("execute", {
        method: "POST",
        body: JSON.stringify({
          question_id: question.id,
          language,
          source_code: sourceCode,
          stdin: stdin,
        }),
      });

      const body =
        result.stderr ||
        result.compile_output ||
        result.stdout ||
        "Code executed successfully (no stdout produced).";
      const tone = result.stderr || result.compile_output ? "bad" : "ok";
      setConsoleResult({
        title: result.status?.description || (tone === "ok" ? "Execution Successful" : "Execution Error"),
        body: `${body}${result.time ? `\n\n[Runtime: ${result.time}s | Memory: ${result.memory ?? 0}KB]` : ""}`,
        tone,
      });
    } catch (cause) {
      setConsoleResult({
        title: "Sandbox Error",
        body: cause instanceof Error ? cause.message : "Failed to execute code in sandbox.",
        tone: "bad",
      });
    } finally {
      setRunning(false);
    }
  };

  const submitSolution = async () => {
    if (!question || !selectedPractical) return;
    setSubmitting(true);
    setConsoleResult(null);
    try {
      const result = await api<{
        id: number;
        status: string;
        total_test_cases: number;
        passed_test_cases: number;
        score: number;
        test_case_results?: {
          test_case_id: number;
          passed: boolean;
          status: string;
          stdout?: string;
          stderr?: string;
        }[];
      }>("submissions", {
        method: "POST",
        body: JSON.stringify({
          question_id: question.id,
          practical_id: selectedPractical.id,
          language,
          source_code: sourceCode,
        }),
      });

      setLastSubmissionId(result.id);
      const isAccepted = result.status === "ACCEPTED" || result.score === 100;

      let details = `Score: ${result.score}% (${result.passed_test_cases}/${result.total_test_cases} test cases passed)\nStatus: ${result.status}`;
      if (result.test_case_results && result.test_case_results.length > 0) {
        details += "\n\nTest Case Results:\n";
        result.test_case_results.forEach((tc, idx) => {
          details += `• Test Case #${idx + 1}: ${tc.passed ? "PASSED ✓" : "FAILED ✗"} (${tc.status})\n`;
        });
      }

      setConsoleResult({
        title: isAccepted ? "Accepted ✓" : `Submission: ${result.status}`,
        body: details,
        tone: isAccepted ? "ok" : "bad",
      });

      if (selectedLab) {
        void loadPracticals(selectedLab);
      }
      void refreshWorkspace();
    } catch (cause) {
      setConsoleResult({
        title: "Submission Failed",
        body: cause instanceof Error ? cause.message : "Unable to submit solution.",
        tone: "bad",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const requestAiFeedback = async () => {
    if (!lastSubmissionId) return;
    setFeedbackBusy(true);
    try {
      const res = await api<{ feedback: string }>(`submissions/${lastSubmissionId}/feedback`, {
        method: "GET",
      });
      setAiFeedback(res.feedback);
    } catch (cause) {
      setAiFeedback(cause instanceof Error ? cause.message : "AI feedback unavailable.");
    } finally {
      setFeedbackBusy(false);
    }
  };

  const handleProfileSave = async (e: FormEvent) => {
    e.preventDefault();
    setProfileSaving(true);
    setProfileError("");
    setProfileMessage("");
    try {
      const updated = await api<UserResponse>("profile", {
        method: "PUT",
        body: JSON.stringify(profile),
      });
      setUser(updated);
      setProfileMessage("Academic profile updated successfully.");
      setProfileOpen(false);
      void refreshWorkspace();
    } catch (cause) {
      setProfileError(cause instanceof Error ? cause.message : "Unable to update profile.");
    } finally {
      setProfileSaving(false);
    }
  };

  const logout = async () => {
    setLogoutBusy(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } finally {
      router.replace("/login");
      router.refresh();
    }
  };

  if (loading) {
    return (
      <main
        className="flex min-h-screen items-center justify-center"
        style={{ backgroundColor: "var(--color-background)" }}
      >
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 animate-spin rounded-full border-3 border-[#9F1239] border-t-transparent" />
          <p className="text-sm font-semibold text-[#806777]">
            Loading university laboratory workspace...
          </p>
        </div>
      </main>
    );
  }

  if (error || !user) {
    return (
      <main
        className="flex min-h-screen items-center justify-center p-6"
        style={{ backgroundColor: "var(--color-background)" }}
      >
        <section className="lux-card max-w-lg p-8 text-center shadow-xl border border-[#F0DCE5]">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl badge-danger text-xl">
            ⚠
          </div>
          <h1 className="mt-4 text-xl font-bold text-[#3F1024]">Unable to load workspace</h1>
          <p className="mt-2 text-sm leading-6 text-[#806777]">
            {error || "Your session has expired. Please sign in again."}
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <button
              onClick={() => window.location.reload()}
              className="btn-secondary !py-2.5 !text-xs font-bold"
            >
              Reload Page
            </button>
            <Link href="/login" className="btn-primary !py-2.5 !text-xs font-bold">
              Sign In
            </Link>
          </div>
        </section>
      </main>
    );
  }

  const tabs: Tab[] = ["Overview", "My Labs", "Submissions", "Statistics", "Achievements", "Profile"];
  const allPracticals = Object.values(practicalsByLab).flat();
  const completedCount = allPracticals.filter((p) => p.status === "COMPLETED").length;
  const acceptedSubmissions = submissions.filter((s) => s.status === "ACCEPTED" || s.score === 100);

  return (
    <main className="min-h-screen" style={{ backgroundColor: "var(--color-background)" }}>
      {/* ────── Sticky Institutional Topbar ────── */}
      <header className="sticky top-0 z-30 border-b border-[#F0DCE5] bg-[#FFFFFF]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3.5 sm:px-8">
          <Link href="/student/dashboard" className="flex items-center gap-3 group">
            <span
              className="flex h-10 w-10 items-center justify-center rounded-xl text-lg font-bold text-white shadow-xs"
              style={{ background: "var(--primary-gradient)" }}
            >
              ⬡
            </span>
            <div>
              <p className="text-sm font-bold tracking-tight text-[#3F1024]">LabOS</p>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-[#BE5678]">
                Student Laboratory Workspace
              </p>
            </div>
          </Link>

          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 rounded-full px-3 py-1 text-xs font-bold sm:flex badge-primary">
              <span className="h-2 w-2 rounded-full bg-[#9F1239]" />
              <span>{user.enrollment_number || "Student"}</span>
            </div>

            <button
              onClick={logout}
              disabled={logoutBusy}
              className="btn-secondary !py-1.5 !px-3.5 !text-xs font-bold"
            >
              {logoutBusy ? "Signing out..." : "Sign Out"}
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-8 sm:py-8">
        {/* ────── Hero Banner ────── */}
        <section className="lux-card p-6 sm:p-8 bg-gradient-to-r from-[#FFFFFF] via-[#FFF7FA] to-[#FBEAF0] border border-[#F0DCE5]">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-[#F0DCE5] bg-[#FFFFFF] px-3 py-1 text-[11px] font-bold text-[#9F1239]">
                Academic Session {user.academic_year || "2026-2027"}
              </div>
              <h1 className="mt-2.5 text-2xl font-extrabold tracking-tight text-[#3F1024] sm:text-3xl">
                Welcome back, {user.name}
              </h1>
              <p className="mt-1 text-xs sm:text-sm text-[#806777]">
                Continuous programming practicals, automated sandbox evaluations, and milestone
                diplomas.
              </p>
            </div>

            <div className="flex flex-wrap gap-2 text-xs">
              <span className="rounded-xl px-3 py-2 font-bold bg-[#FFFFFF] border border-[#F0DCE5] text-[#3F1024]">
                {user.academic_course || "Course Not Assigned"}
              </span>
              <span className="rounded-xl px-3 py-2 font-bold bg-[#FFFFFF] border border-[#F0DCE5] text-[#3F1024]">
                {user.year_of_study || "1st Year"} · {user.semester || "Semester 1"}
              </span>
            </div>
          </div>
        </section>

        {/* ────── Navigation Tabs ────── */}
        <nav
          className="mt-6 flex gap-1.5 overflow-x-auto rounded-2xl p-1.5 bg-[#FFFFFF] border border-[#F0DCE5]"
          aria-label="Student Navigation"
        >
          {tabs.map((item) => (
            <button
              key={item}
              onClick={() => {
                setTab(item);
                if (item === "My Labs" && !selectedLab && allLabs.length > 0) {
                  selectLab(allLabs[0].id);
                }
              }}
              className={`shrink-0 rounded-xl px-4 py-2 text-xs font-bold transition-all ${
                tab === item
                  ? "text-white shadow-sm"
                  : "text-[#806777] hover:bg-[#FBEAF0] hover:text-[#9F1239]"
              }`}
              style={tab === item ? { background: "var(--primary-gradient)" } : undefined}
            >
              {item}
            </button>
          ))}
        </nav>

        {profileMessage && (
          <div
            role="status"
            className="mt-4 rounded-xl p-3.5 text-xs font-semibold badge-success animate-fade-in"
          >
            {profileMessage}
          </div>
        )}

        {/* ───────────────── TAB: OVERVIEW ───────────────── */}
        {tab === "Overview" && (
          <div className="mt-6 space-y-6 animate-fade-in">
            {/* KPI Cards */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                { label: "Enrolled Courses", value: courses.length, icon: "📚", color: "text-[#9F1239]" },
                { label: "Available Labs", value: allLabs.length, icon: "🔬", color: "text-[#BE5678]" },
                {
                  label: "Completed Practicals",
                  value: `${completedCount} / ${allPracticals.length || 0}`,
                  icon: "✓",
                  color: "text-emerald-700",
                },
                {
                  label: "Passed Submissions",
                  value: acceptedSubmissions.length,
                  icon: "🏆",
                  color: "text-amber-700",
                },
              ].map((card) => (
                <div key={card.label} className="lux-card p-5 card-hover">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-bold uppercase tracking-wider text-[#806777]">
                      {card.label}
                    </p>
                    <span className="text-xl">{card.icon}</span>
                  </div>
                  <p className={`mt-3 text-3xl font-extrabold ${card.color}`}>{card.value}</p>
                </div>
              ))}
            </div>

            {/* Enrolled Labs Grid */}
            <section className="lux-card p-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-bold text-[#3F1024]">Your Enrolled Laboratories</h2>
                  <p className="mt-0.5 text-xs text-[#806777]">
                    Practicals assigned according to your academic program and semester.
                  </p>
                </div>

                <button
                  onClick={() => {
                    setTab("My Labs");
                    if (allLabs.length) selectLab(allLabs[0].id);
                  }}
                  className="btn-primary !py-2 !px-4 !text-xs font-bold"
                >
                  Enter Code Editor →
                </button>
              </div>

              {allLabs.length > 0 ? (
                <div className="mt-5 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {allLabs.map((lab) => (
                    <button
                      key={lab.id}
                      onClick={() => {
                        selectLab(lab.id);
                        setTab("My Labs");
                      }}
                      className="lux-card p-5 text-left transition-all card-hover bg-[#FFFFFF]"
                    >
                      <div className="flex items-center justify-between">
                        <span className="badge-primary px-2.5 py-0.5 text-[10px] font-bold rounded-md">
                          {lab.program}
                        </span>
                        <span className="text-xs font-semibold text-[#806777]">
                          {lab.practical_count} Practicals
                        </span>
                      </div>
                      <h3 className="mt-3 font-bold text-[#3F1024]">{lab.title}</h3>
                      <p className="mt-1 text-xs text-[#806777]">{lab.courseName}</p>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="mt-6 text-center py-10">
                  <p className="text-sm font-semibold text-[#806777]">
                    No published laboratories match your academic program yet.
                  </p>
                </div>
              )}
            </section>
          </div>
        )}

        {/* ───────────────── TAB: MY LABS (LEETCODE / CURSOR IDE) ───────────────── */}
        {tab === "My Labs" && (
          <div className="mt-6 space-y-6 animate-fade-in">
            {/* Lab Switcher Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 lux-card p-4">
              <div className="flex items-center gap-3 overflow-x-auto">
                <span className="text-xs font-bold uppercase tracking-wider text-[#806777]">
                  Active Lab:
                </span>
                {allLabs.map((l) => (
                  <button
                    key={l.id}
                    onClick={() => selectLab(l.id)}
                    className={`rounded-xl px-3.5 py-1.5 text-xs font-bold transition-all ${
                      selectedLab === l.id
                        ? "text-white shadow-xs"
                        : "bg-[#FFF7FA] text-[#3F1024] hover:bg-[#FBEAF0] border border-[#F0DCE5]"
                    }`}
                    style={selectedLab === l.id ? { background: "var(--primary-gradient)" } : undefined}
                  >
                    {l.title}
                  </button>
                ))}
              </div>

              {/* Practicals sequence badges */}
              {selectedLab && practicalsByLab[selectedLab] && (
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-[#806777]">Sequential Progress:</span>
                  <div className="flex gap-1.5">
                    {practicalsByLab[selectedLab].map((p) => (
                      <button
                        key={p.id}
                        onClick={() => selectPractical(p)}
                        className={`flex h-7 w-7 items-center justify-center rounded-lg text-xs font-bold transition-all ${
                          selectedPractical?.id === p.id
                            ? "bg-[#9F1239] text-white ring-2 ring-[#BE5678]"
                            : p.status === "COMPLETED"
                            ? "bg-[#ECFDF5] text-emerald-800 border border-[#A7F3D0]"
                            : p.is_unlocked
                            ? "bg-[#FFF7FA] text-[#3F1024] border border-[#F0DCE5]"
                            : "bg-slate-100 text-slate-400 opacity-60 cursor-not-allowed"
                        }`}
                        title={`Practical #${p.sequence_number}: ${p.effective_title}`}
                      >
                        {p.status === "COMPLETED" ? "✓" : p.sequence_number}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Split Screen Workspace */}
            <div className="grid gap-6 lg:grid-cols-[1.05fr_1.35fr]">
              {/* Left Column: Problem Statement & Test Cases */}
              <div className="space-y-4">
                <div className="lux-card p-6">
                  {questionLoading ? (
                    <div className="flex h-64 flex-col items-center justify-center gap-2 text-xs text-[#806777]">
                      <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#9F1239] border-t-transparent" />
                      <span>Loading problem definition...</span>
                    </div>
                  ) : questionError ? (
                    <div className="badge-danger p-4 rounded-xl text-xs">{questionError}</div>
                  ) : question ? (
                    <div className="space-y-5">
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="badge-primary px-2.5 py-0.5 text-[10px] font-bold rounded-md">
                            Practical #{selectedPractical?.sequence_number || 1}
                          </span>
                          <span className="text-xs font-semibold text-[#806777]">
                            Allowed: {question.allowed_languages?.join(", ") || "All"}
                          </span>
                        </div>
                        <h2 className="mt-2 text-xl font-extrabold text-[#3F1024]">{question.title}</h2>
                      </div>

                      <div className="prose max-w-none text-xs leading-relaxed text-[#3F1024] whitespace-pre-line">
                        {question.description}
                      </div>

                      {question.input_format && (
                        <div>
                          <h3 className="text-xs font-bold uppercase tracking-wider text-[#BE5678]">
                            Input Format
                          </h3>
                          <p className="mt-1 text-xs text-[#806777] bg-[#FFF7FA] p-3 rounded-xl border border-[#F0DCE5]">
                            {question.input_format}
                          </p>
                        </div>
                      )}

                      {question.output_format && (
                        <div>
                          <h3 className="text-xs font-bold uppercase tracking-wider text-[#BE5678]">
                            Output Format
                          </h3>
                          <p className="mt-1 text-xs text-[#806777] bg-[#FFF7FA] p-3 rounded-xl border border-[#F0DCE5]">
                            {question.output_format}
                          </p>
                        </div>
                      )}

                      {question.constraints && (
                        <div>
                          <h3 className="text-xs font-bold uppercase tracking-wider text-[#BE5678]">
                            Constraints
                          </h3>
                          <pre className="mt-1 font-mono text-xs text-[#3F1024] bg-[#FFF7FA] p-3 rounded-xl border border-[#F0DCE5]">
                            {question.constraints}
                          </pre>
                        </div>
                      )}

                      {question.examples && question.examples.length > 0 && (
                        <div className="space-y-3">
                          <h3 className="text-xs font-bold uppercase tracking-wider text-[#BE5678]">
                            Sample Test Cases
                          </h3>
                          {question.examples.map((ex, i) => (
                            <div
                              key={i}
                              className="rounded-xl border border-[#F0DCE5] bg-[#FFF7FA] p-3.5 space-y-2"
                            >
                              <div className="flex items-center justify-between text-[11px] font-bold text-[#806777]">
                                <span>Example {i + 1}</span>
                                <button
                                  type="button"
                                  onClick={() => setStdin(ex.input)}
                                  className="text-[10px] font-bold text-[#9F1239] hover:underline"
                                >
                                  Copy to Custom Input
                                </button>
                              </div>
                              <div className="grid grid-cols-2 gap-2 text-xs">
                                <div>
                                  <span className="text-[10px] uppercase font-bold text-[#806777]">
                                    Input:
                                  </span>
                                  <pre className="mt-0.5 rounded-lg bg-[#FFFFFF] p-2 font-mono text-[11px] text-[#3F1024] border border-[#F0DCE5]">
                                    {ex.input}
                                  </pre>
                                </div>
                                <div>
                                  <span className="text-[10px] uppercase font-bold text-[#806777]">
                                    Expected Output:
                                  </span>
                                  <pre className="mt-0.5 rounded-lg bg-[#FFFFFF] p-2 font-mono text-[11px] text-[#3F1024] border border-[#F0DCE5]">
                                    {ex.output}
                                  </pre>
                                </div>
                              </div>
                              {ex.explanation && (
                                <p className="text-[11px] text-[#806777]">
                                  <span className="font-bold">Explanation:</span> {ex.explanation}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-center py-12 text-xs text-[#806777]">
                      Select a practical from the top bar to inspect problem specifications.
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column: Code Editor & Execution Terminal */}
              <div className="space-y-4">
                <div className="lux-card overflow-hidden border border-[#F0DCE5]">
                  {/* Editor Header Bar */}
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#F0DCE5] bg-[#FFF7FA] px-4 py-3">
                    <div className="flex items-center gap-2">
                      <select
                        value={language}
                        onChange={(e) => handleLanguageChange(e.target.value)}
                        className="rounded-lg border border-[#F0DCE5] bg-[#FFFFFF] px-3 py-1.5 text-xs font-bold text-[#3F1024] outline-none"
                      >
                        {DEFAULT_LANGUAGES.map((l) => (
                          <option key={l.value} value={l.value}>
                            {l.label}
                          </option>
                        ))}
                      </select>

                      <button
                        type="button"
                        onClick={resetCode}
                        className="rounded-lg px-2.5 py-1.5 text-xs font-bold text-[#806777] hover:bg-[#FBEAF0] hover:text-[#9F1239] transition-colors"
                        title="Reset code template"
                      >
                        Reset
                      </button>

                      <button
                        type="button"
                        onClick={() => setUseFallbackEditor((v) => !v)}
                        className="text-[11px] font-semibold text-[#806777] hover:text-[#9F1239] transition-colors underline ml-1"
                      >
                        {useFallbackEditor ? "Use Monaco" : "Plain Editor"}
                      </button>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={runCode}
                        disabled={running || submitting || !question}
                        className="btn-secondary !py-1.5 !px-3.5 !text-xs font-bold"
                      >
                        {running ? "Running..." : "▶ Run Code"}
                      </button>

                      <button
                        onClick={submitSolution}
                        disabled={running || submitting || !question}
                        className="btn-primary !py-1.5 !px-4 !text-xs font-bold shadow-xs"
                      >
                        {submitting ? "Submitting..." : "Submit Solution ✓"}
                      </button>
                    </div>
                  </div>

                  {/* Monaco / Textarea Code Surface with Paste Restrictions */}
                  <div className="relative min-h-[460px] bg-[#1e1e1e]">
                    {pasteBlocked && (
                      <div className="absolute top-3 right-3 z-50 flex items-center gap-2 rounded-xl bg-[#BE123C] border border-[#FDA4AF] px-4 py-2.5 text-xs font-bold text-white shadow-2xl backdrop-blur-md animate-fade-in">
                        <span className="text-base">??</span>
                        <span>Paste disabled: Code pasting is restricted in this assessment environment. Please type your code manually.</span>
                      </div>
                    )}
                    {useFallbackEditor ? (
                      <textarea
                        ref={textareaRef}
                        value={sourceCode}
                        onChange={(e) => setSourceCode(e.target.value)}
                        onKeyDown={(e) => {
                          handleTextareaKeyDown(e);
                          const isPaste =
                            ((e.ctrlKey || e.metaKey) && (e.key === "v" || e.key === "V")) ||
                            (e.shiftKey && e.key === "Insert");
                          if (isPaste) {
                            e.preventDefault();
                            setPasteBlocked(true);
                            setTimeout(() => setPasteBlocked(false), 3500);
                          }
                        }}
                        onPaste={(e) => {
                          e.preventDefault();
                          setPasteBlocked(true);
                          setTimeout(() => setPasteBlocked(false), 3500);
                        }}
                        spellCheck={false}
                        className="h-[460px] w-full resize-none p-4 font-mono text-xs leading-5 text-[#d4d4d4] bg-[#1e1e1e] outline-none"
                      />
                    ) : (
                      <MonacoEditor
                        height="460px"
                        language={language === "c" || language === "cpp" ? "cpp" : language}
                        theme="vs-dark"
                        value={sourceCode}
                        onChange={(val) => setSourceCode(val || "")}
                        onMount={(editor, monaco) => {
                          editor.onKeyDown((e) => {
                            const isPaste =
                              ((e.ctrlKey || e.metaKey) && e.keyCode === monaco.KeyCode.KeyV) ||
                              (e.shiftKey && e.keyCode === monaco.KeyCode.Insert);
                            if (isPaste) {
                              e.preventDefault();
                              e.stopPropagation();
                              setPasteBlocked(true);
                              setTimeout(() => setPasteBlocked(false), 3500);
                            }
                          });
                          const domNode = editor.getDomNode();
                          if (domNode) {
                            domNode.addEventListener(
                              "paste",
                              (e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                setPasteBlocked(true);
                                setTimeout(() => setPasteBlocked(false), 3500);
                              },
                              true,
                            );
                          }
                        }}
                        options={{
                          minimap: { enabled: false },
                          fontSize: 13,
                          lineNumbers: "on",
                          scrollBeyondLastLine: false,
                          automaticLayout: true,
                          tabSize: 4,
                          fontFamily: "JetBrains Mono, monospace",
                          contextmenu: false,
                        }}
                      />
                    )}
                  </div>

                  {/* Stdin Drawer */}
                  <div className="border-t border-[#F0DCE5] bg-[#FFFFFF] p-3">
                    <label className="block text-[11px] font-bold uppercase tracking-wider text-[#806777]">
                      Custom Standard Input (stdin)
                    </label>
                    <textarea
                      rows={2}
                      value={stdin}
                      onChange={(e) => setStdin(e.target.value)}
                      placeholder="Optional inputs passed to program stdin when clicking 'Run Code'..."
                      className="mt-1 w-full rounded-lg border border-[#F0DCE5] bg-[#FFF7FA] p-2 font-mono text-xs text-[#3F1024] outline-none"
                    />
                  </div>
                </div>

                {/* Console Output Drawer */}
                {consoleResult && (
                  <div
                    className={`lux-card p-4 animate-fade-in border ${
                      consoleResult.tone === "ok"
                        ? "border-[#A7F3D0] bg-[#ECFDF5]"
                        : "border-[#FECACA] bg-[#FEF2F2]"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span
                        className={`text-xs font-bold uppercase tracking-wider ${
                          consoleResult.tone === "ok" ? "text-emerald-800" : "text-rose-900"
                        }`}
                      >
                        {consoleResult.title}
                      </span>
                      {lastSubmissionId && (
                        <button
                          onClick={requestAiFeedback}
                          disabled={feedbackBusy}
                          className="text-[11px] font-bold text-[#9F1239] underline hover:text-[#BE5678]"
                        >
                          {feedbackBusy ? "Analyzing..." : "Get AI Review 💡"}
                        </button>
                      )}
                    </div>
                    <pre
                      className={`mt-2 font-mono text-xs whitespace-pre-wrap ${
                        consoleResult.tone === "ok" ? "text-emerald-950" : "text-rose-950"
                      }`}
                    >
                      {consoleResult.body}
                    </pre>

                    {aiFeedback && (
                      <div className="mt-3 rounded-lg border border-[#F0DCE5] bg-[#FFFFFF] p-3 text-xs text-[#3F1024]">
                        <span className="font-bold text-[#9F1239]">AI Assistant Advice:</span>
                        <p className="mt-1 whitespace-pre-wrap">{aiFeedback}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ───────────────── TAB: SUBMISSIONS ───────────────── */}
        {tab === "Submissions" && (
          <div className="mt-6 space-y-6 animate-fade-in">
            <div className="lux-card p-6">
              <h2 className="text-lg font-bold text-[#3F1024]">Submission History</h2>
              <p className="mt-0.5 text-xs text-[#806777]">
                Complete audit log of all automated sandbox test evaluations.
              </p>

              {submissions.length > 0 ? (
                <div className="mt-5 overflow-x-auto">
                  <table className="lux-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Problem / Practical</th>
                        <th>Language</th>
                        <th>Result Status</th>
                        <th>Test Cases</th>
                        <th>Score</th>
                        <th>Timestamp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {submissions.map((sub) => (
                        <tr key={sub.id}>
                          <td className="font-mono text-xs font-bold text-[#806777]">#{sub.id}</td>
                          <td className="font-bold text-[#3F1024]">
                            Practical #{sub.practical_id ?? sub.question_id}
                          </td>
                          <td className="font-mono text-xs uppercase">{sub.language}</td>
                          <td>
                            <span
                              className={`px-2 py-0.5 rounded-md text-[10px] font-bold ${
                                sub.status === "ACCEPTED" || sub.score === 100
                                  ? "badge-success"
                                  : "badge-danger"
                              }`}
                            >
                              {sub.status}
                            </span>
                          </td>
                          <td className="text-xs font-semibold text-[#806777]">
                            {sub.passed_test_cases} / {sub.total_test_cases}
                          </td>
                          <td className="font-bold text-[#3F1024]">{sub.score}%</td>
                          <td className="text-xs text-[#806777]">
                            {new Date(sub.created_at).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="mt-6 text-center py-10 text-xs text-[#806777]">
                  No code submissions recorded yet. Open a lab practical and submit your solution.
                </div>
              )}
            </div>
          </div>
        )}

        {/* ───────────────── TAB: STATISTICS ───────────────── */}
        {tab === "Statistics" && (
          <div className="mt-6 space-y-6 animate-fade-in">
            <div className="grid gap-6 md:grid-cols-2">
              <div className="lux-card p-6">
                <h2 className="text-base font-bold text-[#3F1024]">Laboratory Practical Completion</h2>
                <div className="mt-4 flex items-center justify-between">
                  <span className="text-xs font-semibold text-[#806777]">Overall Curricular Progress</span>
                  <span className="text-xs font-extrabold text-[#9F1239]">
                    {allPracticals.length
                      ? Math.round((completedCount / allPracticals.length) * 100)
                      : 0}
                    %
                  </span>
                </div>
                <div className="mt-2 h-2.5 w-full rounded-full bg-[#FFF7FA] border border-[#F0DCE5] overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      background: "var(--primary-gradient)",
                      width: `${
                        allPracticals.length
                          ? Math.round((completedCount / allPracticals.length) * 100)
                          : 0
                      }%`,
                    }}
                  />
                </div>

                <div className="mt-6 grid grid-cols-2 gap-4 text-center">
                  <div className="p-4 rounded-xl bg-[#FFF7FA] border border-[#F0DCE5]">
                    <p className="text-2xl font-extrabold text-[#9F1239]">{completedCount}</p>
                    <p className="text-xs font-bold text-[#806777]">Practicals Completed</p>
                  </div>
                  <div className="p-4 rounded-xl bg-[#FFF7FA] border border-[#F0DCE5]">
                    <p className="text-2xl font-extrabold text-[#BE5678]">
                      {(allPracticals.length || 0) - completedCount}
                    </p>
                    <p className="text-xs font-bold text-[#806777]">Practicals Remaining</p>
                  </div>
                </div>
              </div>

              <div className="lux-card p-6">
                <h2 className="text-base font-bold text-[#3F1024]">Submissions Breakdown</h2>
                <div className="mt-4 space-y-3">
                  {[
                    { label: "Total Submissions", count: submissions.length, color: "text-[#3F1024]" },
                    {
                      label: "Accepted (100% Score)",
                      count: acceptedSubmissions.length,
                      color: "text-emerald-700 font-bold",
                    },
                    {
                      label: "Failed or Partial Attempts",
                      count: submissions.length - acceptedSubmissions.length,
                      color: "text-rose-700 font-bold",
                    },
                  ].map((row) => (
                    <div
                      key={row.label}
                      className="flex items-center justify-between p-3 rounded-xl bg-[#FFF7FA] border border-[#F0DCE5] text-xs"
                    >
                      <span className="font-semibold text-[#806777]">{row.label}</span>
                      <span className={`text-sm ${row.color}`}>{row.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ───────────────── TAB: ACHIEVEMENTS (PARTS 10, 11 & 12) ───────────────── */}
        {tab === "Achievements" && (
          <div className="mt-6 space-y-6 animate-fade-in">
            {certRequestMessage && (
              <div className="lux-card p-4 bg-[#FFF7FA] border border-[#BE5678]/40 flex items-center justify-between text-xs text-[#9F1239] font-bold">
                <span>{certRequestMessage}</span>
                <button
                  onClick={() => setCertRequestMessage("")}
                  className="text-xs text-[#806777] hover:text-[#3F1024]"
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* AREA A: BADGES (PART 10) */}
            <div className="lux-card p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-[#3F1024]">Earned Practical Badges</h2>
                  <p className="mt-0.5 text-xs text-[#806777]">
                    Automatically unlocked upon achieving 100% test evaluation score on practical challenges.
                  </p>
                </div>
                <span className="badge-primary px-3 py-1 text-xs font-bold rounded-full">
                  {earnedBadges.length} Earned
                </span>
              </div>

              {earnedBadges.length > 0 ? (
                <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {earnedBadges.map((badge) => (
                    <div
                      key={badge.id}
                      className="lux-card p-4 border border-[#F0DCE5] bg-gradient-to-br from-[#FFFFFF] to-[#FFF7FA] flex items-start gap-3.5 hover:shadow-sm transition"
                    >
                      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[#FFF7FA] border border-[#F0DCE5] text-2xl shadow-xs">
                        {badge.icon || "🎖️"}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-extrabold text-xs text-[#3F1024] truncate">
                          {badge.name}
                        </h3>
                        <p className="mt-1 text-[11px] text-[#806777] line-clamp-2">
                          {badge.description || "Milestone awarded for flawless automated test execution."}
                        </p>
                        <p className="mt-2 font-mono text-[10px] text-[#BE5678]">
                          Unlocked: {new Date(badge.earned_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-6 text-center py-8 text-xs text-[#806777] rounded-xl bg-[#FFF7FA] border border-dashed border-[#F0DCE5]">
                  No badges unlocked yet. Score 100% on any curriculum practical to automatically receive your milestone badge.
                </div>
              )}
            </div>

            {/* AREA B: DIGITAL CERTIFICATES & DIPLOMAS (PART 11) */}
            <div className="lux-card p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-[#3F1024]">Digital Milestone Diplomas</h2>
                  <p className="mt-0.5 text-xs text-[#806777]">
                    Cryptographically authenticated and signed with university Ed25519 asymmetric keys.
                  </p>
                </div>
                <span className="badge-primary px-3 py-1 text-xs font-bold rounded-full">
                  {certificateData.certificates.length} Issued
                </span>
              </div>

              {certificateData.certificates.length > 0 ? (
                <div className="mt-6 grid gap-4 md:grid-cols-2">
                  {certificateData.certificates.map((cert) => (
                    <div
                      key={cert.id}
                      className="lux-card p-5 border border-[#F0DCE5] bg-gradient-to-r from-[#FFFFFF] to-[#FFF7FA] flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="badge-success px-2.5 py-0.5 text-[10px] font-bold rounded-md">
                            VALID ED25519 DIPLOMA ✓
                          </span>
                          <span className="font-mono text-[10px] text-[#806777]">
                            {new Date(cert.issued_at).toLocaleDateString()}
                          </span>
                        </div>
                        <h3 className="mt-3 font-extrabold text-[#3F1024]">
                          {cert.lab_title || "Academic Course Completion"}
                        </h3>
                        <p className="mt-1 text-xs text-[#806777]">
                          {cert.practical_title || "All Curriculum Requirements Satisfied"}
                        </p>
                        <p className="mt-2 font-mono text-[10px] text-[#BE5678] truncate">
                          Digest: {cert.payload_digest}
                        </p>
                      </div>

                      <div className="mt-5 pt-3 border-t border-[#F0DCE5]">
                        <Link
                          href={`/certificates/${cert.id}`}
                          className="inline-flex items-center gap-1.5 text-xs font-bold text-[#9F1239] hover:underline"
                        >
                          View Official Verifiable Diploma →
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-6 text-center py-8 text-xs text-[#806777] rounded-xl bg-[#FFF7FA] border border-dashed border-[#F0DCE5]">
                  No diplomas issued yet. Complete all required practicals for a subject below and request faculty verification.
                </div>
              )}
            </div>

            {/* AREA C: SUBJECT ACADEMIC PROGRESS (PART 12) */}
            <div className="lux-card p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-[#3F1024]">Curriculum Subject Progress</h2>
                  <p className="mt-0.5 text-xs text-[#806777]">
                    Track practical completion and certificate eligibility across your active subjects.
                  </p>
                </div>
                <span className="badge-primary px-3 py-1 text-xs font-bold rounded-full">
                  {studentProgress.length} Enrolled
                </span>
              </div>

              {studentProgress.length > 0 ? (
                <div className="mt-6 space-y-4">
                  {studentProgress.map((prog) => (
                    <div
                      key={prog.course_id}
                      className="lux-card p-5 border border-[#F0DCE5] bg-[#FFFFFF] rounded-2xl"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="badge-primary px-2.5 py-0.5 text-[10px] font-bold rounded-md">
                              {prog.course_code || "COURSE"}
                            </span>
                            <h3 className="text-sm font-extrabold text-[#3F1024]">
                              {prog.course_name}
                            </h3>
                          </div>
                          <p className="mt-1 text-xs text-[#806777]">
                            Completed:{" "}
                            <span className="font-bold text-[#3F1024]">
                              {prog.completed_required} of {prog.total_required}
                            </span>{" "}
                            required practical challenges · Badges Earned:{" "}
                            <span className="font-bold text-[#9F1239]">{prog.badges_earned}</span>
                          </p>
                        </div>

                        {/* Status Badge */}
                        <div>
                          {prog.certificate_status === "ISSUED" && (
                            <span className="badge-success px-3 py-1 text-xs font-bold rounded-full">
                              CERTIFICATE ISSUED ✓
                            </span>
                          )}
                          {prog.certificate_status === "PENDING_APPROVAL" && (
                            <span className="badge-warning px-3 py-1 text-xs font-bold rounded-full">
                              FACULTY APPROVAL PENDING
                            </span>
                          )}
                          {prog.certificate_status === "REJECTED" && (
                            <span className="badge-danger px-3 py-1 text-xs font-bold rounded-full">
                              REVISION REQUESTED
                            </span>
                          )}
                          {prog.certificate_status === "ELIGIBLE" && (
                            <span className="badge-success px-3 py-1 text-xs font-bold rounded-full">
                              100% COMPLETED · ELIGIBLE
                            </span>
                          )}
                          {prog.certificate_status === "NOT_ELIGIBLE" && (
                            <span className="bg-slate-100 text-slate-700 px-3 py-1 text-xs font-bold rounded-full border border-slate-200">
                              {prog.remaining_required} PRACTICAL(S) REMAINING
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <div className="mt-4">
                        <div className="flex justify-between text-xs font-bold mb-1">
                          <span className="text-[#806777]">Curriculum Completion</span>
                          <span className="text-[#9F1239]">{prog.completion_percentage}%</span>
                        </div>
                        <div className="h-2 w-full rounded-full bg-[#FFF7FA] border border-[#F0DCE5] overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-500"
                            style={{
                              background: "var(--primary-gradient)",
                              width: `${Math.min(100, Math.max(0, prog.completion_percentage))}%`,
                            }}
                          />
                        </div>
                      </div>

                      {/* Action / Feedback row */}
                      {prog.certificate_status === "REJECTED" && prog.rejection_note && (
                        <div className="mt-3 rounded-xl p-3 bg-rose-50 border border-rose-200 text-xs text-rose-900">
                          <span className="font-bold">Faculty Revision Note:</span>{" "}
                          {prog.rejection_note}
                        </div>
                      )}

                      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-[#F0DCE5]">
                        <p className="text-[11px] text-[#A38C9B]">
                          {prog.certificate_status === "ISSUED"
                            ? "Subject diploma cryptographically active in your records."
                            : prog.certificate_status === "ELIGIBLE"
                            ? "All requirements fulfilled. You can now request your subject diploma."
                            : prog.certificate_status === "REJECTED"
                            ? "Please review faculty feedback before re-submitting request."
                            : "Solve all required practicals with 100% score to unlock certification."}
                        </p>

                        {(prog.certificate_status === "ELIGIBLE" ||
                          prog.certificate_status === "REJECTED") && (
                          <button
                            onClick={() => void handleRequestSubjectCert(prog.course_id)}
                            disabled={requestingCertCourseId === prog.course_id}
                            className="btn-primary !py-2 !px-4 !text-xs font-bold"
                          >
                            {requestingCertCourseId === prog.course_id
                              ? "Submitting..."
                              : prog.certificate_status === "REJECTED"
                              ? "Re-Request Subject Certificate"
                              : "Request Subject Certificate"}
                          </button>
                        )}

                        {prog.certificate_status === "ISSUED" && prog.certificate_id && (
                          <Link
                            href={`/certificates/${prog.certificate_id}`}
                            className="btn-secondary !py-2 !px-4 !text-xs font-bold"
                          >
                            View Diploma →
                          </Link>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-6 text-center py-8 text-xs text-[#806777] rounded-xl bg-[#FFF7FA] border border-dashed border-[#F0DCE5]">
                  No active enrolled subjects found for your profile. Contact your department administrator.
                </div>
              )}
            </div>
          </div>
        )}

        {/* ───────────────── TAB: PROFILE ───────────────── */}
        {tab === "Profile" && (
          <div className="mt-6 space-y-6 animate-fade-in">
            <div className="lux-card p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-[#3F1024]">Academic Identity & Credentials</h2>
                  <p className="mt-0.5 text-xs text-[#806777]">
                    Manage your enrollment details, academic course assignment, and semester status.
                  </p>
                </div>
                <button
                  onClick={() => setProfileOpen((o) => !o)}
                  className="btn-secondary !py-1.5 !px-3.5 !text-xs font-bold"
                >
                  {profileOpen ? "Close Editor" : "Edit Profile"}
                </button>
              </div>

              {profileOpen ? (
                <form onSubmit={handleProfileSave} className="mt-6 space-y-4 max-w-xl">
                  {profileError && (
                    <div className="badge-danger p-3 rounded-xl text-xs">{profileError}</div>
                  )}

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[#3F1024] mb-1">
                      Student ID Number
                    </label>
                    <input
                      type="text"
                      value={profile.student_id_number}
                      onChange={(e) =>
                        setProfile((p) => ({ ...p, student_id_number: e.target.value }))
                      }
                      placeholder="e.g. STU-2026-089"
                      className="input-field"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[#3F1024] mb-1">
                      Academic Program
                    </label>
                    <select
                      value={profile.academic_course}
                      onChange={(e) =>
                        setProfile((p) => ({ ...p, academic_course: e.target.value }))
                      }
                      className="input-field"
                    >
                      {PROGRAM_OPTIONS.map((prog) => (
                        <option key={prog} value={prog}>
                          {prog}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-[#3F1024] mb-1">
                        Year of Study
                      </label>
                      <select
                        value={profile.year_of_study}
                        onChange={(e) =>
                          setProfile((p) => ({ ...p, year_of_study: e.target.value }))
                        }
                        className="input-field"
                      >
                        {["1st Year", "2nd Year", "3rd Year", "4th Year"].map((y) => (
                          <option key={y} value={y}>
                            {y}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-[#3F1024] mb-1">
                        Semester
                      </label>
                      <select
                        value={profile.semester}
                        onChange={(e) =>
                          setProfile((p) => ({ ...p, semester: e.target.value }))
                        }
                        className="input-field"
                      >
                        {[
                          "Semester 1",
                          "Semester 2",
                          "Semester 3",
                          "Semester 4",
                          "Semester 5",
                          "Semester 6",
                          "Semester 7",
                          "Semester 8",
                        ].map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={profileSaving}
                    className="btn-primary !py-2.5 !px-6 !text-xs font-bold"
                  >
                    {profileSaving ? "Saving credentials..." : "Save Academic Profile"}
                  </button>
                </form>
              ) : (
                <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {[
                    { label: "Full Name", value: user.name },
                    { label: "Enrollment Number", value: user.enrollment_number },
                    { label: "Academic Program", value: user.academic_course },
                    { label: "Year of Study", value: user.year_of_study },
                    { label: "Semester", value: user.semester },
                    { label: "Academic Session", value: user.academic_year },
                    { label: "Student ID", value: user.student_id_number || "Not set" },
                  ].map((x) => (
                    <div key={x.label} className="p-4 rounded-xl bg-[#FFF7FA] border border-[#F0DCE5]">
                      <p className="text-[11px] font-bold uppercase tracking-wider text-[#806777]">
                        {x.label}
                      </p>
                      <p className="mt-1 text-sm font-bold text-[#3F1024]">{x.value || "Not set"}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        <footer className="mt-12 text-center text-xs py-4 text-[#806777]">
          LabOS · Cryptographically Signed University Assessments · 2026
        </footer>
      </div>
    </main>
  );
}
