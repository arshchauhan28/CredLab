"use client";
/* eslint react-hooks/set-state-in-effect: off */

import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { UserResponse } from "@/types/auth";
import { CredLabLogo } from "@/components/CredLabLogo";
import { DashboardAmbientGrid } from "@/components/3d/DashboardAmbientGrid";

type Course = {
  id: number;
  code?: string | null;
  name: string;
  program: string;
  year_of_study: string;
  semester: string;
  academic_year?: string | null;
  faculty_names?: string[];
  lab_count: number;
  student_count: number;
};

type Lab = {
  id: number;
  course_id: number;
  title: string;
  description?: string | null;
  instructions?: string | null;
  is_published: boolean;
  practical_count: number;
};

type Practical = {
  id: number;
  lab_id: number;
  question_id: number;
  effective_title: string;
  sequence_number: number;
  is_required?: boolean;
  is_active?: boolean;
  passing_threshold?: number;
};

type Submission = {
  id: number;
  user_id: number;
  student_name: string;
  question_id: number;
  question_title: string;
  practical_id?: number;
  language: string;
  status: string;
  total_test_cases: number;
  passed_test_cases: number;
  score: number;
  created_at: string;
};

type Approval = {
  id: number;
  student_id: number;
  student_name: string;
  student_email: string;
  lab_id: number;
  lab_title: string;
  course_id: number;
  practical_id: number;
  submission_id: number;
  status: string;
  requested_at: string;
  review_note?: string | null;
};

type SubjectApproval = {
  id: number;
  student_id: number;
  student_name: string;
  student_email: string;
  enrollment_number?: string;
  course_id: number;
  course_name: string;
  course_code?: string;
  total_required: number;
  status: string;
  review_note?: string | null;
  requested_at: string;
  reviewed_at?: string | null;
};

type PracticalDeletionPreview = {
  practical_id: number;
  title: string;
  subject_name: string;
  lab_title: string;
  historical_submissions_count: number;
  has_historical_activity: boolean;
  action: string;
  warning_message: string;
};

type Section =
  | "Overview"
  | "My Courses"
  | "Subject Practicals"
  | "Submissions"
  | "Certificates"
  | "Profile";

const LANGS = ["python", "cpp", "c", "java"];

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(`/api/admin/${path.replace(/^\/+/, "")}`, {
    ...init,
    cache: "no-store",
    headers,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string" ? data.detail : `Request failed (${response.status})`,
    );
  return data as T;
}

