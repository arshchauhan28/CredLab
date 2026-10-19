"use client";
/* eslint react-hooks/set-state-in-effect: off */

import { useCallback, useEffect, useMemo, useState, useRef } from "react";
import type { FormEvent } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import type { UserResponse } from "@/types/auth";
import { PROGRAM_OPTIONS } from "@/lib/academic-options";
import { CredLabLogo } from "@/components/CredLabLogo";
import { DashboardAmbientGrid } from "@/components/3d/DashboardAmbientGrid";
import { BadgeRenderer, downloadBadgePng } from "@/components/BadgeRenderer";
import { BadgeModal } from "@/components/BadgeModal";
import { CertificateRenderer } from "@/components/CertificateRenderer";
import { CertificateModal } from "@/components/CertificateModal";
import {
  Award,
  ShieldCheck,
  Download,
  Search,
  Sparkles,
  CheckCircle2,
  ChevronRight,
  ArrowRight,
  Eye,
  BookOpen,
} from "lucide-react";

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

type SubmissionTestResult = {
  id: number;
  submission_id: number;
  test_case_id?: number | null;
  status: string;
  passed: boolean;
  execution_time_ms?: number | null;
  memory_kb?: number | null;
  is_hidden: boolean;
  display_order: number;
  input?: string | null;
  expected_output?: string | null;
  stdout?: string | null;
  stderr?: string | null;
  error_message?: string | null;
  created_at: string;
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
  execution_time_ms?: number | null;
  memory_kb?: number | null;
  error_message?: string | null;
  source_code?: string;
  test_results?: SubmissionTestResult[];
  created_at: string;
};