export default function FacultyDashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserResponse | null>(null);
  const [section, setSection] = useState<Section>("Overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  // Core Data
  const [courses, setCourses] = useState<Course[]>([]);
  const [courseId, setCourseId] = useState<number | "">("");
  const [coursePracticals, setCoursePracticals] = useState<Practical[]>([]);
  const [coursePracticalsLoading, setCoursePracticalsLoading] = useState(false);
  const [labs, setLabs] = useState<Lab[]>([]);
  const [showAdvancedLabs, setShowAdvancedLabs] = useState(false);
  const [submissions, setSubmissions] = useState<Submission[]>([]);

  // Certificates state
  const [certTab, setCertTab] = useState<"SUBJECT" | "LAB">("SUBJECT");
  const [subjectApprovals, setSubjectApprovals] = useState<SubjectApproval[]>([]);
  const [subjectReviewNotes, setSubjectReviewNotes] = useState<Record<number, string>>({});
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [reviewNotes, setReviewNotes] = useState<Record<number, string>>({});

  // Practical Deletion Modal
  const [deletingPractical, setDeletingPractical] = useState<Practical | null>(null);
  const [deletionPreview, setDeletionPreview] = useState<PracticalDeletionPreview | null>(null);
  const [deletionLoading, setDeletionLoading] = useState(false);

  // Create Lab Form (Advanced)
  const [labForm, setLabForm] = useState({
    title: "",
    description: "",
    instructions: "",
    is_published: true,
  });

  // Create Practical directly under Course
  const [problemForm, setProblemForm] = useState({
    title: "",
    description: "",
    input_format: "",
    output_format: "",
    difficulty: "EASY",
    sample_input: "",
    sample_output: "",
  });
  const [languages, setLanguages] = useState<string[]>(["python", "cpp", "c", "java"]);

  // Fetch practicals for the currently selected course
  const loadPracticalsForCourse = useCallback(async (cId: number) => {
    try {
      setCoursePracticalsLoading(true);
      const list = await api<Practical[]>(`courses/${cId}/practicals`).catch(() => []);
      setCoursePracticals(list);
    } catch {
      setCoursePracticals([]);
    } finally {
      setCoursePracticalsLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    try {
      setBusy(true);
      const [cList, subList, appList, subjAppList] = await Promise.all([
        api<Course[]>("courses"),
        api<{ items: Submission[] }>("submissions?page=1&page_size=50").catch(() => ({
          items: [],
        })),
        api<{ items: Approval[] }>("certificates/approvals").catch(() => ({
          items: [],
        })),
        api<{ items: SubjectApproval[] }>("certificates/subject-approvals").catch(() => ({
          items: [],
        })),
      ]);

      setCourses(cList);
      setSubmissions(subList.items ?? []);
      setApprovals(appList.items ?? []);
      setSubjectApprovals(subjAppList.items ?? []);

      let activeCourseId = courseId;
      if (cList.length && (courseId === "" || !cList.some((c) => c.id === courseId))) {
        activeCourseId = cList[0].id;
        setCourseId(cList[0].id);
      }

      if (activeCourseId) {
        await loadPracticalsForCourse(Number(activeCourseId));
      }

      // Collect labs across courses for advanced view
      const allLabsNested = await Promise.all(
        cList.map(async (c) => {
          try {
            return await api<Lab[]>(`courses/${c.id}/labs`);
          } catch {
            return [];
          }
        }),
      );
      setLabs(allLabsNested.flat());
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : "Failed to refresh dashboard data.");
    } finally {
      setBusy(false);
    }
  }, [courseId, loadPracticalsForCourse]);

  useEffect(() => {
    let cancelled = false;
    async function init() {
      try {
        const response = await fetch("/api/auth/session", { cache: "no-store" });
        if (response.status === 401) {
          router.replace("/login");
          return;
        }
        if (!response.ok) throw new Error("Authentication failed.");
        const session = (await response.json()) as { user: UserResponse };
        if (session.user.role !== "FACULTY") {
          router.replace(session.user.role === "ADMIN" ? "/admin/dashboard" : "/student/dashboard");
          return;
        }
        if (cancelled) return;
        setUser(session.user);
        await refresh();
      } catch (cause) {
        if (!cancelled)
          setError(cause instanceof Error ? cause.message : "Could not load faculty dashboard.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void init();
    return () => {
      cancelled = true;
    };
  }, [refresh, router]);

  // When courseId changes from user dropdown
  function handleCourseChange(newId: number) {
    setCourseId(newId);
    void loadPracticalsForCourse(newId);
  }

  // Create Practical directly linked to Course (Part 5)
  async function createPractical(e: FormEvent) {
    e.preventDefault();
    if (!courseId) {
      setNotice("Select a target course first.");
      return;
    }
    setBusy(true);
    try {
      // Step 1: Create Question
      const q = await api<{ id: number }>("questions", {
        method: "POST",
        body: JSON.stringify({
          title: problemForm.title,
          description: problemForm.description,
          input_format: problemForm.input_format || undefined,
          output_format: problemForm.output_format || undefined,
          difficulty: problemForm.difficulty,
          status: "PUBLISHED",
          allowed_languages: languages,
          examples: problemForm.sample_input
            ? [
                {
                  input: problemForm.sample_input,
                  output: problemForm.sample_output,
                  is_public: true,
                },
              ]
            : [],
        }),
      });

      // Step 2: Attach practical directly to course
      await api(`courses/${courseId}/practicals`, {
        method: "POST",
        body: JSON.stringify({
          question_id: q.id,
          title: problemForm.title,
          effective_title: problemForm.title,
          is_required: true,
          passing_threshold: 100,
        }),
      });

      setNotice(`Practical challenge '${problemForm.title}' added to subject curriculum!`);
      setProblemForm({
        title: "",
        description: "",
        input_format: "",
        output_format: "",
        difficulty: "EASY",
        sample_input: "",
        sample_output: "",
      });
      await loadPracticalsForCourse(Number(courseId));
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : "Failed to create practical.");
    } finally {
      setBusy(false);
    }
  }

  // Practical Deletion Workflow (Part 14)
  async function openDeletionModal(p: Practical) {
    setDeletingPractical(p);
    setDeletionPreview(null);
    setDeletionLoading(true);
    try {
      const preview = await api<PracticalDeletionPreview>(`practicals/${p.id}/deletion-preview`);
      setDeletionPreview(preview);
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : "Failed to inspect practical impact.");
      setDeletingPractical(null);
    } finally {
      setDeletionLoading(false);
    }
  }

  async function confirmDeletePractical() {
    if (!deletingPractical) return;
    setBusy(true);
    try {
      const res = await api<{ detail: string; archived: boolean }>(
        `practicals/${deletingPractical.id}?archive_if_dependent=true`,
        { method: "DELETE" },
      );
      setNotice(res.detail || "Practical deleted successfully.");
      setDeletingPractical(null);
      setDeletionPreview(null);
      if (courseId) {
        await loadPracticalsForCourse(Number(courseId));
      }
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : "Failed to delete practical.");
    } finally {
      setBusy(false);
    }
  }

  // Subject Certificate Review (Part 11)
  async function reviewSubjectCertificate(requestId: number, action: "APPROVE" | "REJECT") {
    const note = (subjectReviewNotes[requestId] || "").trim();
    if (action === "REJECT" && !note) {
      setNotice("A reason must be provided in the review note when rejecting a certificate request.");
      return;
    }
    setBusy(true);
    try {
      await api(`certificates/subject-approvals/${requestId}`, {
        method: "POST",
        body: JSON.stringify({ action, note }),
      });
      setNotice(
        action === "APPROVE"
          ? "Subject completion certificate approved and cryptographically signed with Ed25519 key!"
          : "Subject certificate request rejected.",
      );
      await refresh();
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : "Review action failed.");
    } finally {
      setBusy(false);
    }
  }

  // Lab Certificate Review (Legacy / Lab level)
  async function reviewCertificate(requestId: number, action: "APPROVE" | "REJECT") {
    setBusy(true);
    try {
      await api(`certificates/approvals/${requestId}`, {
        method: "POST",
        body: JSON.stringify({
          action,
          note: reviewNotes[requestId] || "",
          review_note: reviewNotes[requestId] || "",
        }),
      });
      setNotice(
        action === "APPROVE"
          ? "Lab certificate approved and signed with Ed25519 key!"
          : "Certificate request rejected.",
      );
      await refresh();
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : "Review action failed.");
    } finally {
      setBusy(false);
    }
  }

  // Advanced: Create Lab Module
  async function createLab(e: FormEvent) {
    e.preventDefault();
    if (!courseId) {
      setNotice("Select a target course first.");
      return;
    }
    setBusy(true);
    try {
      await api(`courses/${courseId}/labs`, {
        method: "POST",
        body: JSON.stringify(labForm),
      });
      setNotice("Laboratory module created successfully!");
      setLabForm({ title: "", description: "", instructions: "", is_published: true });
      await refresh();
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : "Failed to create lab module.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleLab(lab: Lab) {
    setBusy(true);
    try {
      await api(`labs/${lab.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_published: !lab.is_published }),
      });
      setNotice(`Laboratory ${lab.is_published ? "unpublished" : "published"} successfully.`);
      await refresh();
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : "Failed to update lab visibility.");
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  if (loading) {
    return (
      <main
        className="flex min-h-screen items-center justify-center"
        style={{ backgroundColor: "var(--color-background)" }}
      >
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 animate-spin rounded-full border-3 border-[#FF6B2C] border-t-transparent" />
          <p className="text-sm font-semibold text-[#706C65] dark:text-[#A5A29C]">
            Loading faculty control center...
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
        <div className="lux-card max-w-lg p-8 text-center shadow-xl border border-[#E4DDD2] dark:border-[#2D2D2D] bg-[#FFFCF6] dark:bg-[#1C1C1C]">
          <h1 className="text-xl font-extrabold text-[#191919] dark:text-[#F7F4EF]">Unable to load faculty workspace</h1>
          <p className="mt-2 text-sm text-[#706C65] dark:text-[#A5A29C]">
            {error || "Session verification failed."}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="btn-primary mt-5 !py-2.5 !text-xs font-bold"
          >
            Reload Page
          </button>
        </div>
      </main>
    );
  }

  const nav: Section[] = [
    "Overview",
    "My Courses",
    "Subject Practicals",
    "Submissions",
    "Certificates",
    "Profile",
  ];

  const pendingSubjectApprovals = subjectApprovals.filter((s) => s.status === "PENDING");
  const pendingLabApprovals = approvals.filter((a) => a.status === "PENDING");
  const totalPendingCertificates = pendingSubjectApprovals.length + pendingLabApprovals.length;

  const currentCourse = courses.find((c) => c.id === courseId);

  return (
    <main className="min-h-screen bg-[#101010] text-[#F7F4EF]">
      {/* ────── Fixed Desktop Sidebar ────── */}
      <aside className="fixed inset-y-0 left-0 hidden w-64 flex-col border-r border-[#353535] bg-[#121212] lg:flex">
        <div className="border-b border-[#353535] p-5">
          <Link href="/faculty/dashboard" className="flex items-center gap-3 group">
            <CredLabLogo size="sm" showWordmark={true} />
            <span className="hidden sm:inline-block text-[11px] font-mono font-semibold uppercase tracking-wider text-[#A5A29C]">
              Faculty
            </span>
          </Link>
        </div>

        <nav className="flex-1 space-y-1.5 p-3" aria-label="Faculty Navigation">
          {nav.map((item) => {
            const isCert = item === "Certificates";
            return (
              <button
                key={item}
                onClick={() => setSection(item)}
                className={`w-full flex items-center justify-between rounded-xl px-4 py-2.5 text-left text-xs font-bold transition-all ${
                  section === item
                    ? "text-white shadow-xs"
                    : "text-[#A5A29C] hover:bg-[#202020] hover:text-[#FF6B2C]"
                }`}
                style={section === item ? { background: "var(--primary-gradient)" } : undefined}
              >
                <span>{item}</span>
                {isCert && totalPendingCertificates > 0 && (
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-extrabold ${
                      section === item ? "bg-white text-[#D94F16]" : "bg-[#FF6B2C] text-white"
                    }`}
                  >
                    {totalPendingCertificates}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        <div className="border-t border-[#353535] p-4 bg-[#161616]">
          <p className="truncate text-xs font-bold text-[#F7F4EF]">{user.name}</p>
          <p className="text-[11px] font-mono font-semibold text-[#A5A29C]">Authorized Instructor</p>
        </div>
      </aside>

      {/* ────── Main Content Area ────── */}
      <div className="lg:pl-64">
        {/* Top Sticky Header */}
        <header className="sticky top-0 z-20 flex items-center justify-between border-b border-[#353535] bg-[#121212]/90 px-5 py-3.5 backdrop-blur-md sm:px-8">
          <div>
            <h1 className="text-sm font-extrabold text-[#F7F4EF]">{section}</h1>
            <p className="text-[11px] font-mono font-semibold text-[#A5A29C]">
              Subject curriculum, practical management, automated evaluation & Ed25519 certificates
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => void refresh()}
              disabled={busy}
              className="btn-secondary !py-2 !px-3.5 !text-xs font-bold"
            >
              {busy ? "Refreshing..." : "↻ Refresh"}
            </button>
            <button
              onClick={() => void logout()}
              className="btn-secondary !py-2 !px-3.5 !text-xs font-bold text-rose-400 hover:bg-rose-950/20"
            >
              Log out
            </button>
          </div>
        </header>

        {/* Mobile Navigation Pill Bar */}
        <div className="flex gap-2 overflow-x-auto border-b border-[#353535] bg-[#121212] px-4 py-2.5 lg:hidden no-scrollbar">
          {nav.map((item) => (
            <button
              key={item}
              onClick={() => setSection(item)}
              className={`shrink-0 rounded-lg px-3 py-1.5 text-xs font-bold transition-all ${
                section === item
                  ? "bg-[#FF6B2C] text-white shadow-xs"
                  : "text-[#A5A29C] hover:bg-[#202020] hover:text-[#F7F4EF] bg-[#1B1B1B] border border-[#353535]"
              }`}
            >
              {item}
            </button>
          ))}
        </div>

        {/* Global Feedback Banner */}
        {notice && (
          <div className="mx-5 mt-4 sm:mx-8">
            <div className="flex items-center justify-between rounded-xl border border-[#FF6B2C]/30 bg-[#FF6B2C]/10 p-3 text-xs font-semibold text-[#FF6B2C] dark:text-[#FFB547]">
              <p>{notice}</p>
              <button
                onClick={() => setNotice("")}
                className="font-bold text-[#FF6B2C] dark:text-[#FFB547] hover:underline"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        <div className="p-5 sm:p-8">
          {/* ───────────────── OVERVIEW ───────────────── */}
          {section === "Overview" && (
            <div className="space-y-6 animate-fade-in">
              <section className="lux-card relative overflow-hidden p-6 sm:p-8 border border-[#353535] bg-gradient-to-br from-[#1B1B1B] via-[#1E1E1E] to-[#242424] shadow-lg">
                <DashboardAmbientGrid />
                <div className="relative z-10 max-w-2xl">
                  <span className="badge-primary px-3 py-1 text-xs font-bold rounded-full">
                    Faculty Workspace Active
                  </span>
                  <h2 className="mt-4 text-2xl font-extrabold tracking-tight text-[#F7F4EF] sm:text-3xl">
                    Welcome back, Prof. {user.name}
                  </h2>
                  <p className="mt-2 text-sm leading-relaxed text-[#A5A29C]">
                    Manage practical programming challenges directly for your assigned subjects,
                    monitor real-time student test executions, and approve cryptographically signed
                    subject diplomas.
                  </p>
                </div>
              </section>

              {/* Metric Counters */}
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {[
                  { label: "Assigned Subjects", val: courses.length, desc: "Curricula under direction" },
                  {
                    label: "Active Practicals",
                    val: courses.reduce((acc, c) => acc + (c.lab_count > 0 ? c.lab_count : 1), 0),
                    desc: "Curriculum challenges",
                  },
                  {
                    label: "Student Submissions",
                    val: submissions.length,
                    desc: "Evaluations recorded",
                  },
                  {
                    label: "Pending Certificates",
                    val: totalPendingCertificates,
                    desc: "Subject & lab diplomas",
                  },
                ].map((m) => (
                  <article key={m.label} className="lux-card p-5 border border-[#E4DDD2] dark:border-[#2D2D2D] hover:border-[#FF6B2C]/50 transition-all">
                    <p className="text-xs font-bold uppercase tracking-wider text-[#706C65] dark:text-[#A5A29C]">
                      {m.label}
                    </p>
                    <p className="mt-2 text-3xl font-extrabold text-[#191919] dark:text-[#F7F4EF]">{m.val}</p>
                    <p className="mt-1 text-xs text-[#D94F16] dark:text-[#FFB547] font-semibold">{m.desc}</p>
                  </article>
                ))}
              </div>

              {/* Action Cards */}
              <div className="grid gap-6 md:grid-cols-2">
                <article className="lux-card p-6 border border-[#E4DDD2] dark:border-[#2D2D2D]">
                  <h3 className="text-base font-bold text-[#191919] dark:text-[#F7F4EF]">Subject Practicals</h3>
                  <p className="mt-1 text-xs text-[#706C65] dark:text-[#A5A29C]">
                    Directly author coding challenges, configure test specifications, and assign them
                    to your active courses without laboratory layers.
                  </p>
                  <button
                    onClick={() => setSection("Subject Practicals")}
                    className="btn-primary mt-5 !py-2.5 !px-5 !text-xs font-bold"
                  >
                    Open Practicals Manager →
                  </button>
                </article>

                <article className="lux-card p-6 border border-[#E4DDD2] dark:border-[#2D2D2D]">
                  <h3 className="text-base font-bold text-[#191919] dark:text-[#F7F4EF]">
                    Certificate Approvals
                  </h3>
                  <p className="mt-1 text-xs text-[#706C65] dark:text-[#A5A29C]">
                    {totalPendingCertificates} certificate request(s) awaiting your cryptographic
                    approval ({pendingSubjectApprovals.length} subject, {pendingLabApprovals.length} lab).
                  </p>
                  <div className="mt-5 flex gap-3">
                    <button
                      onClick={() => {
                        setCertTab("SUBJECT");
                        setSection("Certificates");
                      }}
                      className="btn-primary !py-2.5 !px-5 !text-xs font-bold"
                    >
                      Review Approvals →
                    </button>
                    <button
                      onClick={() => setSection("My Courses")}
                      className="btn-secondary !py-2.5 !px-5 !text-xs font-bold"
                    >
                      View Courses
                    </button>
                  </div>
                </article>
              </div>
            </div>
          )}

          {/* ───────────────── MY COURSES ───────────────── */}
          {section === "My Courses" && (
            <section className="lux-card mt-6 p-6 animate-fade-in border border-[#E4DDD2] dark:border-[#2D2D2D]">
              <h2 className="text-lg font-bold text-[#191919] dark:text-[#F7F4EF]">Assigned Academic Courses</h2>
              <p className="mt-1 text-xs text-[#706C65] dark:text-[#A5A29C]">
                You have administrative authority to manage practicals and issue subject completion
                certificates for these assigned courses.
              </p>

              {courses.length > 0 ? (
                <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {courses.map((c) => (
                    <article key={c.id} className="lux-card p-5 transition-all card-hover border border-[#E4DDD2] dark:border-[#2D2D2D] bg-[#FFFCF6] dark:bg-[#1B1B1B]">
                      <span className="badge-primary px-2.5 py-0.5 text-[10px] font-bold rounded-md">
                        {c.program}
                      </span>
                      <h3 className="mt-3 text-base font-bold text-[#191919] dark:text-[#F7F4EF]">{c.name}</h3>
                      <p className="mt-1 text-xs text-[#706C65] dark:text-[#A5A29C]">Code: {c.code || "N/A"}</p>
                      <p className="mt-1 text-xs text-[#706C65] dark:text-[#A5A29C]">
                        Year {c.year_of_study} · Semester {c.semester}
                      </p>

                      <div className="mt-4 flex gap-4 text-xs font-bold text-[#D94F16] dark:text-[#FFB547]">
                        <span>{c.lab_count} Lab Modules</span>
                        <span>{c.student_count} Students</span>
                      </div>

                      <button
                        onClick={() => {
                          setCourseId(c.id);
                          void loadPracticalsForCourse(c.id);
                          setSection("Subject Practicals");
                        }}
                        className="btn-primary w-full mt-4 !py-2 !text-xs font-bold"
                      >
                        Manage Practicals →
                      </button>
                    </article>
                  ))}
                </div>
              ) : (
                <Empty
                  title="No Courses Assigned"
                  text="Contact an administrator to assign academic courses to your profile."
                />
              )}
            </section>
          )}

          {/* ───────────────── SUBJECT PRACTICALS (PARTS 5 & 14) ───────────────── */}
          {section === "Subject Practicals" && (
            <div className="space-y-6 animate-fade-in">
              {/* Subject Selector Bar */}
              <div className="lux-card p-5 border border-[#E4DDD2] dark:border-[#2D2D2D]">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <label className="text-xs font-extrabold uppercase tracking-wider text-[#191919] dark:text-[#F7F4EF]">
                      Selected Subject / Course
                    </label>
                    <p className="text-xs text-[#706C65] dark:text-[#A5A29C]">
                      Practicals are directly attached to this subject curriculum.
                    </p>
                  </div>
                  <div className="min-w-[280px]">
                    <select
                      value={courseId}
                      onChange={(e) => handleCourseChange(Number(e.target.value))}
                      className="input-field font-bold text-sm"
                    >
                      {courses.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name} ({c.code || c.program})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {currentCourse && (
                  <div className="mt-4 flex flex-wrap gap-2 pt-3 border-t border-[#E4DDD2] dark:border-[#2D2D2D] text-xs font-semibold text-[#706C65] dark:text-[#A5A29C]">
                    <span className="badge-primary px-2.5 py-0.5 rounded-md">
                      Program: {currentCourse.program}
                    </span>
                    <span className="badge-primary px-2.5 py-0.5 rounded-md">
                      Year {currentCourse.year_of_study} · Semester {currentCourse.semester}
                    </span>
                    <span className="badge-primary px-2.5 py-0.5 rounded-md">
                      {coursePracticals.length} Practical Challenges
                    </span>
                  </div>
                )}
              </div>

              {/* Main Split: Practicals List & Add Practical Form */}
              <div className="grid gap-6 xl:grid-cols-2">
                {/* Practicals for this subject */}
                <section className="lux-card p-6 border border-[#353535] bg-[#1B1B1B]">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-lg font-bold text-[#F7F4EF]">
                        Curriculum Practicals
                      </h2>
                      <p className="mt-1 text-xs text-[#A5A29C]">
                        Active coding challenges under {currentCourse?.name || "selected subject"}.
                      </p>
                    </div>
                    <span className="rounded-full bg-[#FF6B2C]/10 border border-[#FF6B2C]/30 px-3 py-1 text-xs font-extrabold text-[#FF8A3D]">
                      {coursePracticals.length} Total
                    </span>
                  </div>

                  {coursePracticalsLoading ? (
                    <div className="mt-8 flex justify-center py-10">
                      <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#FF6B2C] border-t-transparent" />
                    </div>
                  ) : coursePracticals.length > 0 ? (
                    <div className="mt-5 space-y-3 max-h-[600px] overflow-y-auto pr-1">
                      {coursePracticals.map((p) => (
                        <article
                          key={p.id}
                          className="rounded-2xl p-4 transition-all border border-[#353535] bg-[#1B1B1B] hover:border-[#FF6B2C]/60 hover:bg-[#242424] shadow-xs group"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <span className="font-extrabold text-xs text-[#FF8A3D] bg-[#FF6B2C]/10 px-2 py-0.5 rounded-md border border-[#FF6B2C]/20">
                                  #{p.sequence_number}
                                </span>
                                <h3 className="font-bold text-sm text-[#F7F4EF]">
                                  {p.effective_title}
                                </h3>
                              </div>
                              <div className="mt-2 flex flex-wrap gap-2 text-[11px] font-semibold">
                                <span className="rounded-md bg-rose-500/15 border border-rose-500/20 px-2 py-0.5 text-rose-300 font-bold">
                                  Score Threshold: {p.passing_threshold ?? 100}%
                                </span>
                                {p.is_required && (
                                  <span className="rounded-md bg-amber-500/15 border border-amber-500/20 px-2 py-0.5 text-amber-300 font-bold">
                                    ★ Required for Certificate & Badge
                                  </span>
                                )}
                              </div>
                            </div>

                            <button
                              onClick={() => void openDeletionModal(p)}
                              disabled={busy}
                              className="rounded-xl border border-rose-900/60 bg-rose-950/40 px-3 py-1.5 text-xs font-bold text-rose-300 transition hover:bg-rose-900/60 hover:border-rose-400"
                              title="Delete or archive practical"
                            >
                              Delete
                            </button>
                          </div>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <Empty
                      title="No Practicals Yet"
                      text="No practicals have been added to this subject. Use the form on the right to publish your first coding challenge."
                    />
                  )}
                </section>

                {/* Add Practical Form directly to Subject */}
                <section className="lux-card p-6 border border-[#353535] bg-[#1B1B1B]">
                  <h2 className="text-lg font-bold text-[#F7F4EF]">
                    Add Practical to {currentCourse?.name || "Subject"}
                  </h2>
                  <p className="mt-1 text-xs text-[#A5A29C]">
                    Define problem requirements, test specifications, and permitted execution languages.
                  </p>

                  <form onSubmit={createPractical} className="mt-5 space-y-4">
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="sm:col-span-2">
                        <label className="text-xs font-bold uppercase tracking-wider text-[#F7F4EF]">
                          Practical Title
                        </label>
                        <input
                          required
                          minLength={2}
                          value={problemForm.title}
                          onChange={(e) =>
                            setProblemForm((x) => ({ ...x, title: e.target.value }))
                          }
                          placeholder="e.g. Implement Binary Search Tree Insertion"
                          className="input-field mt-1.5"
                        />
                      </div>

                      <div className="sm:col-span-2">
                        <label className="text-xs font-bold uppercase tracking-wider text-[#F7F4EF]">
                          Problem Statement & Instructions
                        </label>
                        <textarea
                          required
                          minLength={5}
                          rows={4}
                          value={problemForm.description}
                          onChange={(e) =>
                            setProblemForm((x) => ({ ...x, description: e.target.value }))
                          }
                          placeholder="Explain problem requirements, algorithms to use, input format, output format, and edge cases..."
                          className="input-field mt-1.5"
                        />
                      </div>

                      <div>
                        <label className="text-xs font-bold uppercase tracking-wider text-[#F7F4EF]">
                          Input Format
                        </label>
                        <textarea
                          rows={2}
                          value={problemForm.input_format}
                          onChange={(e) =>
                            setProblemForm((x) => ({ ...x, input_format: e.target.value }))
                          }
                          placeholder="e.g. First line contains integer N..."
                          className="input-field mt-1.5"
                        />
                      </div>

                      <div>
                        <label className="text-xs font-bold uppercase tracking-wider text-[#F7F4EF]">
                          Output Format
                        </label>
                        <textarea
                          rows={2}
                          value={problemForm.output_format}
                          onChange={(e) =>
                            setProblemForm((x) => ({ ...x, output_format: e.target.value }))
                          }
                          placeholder="e.g. Print result on a single line..."
                          className="input-field mt-1.5"
                        />
                      </div>

                      <div className="sm:col-span-2">
                        <label className="text-xs font-bold uppercase tracking-wider text-[#F7F4EF]">
                          Difficulty Level
                        </label>
                        <select
                          value={problemForm.difficulty}
                          onChange={(e) =>
                            setProblemForm((x) => ({ ...x, difficulty: e.target.value }))
                          }
                          className="input-field mt-1.5"
                        >
                          <option value="EASY">Easy</option>
                          <option value="MEDIUM">Medium</option>
                          <option value="HARD">Hard</option>
                        </select>
                      </div>

                      <div className="sm:col-span-2">
                        <label className="text-xs font-bold uppercase tracking-wider text-[#F7F4EF]">
                          Permitted Languages
                        </label>
                        <div className="mt-2 flex flex-wrap gap-2.5">
                          {LANGS.map((l) => (
                            <label
                              key={l}
                              className={`flex items-center gap-2 rounded-xl px-3 py-1.5 text-xs font-bold cursor-pointer border transition-colors ${
                                languages.includes(l)
                                  ? "bg-[#FF6B2C]/10 border-[#FF6B2C] text-[#FF8A3D]"
                                  : "bg-[#161616] border-[#353535] text-[#A5A29C] hover:border-[#FF6B2C]/50"
                              }`}
                            >
                              <input
                                type="checkbox"
                                checked={languages.includes(l)}
                                onChange={(e) =>
                                  setLanguages((old) =>
                                    e.target.checked ? [...old, l] : old.filter((v) => v !== l),
                                  )
                                }
                                className="accent-[#FF6B2C]"
                              />
                              {l.toUpperCase()}
                            </label>
                          ))}
                        </div>
                      </div>

                      {/* Sample Test Case */}
                      <div className="sm:col-span-2 grid gap-4 sm:grid-cols-2 rounded-2xl p-4 bg-[#161616] border border-[#353535]">
                        <div>
                          <label className="text-xs font-bold uppercase tracking-wider text-[#F7F4EF]">
                            Sample Input
                          </label>
                          <textarea
                            value={problemForm.sample_input}
                            onChange={(e) =>
                              setProblemForm((x) => ({ ...x, sample_input: e.target.value }))
                            }
                            rows={3}
                            placeholder="5&#10;1 2 3 4 5"
                            className="input-field font-mono mt-1.5"
                          />
                        </div>
                        <div>
                          <label className="text-xs font-bold uppercase tracking-wider text-[#F7F4EF]">
                            Sample Expected Output
                          </label>
                          <textarea
                            value={problemForm.sample_output}
                            onChange={(e) =>
                              setProblemForm((x) => ({ ...x, sample_output: e.target.value }))
                            }
                            rows={3}
                            placeholder="15"
                            className="input-field font-mono mt-1.5"
                          />
                        </div>
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={busy || !courseId}
                      className="btn-primary w-full !py-3.5 !text-xs font-bold tracking-wide"
                    >
                      {busy ? "Adding practical..." : "Add Practical to Subject"}
                    </button>
                  </form>
                </section>
              </div>

              {/* Advanced Collapsible: Custom Lab Modules */}
              <div className="lux-card p-5 border border-[#E4DDD2] dark:border-[#2D2D2D]">
                <button
                  type="button"
                  onClick={() => setShowAdvancedLabs((x) => !x)}
                  className="flex w-full items-center justify-between text-left"
                >
                  <div>
                    <h3 className="text-sm font-bold text-[#191919] dark:text-[#F7F4EF]">
                      Advanced: Custom Laboratory Groupings
                    </h3>
                    <p className="text-xs text-[#706C65] dark:text-[#A5A29C]">
                      Optional multi-lab structures, custom lab names, and manual publication toggles.
                    </p>
                  </div>
                  <span className="text-xs font-extrabold text-[#D94F16] dark:text-[#FFB547]">
                    {showAdvancedLabs ? "▲ Hide" : "▼ Show"}
                  </span>
                </button>

                {showAdvancedLabs && (
                  <div className="mt-6 pt-5 border-t border-[#E4DDD2] dark:border-[#2D2D2D] grid gap-6 xl:grid-cols-2">
                    {/* Create Lab */}
                    <div>
                      <h4 className="text-sm font-bold text-[#191919] dark:text-[#F7F4EF]">Create Custom Lab Module</h4>
                      <form onSubmit={createLab} className="mt-3 space-y-3">
                        <input
                          required
                          value={labForm.title}
                          onChange={(e) => setLabForm((x) => ({ ...x, title: e.target.value }))}
                          placeholder="e.g. Lab Module 2: Graph Theory"
                          className="input-field"
                        />
                        <textarea
                          value={labForm.description}
                          onChange={(e) => setLabForm((x) => ({ ...x, description: e.target.value }))}
                          rows={2}
                          placeholder="Description..."
                          className="input-field"
                        />
                        <button
                          type="submit"
                          disabled={busy || !courseId}
                          className="btn-secondary !py-2 !px-4 !text-xs font-bold"
                        >
                          Create Module
                        </button>
                      </form>
                    </div>

                    {/* Existing Labs */}
                    <div>
                      <h4 className="text-sm font-bold text-[#191919] dark:text-[#F7F4EF]">
                        Existing Modules for Selected Course
                      </h4>
                      <div className="mt-3 space-y-2">
                        {labs
                          .filter((l) => l.course_id === Number(courseId))
                          .map((l) => (
                            <div
                              key={l.id}
                              className="flex items-center justify-between rounded-xl p-3 border border-[#E4DDD2] dark:border-[#2D2D2D] bg-[#FFFCF6] dark:bg-[#1B1B1B]"
                            >
                              <div>
                                <p className="text-xs font-bold text-[#191919] dark:text-[#F7F4EF]">{l.title}</p>
                                <p className="text-[11px] text-[#706C65] dark:text-[#A5A29C]">
                                  {l.practical_count} practical(s)
                                </p>
                              </div>
                              <div className="flex items-center gap-2">
                                <span
                                  className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                                    l.is_published ? "badge-success" : "badge-warning"
                                  }`}
                                >
                                  {l.is_published ? "LIVE" : "DRAFT"}
                                </span>
                                <button
                                  type="button"
                                  onClick={() => void toggleLab(l)}
                                  disabled={busy}
                                  className="btn-secondary !py-1 !px-2.5 !text-[11px] font-bold"
                                >
                                  {l.is_published ? "Unpublish" : "Publish"}
                                </button>
                              </div>
                            </div>
                          ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ───────────────── SUBMISSIONS ───────────────── */}
          {section === "Submissions" && (
            <section className="lux-card mt-6 p-6 animate-fade-in border border-[#E4DDD2] dark:border-[#2D2D2D]">
              <h2 className="text-lg font-bold text-[#191919] dark:text-[#F7F4EF]">Student Submissions</h2>
              <p className="mt-1 text-xs text-[#706C65] dark:text-[#A5A29C]">
                Real-time automated evaluation logs across your assigned courses.
              </p>

              {submissions.length > 0 ? (
                <div className="mt-5 overflow-x-auto">
                  <table className="lux-table">
                    <thead>
                      <tr>
                        <th>Student</th>
                        <th>Practical</th>
                        <th>Language</th>
                        <th>Evaluation</th>
                        <th>Submitted At</th>
                      </tr>
                    </thead>
                    <tbody>
                      {submissions.map((s) => (
                        <tr key={s.id}>
                          <td className="font-bold text-[#191919] dark:text-[#F7F4EF]">
                            {s.student_name}
                            <span className="block text-[10px] font-semibold text-[#706C65] dark:text-[#A5A29C]">
                              Student #{s.user_id}
                            </span>
                          </td>
                          <td className="text-xs text-[#191919] dark:text-[#F7F4EF]">{s.question_title}</td>
                          <td className="font-mono text-xs uppercase text-[#706C65] dark:text-[#A5A29C]">{s.language}</td>
                          <td>
                            <span
                              className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold ${
                                s.status === "ACCEPTED" || s.score === 100
                                  ? "badge-success"
                                  : "badge-danger"
                              }`}
                            >
                              {s.status} · {s.score}%
                            </span>
                          </td>
                          <td className="text-xs text-[#706C65] dark:text-[#A5A29C]">
                            {new Date(s.created_at).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <Empty
                  title="No Submissions Yet"
                  text="Student code executions will show up here once practicals are attempted."
                />
              )}
            </section>
          )}

          {/* ───────────────── CERTIFICATES (PART 11) ───────────────── */}
          {section === "Certificates" && (
            <section className="lux-card mt-6 p-6 animate-fade-in border border-[#E4DDD2] dark:border-[#2D2D2D]">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold text-[#191919] dark:text-[#F7F4EF]">
                    Certificate Approval Center
                  </h2>
                  <p className="mt-1 text-xs text-[#706C65] dark:text-[#A5A29C]">
                    Verify curriculum completion and issue cryptographically signed Ed25519 diplomas.
                  </p>
                </div>

                {/* Sub-tabs: Subject Certificates vs Lab Module Certificates */}
                <div className="flex rounded-xl bg-[#EEE8DE]/60 dark:bg-[#181818] p-1 border border-[#E4DDD2] dark:border-[#2D2D2D]">
                  <button
                    onClick={() => setCertTab("SUBJECT")}
                    className={`rounded-lg px-4 py-1.5 text-xs font-bold transition ${
                      certTab === "SUBJECT"
                        ? "bg-[#FF6B2C] text-white shadow-xs"
                        : "text-[#706C65] dark:text-[#A5A29C] hover:text-[#D94F16] dark:hover:text-[#FF6B2C]"
                    }`}
                  >
                    Subject Certificates ({pendingSubjectApprovals.length})
                  </button>
                  <button
                    onClick={() => setCertTab("LAB")}
                    className={`rounded-lg px-4 py-1.5 text-xs font-bold transition ${
                      certTab === "LAB"
                        ? "bg-[#FF6B2C] text-white shadow-xs"
                        : "text-[#706C65] dark:text-[#A5A29C] hover:text-[#D94F16] dark:hover:text-[#FF6B2C]"
                    }`}
                  >
                    Lab Module Certificates ({pendingLabApprovals.length})
                  </button>
                </div>
              </div>

              {/* SUBJECT CERTIFICATES (PART 11) */}
              {certTab === "SUBJECT" && (
                <div className="mt-6">
                  {subjectApprovals.length > 0 ? (
                    <div className="space-y-4">
                      {subjectApprovals.map((a) => (
                        <article
                          key={a.id}
                          className="lux-card p-5 bg-[#FFFCF6] dark:bg-[#1B1B1B] border border-[#E4DDD2] dark:border-[#2D2D2D]"
                        >
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="badge-primary px-2.5 py-0.5 text-[10px] font-bold rounded-md">
                                  {a.course_code || "SUBJECT"}
                                </span>
                                <h3 className="text-sm font-extrabold text-[#191919] dark:text-[#F7F4EF]">
                                  {a.course_name}
                                </h3>
                              </div>
                              <p className="mt-1.5 text-xs text-[#706C65] dark:text-[#A5A29C]">
                                Candidate:{" "}
                                <span className="text-[#191919] dark:text-[#F7F4EF] font-bold">{a.student_name}</span> (
                                {a.student_email}) · Enrollment:{" "}
                                <span className="font-mono text-[#191919] dark:text-[#F7F4EF]">
                                  {a.enrollment_number || `ID #${a.student_id}`}
                                </span>
                              </p>
                              <p className="mt-1 text-[11px] text-[#8C867E] dark:text-[#8E8982]">
                                Completed Practicals:{" "}
                                <span className="font-bold text-[#D94F16] dark:text-[#FF6B2C]">
                                  {a.total_required} / {a.total_required} (100% verified)
                                </span>{" "}
                                · Requested: {new Date(a.requested_at).toLocaleString()}
                              </p>
                            </div>

                            <span
                              className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold ${
                                a.status === "PENDING"
                                  ? "badge-warning"
                                  : a.status === "APPROVED"
                                  ? "badge-success"
                                  : "badge-danger"
                              }`}
                            >
                              {a.status}
                            </span>
                          </div>

                          {a.status === "PENDING" && (
                            <div className="mt-4 pt-3 border-t border-[#E4DDD2] dark:border-[#2D2D2D]">
                              <input
                                value={subjectReviewNotes[a.id] || ""}
                                onChange={(e) =>
                                  setSubjectReviewNotes((x) => ({ ...x, [a.id]: e.target.value }))
                                }
                                placeholder="Faculty review note (required if rejecting)..."
                                className="input-field text-xs mb-3"
                              />
                              <div className="flex gap-2">
                                <button
                                  disabled={busy}
                                  onClick={() => void reviewSubjectCertificate(a.id, "APPROVE")}
                                  className="btn-primary !py-2 !px-4 !text-xs font-bold"
                                >
                                  Approve & Issue Subject Certificate (Ed25519)
                                </button>
                                <button
                                  disabled={busy}
                                  onClick={() => void reviewSubjectCertificate(a.id, "REJECT")}
                                  className="btn-secondary !py-2 !px-4 !text-xs font-bold text-rose-700 dark:text-rose-400"
                                >
                                  Reject Request
                                </button>
                              </div>
                            </div>
                          )}

                          {a.status !== "PENDING" && a.review_note && (
                            <div className="mt-3 pt-2 border-t border-[#E4DDD2] dark:border-[#2D2D2D] text-xs text-[#706C65] dark:text-[#A5A29C]">
                              <span className="font-bold text-[#191919] dark:text-[#F7F4EF]">Review Note:</span>{" "}
                              {a.review_note}
                            </div>
                          )}
                        </article>
                      ))}
                    </div>
                  ) : (
                    <Empty
                      title="No Subject Certificate Requests"
                      text="When students complete 100% of the required practicals for an assigned subject and request verification, their diploma requests appear here."
                    />
                  )}
                </div>
              )}

              {/* LAB MODULE CERTIFICATES (LEGACY) */}
              {certTab === "LAB" && (
                <div className="mt-6">
                  {approvals.length > 0 ? (
                    <div className="space-y-4">
                      {approvals.map((a) => (
                        <article
                          key={a.id}
                          className="lux-card p-5 bg-[#FFFCF6] dark:bg-[#1B1B1B] border border-[#E4DDD2] dark:border-[#2D2D2D]"
                        >
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <h3 className="text-sm font-extrabold text-[#191919] dark:text-[#F7F4EF]">
                                {a.lab_title}
                              </h3>
                              <p className="mt-1 text-xs text-[#706C65] dark:text-[#A5A29C]">
                                Candidate:{" "}
                                <span className="text-[#191919] dark:text-[#F7F4EF] font-bold">{a.student_name}</span> (
                                {a.student_email})
                              </p>
                              <p className="mt-1 text-[11px] text-[#8C867E] dark:text-[#8E8982]">
                                Submission #{a.submission_id} · Requested{" "}
                                {new Date(a.requested_at).toLocaleString()}
                              </p>
                            </div>

                            <span
                              className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold ${
                                a.status === "PENDING"
                                  ? "badge-warning"
                                  : a.status === "APPROVED"
                                  ? "badge-success"
                                  : "badge-danger"
                              }`}
                            >
                              {a.status}
                            </span>
                          </div>

                          {a.status === "PENDING" && (
                            <div className="mt-4 pt-3 border-t border-[#E4DDD2] dark:border-[#2D2D2D]">
                              <input
                                value={reviewNotes[a.id] || ""}
                                onChange={(e) =>
                                  setReviewNotes((x) => ({ ...x, [a.id]: e.target.value }))
                                }
                                placeholder="Optional evaluation note..."
                                className="input-field text-xs mb-3"
                              />
                              <div className="flex gap-2">
                                <button
                                  disabled={busy}
                                  onClick={() => void reviewCertificate(a.id, "APPROVE")}
                                  className="btn-primary !py-2 !px-4 !text-xs font-bold"
                                >
                                  Approve & Sign Certificate (Ed25519)
                                </button>
                                <button
                                  disabled={busy}
                                  onClick={() => void reviewCertificate(a.id, "REJECT")}
                                  className="btn-secondary !py-2 !px-4 !text-xs font-bold text-rose-700 dark:text-rose-400"
                                >
                                  Reject
                                </button>
                              </div>
                            </div>
                          )}
                        </article>
                      ))}
                    </div>
                  ) : (
                    <Empty
                      title="No Pending Requests"
                      text="When students complete all required practicals in a lab module, certificate approval requests appear here."
                    />
                  )}
                </div>
              )}
            </section>
          )}

          {/* ───────────────── PROFILE ───────────────── */}
          {section === "Profile" && (
            <section className="lux-card mt-6 p-6 animate-fade-in border border-[#E4DDD2] dark:border-[#2D2D2D]">
              <h2 className="text-lg font-bold text-[#191919] dark:text-[#F7F4EF]">Faculty Information</h2>
              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                {[
                  { label: "Full Name", value: user.name },
                  { label: "Institutional Email", value: user.email },
                  { label: "Employee Number", value: user.enrollment_number },
                  { label: "Account Status", value: user.is_active ? "Active" : "Suspended" },
                ].map((x) => (
                  <div key={x.label} className="p-4 rounded-xl bg-[#EEE8DE]/40 dark:bg-[#161616] border border-[#E4DDD2] dark:border-[#2D2D2D]">
                    <p className="text-[11px] font-bold uppercase tracking-wider text-[#706C65] dark:text-[#A5A29C]">
                      {x.label}
                    </p>
                    <p className="mt-1 text-sm font-bold text-[#191919] dark:text-[#F7F4EF]">{x.value || "Not set"}</p>
                  </div>
                ))}
              </div>
            </section>
          )}

          <footer className="mt-12 text-center text-xs py-4 text-[#706C65] dark:text-[#A5A29C] font-mono">
            CredLab · Faculty Management System · 2026
          </footer>
        </div>
      </div>

      {/* ───────────────── PRACTICAL DELETION MODAL (PART 14) ───────────────── */}
      {deletingPractical && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-lg p-6 bg-[#FFFCF6] dark:bg-[#1C1C1C] rounded-2xl shadow-2xl border border-[#E4DDD2] dark:border-[#353535] animate-scale-in text-[#191919] dark:text-[#F7F4EF]">
            <div className="flex items-start justify-between gap-3">
              <div>
                <span className="badge-danger px-2.5 py-0.5 text-[10px] font-extrabold rounded-md">
                  Deletion Impact Assessment
                </span>
                <h3 className="mt-2 text-base font-extrabold text-[#191919] dark:text-[#F7F4EF]">
                  Delete Practical #{deletingPractical.sequence_number}
                </h3>
                <p className="mt-1 text-xs text-[#706C65] dark:text-[#A5A29C] font-semibold">
                  {deletingPractical.effective_title}
                </p>
              </div>
              <button
                onClick={() => {
                  setDeletingPractical(null);
                  setDeletionPreview(null);
                }}
                className="text-[#706C65] dark:text-[#A5A29C] hover:text-[#191919] dark:hover:text-[#F7F4EF] font-bold text-sm"
              >
                ✕
              </button>
            </div>

            {deletionLoading ? (
              <div className="py-8 text-center">
                <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-[#FF6B2C] border-t-transparent" />
                <p className="mt-3 text-xs text-[#706C65] dark:text-[#A5A29C]">Analyzing candidate dependencies...</p>
              </div>
            ) : deletionPreview ? (
              <div className="mt-4 space-y-4">
                <div className="rounded-xl p-3 bg-[#EEE8DE]/40 dark:bg-[#161616] border border-[#E4DDD2] dark:border-[#2D2D2D] text-xs space-y-1">
                  <p>
                    <span className="font-bold text-[#191919] dark:text-[#F7F4EF]">Subject:</span>{" "}
                    {deletionPreview.subject_name}
                  </p>
                  <p>
                    <span className="font-bold text-[#191919] dark:text-[#F7F4EF]">Recorded Submissions:</span>{" "}
                    <span className="font-bold text-[#D94F16] dark:text-[#FF6B2C]">
                      {deletionPreview.historical_submissions_count}
                    </span>
                  </p>
                  <p>
                    <span className="font-bold text-[#191919] dark:text-[#F7F4EF]">Action Policy:</span>{" "}
                    <span
                      className={`font-extrabold ${
                        deletionPreview.has_historical_activity
                          ? "text-amber-700 dark:text-amber-400"
                          : "text-emerald-700 dark:text-emerald-400"
                      }`}
                    >
                      {deletionPreview.has_historical_activity
                        ? "Safe Archival (Preserves Student Submissions & Badges)"
                        : "Permanent Removal"}
                    </span>
                  </p>
                </div>

                <div
                  className={`rounded-xl p-3.5 text-xs font-semibold leading-relaxed border ${
                    deletionPreview.has_historical_activity
                      ? "bg-amber-500/10 border-amber-500/20 text-amber-800 dark:text-amber-300"
                      : "bg-emerald-500/10 border-emerald-500/20 text-emerald-800 dark:text-emerald-300"
                  }`}
                >
                  {deletionPreview.warning_message}
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setDeletingPractical(null);
                      setDeletionPreview(null);
                    }}
                    className="btn-secondary !py-2 !px-4 !text-xs font-bold"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void confirmDeletePractical()}
                    className="rounded-xl bg-[#DC2626] hover:bg-[#B91C1C] px-4 py-2 text-xs font-bold text-white shadow-xs transition disabled:opacity-50"
                  >
                    {busy
                      ? "Processing..."
                      : deletionPreview.has_historical_activity
                      ? "Confirm Safe Archival"
                      : "Confirm Deletion"}
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </main>
  );
}

function Empty({ title, text }: { title: string; text: string }) {
  return (
    <div className="mt-6 rounded-2xl p-8 text-center border border-dashed border-[#E4DDD2] dark:border-[#2D2D2D] bg-[#EEE8DE]/20 dark:bg-[#161616]/50">
      <h3 className="text-sm font-bold text-[#191919] dark:text-[#F7F4EF]">{title}</h3>
      <p className="mt-1.5 text-xs max-w-md mx-auto text-[#706C65] dark:text-[#A5A29C]">{text}</p>
    </div>
  );
}