type CertificateData = {
  certificates: {
    id: string;
    status: string;
    certificate_type?: string;
    course_id?: number | null;
    course_name?: string;
    course_code?: string;
    lab_title: string;
    practical_title: string;
    completed_practicals_count?: number;
    total_practicals_count?: number;
    completed_at?: string;
    issued_at: string;
    payload_digest: string;
  }[];
  requests: {
    id: number;
    course_id?: number;
    course_name?: string;
    lab_id?: number;
    lab_title?: string;
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
  practical_title?: string;
  course_id?: number | null;
  course_name?: string;
  course_code?: string;
  meta?: Record<string, unknown> | null;
};

type Tab = "Overview" | "My Labs" | "Submissions" | "Statistics" | "Achievements" | "Profile";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[420px] flex-col items-center justify-center gap-3 text-xs text-[#A5A29C] bg-[#1e1e1e]">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#FF6B2C] border-t-transparent" />
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

  // Achievement & Credential Modals & Filtering State
  const [selectedBadgeForModal, setSelectedBadgeForModal] = useState<BadgeItem | null>(null);
  const [selectedCertForModal, setSelectedCertForModal] = useState<{
    id: string;
    student_name?: string;
    course_name?: string;
    course_code?: string;
    completed_practicals_count?: number;
    total_practicals_count?: number;
    completed_at?: string;
    issued_at?: string;
    issuer?: string;
    status?: string;
  } | null>(null);
  const [badgeSearchQuery, setBadgeSearchQuery] = useState("");
  const [badgeSubjectFilter, setBadgeSubjectFilter] = useState("ALL");
  const [badgeSortOrder, setBadgeSortOrder] = useState<"newest" | "oldest" | "alpha">("newest");

  // Derived unique subjects for badge filter
  const badgeSubjects = useMemo(() => {
    const set = new Set<string>();
    earnedBadges.forEach((b) => {
      const s = b.course_name || (b.meta as { course_name?: string })?.course_name;
      if (s) set.add(s);
    });
    return Array.from(set);
  }, [earnedBadges]);

  // Filtered and sorted badges for the gallery
  const filteredBadges = useMemo(() => {
    return earnedBadges
      .filter((b) => {
        const subj = (b.course_name || (b.meta as { course_name?: string })?.course_name || "").toLowerCase();
        const prac = (b.practical_title || (b.meta as { practical_title?: string })?.practical_title || b.name || "").toLowerCase();
        const code = (b.course_code || (b.meta as { course_code?: string })?.course_code || "").toLowerCase();
        const q = badgeSearchQuery.toLowerCase().trim();

        const matchesQuery = !q || subj.includes(q) || prac.includes(q) || code.includes(q);
        const matchesSubj =
          badgeSubjectFilter === "ALL" ||
          (b.course_name || (b.meta as { course_name?: string })?.course_name) === badgeSubjectFilter;
        return matchesQuery && matchesSubj;
      })
      .sort((a, b) => {
        if (badgeSortOrder === "newest") {
          return new Date(b.earned_at).getTime() - new Date(a.earned_at).getTime();
        }
        if (badgeSortOrder === "oldest") {
          return new Date(a.earned_at).getTime() - new Date(b.earned_at).getTime();
        }
        const titleA = a.practical_title || (a.meta as { practical_title?: string })?.practical_title || a.name || "";
        const titleB = b.practical_title || (b.meta as { practical_title?: string })?.practical_title || b.name || "";
        return titleA.localeCompare(titleB);
      });
  }, [earnedBadges, badgeSearchQuery, badgeSubjectFilter, badgeSortOrder]);

  // Challenge-specific Submission History (LeetCode-style)
  const [problemPaneTab, setProblemPaneTab] = useState<"description" | "submissions">("description");
  const [challengeSubmissions, setChallengeSubmissions] = useState<Submission[]>([]);
  const [challengeSubmissionsLoading, setChallengeSubmissionsLoading] = useState(false);
  const [challengeSubmissionsError, setChallengeSubmissionsError] = useState("");

  // Loaded historical submission banner & tracking
  const [loadedSubmissionInfo, setLoadedSubmissionInfo] = useState<{
    id: number;
    timestamp: string;
    status: string;
    score: number;
    language: string;
  } | null>(null);

  // Submission Inspection Modal ("View Code")
  const [viewingSubmission, setViewingSubmission] = useState<Submission | null>(null);
  const [viewingSubmissionLoading, setViewingSubmissionLoading] = useState(false);
  const [codeCopied, setCodeCopied] = useState(false);

  // Unsaved changes confirmation dialog
  const [pendingSubmissionToLoad, setPendingSubmissionToLoad] = useState<Submission | null>(null);
  const [confirmOverwriteOpen, setConfirmOverwriteOpen] = useState(false);

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

  const fetchChallengeSubmissions = useCallback(async (qId: number, pId?: number | null) => {
    setChallengeSubmissionsLoading(true);
    setChallengeSubmissionsError("");
    try {
      const params = new URLSearchParams();
      params.set("question_id", String(qId));
      if (pId) params.set("practical_id", String(pId));
      params.set("page", "1");
      params.set("page_size", "50");
      const res = await api<{ items: Submission[]; total: number }>(`submissions?${params.toString()}`);
      setChallengeSubmissions(res.items || []);
    } catch (err) {
      setChallengeSubmissionsError(err instanceof Error ? err.message : "Failed to load submission history.");
    } finally {
      setChallengeSubmissionsLoading(false);
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
    setLoadedSubmissionInfo(null);
    setProblemPaneTab("description");
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
      void fetchChallengeSubmissions(p.question_id, p.id);
      const validLangs = q.allowed_languages?.filter((l) =>
        DEFAULT_LANGUAGES.some((dl) => dl.value === l),
      );
      const chosenLang = validLangs?.includes(language)
        ? language
        : validLangs?.[0] || "python";
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
        status?: { description?: string } | string;
        status_id?: number;
        status_description?: string;
        time?: string;
        time_ms?: number;
        memory?: number;
        memory_kb?: number;
      }>("execute", {
        method: "POST",
        body: JSON.stringify({
          question_id: question.id,
          language,
          source_code: sourceCode,
          stdin: stdin,
        }),
      });

      const rawStatus = result.status;
      const statusStr =
        typeof rawStatus === "string"
          ? rawStatus
          : rawStatus?.description || result.status_description || "";

      const isAccepted = statusStr === "Accepted" || result.status_id === 3;
      const tone: "ok" | "bad" = isAccepted ? "ok" : "bad";

      let body = "";
      if (result.compile_output && result.compile_output.trim()) {
        body = result.compile_output;
      } else if (statusStr === "Time Limit Exceeded" || result.status_id === 5) {
        body = result.stderr || "Execution timed out (exceeded CPU time limit).";
      } else if (result.stderr && result.stdout) {
        body = `[Standard Output]\n${result.stdout}\n\n[Error Output]\n${result.stderr}`;
      } else if (result.stderr) {
        body = result.stderr;
      } else if (result.stdout) {
        body = result.stdout;
      } else {
        body = isAccepted
          ? "Code executed successfully (no stdout produced)."
          : "Process terminated without output.";
      }

      const runtimeStr =
        result.time ||
        (typeof result.time_ms === "number" ? `${(result.time_ms / 1000).toFixed(3)}s` : "");
      const memKb =
        typeof result.memory === "number"
          ? result.memory
          : typeof result.memory_kb === "number"
            ? result.memory_kb
            : null;

      const metricParts: string[] = [];
      if (runtimeStr) metricParts.push(`Runtime: ${runtimeStr}`);
      if (memKb !== null) metricParts.push(`Memory: ${memKb}KB`);
      if (metricParts.length > 0) {
        body += `\n\n[${metricParts.join(" | ")}]`;
      }

      const title = statusStr || (isAccepted ? "Execution Successful" : "Execution Error");

      setConsoleResult({
        title,
        body,
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
      if (question) {
        void fetchChallengeSubmissions(question.id, selectedPractical.id);
      }
      setLoadedSubmissionInfo(null);
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

  const hasUnsavedChanges = (targetCode?: string) => {
    const trimmed = sourceCode.trim();
    if (!trimmed) return false;
    const isStarter = DEFAULT_LANGUAGES.some(
      (l) =>
        l.starter.trim() === trimmed ||
        (selectedPractical && `# Solution for ${selectedPractical.effective_title}`.trim() === trimmed),
    );
    if (isStarter) return false;
    if (targetCode && targetCode.trim() === trimmed) return false;
    return true;
  };

  const loadSubmissionIntoEditor = (sub: Submission) => {
    if (sub.source_code !== undefined && sub.source_code !== null) {
      setSourceCode(sub.source_code);
      if (sub.language && DEFAULT_LANGUAGES.some((l) => l.value === sub.language.toLowerCase())) {
        setLanguage(sub.language.toLowerCase());
      }
      setLoadedSubmissionInfo({
        id: sub.id,
        timestamp: sub.created_at,
        status: sub.status,
        score: sub.score,
        language: sub.language,
      });
      setConfirmOverwriteOpen(false);
      setPendingSubmissionToLoad(null);
      setViewingSubmission(null);
    }
  };

  const handleRequestLoadSubmission = async (sub: Submission) => {
    let targetCode = sub.source_code;
    let fullSub = sub;
    if (!targetCode) {
      try {
        fullSub = await api<Submission>(
          `submissions/${sub.id}?question_id=${sub.question_id}${sub.practical_id ? `&practical_id=${sub.practical_id}` : ""}`,
        );
        targetCode = fullSub.source_code;
      } catch (err) {
        alert(err instanceof Error ? err.message : "Failed to retrieve submission code.");
        return;
      }
    }

    if (hasUnsavedChanges(targetCode)) {
      setPendingSubmissionToLoad(fullSub);
      setConfirmOverwriteOpen(true);
    } else {
      loadSubmissionIntoEditor(fullSub);
    }
  };

  const handleViewSubmission = async (sub: Submission) => {
    setViewingSubmission(sub);
    setCodeCopied(false);
    if (!sub.source_code) {
      setViewingSubmissionLoading(true);
      try {
        const full = await api<Submission>(
          `submissions/${sub.id}?question_id=${sub.question_id}${sub.practical_id ? `&practical_id=${sub.practical_id}` : ""}`,
        );
        setViewingSubmission(full);
      } catch (err) {
        console.error("Failed to load submission details:", err);
      } finally {
        setViewingSubmissionLoading(false);
      }
    }
  };

  const handleOpenGlobalSubmissionInEditor = async (sub: Submission) => {
    let foundLabId: number | null = null;
    let foundPractical: Practical | null = null;

    for (const [labIdStr, practicals] of Object.entries(practicalsByLab)) {
      const match = practicals.find((p) => p.id === sub.practical_id);
      if (match) {
        foundLabId = Number(labIdStr);
        foundPractical = match;
        break;
      }
    }

    if (foundLabId && foundPractical) {
      setSelectedLab(foundLabId);
      await selectPractical(foundPractical);
    } else if (allLabs.length > 0) {
      setSelectedLab(allLabs[0].id);
    }
    setTab("My Labs");
    void handleRequestLoadSubmission(sub);
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
          <div className="h-10 w-10 animate-spin rounded-full border-3 border-[#FF6B2C] border-t-transparent" />
          <p className="text-sm font-semibold text-[#706C65] dark:text-[#A5A29C]">
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
        <section className="lux-card max-w-lg p-8 text-center shadow-xl border border-[#E4DDD2] dark:border-[#2D2D2D] bg-[#FFFCF6] dark:bg-[#1B1B1B]">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl badge-danger text-xl">
            ⚠
          </div>
          <h1 className="mt-4 text-xl font-bold text-[#191919] dark:text-[#F7F4EF]">Unable to load workspace</h1>
          <p className="mt-2 text-sm leading-6 text-[#706C65] dark:text-[#A5A29C]">
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
      <header className="sticky top-0 z-30 border-b border-[#353535] bg-[#121212]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-8">
          <Link href="/student/dashboard" className="flex items-center gap-3 group">
            <CredLabLogo size="sm" showWordmark={true} />
            <span className="hidden sm:inline-block text-[11px] font-mono font-semibold uppercase tracking-wider text-[#A5A29C] border-l border-[#353535] pl-3">
              Student Workspace
            </span>
          </Link>

          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 rounded-full px-3 py-1 text-xs font-mono font-bold sm:flex badge-primary">
              <span className="h-2 w-2 rounded-full bg-[#FF6B2C]" />
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
        <section className="lux-card relative overflow-hidden p-6 sm:p-8 bg-gradient-to-r from-[#1B1B1B] via-[#1E1E1E] to-[#242424] border border-[#353535] shadow-lg">
          <DashboardAmbientGrid />
          <div className="relative z-10 flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-[#FF6B2C]/25 bg-[#FF6B2C]/10 px-3 py-1 text-[11px] font-bold text-[#FF8A3D]">
                Academic Session {user.academic_year || "2026-2027"}
              </div>
              <h1 className="mt-2.5 text-2xl font-extrabold tracking-tight text-[#F7F4EF] sm:text-3xl">
                Welcome back, {user.name}
              </h1>
              <p className="mt-1 text-xs sm:text-sm text-[#A5A29C]">
                Continuous programming practicals, automated sandbox evaluations, and milestone
                diplomas.
              </p>
            </div>

            <div className="flex flex-wrap gap-2 text-xs">
              <span className="rounded-xl px-3 py-2 font-bold bg-[#161616] border border-[#353535] text-[#F7F4EF]">
                {user.academic_course || "Course Not Assigned"}
              </span>
              <span className="rounded-xl px-3 py-2 font-bold bg-[#161616] border border-[#353535] text-[#F7F4EF]">
                {user.year_of_study || "1st Year"} · {user.semester || "Semester 1"}
              </span>
            </div>
          </div>
        </section>

        {/* ────── Navigation Tabs ────── */}
        <nav
          className="mt-6 flex gap-1.5 overflow-x-auto rounded-2xl p-1.5 bg-[#FFFCF6] dark:bg-[#151515] border border-[#E4DDD2] dark:border-[#2D2D2D]"
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
                  : "text-[#706C65] dark:text-[#A5A29C] hover:bg-[#EEE8DE]/60 dark:hover:bg-[#202020] hover:text-[#D94F16] dark:hover:text-[#FF6B2C]"
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
                { label: "Enrolled Courses", value: courses.length, icon: "📚", color: "text-[#D94F16] dark:text-[#FF6B2C]" },
                { label: "Available Labs", value: allLabs.length, icon: "🔬", color: "text-[#D94F16] dark:text-[#FFB547]" },
                {
                  label: "Completed Practicals",
                  value: `${completedCount} / ${allPracticals.length || 0}`,
                  icon: "✓",
                  color: "text-emerald-700 dark:text-emerald-400",
                },
                {
                  label: "Passed Submissions",
                  value: acceptedSubmissions.length,
                  icon: "🏆",
                  color: "text-amber-700 dark:text-amber-400",
                },
              ].map((card) => (
                <div key={card.label} className="lux-card p-5 card-hover border border-[#E4DDD2] dark:border-[#2D2D2D]">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-bold uppercase tracking-wider text-[#706C65] dark:text-[#A5A29C]">
                      {card.label}
                    </p>
                    <span className="text-xl">{card.icon}</span>
                  </div>
                  <p className={`mt-3 text-3xl font-extrabold ${card.color}`}>{card.value}</p>
                </div>
              ))}
            </div>

            {/* Enrolled Labs Grid */}
            <section className="lux-card p-6 border border-[#E4DDD2] dark:border-[#2D2D2D]">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-bold text-[#191919] dark:text-[#F7F4EF]">Your Enrolled Laboratories</h2>
                  <p className="mt-0.5 text-xs text-[#706C65] dark:text-[#A5A29C]">
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
                      className="lux-card p-5 text-left transition-all card-hover border border-[#E4DDD2] dark:border-[#2D2D2D] bg-[#FFFCF6] dark:bg-[#1B1B1B]"
                    >
                      <div className="flex items-center justify-between">
                        <span className="badge-primary px-2.5 py-0.5 text-[10px] font-bold rounded-md">
                          {lab.program}
                        </span>
                        <span className="text-xs font-semibold text-[#706C65] dark:text-[#A5A29C]">
                          {lab.practical_count} Practicals
                        </span>
                      </div>
                      <h3 className="mt-3 font-bold text-[#191919] dark:text-[#F7F4EF]">{lab.title}</h3>
                      <p className="mt-1 text-xs text-[#706C65] dark:text-[#A5A29C]">{lab.courseName}</p>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="mt-6 text-center py-10">
                  <p className="text-sm font-semibold text-[#706C65] dark:text-[#A5A29C]">
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
                <span className="text-xs font-bold uppercase tracking-wider text-[#706C65] dark:text-[#A5A29C]">
                  Active Lab:
                </span>
                {allLabs.map((l) => (
                  <button
                    key={l.id}
                    onClick={() => selectLab(l.id)}
                    className={`rounded-xl px-3.5 py-1.5 text-xs font-bold transition-all ${
                      selectedLab === l.id
                        ? "text-white shadow-xs"
                        : "bg-[#1B1B1B] text-[#F7F4EF] hover:border-[#FF6B2C]/50 border border-[#353535]"
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
                  <span className="text-xs font-semibold text-[#A5A29C]">Sequential Progress:</span>
                  <div className="flex gap-1.5">
                    {practicalsByLab[selectedLab].map((p) => (
                      <button
                        key={p.id}
                        onClick={() => selectPractical(p)}
                        className={`flex h-7 w-7 items-center justify-center rounded-lg text-xs font-bold transition-all ${
                          selectedPractical?.id === p.id
                            ? "bg-[#FF6B2C] text-white ring-2 ring-[#FF6B2C]/40 shadow-xs"
                            : p.status === "COMPLETED"
                            ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                            : p.is_unlocked
                            ? "bg-[#1B1B1B] text-[#F7F4EF] border border-[#353535] hover:border-[#FF6B2C]"
                            : "bg-[#151515] text-[#77736D] opacity-60 cursor-not-allowed border border-[#292929]"
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
              {/* Left Column: Problem Statement & Test Cases / Submissions */}
              <div className="space-y-4">
                <div className="lux-card p-6 border border-[#353535] bg-[#1B1B1B]">
                  {/* Pane Navigation Tabs */}
                  <div className="flex items-center justify-between border-b border-[#353535] pb-3 mb-5">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setProblemPaneTab("description")}
                        className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                          problemPaneTab === "description"
                            ? "bg-[#252525] text-[#FF8A3D] border border-[#FF6B2C]/40 shadow-xs"
                            : "text-[#A5A29C] hover:text-[#F7F4EF] hover:bg-[#202020]"
                        }`}
                      >
                        <span>Description</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          setProblemPaneTab("submissions");
                          if (question) {
                            void fetchChallengeSubmissions(question.id, selectedPractical?.id);
                          }
                        }}
                        className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                          problemPaneTab === "submissions"
                            ? "bg-[#252525] text-[#FF8A3D] border border-[#FF6B2C]/40 shadow-xs"
                            : "text-[#A5A29C] hover:text-[#F7F4EF] hover:bg-[#202020]"
                        }`}
                      >
                        <span>Submissions</span>
                        {challengeSubmissions.length > 0 && (
                          <span className="rounded-full bg-[#FF6B2C]/20 border border-[#FF6B2C]/30 px-1.5 py-0.2 text-[10px] font-mono text-[#FF8A3D]">
                            {challengeSubmissions.length}
                          </span>
                        )}
                      </button>
                    </div>

                    {problemPaneTab === "submissions" && question && (
                      <button
                        type="button"
                        onClick={() => void fetchChallengeSubmissions(question.id, selectedPractical?.id)}
                        disabled={challengeSubmissionsLoading}
                        className="text-[11px] font-bold text-[#A5A29C] hover:text-[#FF6B2C] transition-colors flex items-center gap-1"
                        title="Refresh submissions"
                      >
                        <span className={challengeSubmissionsLoading ? "animate-spin" : ""}>🔄</span>
                        <span className="hidden sm:inline">Refresh</span>
                      </button>
                    )}
                  </div>

                  {problemPaneTab === "description" ? (
                    questionLoading ? (
                      <div className="flex h-64 flex-col items-center justify-center gap-2 text-xs text-[#A5A29C]">
                        <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#FF6B2C] border-t-transparent" />
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
                            <span className="text-xs font-semibold text-[#A5A29C]">
                              Allowed: {question.allowed_languages?.join(", ") || "All"}
                            </span>
                          </div>
                          <h2 className="mt-2 text-xl font-extrabold text-[#F7F4EF]">{question.title}</h2>
                        </div>

                        <div className="prose max-w-none text-xs leading-relaxed text-[#C2BDB5] whitespace-pre-line">
                          {question.description}
                        </div>

                        {question.input_format && (
                          <div>
                            <h3 className="text-xs font-bold uppercase tracking-wider text-[#FF8A3D]">
                              Input Format
                            </h3>
                            <p className="mt-1 text-xs text-[#C2BDB5] bg-[#161616] p-3 rounded-xl border border-[#353535]">
                              {question.input_format}
                            </p>
                          </div>
                        )}

                        {question.output_format && (
                          <div>
                            <h3 className="text-xs font-bold uppercase tracking-wider text-[#FF8A3D]">
                              Output Format
                            </h3>
                            <p className="mt-1 text-xs text-[#C2BDB5] bg-[#161616] p-3 rounded-xl border border-[#353535]">
                              {question.output_format}
                            </p>
                          </div>
                        )}

                        {question.constraints && (
                          <div>
                            <h3 className="text-xs font-bold uppercase tracking-wider text-[#FF8A3D]">
                              Constraints
                            </h3>
                            <pre className="mt-1 font-mono text-xs text-[#F7F4EF] bg-[#161616] p-3 rounded-xl border border-[#353535]">
                              {question.constraints}
                            </pre>
                          </div>
                        )}

                        {question.examples && question.examples.length > 0 && (
                          <div className="space-y-3">
                            <h3 className="text-xs font-bold uppercase tracking-wider text-[#FF8A3D]">
                              Sample Test Cases
                            </h3>
                            {question.examples.map((ex, i) => (
                              <div
                                key={i}
                                className="rounded-xl border border-[#353535] bg-[#161616] p-3.5 space-y-2"
                              >
                                <div className="flex items-center justify-between text-[11px] font-bold text-[#A5A29C]">
                                  <span>Example {i + 1}</span>
                                  <button
                                    type="button"
                                    onClick={() => setStdin(ex.input)}
                                    className="text-[10px] font-bold text-[#FF6B2C] dark:text-[#FFB547] hover:underline"
                                  >
                                    Copy to Custom Input
                                  </button>
                                </div>
                                <div className="grid grid-cols-2 gap-2 text-xs">
                                  <div>
                                    <span className="text-[10px] uppercase font-bold text-[#706C65] dark:text-[#A5A29C]">
                                      Input:
                                    </span>
                                    <pre className="mt-0.5 rounded-lg bg-[#FFFFFF] dark:bg-[#151515] p-2 font-mono text-[11px] text-[#191919] dark:text-[#F7F4EF] border border-[#E4DDD2] dark:border-[#2D2D2D]">
                                      {ex.input}
                                    </pre>
                                  </div>
                                  <div>
                                    <span className="text-[10px] uppercase font-bold text-[#706C65] dark:text-[#A5A29C]">
                                      Expected Output:
                                    </span>
                                    <pre className="mt-0.5 rounded-lg bg-[#FFFFFF] dark:bg-[#151515] p-2 font-mono text-[11px] text-[#191919] dark:text-[#F7F4EF] border border-[#E4DDD2] dark:border-[#2D2D2D]">
                                      {ex.output}
                                    </pre>
                                  </div>
                                </div>
                                {ex.explanation && (
                                  <p className="text-[11px] text-[#706C65] dark:text-[#A5A29C]">
                                    <span className="font-bold">Explanation:</span> {ex.explanation}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-12 text-xs text-[#706C65] dark:text-[#A5A29C]">
                        Select a practical from the top bar to inspect problem specifications.
                      </div>
                    )
                  ) : (
                    /* Submissions History Pane */
                    <div className="space-y-4">
                      <div>
                        <h3 className="text-sm font-bold text-[#F7F4EF]">
                          Submission History
                        </h3>
                        <p className="mt-0.5 text-[11px] text-[#A5A29C]">
                          Past attempts for this practical. Select any attempt to view submitted code, inspect results, or load into the editor as an editable copy.
                        </p>
                      </div>

                      {challengeSubmissionsLoading ? (
                        <div className="flex h-48 flex-col items-center justify-center gap-2 text-xs text-[#A5A29C]">
                          <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#FF6B2C] border-t-transparent" />
                          <span>Retrieving submission attempts...</span>
                        </div>
                      ) : challengeSubmissionsError ? (
                        <div className="badge-danger p-4 rounded-xl text-xs space-y-2">
                          <p>{challengeSubmissionsError}</p>
                          <button
                            type="button"
                            onClick={() => {
                              if (question) void fetchChallengeSubmissions(question.id, selectedPractical?.id);
                            }}
                            className="btn-secondary !py-1 !px-2.5 !text-[11px] font-bold"
                          >
                            Retry
                          </button>
                        </div>
                      ) : challengeSubmissions.length === 0 ? (
                        <div className="rounded-xl border border-dashed border-[#353535] bg-[#161616]/50 p-8 text-center">
                          <span className="text-2xl">⏳</span>
                          <h4 className="mt-2 text-xs font-bold text-[#F7F4EF]">No Submissions Yet</h4>
                          <p className="mt-1 text-[11px] text-[#A5A29C] max-w-xs mx-auto">
                            You have not submitted any solutions for this challenge yet. Write your code in the editor and click &ldquo;Submit Solution&rdquo; to record your first attempt.
                          </p>
                        </div>
                      ) : (
                        <div className="space-y-3 max-h-[560px] overflow-y-auto pr-1">
                          {challengeSubmissions.map((sub, idx) => {
                            const isAccepted = sub.status === "ACCEPTED" || sub.score === 100;
                            const isRunning = sub.status === "PENDING" || sub.status === "RUNNING";
                            const attemptNum = challengeSubmissions.length - idx;
                            return (
                              <div
                                key={sub.id}
                                className={`rounded-xl border p-3.5 transition-all ${
                                  loadedSubmissionInfo?.id === sub.id
                                    ? "border-[#FF6B2C] bg-[#FF6B2C]/10 ring-1 ring-[#FF6B2C]/30"
                                    : "border-[#353535] bg-[#161616] hover:border-[#454545]"
                                }`}
                              >
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <div className="flex items-center gap-2">
                                    <span className="rounded-md bg-[#252525] px-2 py-0.5 font-mono text-[11px] font-bold text-[#F7F4EF] border border-[#353535]">
                                      Attempt #{attemptNum}
                                    </span>
                                    <span
                                      className={`px-2 py-0.5 rounded-md text-[10px] font-bold ${
                                        isAccepted
                                          ? "badge-success"
                                          : isRunning
                                          ? "badge-warning"
                                          : "badge-danger"
                                      }`}
                                    >
                                      {sub.status === "ACCEPTED"
                                        ? "Accepted ✓"
                                        : sub.status === "WRONG_ANSWER"
                                        ? "Wrong Answer ✗"
                                        : sub.status === "COMPILATION_ERROR"
                                        ? "Compile Error ⚠"
                                        : sub.status === "RUNTIME_ERROR"
                                        ? "Runtime Error ⚠"
                                        : sub.status === "TIME_LIMIT_EXCEEDED"
                                        ? "TLE ⏱"
                                        : sub.status}
                                    </span>
                                    {loadedSubmissionInfo?.id === sub.id && (
                                      <span className="rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/30 px-1.5 py-0.2 text-[10px] font-bold">
                                        Loaded in Editor
                                      </span>
                                    )}
                                  </div>

                                  <span className="text-[11px] font-mono text-[#A5A29C]">
                                    {new Date(sub.created_at).toLocaleString([], {
                                      month: "short",
                                      day: "numeric",
                                      hour: "2-digit",
                                      minute: "2-digit",
                                    })}
                                  </span>
                                </div>

                                <div className="mt-2.5 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
                                  <div className="rounded-lg bg-[#121212] p-2 border border-[#252525]">
                                    <span className="text-[10px] uppercase font-bold text-[#77736D]">Language</span>
                                    <p className="font-mono text-[11px] font-bold text-[#F7F4EF] uppercase">{sub.language}</p>
                                  </div>
                                  <div className="rounded-lg bg-[#121212] p-2 border border-[#252525]">
                                    <span className="text-[10px] uppercase font-bold text-[#77736D]">Score</span>
                                    <p className={`font-mono text-[11px] font-bold ${isAccepted ? "text-emerald-400" : "text-amber-400"}`}>
                                      {sub.score}%
                                    </p>
                                  </div>
                                  <div className="rounded-lg bg-[#121212] p-2 border border-[#252525]">
                                    <span className="text-[10px] uppercase font-bold text-[#77736D]">Test Cases</span>
                                    <p className="font-mono text-[11px] text-[#C2BDB5]">
                                      {sub.passed_test_cases} / {sub.total_test_cases}
                                    </p>
                                  </div>
                                  <div className="rounded-lg bg-[#121212] p-2 border border-[#252525]">
                                    <span className="text-[10px] uppercase font-bold text-[#77736D]">Runtime</span>
                                    <p className="font-mono text-[11px] text-[#C2BDB5]">
                                      {sub.execution_time_ms ? `${sub.execution_time_ms}ms` : "--"}
                                    </p>
                                  </div>
                                </div>

                                {sub.error_message && (
                                  <div className="mt-2 rounded-lg bg-rose-500/10 border border-rose-500/20 p-2 text-[11px] text-rose-300 font-mono truncate">
                                    {sub.error_message}
                                  </div>
                                )}

                                <div className="mt-3 flex items-center justify-end gap-2 border-t border-[#252525] pt-2.5">
                                  <button
                                    type="button"
                                    onClick={() => void handleViewSubmission(sub)}
                                    className="btn-secondary !py-1 !px-2.5 !text-[11px] font-bold"
                                  >
                                    View Code
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => void handleRequestLoadSubmission(sub)}
                                    className="btn-primary !py-1 !px-3 !text-[11px] font-bold"
                                  >
                                    Open in Editor →
                                  </button>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column: Code Editor & Execution Terminal */}
              <div className="space-y-4">
                <div className="lux-card overflow-hidden border border-[#353535] bg-[#1B1B1B]">
                  {/* Editor Header Bar */}
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#353535] bg-[#161616] px-4 py-3">
                    <div className="flex items-center gap-2">
                      <select
                        value={language}
                        onChange={(e) => handleLanguageChange(e.target.value)}
                        className="rounded-lg border border-[#353535] bg-[#121212] px-3 py-1.5 text-xs font-bold text-[#F7F4EF] outline-none"
                      >
                        {(() => {
                          const filtered = question?.allowed_languages?.length
                            ? DEFAULT_LANGUAGES.filter((l) =>
                                question.allowed_languages.includes(l.value)
                              )
                            : DEFAULT_LANGUAGES;
                          const options = filtered.length ? filtered : DEFAULT_LANGUAGES;
                          return options.map((l) => (
                            <option key={l.value} value={l.value}>
                              {l.label}
                            </option>
                          ));
                        })()}
                      </select>

                      <button
                        type="button"
                        onClick={resetCode}
                        className="rounded-lg px-2.5 py-1.5 text-xs font-bold text-[#A5A29C] hover:bg-[#202020] hover:text-[#FF6B2C] transition-colors"
                        title="Reset code template"
                      >
                        Reset
                      </button>

                      <button
                        type="button"
                        onClick={() => setUseFallbackEditor((v) => !v)}
                        className="text-[11px] font-semibold text-[#A5A29C] hover:text-[#FF6B2C] transition-colors underline ml-1"
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

                  {/* Historical Submission Loaded Notification Banner */}
                  {loadedSubmissionInfo && (
                    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-amber-500/30 bg-amber-500/10 px-4 py-2.5 text-xs text-amber-200 animate-fade-in">
                      <div className="flex items-center gap-2">
                        <span className="text-base">📝</span>
                        <div>
                          <span className="font-bold text-amber-300">
                            Editing a copy of Submission #{loadedSubmissionInfo.id}
                          </span>
                          <span className="ml-2 font-mono text-[11px] text-amber-300/80">
                            ({loadedSubmissionInfo.status} • Score: {loadedSubmissionInfo.score}%)
                          </span>
                          <span className="ml-2 hidden text-[11px] text-amber-200/70 md:inline">
                            Submitting will create a <strong>NEW</strong> attempt without modifying the original.
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => setLoadedSubmissionInfo(null)}
                          className="rounded px-2 py-0.5 text-[11px] font-bold text-amber-300 hover:bg-amber-500/20 transition-colors"
                        >
                          Dismiss Notice
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            resetCode();
                            setLoadedSubmissionInfo(null);
                          }}
                          className="rounded px-2 py-0.5 text-[11px] font-bold text-[#A5A29C] hover:text-[#F7F4EF] hover:bg-[#202020] transition-colors"
                        >
                          Reset to Starter
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Monaco / Textarea Code Surface with Paste Restrictions */}
                  <div className="relative min-h-[460px] bg-[#1e1e1e]">
                    {pasteBlocked && (
                      <div className="absolute top-3 right-3 z-50 flex items-center gap-2 rounded-xl bg-[#BE123C] border border-[#FDA4AF] px-4 py-2.5 text-xs font-bold text-white shadow-2xl backdrop-blur-md animate-fade-in">
                        <span className="text-base">⚠️</span>
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
                  <div className="border-t border-[#353535] bg-[#121212] p-3">
                    <label className="block text-[11px] font-bold uppercase tracking-wider text-[#A5A29C]">
                      Custom Standard Input (stdin)
                    </label>
                    <textarea
                      rows={2}
                      value={stdin}
                      onChange={(e) => setStdin(e.target.value)}
                      placeholder="Optional inputs passed to program stdin when clicking 'Run Code'..."
                      className="mt-1 w-full rounded-lg border border-[#353535] bg-[#161616] p-2 font-mono text-xs text-[#F7F4EF] placeholder:text-[#77736D] outline-none"
                    />
                  </div>
                </div>

                {/* Console Output Drawer */}
                {consoleResult && (
                  <div
                    className={`lux-card p-4 animate-fade-in border ${
                      consoleResult.tone === "ok"
                        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                        : "border-rose-500/30 bg-rose-500/10 text-rose-300"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span
                        className={`text-xs font-bold uppercase tracking-wider ${
                          consoleResult.tone === "ok" ? "text-emerald-300" : "text-rose-300"
                        }`}
                      >
                        {consoleResult.title}
                      </span>
                      {lastSubmissionId && (
                        <button
                          onClick={requestAiFeedback}
                          disabled={feedbackBusy}
                          className="text-[11px] font-bold text-[#FF8A3D] underline hover:text-[#FF6B2C]"
                        >
                          {feedbackBusy ? "Analyzing..." : "Get AI Review 💡"}
                        </button>
                      )}
                    </div>
                    <pre
                      className={`mt-2 font-mono text-xs whitespace-pre-wrap ${
                        consoleResult.tone === "ok" ? "text-emerald-200" : "text-rose-200"
                      }`}
                    >
                      {consoleResult.body}
                    </pre>

                    {aiFeedback && (
                      <div className="mt-3 rounded-lg border border-[#353535] bg-[#161616] p-3 text-xs text-[#F7F4EF]">
                        <span className="font-bold text-[#FF8A3D]">AI Assistant Advice:</span>
                        <p className="mt-1 whitespace-pre-wrap text-[#C2BDB5]">{aiFeedback}</p>
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
            <div className="lux-card p-6 border border-[#353535] bg-[#1B1B1B]">
              <h2 className="text-lg font-bold text-[#F7F4EF]">Submission History</h2>
              <p className="mt-0.5 text-xs text-[#A5A29C]">
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
                        <th className="text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {submissions.map((sub) => (
                        <tr key={sub.id}>
                          <td className="font-mono text-xs font-bold text-[#706C65] dark:text-[#A5A29C]">#{sub.id}</td>
                          <td className="font-bold text-[#191919] dark:text-[#F7F4EF]">
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
                          <td className="text-xs font-semibold text-[#706C65] dark:text-[#A5A29C]">
                            {sub.passed_test_cases} / {sub.total_test_cases}
                          </td>
                          <td className="font-bold text-[#191919] dark:text-[#F7F4EF]">{sub.score}%</td>
                          <td className="text-xs text-[#706C65] dark:text-[#A5A29C]">
                            {new Date(sub.created_at).toLocaleString()}
                          </td>
                          <td className="text-right whitespace-nowrap">
                            <button
                              type="button"
                              onClick={() => void handleOpenGlobalSubmissionInEditor(sub)}
                              className="btn-secondary !py-1 !px-2.5 !text-[11px] font-bold hover:text-[#FF6B2C]"
                              title="Open in editor as an editable copy"
                            >
                              Open in Editor →
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="mt-6 text-center py-10 text-xs text-[#706C65] dark:text-[#A5A29C]">
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
                <h2 className="text-base font-bold text-[#191919] dark:text-[#F7F4EF]">Laboratory Practical Completion</h2>
                <div className="mt-4 flex items-center justify-between">
                  <span className="text-xs font-semibold text-[#706C65] dark:text-[#A5A29C]">Overall Curricular Progress</span>
                  <span className="text-xs font-extrabold text-[#FF6B2C] dark:text-[#FFB547]">
                    {allPracticals.length
                      ? Math.round((completedCount / allPracticals.length) * 100)
                      : 0}
                    %
                  </span>
                </div>
                <div className="mt-2 h-2.5 w-full rounded-full bg-[#F3EFEA] dark:bg-[#252525] border border-[#E4DDD2] dark:border-[#2D2D2D] overflow-hidden">
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
                  <div className="p-4 rounded-xl bg-[#FFFCF6] dark:bg-[#1B1B1B] border border-[#E4DDD2] dark:border-[#2D2D2D]">
                    <p className="text-2xl font-extrabold text-[#FF6B2C] dark:text-[#FFB547]">{completedCount}</p>
                    <p className="text-xs font-bold text-[#706C65] dark:text-[#A5A29C]">Practicals Completed</p>
                  </div>
                  <div className="p-4 rounded-xl bg-[#FFFCF6] dark:bg-[#1B1B1B] border border-[#E4DDD2] dark:border-[#2D2D2D]">
                    <p className="text-2xl font-extrabold text-[#E88A24] dark:text-[#FFB547]">
                      {(allPracticals.length || 0) - completedCount}
                    </p>
                    <p className="text-xs font-bold text-[#706C65] dark:text-[#A5A29C]">Practicals Remaining</p>
                  </div>
                </div>
              </div>

              <div className="lux-card p-6">
                <h2 className="text-base font-bold text-[#191919] dark:text-[#F7F4EF]">Submissions Breakdown</h2>
                <div className="mt-4 space-y-3">
                  {[
                    { label: "Total Submissions", count: submissions.length, color: "text-[#191919] dark:text-[#F7F4EF] font-bold" },
                    {
                      label: "Accepted (100% Score)",
                      count: acceptedSubmissions.length,
                      color: "text-emerald-600 dark:text-emerald-400 font-bold",
                    },
                    {
                      label: "Failed or Partial Attempts",
                      count: submissions.length - acceptedSubmissions.length,
                      color: "text-rose-600 dark:text-rose-400 font-bold",
                    },
                  ].map((row) => (
                    <div
                      key={row.label}
                      className="flex items-center justify-between p-3 rounded-xl bg-[#FFFCF6] dark:bg-[#1B1B1B] border border-[#E4DDD2] dark:border-[#2D2D2D] text-xs"
                    >
                      <span className="font-semibold text-[#706C65] dark:text-[#A5A29C]">{row.label}</span>
                      <span className={`text-sm ${row.color}`}>{row.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ───────────────── TAB: ACHIEVEMENTS (UNIFIED CREDENTIAL SYSTEM) ───────────────── */}
        {tab === "Achievements" && (
          <div className="mt-6 space-y-8 animate-fade-in">
            {certRequestMessage && (
              <div className="lux-card p-4 bg-[#FF6B2C]/10 border border-[#FF6B2C]/30 flex items-center justify-between text-xs text-[#FF6B2C] dark:text-[#FFB547] font-bold rounded-2xl">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-[#FF7A18]" />
                  <span>{certRequestMessage}</span>
                </div>
                <button
                  onClick={() => setCertRequestMessage("")}
                  className="text-xs text-[#706C65] dark:text-[#A5A29C] hover:text-[#191919] dark:hover:text-[#F7F4EF] transition cursor-pointer"
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* STATS OVERVIEW CARDS */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="lux-card p-5 border border-[#E4DDD2] dark:border-[#2D2D2D] bg-[#FFFCF6] dark:bg-[#18181A] rounded-2xl flex items-center gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-orange-500/10 text-[#FF7A18] border border-orange-500/20">
                  <Award className="w-6 h-6" />
                </div>
                <div>
                  <div className="text-2xl font-black text-[#191919] dark:text-[#F7F4EF]">
                    {earnedBadges.length}
                  </div>
                  <div className="text-xs font-bold text-[#706C65] dark:text-[#A5A29C]">
                    Practical Badges Earned
                  </div>
                </div>
              </div>

              <div className="lux-card p-5 border border-[#E4DDD2] dark:border-[#2D2D2D] bg-[#FFFCF6] dark:bg-[#18181A] rounded-2xl flex items-center gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                  <ShieldCheck className="w-6 h-6" />
                </div>
                <div>
                  <div className="text-2xl font-black text-[#191919] dark:text-[#F7F4EF]">
                    {studentProgress.filter((s) => s.certificate_status === "ISSUED").length}
                  </div>
                  <div className="text-xs font-bold text-[#706C65] dark:text-[#A5A29C]">
                    Certified Subjects
                  </div>
                </div>
              </div>

              <div className="lux-card p-5 border border-[#E4DDD2] dark:border-[#2D2D2D] bg-[#FFFCF6] dark:bg-[#18181A] rounded-2xl flex items-center gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-amber-500/10 text-amber-500 border border-amber-500/20">
                  <BookOpen className="w-6 h-6" />
                </div>
                <div>
                  <div className="text-2xl font-black text-[#191919] dark:text-[#F7F4EF]">
                    {studentProgress.reduce((acc, s) => acc + s.completed_required, 0)} /{" "}
                    {studentProgress.reduce((acc, s) => acc + s.total_required, 0)}
                  </div>
                  <div className="text-xs font-bold text-[#706C65] dark:text-[#A5A29C]">
                    Required Practicals Done
                  </div>
                </div>
              </div>

              <div className="lux-card p-5 border border-[#E4DDD2] dark:border-[#2D2D2D] bg-[#FFFCF6] dark:bg-[#18181A] rounded-2xl flex items-center gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-blue-500/10 text-blue-500 border border-blue-500/20">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
                <div>
                  <div className="text-sm font-black text-[#191919] dark:text-[#F7F4EF] uppercase tracking-wide">
                    ED25519-SHA256
                  </div>
                  <div className="text-xs font-bold text-[#706C65] dark:text-[#A5A29C]">
                    Cryptographic Integrity
                  </div>
                </div>
              </div>
            </div>

            {/* ═══════════════════════════════════════════════════════════════ */}
            {/* SECTION 1: PRACTICAL ACHIEVEMENT BADGE GALLERY (APPEARS FIRST)  */}
            {/* ═══════════════════════════════════════════════════════════════ */}
            <section className="lux-card p-6 sm:p-8 rounded-3xl border border-[#E4DDD2] dark:border-[#2D2D2D] bg-[#FFFCF6] dark:bg-[#161618] shadow-sm">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-[#E4DDD2] dark:border-[#2D2D2D]">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="p-1.5 rounded-lg bg-[#FF7A18]/10 text-[#FF7A18]">
                      <Award className="w-5 h-5" />
                    </span>
                    <h2 className="text-xl font-extrabold text-[#191919] dark:text-[#F7F4EF] tracking-tight">
                      Practical Achievement Badge Gallery
                    </h2>
                  </div>
                  <p className="mt-1 text-xs text-[#706C65] dark:text-[#A5A29C]">
                    Individual practical completion badges automatically awarded upon passing automated evaluations.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="badge-primary px-3.5 py-1 text-xs font-extrabold rounded-full shadow-xs">
                    {filteredBadges.length} {filteredBadges.length === 1 ? "Badge" : "Badges"} Unlocked
                  </span>
                </div>
              </div>

              {/* SEARCH & FILTER CONTROLS */}
              {earnedBadges.length > 0 && (
                <div className="mt-6 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                  {/* Search Bar */}
                  <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#706C65] dark:text-[#A5A29C]" />
                    <input
                      type="text"
                      value={badgeSearchQuery}
                      onChange={(e) => setBadgeSearchQuery(e.target.value)}
                      placeholder="Search badges by practical title or subject..."
                      className="w-full pl-9.5 pr-4 py-2 rounded-xl text-xs bg-[#F7F4EF] dark:bg-[#1E1E22] border border-[#E4DDD2] dark:border-[#2E2E32] text-[#191919] dark:text-[#F7F4EF] placeholder-[#A5A29C] focus:outline-none focus:border-[#FF7A18] transition"
                    />
                  </div>

                  {/* Filter Pills & Sort Dropdown */}
                  <div className="flex flex-wrap items-center gap-2">
                    {/* Subject Filter Dropdown */}
                    {badgeSubjects.length > 0 && (
                      <select
                        value={badgeSubjectFilter}
                        onChange={(e) => setBadgeSubjectFilter(e.target.value)}
                        className="py-2 px-3 rounded-xl text-xs font-bold bg-[#F7F4EF] dark:bg-[#1E1E22] border border-[#E4DDD2] dark:border-[#2E2E32] text-[#191919] dark:text-[#F7F4EF] focus:outline-none focus:border-[#FF7A18] transition cursor-pointer"
                      >
                        <option value="ALL">All Subjects ({earnedBadges.length})</option>
                        {badgeSubjects.map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                    )}

                    {/* Sort Order Selector */}
                    <select
                      value={badgeSortOrder}
                      onChange={(e) => setBadgeSortOrder(e.target.value as "newest" | "oldest" | "alpha")}
                      className="py-2 px-3 rounded-xl text-xs font-bold bg-[#F7F4EF] dark:bg-[#1E1E22] border border-[#E4DDD2] dark:border-[#2E2E32] text-[#191919] dark:text-[#F7F4EF] focus:outline-none focus:border-[#FF7A18] transition cursor-pointer"
                    >
                      <option value="newest">Newest First</option>
                      <option value="oldest">Oldest First</option>
                      <option value="alpha">Title (A-Z)</option>
                    </select>
                  </div>
                </div>
              )}

              {/* BADGE GALLERY GRID */}
              {filteredBadges.length > 0 ? (
                <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                  {filteredBadges.map((badge) => {
                    const subjectTitle =
                      badge.course_name ||
                      (badge.meta as { course_name?: string })?.course_name ||
                      "Curriculum Lab";
                    const practicalTitle =
                      badge.practical_title ||
                      (badge.meta as { practical_title?: string })?.practical_title ||
                      badge.name ||
                      "Practical Challenge";
                    const unlockedDate = new Date(badge.earned_at).toLocaleDateString("en-US", {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    });

                    return (
                      <div
                        key={badge.id}
                        onClick={() => setSelectedBadgeForModal(badge)}
                        className="group relative rounded-3xl bg-[#121214] border border-zinc-800/80 p-4 shadow-lg hover:shadow-2xl hover:border-orange-500/50 hover:-translate-y-1 transition duration-300 flex flex-col justify-between cursor-pointer"
                      >
                        {/* 1:1 Badge Component Display */}
                        <div className="relative w-full aspect-square flex items-center justify-center p-1">
                          <BadgeRenderer
                            subjectName={subjectTitle}
                            practicalTitle={practicalTitle}
                            courseCode={badge.course_code || (badge.meta as { course_code?: string })?.course_code}
                            earnedAt={badge.earned_at}
                            className="w-full h-full transform transition duration-300 group-hover:scale-[1.02]"
                          />
                        </div>

                        {/* Card Footer Details */}
                        <div className="mt-3.5 pt-3 border-t border-zinc-800/70 flex items-center justify-between text-xs">
                          <div className="min-w-0 flex-1 pr-2">
                            <div className="text-[11px] font-mono text-[#FF7A18] font-semibold truncate">
                              {unlockedDate}
                            </div>
                            <div className="text-zinc-400 text-[10px] truncate">
                              Automated Test Verified
                            </div>
                          </div>

                          <div className="flex items-center gap-1.5 shrink-0">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                const clean = practicalTitle.toLowerCase().replace(/[^a-z0-9]/g, "-");
                                void downloadBadgePng(badge, `credlab-badge-${clean}.png`);
                              }}
                              title="Download Badge PNG"
                              className="p-2 rounded-xl bg-zinc-800 text-zinc-300 hover:text-white hover:bg-orange-500/20 hover:text-[#FF7A18] transition cursor-pointer"
                            >
                              <Download className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedBadgeForModal(badge);
                              }}
                              title="Inspect Badge"
                              className="p-2 rounded-xl bg-orange-500/10 text-[#FF7A18] hover:bg-orange-500 hover:text-white transition cursor-pointer"
                            >
                              <Eye className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : earnedBadges.length > 0 ? (
                <div className="mt-8 py-12 text-center rounded-2xl bg-[#F7F4EF] dark:bg-[#1A1A1D] border border-dashed border-[#E4DDD2] dark:border-[#2D2D2D] p-6">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-zinc-800 text-zinc-400 mb-3">
                    <Search className="w-6 h-6" />
                  </div>
                  <h3 className="font-extrabold text-sm text-[#191919] dark:text-[#F7F4EF]">
                    No badges match your search or filter
                  </h3>
                  <p className="mt-1 text-xs text-[#706C65] dark:text-[#A5A29C]">
                    Try clearing your search query or choosing another subject filter.
                  </p>
                  <button
                    onClick={() => {
                      setBadgeSearchQuery("");
                      setBadgeSubjectFilter("ALL");
                    }}
                    className="mt-4 px-4 py-2 rounded-xl text-xs font-bold bg-[#FF7A18] text-white hover:brightness-110 transition cursor-pointer"
                  >
                    Reset Filters
                  </button>
                </div>
              ) : (
                <div className="mt-8 py-12 text-center rounded-3xl bg-[#F7F4EF] dark:bg-[#141416] border border-dashed border-[#E4DDD2] dark:border-[#2D2D2D] p-8">
                  <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl bg-orange-500/10 text-[#FF7A18] mb-4">
                    <Award className="w-8 h-8" />
                  </div>
                  <h3 className="text-base font-extrabold text-[#191919] dark:text-[#F7F4EF]">
                    No Achievement Badges Unlocked Yet
                  </h3>
                  <p className="mt-1.5 max-w-md mx-auto text-xs text-[#706C65] dark:text-[#A5A29C]">
                    Badges are automatically awarded whenever you pass all unit tests with passing score on any curriculum practical.
                  </p>
                  <button
                    onClick={() => setTab("My Labs")}
                    className="mt-5 btn-primary !py-2.5 !px-5 !text-xs font-bold inline-flex items-center gap-2"
                  >
                    <span>Go to My Labs &amp; Solve Practicals</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              )}
            </section>

            {/* ══════════════════════════════════════════════════════════════════════ */}
            {/* SECTION 2: SUBJECT COMPLETION CERTIFICATIONS (APPEARS BELOW BADGES)   */}
            {/* ══════════════════════════════════════════════════════════════════════ */}
            <section className="lux-card p-6 sm:p-8 rounded-3xl border border-[#E4DDD2] dark:border-[#2D2D2D] bg-[#FFFCF6] dark:bg-[#161618] shadow-sm space-y-8">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-[#E4DDD2] dark:border-[#2D2D2D]">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-500">
                      <ShieldCheck className="w-5 h-5" />
                    </span>
                    <h2 className="text-xl font-extrabold text-[#191919] dark:text-[#F7F4EF] tracking-tight">
                      Curriculum Subject Certifications
                    </h2>
                  </div>
                  <p className="mt-1 text-xs text-[#706C65] dark:text-[#A5A29C]">
                    Official degree-aligned completion credentials cryptographically signed with Ed25519 institutional keys.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <span className="badge-success px-3.5 py-1 text-xs font-extrabold rounded-full">
                    {studentProgress.filter((s) => s.certificate_status === "ISSUED").length} of {studentProgress.length} Certified
                  </span>
                </div>
              </div>

              {/* 2A: ISSUED SUBJECT CERTIFICATES PREVIEWS (IF ANY) */}
              {certificateData.certificates.length > 0 && (
                <div>
                  <h3 className="text-sm font-bold uppercase tracking-wider text-[#FF7A18] mb-4 flex items-center gap-2">
                    <Sparkles className="w-4 h-4" />
                    <span>Issued Subject Certificates</span>
                  </h3>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {certificateData.certificates.map((cert) => {
                      const courseName = cert.course_name || cert.lab_title || "Curriculum Subject";
                      const courseCode = cert.course_code || "";

                      return (
                        <div
                          key={cert.id}
                          className="rounded-3xl bg-[#121214] border border-zinc-800 p-5 shadow-xl flex flex-col justify-between group hover:border-orange-500/40 transition duration-300"
                        >
                          {/* Certificate Landscape Renderer Preview */}
                          <div
                            onClick={() =>
                              setSelectedCertForModal({
                                id: cert.id,
                                student_name: user?.name || "Student",
                                course_name: courseName,
                                course_code: courseCode,
                                completed_practicals_count: cert.completed_practicals_count || 8,
                                total_practicals_count: cert.total_practicals_count || 8,
                                issued_at: cert.issued_at,
                                completed_at: cert.completed_at || cert.issued_at,
                              })
                            }
                            className="rounded-2xl overflow-hidden shadow-md cursor-pointer transform transition duration-300 group-hover:scale-[1.01]"
                          >
                            <CertificateRenderer
                              certificateId={cert.id}
                              studentName={user?.name || "Student Name"}
                              courseName={courseName}
                              courseCode={courseCode}
                              completedPracticalsCount={cert.completed_practicals_count || 8}
                              totalPracticalsCount={cert.total_practicals_count || 8}
                              completedAt={cert.completed_at || cert.issued_at}
                              issuedAt={cert.issued_at}
                              status="Verified & Issued"
                            />
                          </div>

                          {/* Card Footer Details */}
                          <div className="mt-4 pt-3 border-t border-zinc-800/80 flex flex-wrap items-center justify-between gap-3">
                            <div className="min-w-0">
                              <span className="badge-success px-2.5 py-0.5 text-[10px] font-bold rounded-md">
                                ACTIVE ED25519 DIPLOMA ✓
                              </span>
                              <div className="font-mono text-[10px] text-zinc-400 mt-1 truncate">
                                Issued: {new Date(cert.issued_at).toLocaleDateString()}
                              </div>
                            </div>

                            <div className="flex items-center gap-2">
                              <button
                                onClick={() =>
                                  setSelectedCertForModal({
                                    id: cert.id,
                                    student_name: user?.name || "Student",
                                    course_name: courseName,
                                    course_code: courseCode,
                                    completed_practicals_count: cert.completed_practicals_count || 8,
                                    total_practicals_count: cert.total_practicals_count || 8,
                                    issued_at: cert.issued_at,
                                    completed_at: cert.completed_at || cert.issued_at,
                                  })
                                }
                                className="px-3.5 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-[#FF7A18] to-[#E65100] text-white hover:brightness-110 shadow-md transition flex items-center gap-1.5 cursor-pointer"
                              >
                                <Download className="w-3.5 h-3.5" />
                                <span>Preview &amp; PDF</span>
                              </button>
                              <Link
                                href={`/certificates/${cert.id}`}
                                className="px-3 py-2 rounded-xl text-xs font-semibold bg-zinc-800 text-zinc-300 hover:text-white hover:bg-zinc-700 transition"
                              >
                                Verify
                              </Link>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* 2B: ENROLLED SUBJECT PROGRESS & CERTIFICATE STATUS */}
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-[#706C65] dark:text-[#A5A29C] mb-4">
                  Enrolled Subjects &amp; Practical Completion
                </h3>

                {studentProgress.length > 0 ? (
                  <div className="space-y-4">
                    {studentProgress.map((prog) => (
                      <div
                        key={prog.course_id}
                        className="lux-card p-5 sm:p-6 border border-[#E4DDD2] dark:border-[#2D2D2D] bg-[#FFFCF6] dark:bg-[#1A1A1D] rounded-2xl transition hover:shadow-md"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-4">
                          <div className="flex-1 min-w-[240px]">
                            <div className="flex items-center gap-2">
                              <span className="badge-primary px-2.5 py-0.5 text-[10px] font-extrabold rounded-md">
                                {prog.course_code || "SUBJECT"}
                              </span>
                              <h4 className="text-base font-extrabold text-[#191919] dark:text-[#F7F4EF]">
                                {prog.course_name}
                              </h4>
                            </div>

                            <p className="mt-2 text-xs text-[#706C65] dark:text-[#A5A29C]">
                              Required Challenges:{" "}
                              <span className="font-extrabold text-[#191919] dark:text-[#F7F4EF]">
                                {prog.completed_required} of {prog.total_required} completed
                              </span>{" "}
                              · Achievement Badges Earned:{" "}
                              <span className="font-extrabold text-[#FF6B2C] dark:text-[#FFB547]">
                                {prog.badges_earned}
                              </span>
                            </p>
                          </div>

                          {/* Dynamic Status Pill */}
                          <div className="shrink-0">
                            {prog.certificate_status === "ISSUED" && (
                              <span className="badge-success px-3.5 py-1 text-xs font-bold rounded-full">
                                CERTIFICATE ISSUED ✓
                              </span>
                            )}
                            {prog.certificate_status === "PENDING_APPROVAL" && (
                              <span className="badge-warning px-3.5 py-1 text-xs font-bold rounded-full animate-pulse">
                                AWAITING FACULTY APPROVAL
                              </span>
                            )}
                            {prog.certificate_status === "REJECTED" && (
                              <span className="badge-danger px-3.5 py-1 text-xs font-bold rounded-full">
                                REVISION REQUESTED
                              </span>
                            )}
                            {prog.certificate_status === "ELIGIBLE" && (
                              <span className="px-3.5 py-1 text-xs font-extrabold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                                100% COMPLETED · ELIGIBLE
                              </span>
                            )}
                            {prog.certificate_status === "NOT_ELIGIBLE" && (
                              <span className="bg-[#F3EFEA] dark:bg-[#252525] text-[#706C65] dark:text-[#A5A29C] px-3.5 py-1 text-xs font-bold rounded-full border border-[#E4DDD2] dark:border-[#2D2D2D]">
                                {prog.remaining_required} PRACTICAL(S) REMAINING
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Progress Bar */}
                        <div className="mt-4">
                          <div className="flex justify-between text-xs font-bold mb-1.5">
                            <span className="text-[#706C65] dark:text-[#A5A29C]">Curriculum Completion</span>
                            <span className="text-[#FF6B2C] dark:text-[#FFB547] font-mono">
                              {prog.completion_percentage}%
                            </span>
                          </div>
                          <div className="h-2.5 w-full rounded-full bg-[#EEE8DE] dark:bg-[#252525] border border-[#E4DDD2] dark:border-[#2D2D2D] overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-700 ease-out"
                              style={{
                                background: "linear-gradient(90deg, #FF7A18, #E65100)",
                                width: `${Math.min(100, Math.max(0, prog.completion_percentage))}%`,
                              }}
                            />
                          </div>
                        </div>

                        {/* Faculty Feedback Note if Rejected */}
                        {prog.certificate_status === "REJECTED" && prog.rejection_note && (
                          <div className="mt-3.5 rounded-xl p-3.5 bg-rose-500/10 border border-rose-500/30 text-xs text-rose-800 dark:text-rose-300">
                            <span className="font-extrabold">Faculty Revision Note:</span>{" "}
                            {prog.rejection_note}
                          </div>
                        )}

                        {/* Action Row */}
                        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 pt-3.5 border-t border-[#E4DDD2] dark:border-[#2D2D2D]">
                          <p className="text-[11px] text-[#706C65] dark:text-[#A5A29C]">
                            {prog.certificate_status === "ISSUED"
                              ? "Official subject diploma is active and verifiable in your academic portfolio."
                              : prog.certificate_status === "ELIGIBLE"
                              ? "All required challenges passed! You may now request faculty certification."
                              : prog.certificate_status === "PENDING_APPROVAL"
                              ? "Certificate request is in the faculty verification queue."
                              : prog.certificate_status === "REJECTED"
                              ? "Please review faculty feedback and resolve outstanding items."
                              : "Solve and pass all required practical challenges with passing score to unlock certification."}
                          </p>

                          {(prog.certificate_status === "ELIGIBLE" || prog.certificate_status === "REJECTED") && (
                            <button
                              onClick={() => void handleRequestSubjectCert(prog.course_id)}
                              disabled={requestingCertCourseId === prog.course_id}
                              className="btn-primary !py-2 !px-4 !text-xs font-bold flex items-center gap-1.5"
                            >
                              <ShieldCheck className="w-3.5 h-3.5" />
                              <span>
                                {requestingCertCourseId === prog.course_id
                                  ? "Submitting..."
                                  : prog.certificate_status === "REJECTED"
                                  ? "Re-Request Subject Certificate"
                                  : "Request Subject Certificate"}
                              </span>
                            </button>
                          )}

                          {prog.certificate_status === "ISSUED" && prog.certificate_id && (
                            <Link
                              href={`/certificates/${prog.certificate_id}`}
                              className="btn-secondary !py-2 !px-4 !text-xs font-bold inline-flex items-center gap-1.5"
                            >
                              <span>View Certificate</span>
                              <ChevronRight className="w-3.5 h-3.5" />
                            </Link>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="mt-4 text-center py-8 text-xs text-[#706C65] dark:text-[#A5A29C] rounded-2xl bg-[#FFFCF6] dark:bg-[#1A1A1D] border border-dashed border-[#E4DDD2] dark:border-[#2D2D2D]">
                    No enrolled curriculum subjects found for your profile.
                  </div>
                )}
              </div>
            </section>
          </div>
        )}

        {/* ───────────────── TAB: PROFILE ───────────────── */}
        {tab === "Profile" && (
          <div className="mt-6 space-y-6 animate-fade-in">
            <div className="lux-card p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-[#191919] dark:text-[#F7F4EF]">Academic Identity & Credentials</h2>
                  <p className="mt-0.5 text-xs text-[#706C65] dark:text-[#A5A29C]">
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
                    <label className="block text-xs font-bold uppercase tracking-wider text-[#191919] dark:text-[#F7F4EF] mb-1">
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
                    <label className="block text-xs font-bold uppercase tracking-wider text-[#191919] dark:text-[#F7F4EF] mb-1">
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
                      <label className="block text-xs font-bold uppercase tracking-wider text-[#191919] dark:text-[#F7F4EF] mb-1">
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
                      <label className="block text-xs font-bold uppercase tracking-wider text-[#191919] dark:text-[#F7F4EF] mb-1">
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
                    <div key={x.label} className="p-4 rounded-xl bg-[#FFFCF6] dark:bg-[#1B1B1B] border border-[#E4DDD2] dark:border-[#2D2D2D]">
                      <p className="text-[11px] font-bold uppercase tracking-wider text-[#706C65] dark:text-[#A5A29C]">
                        {x.label}
                      </p>
                      <p className="mt-1 text-sm font-bold text-[#191919] dark:text-[#F7F4EF]">{x.value || "Not set"}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        <footer className="mt-12 text-center text-xs py-4 text-[#706C65] dark:text-[#A5A29C] font-mono">
          CredLab · Cryptographically Signed University Assessments · 2026
        </footer>
      </div>

      {/* ───────────────── VIEW CODE & SUBMISSION INSPECTION MODAL ───────────────── */}
      {viewingSubmission && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4 animate-fade-in">
          <div className="flex max-h-[90vh] w-full max-w-3xl flex-col rounded-2xl border border-[#353535] bg-[#1B1B1B] shadow-2xl">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-[#353535] px-6 py-4">
              <div className="flex items-center gap-3">
                <span className="text-xl">📄</span>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-[#F7F4EF]">
                      Submission #{viewingSubmission.id}
                    </h3>
                    <span
                      className={`px-2 py-0.5 rounded-md text-[10px] font-bold ${
                        viewingSubmission.status === "ACCEPTED" || viewingSubmission.score === 100
                          ? "badge-success"
                          : "badge-danger"
                      }`}
                    >
                      {viewingSubmission.status}
                    </span>
                  </div>
                  <p className="text-[11px] font-mono text-[#A5A29C]">
                    Submitted {new Date(viewingSubmission.created_at).toLocaleString()} • Language: {viewingSubmission.language.toUpperCase()}
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setViewingSubmission(null)}
                className="rounded-lg p-1.5 text-xs text-[#A5A29C] hover:bg-[#252525] hover:text-[#F7F4EF]"
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            {/* Modal Metrics Bar */}
            <div className="grid grid-cols-2 gap-3 border-b border-[#292929] bg-[#161616] px-6 py-3 sm:grid-cols-4 text-xs font-mono">
              <div>
                <span className="text-[10px] uppercase font-bold text-[#77736D]">Score</span>
                <p className="font-bold text-[#F7F4EF]">{viewingSubmission.score}%</p>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-[#77736D]">Test Cases</span>
                <p className="font-bold text-[#F7F4EF]">
                  {viewingSubmission.passed_test_cases} / {viewingSubmission.total_test_cases}
                </p>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-[#77736D]">Runtime</span>
                <p className="text-[#C2BDB5]">
                  {viewingSubmission.execution_time_ms ? `${viewingSubmission.execution_time_ms} ms` : "--"}
                </p>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-[#77736D]">Memory</span>
                <p className="text-[#C2BDB5]">
                  {viewingSubmission.memory_kb ? `${viewingSubmission.memory_kb} KB` : "--"}
                </p>
              </div>
            </div>

            {/* Modal Body: Source Code & Test Details */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {viewingSubmissionLoading ? (
                <div className="flex h-48 flex-col items-center justify-center gap-2 text-xs text-[#A5A29C]">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#FF6B2C] border-t-transparent" />
                  <span>Loading submitted source code...</span>
                </div>
              ) : (
                <>
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-[#FF8A3D]">
                        Submitted Source Code
                      </span>
                      <button
                        type="button"
                        onClick={() => {
                          if (viewingSubmission.source_code) {
                            void navigator.clipboard.writeText(viewingSubmission.source_code);
                            setCodeCopied(true);
                            setTimeout(() => setCodeCopied(false), 2000);
                          }
                        }}
                        className="text-[11px] font-bold text-[#A5A29C] hover:text-[#FF6B2C] transition-colors"
                      >
                        {codeCopied ? "Copied! ✓" : "Copy Code 📋"}
                      </button>
                    </div>
                    <pre className="rounded-xl border border-[#353535] bg-[#121212] p-4 font-mono text-xs text-[#d4d4d4] leading-5 overflow-x-auto max-h-[300px]">
                      {viewingSubmission.source_code || "// Source code not available."}
                    </pre>
                  </div>

                  {viewingSubmission.error_message && (
                    <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs">
                      <span className="font-bold text-rose-300 uppercase tracking-wider text-[10px]">
                        Error Diagnostic Output
                      </span>
                      <pre className="mt-1 font-mono text-rose-200 whitespace-pre-wrap">
                        {viewingSubmission.error_message}
                      </pre>
                    </div>
                  )}

                  {viewingSubmission.test_results && viewingSubmission.test_results.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-[#A5A29C]">
                        Test Case Evaluations
                      </span>
                      <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
                        {viewingSubmission.test_results.map((tr, i) => (
                          <div
                            key={tr.id || i}
                            className={`rounded-lg border p-2.5 text-xs ${
                              tr.passed
                                ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-200"
                                : "border-rose-500/30 bg-rose-500/5 text-rose-200"
                            }`}
                          >
                            <div className="flex items-center justify-between font-mono font-bold text-[11px]">
                              <span>
                                {tr.is_hidden ? `Hidden Assessment Case #${i + 1}` : `Public Sample Test #${i + 1}`}
                              </span>
                              <span>{tr.passed ? "PASSED ✓" : `FAILED ✗ (${tr.status})`}</span>
                            </div>
                            {!tr.is_hidden && tr.input && (
                              <div className="mt-1.5 grid grid-cols-2 gap-2 text-[10px] text-[#A5A29C]">
                                <div>
                                  <span className="font-bold uppercase">Input:</span>
                                  <pre className="bg-[#121212] p-1.5 rounded font-mono text-[#F7F4EF]">{tr.input}</pre>
                                </div>
                                <div>
                                  <span className="font-bold uppercase">Expected:</span>
                                  <pre className="bg-[#121212] p-1.5 rounded font-mono text-[#F7F4EF]">{tr.expected_output}</pre>
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Modal Footer */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#353535] bg-[#161616] px-6 py-3.5">
              <span className="text-[11px] text-[#A5A29C]">
                Clicking &ldquo;Open in Editor&rdquo; loads this code as an editable copy to submit as a new attempt.
              </span>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setViewingSubmission(null)}
                  className="btn-secondary !py-2 !px-4 !text-xs font-bold"
                >
                  Close
                </button>
                <button
                  type="button"
                  onClick={() => void handleRequestLoadSubmission(viewingSubmission)}
                  className="btn-primary !py-2 !px-4 !text-xs font-bold"
                >
                  Open in Editor →
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ───────────────── UNSAVED CHANGES CONFIRMATION MODAL ───────────────── */}
      {confirmOverwriteOpen && pendingSubmissionToLoad && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4 animate-fade-in">
          <div className="w-full max-w-md rounded-2xl border border-amber-500/30 bg-[#1B1B1B] p-6 shadow-2xl">
            <div className="flex items-center gap-3 text-amber-400">
              <span className="text-2xl">⚠️</span>
              <h3 className="text-base font-bold text-[#F7F4EF]">Unsaved Code In Editor</h3>
            </div>
            <p className="mt-3 text-xs leading-5 text-[#C2BDB5]">
              You have unsaved changes in the editor. Loading <strong>Submission #{pendingSubmissionToLoad.id}</strong> will replace your current editor contents with a copy of that attempt.
            </p>
            <p className="mt-2 text-[11px] text-[#A5A29C]">
              Note: The loaded code will remain fully editable, and submitting it will create a <strong>NEW</strong> submission attempt.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setConfirmOverwriteOpen(false);
                  setPendingSubmissionToLoad(null);
                }}
                className="btn-secondary !py-2 !px-4 !text-xs font-bold"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  if (pendingSubmissionToLoad) {
                    loadSubmissionIntoEditor(pendingSubmissionToLoad);
                  }
                }}
                className="btn-primary !py-2 !px-4 !text-xs font-bold"
              >
                Replace Editor Contents
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ───────────────── BADGE INSPECTION & DOWNLOAD MODAL ───────────────── */}
      {selectedBadgeForModal && (
        <BadgeModal
          badge={selectedBadgeForModal}
          onClose={() => setSelectedBadgeForModal(null)}
        />
      )}

      {/* ───────────────── CERTIFICATE INSPECTION & PDF EXPORT MODAL ───────────────── */}
      {selectedCertForModal && (
        <CertificateModal
          certificate={selectedCertForModal}
          onClose={() => setSelectedCertForModal(null)}
        />
      )}
    </main>
  );
}
