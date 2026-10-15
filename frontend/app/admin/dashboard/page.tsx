"use client";
/* eslint react-hooks/set-state-in-effect: off */

import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { useRouter } from "next/navigation";
import type { UserResponse, UserRole } from "@/types/auth";
import { PROGRAM_OPTIONS, SEMESTER_OPTIONS, YEAR_OF_STUDY_OPTIONS } from "@/lib/academic-options";
import { CredLabLogo } from "@/components/CredLabLogo";
import { DashboardAmbientGrid } from "@/components/3d/DashboardAmbientGrid";

type RegistrationApproval = {
  id: number;
  applicant_id: number;
  applicant_name: string;
  applicant_email: string;
  applicant_enrollment_number: string;
  account_type: "FACULTY" | "ADMIN";
  admin_job_role?: string | null;
  decision: "PENDING" | "APPROVED" | "REJECTED";
  reviewer_id?: number | null;
  reviewer_name?: string | null;
  rejection_reason?: string | null;
  requested_at: string;
  reviewed_at?: string | null;
};

type CourseDeletionPreview = {
  course_id: number;
  course_name: string;
  course_code: string;
  lab_count: number;
  practical_count: number;
  enrolled_student_count: number;
  historical_submissions_count: number;
  has_historical_activity: boolean;
  recommended_action: string;
  warning_message: string;
};

type AdminSection =
  | "Overview"
  | "User Management"
  | "Registration Approvals"
  | "Faculty Management"
  | "Course Management"
  | "Assessment Management"
  | "Submissions"
  | "Results & Analytics"
  | "Authorization"
  | "Settings";

type Course = {
  id: number;
  code: string | null;
  name: string;
  program: string;
  year_of_study: string;
  description: string | null;
  semester: string;
  academic_year: string | null;
  is_active: boolean;
  created_by: number;
  created_at: string;
  updated_at: string;
  lab_count: number;
  student_count: number;
  faculty_count: number;
  faculty_names: string[];
};

type Question = {
  id: number;
  title: string;
  slug: string;
  description: string;
  difficulty: "EASY" | "MEDIUM" | "HARD";
  status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
  allowed_languages: string[];
  example_count: number;
  created_at: string;
};

type Submission = {
  id: number;
  user_id: number;
  question_id: number;
  practical_id: number | null;
  language: string;
  status: string;
  total_test_cases: number;
  passed_test_cases: number;
  score: number;
  execution_time_ms: number | null;
  memory_kb: number | null;
  created_at: string;
};

type SubmissionPage = {
  items: Submission[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

type EnrollmentAuthorization = {
  id: number;
  enrollment_number: string;
  expected_role: UserRole;
  admin_job_role: string | null;
  is_active: boolean;
  course_id: number | null;
  claimed_by_user_id: number | null;
  created_at: string;
};


type AcademicProfileForm = {
  academic_course: string;
  year_of_study: string;
  semester: string;
  academic_year: string;
};

const sections: { name: AdminSection; description: string; icon: string }[] = [
  { name: "Overview", description: "Platform metrics summary", icon: "▦" },
  { name: "User Management", description: "Registered student and faculty accounts", icon: "♙" },
  { name: "Registration Approvals", description: "Faculty and administrator account approval queue", icon: "✓" },
  { name: "Faculty Management", description: "Instructor roster & assignments", icon: "♟" },
  { name: "Course Management", description: "University courses and syllabi", icon: "▤" },
  { name: "Assessment Management", description: "Authoritative question bank", icon: "⌘" },
  { name: "Submissions", description: "Live evaluation audit log", icon: "⇧" },
  { name: "Results & Analytics", description: "Platform-wide grading trends", icon: "▥" },
  { name: "Authorization", description: "Registration access codes", icon: "◇" },
  { name: "Settings", description: "Admin identity & credentials", icon: "⚙" },
];

async function adminApi<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/admin/${path.replace(/^\/+/, "")}`, {
    ...init,
    cache: "no-store",
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (Array.isArray(body.detail)) {
        message = body.detail.map((err: { msg?: string }) => err.msg || JSON.stringify(err)).join(", ");
      } else if (typeof body.message === "string") {
        message = body.message;
      }
    } catch {
      /* keep generic error */
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function dateLabel(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function initials(name: string) {
  return (
    name
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("") || "AD"
  );
}

function cx(...values: Array<string | false | undefined>) {
  return values.filter(Boolean).join(" ");
}

function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "good" | "warn" | "bad" | "blue";
}) {
  const tones = {
    neutral: "badge-primary",
    good: "badge-success",
    warn: "badge-warning",
    bad: "badge-danger",
    blue: "badge-info",
  };
  return (
    <span className={`inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-bold ${tones[tone]}`}>
      {children}
    </span>
  );
}

function Button({
  children,
  onClick,
  type = "button",
  disabled = false,
  variant = "primary",
}: {
  children: ReactNode;
  onClick?: () => void;
  type?: "button" | "submit";
  disabled?: boolean;
  variant?: "primary" | "secondary" | "danger";
}) {
  const styles = {
    primary: "btn-primary !text-xs font-bold",
    secondary: "btn-secondary !text-xs font-bold",
    danger: "badge-danger font-bold rounded-xl px-4 py-2 text-xs",
  };
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex min-h-9 items-center justify-center transition disabled:cursor-not-allowed disabled:opacity-50 ${styles[variant]}`}
    >
      {children}
    </button>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  required = false,
  type = "text",
  pattern,
  title,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  type?: string;
  pattern?: string;
  title?: string;
}) {
  return (
    <label className="block text-xs font-bold uppercase tracking-wider text-[#191919] dark:text-[#F7F4EF]">
      <span className="mb-1.5 block">{label}</span>
      <input
        type={type}
        value={value}
        required={required}
        pattern={pattern}
        title={title}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="input-field text-xs"
      />
    </label>
  );
}

function SelectField({
  label,
  value,
  onChange,
  options,
  required = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { label: string; value: string }[];
  required?: boolean;
}) {
  return (
    <label className="block text-xs font-bold uppercase tracking-wider text-[#191919] dark:text-[#F7F4EF]">
      <span className="mb-1.5 block">{label}</span>
      <select
        required={required}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="input-field text-xs"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value} className="bg-white dark:bg-[#1B1B1B] text-[#191919] dark:text-[#F7F4EF]">
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function StatCard({
  label,
  value,
  detail,
  icon,
}: {
  label: string;
  value: string | number;
  detail: string;
  icon: string;
}) {
  return (
    <article className="lux-card p-5 card-hover bg-[#FFFCF6] dark:bg-[#1B1B1B] border border-[#E4DDD2] dark:border-[#2D2D2D]">
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-bold uppercase tracking-wider text-[#706C65] dark:text-[#A5A29C]">{label}</p>
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#FF6B2C]/10 text-[#FF6B2C] dark:text-[#FFB547] border border-[#FF6B2C]/20 text-lg font-bold">
          {icon}
        </span>
      </div>
      <p className="mt-4 text-3xl font-extrabold tracking-tight text-[#191919] dark:text-[#F7F4EF]">{value}</p>
      <p className="mt-1 text-xs text-[#706C65] dark:text-[#A5A29C]">{detail}</p>
    </article>
  );
}

function SectionHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-[#FF6B2C] dark:text-[#FFB547]">
          {eyebrow}
        </p>
        <h2 className="mt-1 text-2xl font-extrabold tracking-tight text-[#191919] dark:text-[#F7F4EF]">{title}</h2>
        <p className="mt-1 max-w-2xl text-xs leading-5 text-[#706C65] dark:text-[#A5A29C]">{description}</p>
      </div>
      {action}
    </div>
  );
}

function Notice({
  kind = "error",
  children,
}: {
  kind?: "error" | "success" | "info";
  children: ReactNode;
}) {
  const style =
    kind === "error"
      ? "badge-danger"
      : kind === "success"
      ? "badge-success"
      : "badge-primary";
  return (
    <div
      role={kind === "error" ? "alert" : "status"}
      className={`mb-5 rounded-xl border p-4 text-xs font-semibold animate-fade-in ${style}`}
    >
      {children}
    </div>
  );
}

function LoadingBlock() {
  return (
    <div className="space-y-3" aria-label="Loading data">
      <div className="h-12 animate-pulse rounded-xl bg-[#FF6B2C]/10 dark:bg-[#252525]" />
      <div className="h-12 animate-pulse rounded-xl bg-[#FF6B2C]/10 dark:bg-[#252525]" />
      <div className="h-12 animate-pulse rounded-xl bg-[#FF6B2C]/10 dark:bg-[#252525]" />
    </div>
  );
}

function EmptyBlock({ title, description }: { title: string; description: string }) {
  return (
    <div
      className="rounded-2xl p-12 text-center bg-[#FFFCF6] dark:bg-[#1B1B1B] border border-dashed border-[#E4DDD2] dark:border-[#2D2D2D]"
    >
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-[#FFFFFF] dark:bg-[#252525] border border-[#E4DDD2] dark:border-[#2D2D2D] text-xl text-[#FF6B2C] dark:text-[#FFB547] font-bold">
        ∅
      </div>
      <h3 className="mt-4 font-bold text-[#191919] dark:text-[#F7F4EF] text-sm">{title}</h3>
      <p className="mx-auto mt-1.5 max-w-md text-xs leading-5 text-[#706C65] dark:text-[#A5A29C]">{description}</p>
    </div>
  );
}

export default function AdminDashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserResponse | null>(null);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [loggingOut, setLoggingOut] = useState(false);
  const [activeSection, setActiveSection] = useState<AdminSection>("Overview");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadingData, setLoadingData] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [users, setUsers] = useState<UserResponse[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [submissionPage, setSubmissionPage] = useState<SubmissionPage | null>(null);
  const [authorizations, setAuthorizations] = useState<EnrollmentAuthorization[]>([]);
  const [approvals, setApprovals] = useState<RegistrationApproval[]>([]);
  const [approvalFilter, setApprovalFilter] = useState<"ALL" | "PENDING" | "APPROVED" | "REJECTED">("PENDING");
  const [rejectingApproval, setRejectingApproval] = useState<RegistrationApproval | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [deletingCourse, setDeletingCourse] = useState<Course | null>(null);
  const [deletionPreview, setDeletionPreview] = useState<CourseDeletionPreview | null>(null);
  const [deletingCourseBusy, setDeletingCourseBusy] = useState(false);
  const [authorizationFormOpen, setAuthorizationFormOpen] = useState(false);
  const [authorizationForm, setAuthorizationForm] = useState({
    enrollment_number: "",
    expected_role: "STUDENT" as UserRole,
    admin_job_role: "UNIVERSITY_ADMIN",
  });
  const [overview, setOverview] = useState<{
    users: UserResponse[] | null;
    courses: Course[] | null;
    questions: Question[] | null;
    submissions: SubmissionPage | null;
  }>({ users: null, courses: null, questions: null, submissions: null });
  const [courseFormOpen, setCourseFormOpen] = useState(false);
  const [courseForm, setCourseForm] = useState<{
    program: string;
    year_of_study: string;
    semester: string;
    name: string;
    code: string;
    academic_year: string;
    description: string;
    faculty_id: string;
  }>({
    program: PROGRAM_OPTIONS[2],
    year_of_study: YEAR_OF_STUDY_OPTIONS[0],
    semester: SEMESTER_OPTIONS[0],
    name: "",
    code: "",
    academic_year: "2026-2027",
    description: "",
    faculty_id: "",
  });
  const [editingStudent, setEditingStudent] = useState<UserResponse | null>(null);
  const [academicProfileError, setAcademicProfileError] = useState("");
  const [academicProfileForm, setAcademicProfileForm] = useState<AcademicProfileForm>({
    academic_course: "",
    year_of_study: "",
    semester: "",
    academic_year: "",
  });
  const [questionFormOpen, setQuestionFormOpen] = useState(false);
  const [questionForm, setQuestionForm] = useState({
    title: "",
    description: "",
    difficulty: "EASY",
    status: "DRAFT",
  });

  useEffect(() => {
    let cancelled = false;
    async function loadSession() {
      try {
        const response = await fetch("/api/auth/session", { cache: "no-store" });
        if (response.status === 401) {
          router.replace("/login");
          return;
        }
        if (!response.ok) throw new Error("Unable to load your account.");
        const data = (await response.json()) as { user: UserResponse };
        if (data.user.role !== "ADMIN") {
          router.replace(
            data.user.role === "STUDENT" ? "/student/dashboard" : "/faculty/dashboard",
          );
          return;
        }
        if (!cancelled) setUser(data.user);
      } catch {
        if (!cancelled)
          setError(
            "We couldn't connect to the authentication server. Check that the backend is running.",
          );
      } finally {
        if (!cancelled) setSessionLoading(false);
      }
    }
    void loadSession();
    return () => {
      cancelled = true;
    };
  }, [router]);

  const loadOverview = useCallback(async () => {
    setLoadingData(true);
    setError("");
    setOverview({ users: null, courses: null, questions: null, submissions: null });
    const results = await Promise.allSettled([
      adminApi<UserResponse[]>("users"),
      adminApi<Course[]>("courses"),
      adminApi<Question[]>("questions"),
      adminApi<SubmissionPage>("submissions/admin/list?page=1&page_size=1"),
    ]);
    setOverview({
      users: results[0].status === "fulfilled" ? results[0].value : null,
      courses: results[1].status === "fulfilled" ? results[1].value : null,
      questions: results[2].status === "fulfilled" ? results[2].value : null,
      submissions: results[3].status === "fulfilled" ? results[3].value : null,
    });
    const failed = results.filter((item) => item.status === "rejected");
    if (failed.length === results.length)
      setError(
        "The dashboard data could not be loaded. Check the backend connection and your administrator permissions.",
      );
    setLoadingData(false);
  }, []);

  const loadSection = useCallback(
    async (section: AdminSection) => {
      setLoadingData(true);
      setError("");
      setNotice("");
      if (section === "User Management" || section === "Faculty Management") setUsers([]);
      if (section === "Course Management") setCourses([]);
      if (section === "Assessment Management") setQuestions([]);
      if (section === "Submissions" || section === "Results & Analytics") setSubmissionPage(null);
      if (section === "Authorization") setAuthorizations([]);
      try {
        if (section === "User Management" || section === "Faculty Management") {
          const role = section === "Faculty Management" ? "?role=FACULTY" : "";
          setUsers(await adminApi<UserResponse[]>(`users${role}`));
        } else if (section === "Course Management") {
          const [courseRows, facultyRows] = await Promise.all([
            adminApi<Course[]>("courses"),
            adminApi<UserResponse[]>("users?role=FACULTY"),
          ]);
          setCourses(courseRows);
          setUsers(facultyRows.filter((item) => item.role === "FACULTY" && item.is_active));
        } else if (section === "Assessment Management") {
          setQuestions(await adminApi<Question[]>("questions"));
        } else if (section === "Submissions" || section === "Results & Analytics") {
          setSubmissionPage(
            await adminApi<SubmissionPage>("submissions/admin/list?page=1&page_size=100"),
          );
          if (section === "Results & Analytics") {
            const [u, c, q] = await Promise.all([
              adminApi<UserResponse[]>("users"),
              adminApi<Course[]>("courses"),
              adminApi<Question[]>("questions"),
            ]);
            setUsers(u);
            setCourses(c);
            setQuestions(q);
          }
        } else if (section === "Registration Approvals") {
  setApprovals(await adminApi<RegistrationApproval[]>("approvals"));
} else if (section === "Authorization") {
          setAuthorizations(await adminApi<EnrollmentAuthorization[]>("authorized-enrollments"));
        } else if (section === "Overview") {
          await loadOverview();
        }
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "Unable to load data.");
      } finally {
        setLoadingData(false);
      }
    },
    [loadOverview],
  );

  useEffect(() => {
    if (!sessionLoading && user && activeSection !== "Settings") void loadSection(activeSection);
  }, [activeSection, sessionLoading, user, loadSection]);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } finally {
      router.replace("/login");
      router.refresh();
    }
  }

  async function refresh() {
    await loadSection(activeSection);
  }

  function navigate(section: AdminSection) {
    setActiveSection(section);
    setSearch("");
    setError("");
    setNotice("");
    setMobileNavOpen(false);
  }

  async function approveRegistration(id: number) {
    setBusy(true);
    setError("");
    try {
      await adminApi(`approvals/${id}/approve`, { method: "POST" });
      setNotice("Account registration approved successfully.");
      setApprovals(await adminApi<RegistrationApproval[]>("approvals"));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to approve registration.");
    } finally {
      setBusy(false);
    }
  }

  async function rejectRegistration(e: FormEvent) {
    e.preventDefault();
    if (!rejectingApproval || !rejectionReason.trim()) return;
    setBusy(true);
    setError("");
    try {
      await adminApi(`approvals/${rejectingApproval.id}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason: rejectionReason.trim() }),
      });
      setNotice("Registration rejected.");
      setRejectingApproval(null);
      setRejectionReason("");
      setApprovals(await adminApi<RegistrationApproval[]>("approvals"));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to reject registration.");
    } finally {
      setBusy(false);
    }
  }

  async function openSubjectDeleteModal(course: Course) {
    setDeletingCourse(course);
    setDeletionPreview(null);
    setDeletingCourseBusy(true);
    try {
      const preview = await adminApi<CourseDeletionPreview>(`courses/${course.id}/deletion-preview`);
      setDeletionPreview(preview);
    } catch {
      // fallback
    } finally {
      setDeletingCourseBusy(false);
    }
  }

  async function confirmDeleteSubject() {
    if (!deletingCourse) return;
    setBusy(true);
    setError("");
    try {
      const res = await adminApi<{ detail: string }>(`courses/${deletingCourse.id}?archive_if_dependent=true`, { method: "DELETE" });
      setNotice(res.detail || "Subject deleted successfully.");
      setDeletingCourse(null);
      setDeletionPreview(null);
      setCourses(await adminApi<Course[]>("courses"));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete subject.");
    } finally {
      setBusy(false);
    }
  }

  async function updateUserRole(target: UserResponse, nextRole: UserRole) {
    if (target.role === nextRole) return;
    const ok = window.confirm(
      `Change ${target.name}'s role from ${target.role} to ${nextRole}? This may change which parts of the platform they can access.`,
    );
    if (!ok) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await adminApi<UserResponse>(`users/${target.id}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role: nextRole }),
      });
      setUsers((current) =>
        current.map((item) => (item.id === target.id ? { ...item, role: nextRole } : item)),
      );
      setNotice(`Role updated for ${target.name}.`);
      if (target.id === user?.id && nextRole !== "ADMIN") router.replace("/login");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Role update failed.");
    } finally {
      setBusy(false);
    }
  }

  function editAcademicProfile(student: UserResponse) {
    setEditingStudent(student);
    setAcademicProfileError("");
    setAcademicProfileForm({
      academic_course: student.academic_course ?? "",
      year_of_study: student.year_of_study ?? "",
      semester: student.semester ?? "",
      academic_year: student.academic_year ?? "",
    });
    setError("");
    setNotice("");
  }

  async function saveAcademicProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingStudent) return;
    setBusy(true);
    setError("");
    setNotice("");
    setAcademicProfileError("");
    try {
      const updated = await adminApi<UserResponse>(`users/${editingStudent.id}/academic-profile`, {
        method: "PATCH",
        body: JSON.stringify({
          academic_course: academicProfileForm.academic_course,
          year_of_study: academicProfileForm.year_of_study,
          semester: academicProfileForm.semester,
          academic_year: academicProfileForm.academic_year.trim(),
        }),
      });
      setUsers((current) =>
        current.map((item) =>
          item.id === updated.id
            ? { ...item, ...updated, enrolled_courses: item.enrolled_courses }
            : item,
        ),
      );
      setEditingStudent(null);
      setNotice(`Academic profile updated for ${updated.name}; matching active subjects were enrolled.`);
    } catch (cause) {
      setAcademicProfileError(cause instanceof Error ? cause.message : "Academic profile update failed.");
    } finally {
      setBusy(false);
    }
  }

  async function createCourse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      if (!courseForm.faculty_id)
        throw new Error("Select a faculty member before creating the subject.");
      await adminApi<Course>("courses", {
        method: "POST",
        body: JSON.stringify({
          program: courseForm.program,
          year_of_study: courseForm.year_of_study,
          semester: courseForm.semester,
          name: courseForm.name.trim(),
          code: courseForm.code.trim() ? courseForm.code.trim().toUpperCase() : null,
          academic_year: courseForm.academic_year.trim(),
          description: courseForm.description.trim() || null,
          faculty_id: Number(courseForm.faculty_id),
          is_active: true,
        }),
      });
      setCourseForm({
        program: PROGRAM_OPTIONS[2],
        year_of_study: YEAR_OF_STUDY_OPTIONS[0],
        semester: SEMESTER_OPTIONS[0],
        name: "",
        code: "",
        academic_year: "2026-2027",
        description: "",
        faculty_id: "",
      });
      setCourseFormOpen(false);
      setNotice("Subject created and faculty assigned successfully.");
      await loadSection("Course Management");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Course creation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function createAuthorization(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const payload = {
        enrollment_number: authorizationForm.enrollment_number.trim().toUpperCase(),
        expected_role: authorizationForm.expected_role,
        admin_job_role:
          authorizationForm.expected_role === "ADMIN" ? authorizationForm.admin_job_role : null,
        is_active: true,
      };
      await adminApi<EnrollmentAuthorization>("authorized-enrollments", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setAuthorizationForm({
        enrollment_number: "",
        expected_role: "STUDENT",
        admin_job_role: "UNIVERSITY_ADMIN",
      });
      setAuthorizationFormOpen(false);
      setNotice("Enrollment authorization created.");
      setAuthorizations(await adminApi<EnrollmentAuthorization[]>("authorized-enrollments"));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Authorization creation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function updateAuthorizationJobRole(record: EnrollmentAuthorization, jobRole: string) {
    if (record.expected_role !== "ADMIN" || !jobRole || jobRole === record.admin_job_role) return;
    if (
      !window.confirm(
        `Set ${record.enrollment_number} to the ${jobRole.replaceAll("_", " ")} registration role?`,
      )
    )
      return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await adminApi<EnrollmentAuthorization>(
        `authorized-enrollments/${record.id}`,
        { method: "PATCH", body: JSON.stringify({ admin_job_role: jobRole }) },
      );
      setAuthorizations((current) =>
        current.map((item) => (item.id === record.id ? updated : item)),
      );
      setNotice(`Administrative job role provisioned for ${record.enrollment_number}.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Administrative job-role update failed.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleAuthorization(record: EnrollmentAuthorization) {
    if (
      !window.confirm(
        `${record.is_active ? "Deactivate" : "Activate"} authorization for ${record.enrollment_number}?`,
      )
    )
      return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await adminApi<EnrollmentAuthorization>(
        `authorized-enrollments/${record.id}`,
        { method: "PATCH", body: JSON.stringify({ is_active: !record.is_active }) },
      );
      setAuthorizations((current) =>
        current.map((item) => (item.id === record.id ? updated : item)),
      );
      setNotice(
        `Authorization for ${record.enrollment_number} is now ${
          updated.is_active ? "active" : "inactive"
        }.`,
      );
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Authorization update failed.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleCourse(course: Course) {
    const next = !course.is_active;
    const subjectLabel = course.code || course.name;
    if (!window.confirm(`${next ? "Activate" : "Deactivate"} ${subjectLabel}?`)) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await adminApi<Course>(`courses/${course.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: next }),
      });
      setCourses((current) =>
        current.map((item) => (item.id === course.id ? updated : item)),
      );
      setNotice(`${subjectLabel} is now ${next ? "active" : "inactive"}.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Course update failed.");
    } finally {
      setBusy(false);
    }
  }

  async function createQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await adminApi<Question>("questions", {
        method: "POST",
        body: JSON.stringify({
          title: questionForm.title.trim(),
          description: questionForm.description.trim(),
          difficulty: questionForm.difficulty,
          status: questionForm.status,
          allowed_languages: ["python", "c", "cpp", "java"],
          examples: [],
        }),
      });
      setQuestionForm({ title: "", description: "", difficulty: "EASY", status: "DRAFT" });
      setQuestionFormOpen(false);
      setNotice(
        "Question created successfully. Add examples and test cases from the question editor when available.",
      );
      await loadSection("Assessment Management");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Question creation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function changeQuestionStatus(question: Question, status: Question["status"]) {
    if (question.status === status) return;
    if (!window.confirm(`Change "${question.title}" to ${status.toLowerCase()}?`)) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await adminApi<Question>(`questions/${question.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      setQuestions((current) =>
        current.map((item) => (item.id === question.id ? { ...item, status: updated.status } : item)),
      );
      setNotice(`Question status updated to ${status}.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Question status update failed.");
    } finally {
      setBusy(false);
    }
  }

  const filteredUsers = useMemo(
    () =>
      users.filter((item) =>
        [item.name, item.email, item.enrollment_number ?? "", item.role, item.academic_course ?? ""]
          .join(" ")
          .toLowerCase()
          .includes(search.toLowerCase()),
      ),
    [users, search],
  );

  const filteredCourses = useMemo(
    () =>
      courses.filter((item) =>
        [
          item.code ?? "",
          item.name,
          item.program,
          item.year_of_study,
          item.semester,
          item.academic_year ?? "",
          ...(item.faculty_names ?? []),
        ]
          .join(" ")
          .toLowerCase()
          .includes(search.toLowerCase()),
      ),
    [courses, search],
  );

  const filteredQuestions = useMemo(
    () =>
      questions.filter((item) =>
        [item.title, item.slug, item.difficulty, item.status]
          .join(" ")
          .toLowerCase()
          .includes(search.toLowerCase()),
      ),
    [questions, search],
  );

  const filteredSubmissions = useMemo(
    () =>
      (submissionPage?.items ?? []).filter((item) =>
        [item.id, item.user_id, item.question_id, item.language, item.status]
          .join(" ")
          .toLowerCase()
          .includes(search.toLowerCase()),
      ),
    [submissionPage, search],
  );

  const filteredApprovals = useMemo(() => {
    return approvals.filter((a) => {
      if (approvalFilter !== "ALL" && a.decision !== approvalFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        return (
          a.applicant_name?.toLowerCase().includes(q) ||
          a.applicant_email?.toLowerCase().includes(q) ||
          a.applicant_enrollment_number?.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [approvals, approvalFilter, search]);

  if (sessionLoading)
    return (
      <main
        className="flex min-h-screen items-center justify-center"
        style={{ backgroundColor: "var(--color-background)" }}
      >
        <div className="text-center">
          <div className="mx-auto mb-4 h-9 w-9 animate-spin rounded-full border-2 border-[#FF6B2C] border-t-transparent" />
          <p className="text-sm font-semibold text-[#706C65] dark:text-[#A5A29C]">Loading administrator suite...</p>
        </div>
      </main>
    );

  if (error && !user)
    return (
      <main
        className="flex min-h-screen items-center justify-center px-5"
        style={{ backgroundColor: "var(--color-background)" }}
      >
        <section className="w-full max-w-md rounded-2xl lux-card p-7 border border-[#E4DDD2] dark:border-[#2D2D2D]">
          <h1 className="text-xl font-extrabold text-[#191919] dark:text-[#F7F4EF]">Unable to load dashboard</h1>
          <p className="mt-3 text-sm leading-6 text-[#706C65] dark:text-[#A5A29C]">{error}</p>
          <div className="mt-6 flex gap-3">
            <Button onClick={() => window.location.reload()}>Try again</Button>
            <Button variant="secondary" onClick={() => router.replace("/login")}>
              Sign in
            </Button>
          </div>
        </section>
      </main>
    );

  if (!user) return null;

  const userRows =
    activeSection === "Faculty Management"
      ? filteredUsers.filter((item) => item.role === "FACULTY")
      : filteredUsers;
  const successBanner = notice ? <Notice kind="success">{notice}</Notice> : null;
  const errorBanner = error ? <Notice>{error}</Notice> : null;
  const searchBox = (
    <label className="block w-full sm:max-w-sm">
      <span className="sr-only">Search this section</span>
      <div className="relative">
        <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-[#706C65] dark:text-[#A5A29C]">
          ⌕
        </span>
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search records..."
          className="input-field pl-10"
        />
      </div>
    </label>
  );

  return (
    <main className="min-h-screen" style={{ backgroundColor: "var(--color-background)" }}>
      <div className="flex min-h-screen">
        {/* Desktop Sidebar */}
        <aside
          className={cx(
            "fixed inset-y-0 left-0 z-40 flex w-[285px] flex-col border-r border-[#E4DDD2] dark:border-[#2D2D2D] bg-[#FFFFFF] dark:bg-[#151515] transition-transform lg:sticky lg:top-0 lg:h-screen lg:translate-x-0",
            mobileNavOpen ? "translate-x-0" : "-translate-x-full",
          )}
        >
          <div className="flex items-center justify-between border-b border-[#E4DDD2] dark:border-[#2D2D2D] px-5 py-4">
            <button
              type="button"
              onClick={() => navigate("Overview")}
              className="flex items-center gap-2.5 text-left"
            >
              <CredLabLogo size="sm" showWordmark={true} />
              <span className="rounded-md bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-bold text-amber-500 uppercase tracking-wider border border-amber-500/20">
                Admin
              </span>
            </button>
            <button
              type="button"
              aria-label="Close navigation"
              onClick={() => setMobileNavOpen(false)}
              className="rounded-lg px-2 py-1 text-[#706C65] dark:text-[#A5A29C] hover:bg-[#FF6B2C]/10 dark:hover:bg-[#252525] lg:hidden"
            >
              ✕
            </button>
          </div>

          <div className="px-5 pb-2 pt-5">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#706C65] dark:text-[#A5A29C]">
              Workspace Control
            </p>
          </div>

          <nav aria-label="Admin navigation" className="flex-1 space-y-1 overflow-y-auto px-3 pb-4">
            {sections.map((sec) => (
              <button
                key={sec.name}
                type="button"
                onClick={() => navigate(sec.name)}
                aria-current={activeSection === sec.name ? "page" : undefined}
                className={cx(
                  "flex w-full items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition-all",
                  activeSection === sec.name
                    ? "text-white shadow-xs"
                    : "border-transparent text-[#706C65] dark:text-[#A5A29C] hover:bg-[#F3EFEA] dark:hover:bg-[#252525] hover:text-[#FF6B2C]",
                )}
                style={activeSection === sec.name ? { background: "var(--primary-gradient)" } : undefined}
              >
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-base font-bold">
                  {sec.icon}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-xs font-bold">{sec.name}</span>
                  <span
                    className={`mt-0.5 block text-[10px] ${
                      activeSection === sec.name ? "text-white/80" : "text-[#706C65] dark:text-[#A5A29C]"
                    }`}
                  >
                    {sec.description}
                  </span>
                </span>
              </button>
            ))}
          </nav>

          <div className="border-t border-[#E4DDD2] dark:border-[#2D2D2D] p-4 bg-[#FFFCF6] dark:bg-[#1B1B1B]">
            <div className="flex items-center gap-3 rounded-xl bg-[#FFFFFF] dark:bg-[#151515] border border-[#E4DDD2] dark:border-[#2D2D2D] p-3">
              <div
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-sm font-bold text-white"
                style={{ background: "var(--primary-gradient)" }}
              >
                {initials(user.name)}
              </div>
              <div className="min-w-0">
                <p className="truncate text-xs font-bold text-[#191919] dark:text-[#F7F4EF]">{user.name}</p>
                <p className="truncate text-[10px] font-semibold text-[#706C65] dark:text-[#A5A29C]">
                  {user.admin_job_role?.replaceAll("_", " ") || "Administrator"}
                </p>
              </div>
            </div>
          </div>
        </aside>

        {mobileNavOpen && (
          <button
            type="button"
            aria-label="Close navigation overlay"
            onClick={() => setMobileNavOpen(false)}
            className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          />
        )}

        <div className="min-w-0 flex-1">
          {/* Sticky Topbar */}
          <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-[#E4DDD2] dark:border-[#2D2D2D] bg-[#FFFFFF]/90 dark:bg-[#151515]/90 px-4 py-3.5 backdrop-blur-md sm:px-7">
            <div className="flex min-w-0 items-center gap-3">
              <button
                type="button"
                aria-label="Open navigation"
                onClick={() => setMobileNavOpen(true)}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-[#E4DDD2] dark:border-[#2D2D2D] text-[#191919] dark:text-[#F7F4EF] hover:bg-[#F3EFEA] dark:hover:bg-[#252525] lg:hidden"
              >
                ☰
              </button>
              <div className="min-w-0">
                <h1 className="truncate text-sm font-extrabold text-[#191919] dark:text-[#F7F4EF]">{activeSection}</h1>
                <p className="truncate text-xs font-semibold text-[#706C65] dark:text-[#A5A29C]">
                  University Administration Portal
                </p>
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-2 sm:gap-3">
              <span className="hidden items-center gap-2 rounded-full border border-emerald-800 bg-emerald-950/40 px-3 py-1 text-xs font-bold text-emerald-300 sm:inline-flex">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                Live Session
              </span>
              <Button variant="secondary" onClick={() => void refresh()} disabled={loadingData}>
                ↻ <span className="ml-1 hidden sm:inline">Refresh</span>
              </Button>
              <Button variant="secondary" onClick={handleLogout} disabled={loggingOut}>
                {loggingOut ? "Signing out…" : "Sign Out"}
              </Button>
            </div>
          </header>

          <div className="mx-auto max-w-[1550px] px-4 py-7 sm:px-7 sm:py-8">
            {/* Banner */}
            <section className="lux-card relative mb-8 overflow-hidden rounded-3xl p-6 sm:p-8 bg-gradient-to-r from-[#1B1B1B] via-[#1E1E1E] to-[#242424] border border-[#353535] shadow-lg">
              <DashboardAmbientGrid />
              <div className="relative z-10 flex flex-col justify-between gap-5 sm:flex-row sm:items-center">
                <div>
                  <p className="inline-flex rounded-full border border-[#353535] bg-[#161616] px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-[#FF8A3D]">
                    INSTITUTIONAL ADMINISTRATION
                  </p>
                  <h2 className="mt-3 text-2xl font-extrabold tracking-tight text-[#F7F4EF] sm:text-3xl">
                    Welcome back, {user.name.split(" ")[0]}
                  </h2>
                  <p className="mt-1 max-w-2xl text-xs sm:text-sm text-[#A5A29C]">
                    Manage platform accounts, university courses, coding question banks, and
                    assessment activity.
                  </p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {user.enrollment_number && <Badge>{user.enrollment_number}</Badge>}
                    <Badge tone={user.is_active ? "good" : "bad"}>
                      {user.is_active ? "Active account" : "Inactive account"}
                    </Badge>
                    {user.admin_job_role && (
                      <Badge tone="blue">{user.admin_job_role.replaceAll("_", " ")}</Badge>
                    )}
                  </div>
                </div>

                <div
                  className="flex h-16 w-16 shrink-0 items-center justify-center self-start rounded-2xl text-xl font-bold text-white shadow-sm sm:h-20 sm:w-20 sm:self-center"
                  style={{ background: "var(--primary-gradient)" }}
                >
                  {initials(user.name)}
                </div>
              </div>
            </section>

            {errorBanner}
            {successBanner}

            {activeSection !== "Overview" && activeSection !== "Settings" && (
              <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                {searchBox}
                <p className="text-xs font-semibold text-[#706C65] dark:text-[#A5A29C]">
                  Records retrieved from PostgreSQL database.
                </p>
              </div>
            )}

            {/* ─────────────── OVERVIEW ─────────────── */}
            {activeSection === "Overview" && (
              <section className="animate-fade-in">
                <SectionHeading
                  eyebrow="Live Platform Data"
                  title="Platform Overview"
                  description="Real-time counts retrieved from backend database models."
                  action={
                    <Button
                      variant="secondary"
                      onClick={() => void loadOverview()}
                      disabled={loadingData}
                    >
                      Refresh Metrics
                    </Button>
                  }
                />
                {loadingData &&
                !overview.users &&
                !overview.courses &&
                !overview.questions &&
                !overview.submissions ? (
                  <LoadingBlock />
                ) : (
                  <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    <StatCard
                      label="Registered Users"
                      value={overview.users ? overview.users.length : "—"}
                      detail={
                        overview.users
                          ? `${overview.users.filter((u) => u.role === "STUDENT").length} students · ${
                              overview.users.filter((u) => u.role === "FACULTY").length
                            } faculty`
                          : "User endpoint unavailable"
                      }
                      icon="♙"
                    />
                    <StatCard
                      label="Active Courses"
                      value={overview.courses ? overview.courses.filter((c) => c.is_active).length : "—"}
                      detail={
                        overview.courses
                          ? `${overview.courses.length} total university subjects`
                          : "Course endpoint unavailable"
                      }
                      icon="▤"
                    />
                    <StatCard
                      label="Question Bank"
                      value={overview.questions ? overview.questions.length : "—"}
                      detail={
                        overview.questions
                          ? `${overview.questions.filter((q) => q.status === "PUBLISHED").length} published practical questions`
                          : "Question endpoint unavailable"
                      }
                      icon="⌘"
                    />
                    <StatCard
                      label="Total Submissions"
                      value={overview.submissions ? overview.submissions.total : "—"}
                      detail={
                        overview.submissions
                          ? "All student test evaluations"
                          : "Submissions endpoint unavailable"
                      }
                      icon="⇧"
                    />
                  </div>
                )}

                <div className="mt-7 grid gap-5 xl:grid-cols-[1.25fr_0.75fr]">
                  <div className="lux-card p-5 sm:p-6 bg-[#FFFCF6] dark:bg-[#1B1B1B] border border-[#E4DDD2] dark:border-[#2D2D2D]">
                    <h3 className="font-bold text-sm text-[#191919] dark:text-[#F7F4EF]">Quick Actions</h3>
                    <p className="mt-0.5 text-xs text-[#706C65] dark:text-[#A5A29C]">
                      Direct shortcuts to core institutional functions.
                    </p>
                    <div className="mt-5 grid gap-3 sm:grid-cols-2">
                      {(
                        [
                          "User Management",
                          "Faculty Management",
                          "Course Management",
                          "Assessment Management",
                          "Submissions",
                          "Results & Analytics",
                        ] as AdminSection[]
                      ).map((name) => (
                        <button
                          key={name}
                          type="button"
                          onClick={() => navigate(name)}
                          className="flex items-center justify-between rounded-xl border border-[#E4DDD2] dark:border-[#2D2D2D] bg-[#FFFFFF] dark:bg-[#151515] px-4 py-3 text-left text-xs font-bold text-[#191919] dark:text-[#F7F4EF] transition hover:border-[#FF6B2C] hover:bg-[#FF6B2C]/10 hover:text-[#FF6B2C] dark:hover:text-[#FFB547]"
                        >
                          <span>{name}</span>
                          <span className="text-[#FF6B2C] dark:text-[#FFB547]">→</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="lux-card p-5 sm:p-6 bg-[#FFFCF6] dark:bg-[#1B1B1B] border border-[#E4DDD2] dark:border-[#2D2D2D]">
                    <h3 className="font-bold text-sm text-[#191919] dark:text-[#F7F4EF]">Security Architecture</h3>
                    <p className="mt-0.5 text-xs text-[#706C65] dark:text-[#A5A29C]">Session and execution assurances.</p>
                    <div className="mt-5 space-y-3.5">
                      <div className="flex items-start gap-3">
                        <span className="text-emerald-600 dark:text-emerald-400 font-bold">●</span>
                        <div>
                          <p className="text-xs font-bold text-[#191919] dark:text-[#F7F4EF]">HTTP-Only Cookie Session</p>
                          <p className="mt-0.5 text-[11px] text-[#706C65] dark:text-[#A5A29C]">
                            Next.js proxy protects credentials from client-side script access.
                          </p>
                        </div>
                      </div>
                      <div className="flex items-start gap-3">
                        <span className="text-[#FF6B2C] dark:text-[#FFB547] font-bold">●</span>
                        <div>
                          <p className="text-xs font-bold text-[#191919] dark:text-[#F7F4EF]">Server-Side Sandbox</p>
                          <p className="mt-0.5 text-[11px] text-[#706C65] dark:text-[#A5A29C]">
                            Subprocess execution isolates student code from application server.
                          </p>
                        </div>
                      </div>
                      <div className="flex items-start gap-3">
                        <span className="text-amber-500 font-bold">●</span>
                        <div>
                          <p className="text-xs font-bold text-[#191919] dark:text-[#F7F4EF]">Ed25519 Cryptographic Signing</p>
                          <p className="mt-0.5 text-[11px] text-[#706C65] dark:text-[#A5A29C]">
                            Certificates contain verifiable digital signatures against public key.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </section>
            )}

            {/* ─────────────── USER & FACULTY MANAGEMENT ─────────────── */}
            {(activeSection === "User Management" || activeSection === "Faculty Management") && (
              <section className="animate-fade-in">
                <SectionHeading
                  eyebrow="Roster Governance"
                  title={activeSection}
                  description={
                    activeSection === "Faculty Management"
                      ? "Inspect faculty accounts and assigned academic subjects."
                      : "Search registered users, inspect academic profiles, and manage system roles."
                  }
                />
                {loadingData ? (
                  <LoadingBlock />
                ) : userRows.length === 0 ? (
                  <EmptyBlock
                    title="No matching accounts"
                    description={
                      search
                        ? "Try another query."
                        : "No accounts were returned by the backend for this view."
                    }
                  />
                ) : (
                  <div className="overflow-hidden lux-card border border-[#E4DDD2] dark:border-[#2D2D2D]">
                    <div className="overflow-x-auto">
                      <table className="lux-table">
                        <thead>
                          <tr>
                            <th>User</th>
                            <th>Enrollment</th>
                            <th>Role & State</th>
                            <th>Academic Profile</th>
                            <th>Registered</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {userRows.map((item) => (
                            <tr key={item.id}>
                              <td>
                                <div className="flex items-center gap-3">
                                  <span
                                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-xs font-bold text-white shadow-xs"
                                    style={{ background: "var(--primary-gradient)" }}
                                  >
                                    {initials(item.name)}
                                  </span>
                                  <div>
                                    <p className="font-bold text-sm text-[#191919] dark:text-[#F7F4EF]">{item.name}</p>
                                    <p className="text-xs text-[#706C65] dark:text-[#A5A29C]">{item.email}</p>
                                  </div>
                                </div>
                              </td>
                              <td className="font-mono text-xs font-bold text-[#191919] dark:text-[#F7F4EF]">
                                {item.enrollment_number || "—"}
                              </td>
                              <td>
                                <Badge tone={item.role === "ADMIN" ? "blue" : item.role === "FACULTY" ? "good" : "neutral"}>
                                  {item.role}
                                </Badge>
                                <div className="mt-1">
                                  <Badge tone={item.is_active ? "good" : "bad"}>
                                    {item.is_active ? "Active" : "Inactive"}
                                  </Badge>
                                </div>
                              </td>
                              <td className="text-xs text-[#706C65] dark:text-[#A5A29C]">
                                {item.role === "STUDENT"
                                  ? [
                                      item.academic_course,
                                      item.year_of_study,
                                      item.semester,
                                      item.academic_year,
                                    ]
                                      .filter(Boolean)
                                      .join(" · ") || "Not set"
                                  : item.role === "FACULTY"
                                  ? item.assigned_courses?.join(", ") || "No courses assigned"
                                  : item.admin_job_role?.replaceAll("_", " ") || "—"}
                              </td>
                              <td className="text-xs text-[#706C65] dark:text-[#A5A29C]">{dateLabel(item.created_at)}</td>
                              <td>
                                <div className="flex flex-col items-start gap-1.5">
                                  <select
                                    aria-label={`Change role for ${item.name}`}
                                    value={item.role}
                                    disabled={busy || item.id === user.id}
                                    onChange={(event) =>
                                      void updateUserRole(item, event.target.value as UserRole)
                                    }
                                    className="rounded-lg border border-[#E4DDD2] dark:border-[#2D2D2D] bg-white dark:bg-[#151515] px-2.5 py-1 text-xs text-[#191919] dark:text-[#F7F4EF] outline-none"
                                  >
                                    <option value="STUDENT">STUDENT</option>
                                    <option value="FACULTY">FACULTY</option>
                                    {item.role === "ADMIN" && <option value="ADMIN">ADMIN</option>}
                                  </select>
                                  {item.role === "STUDENT" && (
                                    <Button
                                      variant="secondary"
                                      disabled={busy}
                                      onClick={() => editAcademicProfile(item)}
                                    >
                                      Edit Profile
                                    </Button>
                                  )}
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </section>
            )}

            {/* ─────────────── COURSE MANAGEMENT ─────────────── */}
            {activeSection === "Course Management" && (
              <section className="animate-fade-in">
                <SectionHeading
                  eyebrow="Curricular Subjects"
                  title="Course Management"
                  description="Create university courses, designate academic semester cohorts, and assign faculty instructors."
                  action={
                    <Button onClick={() => setCourseFormOpen((value) => !value)}>
                      {courseFormOpen ? "Cancel" : "+ New Subject"}
                    </Button>
                  }
                />

                {courseFormOpen && (
                  <form
                    onSubmit={createCourse}
                    className="lux-card mb-6 p-5 sm:p-6 bg-[#FFFCF6] dark:bg-[#1B1B1B] border border-[#E4DDD2] dark:border-[#2D2D2D]"
                  >
                    <h3 className="mb-2 font-bold text-sm text-[#191919] dark:text-[#F7F4EF]">Create Academic Subject</h3>
                    <p className="mb-5 text-xs text-[#706C65] dark:text-[#A5A29C]">
                      Matching enrolled students will be linked to this subject automatically.
                    </p>
                    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                      <SelectField
                        label="Program / Course"
                        value={courseForm.program}
                        onChange={(value) => setCourseForm((f) => ({ ...f, program: value }))}
                        options={PROGRAM_OPTIONS.map((value) => ({ label: value, value }))}
                      />
                      <SelectField
                        label="Year of Study"
                        value={courseForm.year_of_study}
                        onChange={(value) => setCourseForm((f) => ({ ...f, year_of_study: value }))}
                        options={YEAR_OF_STUDY_OPTIONS.map((value) => ({ label: value, value }))}
                      />
                      <SelectField
                        label="Semester"
                        value={courseForm.semester}
                        onChange={(value) => setCourseForm((f) => ({ ...f, semester: value }))}
                        options={SEMESTER_OPTIONS.map((value) => ({ label: value, value }))}
                      />
                      <Field
                        label="Subject Name"
                        value={courseForm.name}
                        onChange={(value) => setCourseForm((f) => ({ ...f, name: value }))}
                        placeholder="e.g. Object Oriented Programming"
                        required
                      />
                      <Field
                        label="Subject Code"
                        value={courseForm.code}
                        onChange={(value) => setCourseForm((f) => ({ ...f, code: value }))}
                        placeholder="CS201"
                      />
                      <Field
                        label="Academic Session"
                        value={courseForm.academic_year}
                        onChange={(value) => setCourseForm((f) => ({ ...f, academic_year: value }))}
                        placeholder="2026-2027"
                        required
                      />
                      <SelectField
                        label="Assign Faculty"
                        value={courseForm.faculty_id}
                        onChange={(value) => setCourseForm((f) => ({ ...f, faculty_id: value }))}
                        options={[
                          { label: "Select faculty member…", value: "" },
                          ...users
                            .filter((item) => item.role === "FACULTY" && item.is_active)
                            .map((item) => ({
                              label: `${item.name} (${item.email})`,
                              value: String(item.id),
                            })),
                        ]}
                      />
                      <div className="sm:col-span-2">
                        <Field
                          label="Description"
                          value={courseForm.description}
                          onChange={(value) =>
                            setCourseForm((f) => ({ ...f, description: value }))
                          }
                          placeholder="Syllabus overview..."
                        />
                      </div>
                    </div>
                    <div className="mt-5 flex justify-end">
                      <Button type="submit" disabled={busy}>
                        {busy ? "Saving…" : "Create Subject & Assign"}
                      </Button>
                    </div>
                  </form>
                )}

                {loadingData ? (
                  <LoadingBlock />
                ) : filteredCourses.length === 0 ? (
                  <EmptyBlock
                    title="No courses found"
                    description="Create a course to begin assigning laboratory practicals."
                  />
                ) : (
                  <div className="overflow-hidden lux-card border border-[#E4DDD2] dark:border-[#2D2D2D]">
                    <div className="overflow-x-auto">
                      <table className="lux-table">
                        <thead>
                          <tr>
                            <th>Subject</th>
                            <th>Cohort</th>
                            <th>Students</th>
                            <th>Faculty</th>
                            <th>Labs</th>
                            <th>Status</th>
                            <th>Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredCourses.map((c) => (
                            <tr key={c.id}>
                              <td>
                                <p className="font-bold text-sm text-[#191919] dark:text-[#F7F4EF]">{c.name}</p>
                                <p className="text-xs text-[#706C65] dark:text-[#A5A29C]">{c.code || "No code"}</p>
                              </td>
                              <td className="text-xs text-[#706C65] dark:text-[#A5A29C]">
                                <span className="font-semibold text-[#191919] dark:text-[#F7F4EF]">{c.program}</span>
                                <p className="mt-0.5">
                                  {c.year_of_study} · {c.semester} · {c.academic_year || "2026-2027"}
                                </p>
                              </td>
                              <td className="font-bold text-xs text-[#191919] dark:text-[#F7F4EF]">{c.student_count}</td>
                              <td className="text-xs text-[#706C65] dark:text-[#A5A29C]">
                                {c.faculty_names?.length ? c.faculty_names.join(", ") : "Unassigned"}
                              </td>
                              <td className="font-bold text-xs text-[#FF6B2C] dark:text-[#FFB547]">{c.lab_count}</td>
                              <td>
                                <Badge tone={c.is_active ? "good" : "warn"}>
                                  {c.is_active ? "Active" : "Inactive"}
                                </Badge>
                              </td>
                              <td>
                                <div className="flex items-center gap-2">
                                  <Button
                                    variant="secondary"
                                    disabled={busy}
                                    onClick={() => void toggleCourse(c)}
                                  >
                                    {c.is_active ? "Deactivate" : "Activate"}
                                  </Button>
                                  <Button
                                    variant="danger"
                                    disabled={busy}
                                    onClick={() => void openSubjectDeleteModal(c)}
                                  >
                                    Delete Subject
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </section>
            )}

            {/* ─────────────── ASSESSMENT MANAGEMENT ─────────────── */}
            {activeSection === "Assessment Management" && (
              <section className="animate-fade-in">
                <SectionHeading
                  eyebrow="Question Bank"
                  title="Assessment Management"
                  description="Curate coding challenges and unit test specifications."
                  action={
                    <Button onClick={() => setQuestionFormOpen((value) => !value)}>
                      {questionFormOpen ? "Cancel" : "+ New Question"}
                    </Button>
                  }
                />

                {questionFormOpen && (
                  <form
                    onSubmit={createQuestion}
                    className="lux-card mb-6 p-5 sm:p-6 bg-[#FFFCF6] dark:bg-[#1B1B1B] border border-[#E4DDD2] dark:border-[#2D2D2D]"
                  >
                    <h3 className="mb-4 font-bold text-sm text-[#191919] dark:text-[#F7F4EF]">Create Coding Question</h3>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <Field
                        label="Question Title"
                        value={questionForm.title}
                        onChange={(value) => setQuestionForm((f) => ({ ...f, title: value }))}
                        placeholder="e.g. Valid Anagram Search"
                        required
                      />
                      <SelectField
                        label="Difficulty"
                        value={questionForm.difficulty}
                        onChange={(value) => setQuestionForm((f) => ({ ...f, difficulty: value }))}
                        options={[
                          { label: "Easy", value: "EASY" },
                          { label: "Medium", value: "MEDIUM" },
                          { label: "Hard", value: "HARD" },
                        ]}
                      />
                      <SelectField
                        label="Status"
                        value={questionForm.status}
                        onChange={(value) => setQuestionForm((f) => ({ ...f, status: value }))}
                        options={[
                          { label: "Draft", value: "DRAFT" },
                          { label: "Published", value: "PUBLISHED" },
                        ]}
                      />
                      <div className="sm:col-span-2">
                        <label className="block text-xs font-bold uppercase tracking-wider text-[#191919] dark:text-[#F7F4EF]">
                          <span className="mb-1.5 block">Problem Statement</span>
                          <textarea
                            value={questionForm.description}
                            required
                            minLength={5}
                            onChange={(event) =>
                              setQuestionForm((f) => ({ ...f, description: event.target.value }))
                            }
                            rows={4}
                            placeholder="Detailed requirements and constraints..."
                            className="input-field text-xs"
                          />
                        </label>
                      </div>
                    </div>
                    <div className="mt-5 flex justify-end">
                      <Button type="submit" disabled={busy}>
                        {busy ? "Saving…" : "Create Question"}
                      </Button>
                    </div>
                  </form>
                )}

                {loadingData ? (
                  <LoadingBlock />
                ) : filteredQuestions.length === 0 ? (
                  <EmptyBlock
                    title="No questions found"
                    description="Create a question to add to practical curricula."
                  />
                ) : (
                  <div className="overflow-hidden lux-card border border-[#E4DDD2] dark:border-[#2D2D2D]">
                    <div className="overflow-x-auto">
                      <table className="lux-table">
                        <thead>
                          <tr>
                            <th>Question</th>
                            <th>Difficulty</th>
                            <th>Languages</th>
                            <th>Examples</th>
                            <th>Created</th>
                            <th>Status</th>
                            <th>Update</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredQuestions.map((q) => (
                            <tr key={q.id}>
                              <td>
                                <p className="font-bold text-sm text-[#191919] dark:text-[#F7F4EF]">{q.title}</p>
                                <p className="text-xs text-[#706C65] dark:text-[#A5A29C] font-mono">{q.slug}</p>
                              </td>
                              <td>
                                <Badge
                                  tone={
                                    q.difficulty === "HARD"
                                      ? "bad"
                                      : q.difficulty === "MEDIUM"
                                      ? "warn"
                                      : "good"
                                  }
                                >
                                  {q.difficulty}
                                </Badge>
                              </td>
                              <td className="text-xs font-mono text-[#706C65] dark:text-[#A5A29C]">
                                {q.allowed_languages.join(", ") || "All"}
                              </td>
                              <td className="text-xs font-bold text-[#191919] dark:text-[#F7F4EF]">{q.example_count}</td>
                              <td className="text-xs text-[#706C65] dark:text-[#A5A29C]">{dateLabel(q.created_at)}</td>
                              <td>
                                <Badge tone={q.status === "PUBLISHED" ? "good" : "warn"}>
                                  {q.status}
                                </Badge>
                              </td>
                              <td>
                                <select
                                  aria-label={`Change status for ${q.title}`}
                                  disabled={busy}
                                  value={q.status}
                                  onChange={(event) =>
                                    void changeQuestionStatus(
                                      q,
                                      event.target.value as Question["status"],
                                    )
                                  }
                                  className="rounded-lg border border-[#E4DDD2] dark:border-[#2D2D2D] bg-white dark:bg-[#151515] px-2 py-1 text-xs text-[#191919] dark:text-[#F7F4EF]"
                                >
                                  <option value="DRAFT">DRAFT</option>
                                  <option value="PUBLISHED">PUBLISHED</option>
                                  <option value="ARCHIVED">ARCHIVED</option>
                                </select>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </section>
            )}

            {/* ─────────────── SUBMISSIONS AUDIT ─────────────── */}
            {activeSection === "Submissions" && (
              <section className="animate-fade-in">
                <SectionHeading
                  eyebrow="Evaluation Audit"
                  title="Platform Submissions"
                  description="Real-time audit log of student code evaluations."
                />
                {loadingData ? (
                  <LoadingBlock />
                ) : filteredSubmissions.length === 0 ? (
                  <EmptyBlock
                    title="No submissions found"
                    description="Student submissions will appear here once practicals are attempted."
                  />
                ) : (
                  <div className="overflow-hidden lux-card border border-[#E4DDD2] dark:border-[#2D2D2D]">
                    <div className="overflow-x-auto">
                      <table className="lux-table">
                        <thead>
                          <tr>
                            <th>Submission</th>
                            <th>Student ID</th>
                            <th>Question ID</th>
                            <th>Language</th>
                            <th>Result</th>
                            <th>Score</th>
                            <th>Test Cases</th>
                            <th>Submitted</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredSubmissions.map((s) => (
                            <tr key={s.id}>
                              <td className="font-mono text-xs font-bold text-[#FF6B2C] dark:text-[#FFB547]">#{s.id}</td>
                              <td className="text-xs font-bold text-[#191919] dark:text-[#F7F4EF]">User #{s.user_id}</td>
                              <td className="text-xs text-[#706C65] dark:text-[#A5A29C]">Question #{s.question_id}</td>
                              <td className="font-mono text-xs uppercase text-[#706C65] dark:text-[#A5A29C]">{s.language}</td>
                              <td>
                                <Badge
                                  tone={
                                    s.status === "ACCEPTED" || s.score === 100
                                      ? "good"
                                      : "bad"
                                  }
                                >
                                  {s.status}
                                </Badge>
                              </td>
                              <td className="font-bold text-xs text-[#191919] dark:text-[#F7F4EF]">{s.score.toFixed(1)}%</td>
                              <td className="text-xs text-[#706C65] dark:text-[#A5A29C]">
                                {s.passed_test_cases}/{s.total_test_cases}
                              </td>
                              <td className="text-xs text-[#706C65] dark:text-[#A5A29C]">{dateLabel(s.created_at)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </section>
            )}

            {/* ─────────────── RESULTS & ANALYTICS ─────────────── */}
            {activeSection === "Results & Analytics" && (
              <section className="animate-fade-in">
                <SectionHeading
                  eyebrow="Reporting"
                  title="Results & Analytics"
                  description="Curriculum completion and question bank distribution."
                />
                {loadingData ? (
                  <LoadingBlock />
                ) : (
                  <div className="space-y-6">
                    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                      <StatCard
                        label="Total Users"
                        value={users.length}
                        detail="Platform-wide registered accounts"
                        icon="♙"
                      />
                      <StatCard
                        label="Active Courses"
                        value={courses.filter((c) => c.is_active).length}
                        detail="Courses running in active session"
                        icon="▤"
                      />
                      <StatCard
                        label="Questions"
                        value={questions.length}
                        detail={`${questions.filter((q) => q.status === "PUBLISHED").length} published`}
                        icon="⌘"
                      />
                      <StatCard
                        label="Submissions"
                        value={submissionPage?.total ?? "—"}
                        detail="Sandbox code executions"
                        icon="⇧"
                      />
                    </div>
                  </div>
                )}
              </section>
            )}

            {/* ─────────────── REGISTRATION APPROVALS ─────────────── */}
            {activeSection === "Registration Approvals" && (
              <section className="animate-fade-in">
                <SectionHeading
                  eyebrow="Access Control"
                  title="Registration Approval Queue"
                  description="Review and adjudicate pending faculty and administrator account registration requests."
                />

                <div className="flex gap-2 mb-4">
                  {(["ALL", "PENDING", "APPROVED", "REJECTED"] as const).map((filter) => (
                    <button
                      key={filter}
                      onClick={() => setApprovalFilter(filter)}
                      className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-colors ${
                        approvalFilter === filter
                          ? "bg-[#FF6B2C] text-white shadow-xs"
                          : "bg-white dark:bg-[#1B1B1B] text-[#706C65] dark:text-[#A5A29C] border border-[#E4DDD2] dark:border-[#2D2D2D] hover:bg-[#F3EFEA] dark:hover:bg-[#252525]"
                      }`}
                    >
                      {filter}
                    </button>
                  ))}
                </div>

                {loadingData ? (
                  <LoadingBlock />
                ) : filteredApprovals.length === 0 ? (
                  <EmptyBlock
                    title={`No ${approvalFilter.toLowerCase()} registration requests`}
                    description="No registration applications match the current filter criteria."
                  />
                ) : (
                  <div className="lux-card bg-[#FFFCF6] dark:bg-[#1B1B1B] border border-[#E4DDD2] dark:border-[#2D2D2D] overflow-hidden">
                    <div className="overflow-x-auto">
                      <table className="lux-table">
                        <thead>
                          <tr>
                            <th>Applicant</th>
                            <th>Staff / Enrollment</th>
                            <th>Account Type</th>
                            <th>Designation</th>
                            <th>Decision</th>
                            <th>Requested At</th>
                            <th>Reviewer Note</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredApprovals.map((req) => (
                            <tr key={req.id}>
                              <td>
                                <div className="font-bold text-xs text-[#191919] dark:text-[#F7F4EF]">{req.applicant_name}</div>
                                <div className="text-[10px] text-[#706C65] dark:text-[#A5A29C]">{req.applicant_email}</div>
                              </td>
                              <td className="font-mono text-xs text-[#191919] dark:text-[#F7F4EF]">
                                {req.applicant_enrollment_number}
                              </td>
                              <td>
                                <Badge tone={req.account_type === "ADMIN" ? "blue" : "neutral"}>
                                  {req.account_type}
                                </Badge>
                              </td>
                              <td className="text-xs text-[#706C65] dark:text-[#A5A29C]">
                                {req.admin_job_role?.replaceAll("_", " ") || "—"}
                              </td>
                              <td>
                                <Badge
                                  tone={
                                    req.decision === "APPROVED"
                                      ? "good"
                                      : req.decision === "REJECTED"
                                      ? "bad"
                                      : "warn"
                                  }
                                >
                                  {req.decision}
                                </Badge>
                              </td>
                              <td className="text-xs text-[#706C65] dark:text-[#A5A29C]">{dateLabel(req.requested_at)}</td>
                              <td className="text-xs text-[#706C65] dark:text-[#A5A29C] max-w-xs truncate">
                                {req.rejection_reason || (req.reviewer_name ? `Approved by ${req.reviewer_name}` : "—")}
                              </td>
                              <td>
                                {req.decision === "PENDING" ? (
                                  <div className="flex gap-2">
                                    <Button
                                      variant="primary"
                                      disabled={busy || (req.account_type === "ADMIN" && user?.admin_job_role !== "SUPER_ADMIN")}
                                      onClick={() => void approveRegistration(req.id)}
                                    >
                                      Approve
                                    </Button>
                                    <Button
                                      variant="danger"
                                      disabled={busy || (req.account_type === "ADMIN" && user?.admin_job_role !== "SUPER_ADMIN")}
                                      onClick={() => setRejectingApproval(req)}
                                    >
                                      Reject
                                    </Button>
                                  </div>
                                ) : (
                                  <span className="text-xs text-[#706C65] dark:text-[#A5A29C]">Completed</span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </section>
            )}

            {/* ─────────────── AUTHORIZATION REGISTRY ─────────────── */}
            {activeSection === "Authorization" && (
              <section className="animate-fade-in">
                <SectionHeading
                  eyebrow="Access Registry"
                  title="Authorization Management"
                  description="Provision university enrollment numbers and roles."
                  action={
                    <Button onClick={() => setAuthorizationFormOpen((value) => !value)}>
                      {authorizationFormOpen ? "Cancel" : "+ Authorize Enrollment"}
                    </Button>
                  }
                />

                {authorizationFormOpen && (
                  <form
                    onSubmit={createAuthorization}
                    className="lux-card mb-6 p-5 sm:p-6 bg-[#FFFCF6] dark:bg-[#1B1B1B] border border-[#E4DDD2] dark:border-[#2D2D2D]"
                  >
                    <h3 className="mb-4 font-bold text-sm text-[#191919] dark:text-[#F7F4EF]">
                      Provision Enrollment Number
                    </h3>
                    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                      <Field
                        label="Enrollment Number"
                        value={authorizationForm.enrollment_number}
                        onChange={(value) =>
                          setAuthorizationForm((f) => ({
                            ...f,
                            enrollment_number: value.toUpperCase(),
                          }))
                        }
                        placeholder="MUR2502214 or EMP0000001"
                        required
                      />
                      <SelectField
                        label="Permitted Account Role"
                        value={authorizationForm.expected_role}
                        onChange={(value) =>
                          setAuthorizationForm((f) => ({
                            ...f,
                            expected_role: value as UserRole,
                          }))
                        }
                        options={[
                          { label: "Student", value: "STUDENT" },
                          { label: "Faculty", value: "FACULTY" },
                          { label: "Administrator", value: "ADMIN" },
                        ]}
                      />
                      {authorizationForm.expected_role === "ADMIN" && (
                        <SelectField
                          label="Admin Job Role"
                          value={authorizationForm.admin_job_role}
                          onChange={(value) =>
                            setAuthorizationForm((f) => ({ ...f, admin_job_role: value }))
                          }
                          options={[
                            { label: "University Admin", value: "UNIVERSITY_ADMIN" },
                            { label: "Department Admin", value: "DEPARTMENT_ADMIN" },
                            { label: "Exam Controller", value: "EXAM_CONTROLLER" },
                            { label: "Lab Admin", value: "LAB_ADMIN" },
                            { label: "Super Admin", value: "SUPER_ADMIN" },
                          ]}
                        />
                      )}
                    </div>
                    <div className="mt-5 flex justify-end">
                      <Button type="submit" disabled={busy}>
                        {busy ? "Saving…" : "Create Authorization"}
                      </Button>
                    </div>
                  </form>
                )}

                {loadingData ? (
                  <LoadingBlock />
                ) : authorizations.length === 0 ? (
                  <EmptyBlock
                    title="No authorization records"
                    description="Provision authorized enrollment numbers for students and faculty."
                  />
                ) : (
                  <div className="overflow-hidden lux-card border border-[#E4DDD2] dark:border-[#2D2D2D]">
                    <div className="overflow-x-auto">
                      <table className="lux-table">
                        <thead>
                          <tr>
                            <th>Enrollment</th>
                            <th>Role</th>
                            <th>Job Role</th>
                            <th>Claimed</th>
                            <th>State</th>
                            <th>Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {authorizations.map((auth) => (
                            <tr key={auth.id}>
                              <td className="font-mono text-xs font-bold text-[#191919] dark:text-[#F7F4EF]">
                                {auth.enrollment_number}
                              </td>
                              <td>
                                <Badge>{auth.expected_role}</Badge>
                              </td>
                              <td className="text-xs text-[#706C65] dark:text-[#A5A29C]">
                                {auth.expected_role === "ADMIN" && user?.admin_job_role === "SUPER_ADMIN" ? (
                                  <select
                                    value={auth.admin_job_role || ""}
                                    onChange={(e) => void updateAuthorizationJobRole(auth, e.target.value)}
                                    disabled={busy}
                                    className="lux-input text-xs py-1"
                                  >
                                    <option value="">Select Role</option>
                                    <option value="UNIVERSITY_ADMIN">University Admin</option>
                                    <option value="DEPARTMENT_ADMIN">Department Admin</option>
                                    <option value="EXAM_CONTROLLER">Exam Controller</option>
                                    <option value="SUPER_ADMIN">Super Admin</option>
                                    <option value="DEAN">Dean</option>
                                    <option value="HEAD_OF_DEPARTMENT">Head Of Department</option>
                                    <option value="SENIOR_FACULTY">Senior Faculty</option>
                                  </select>
                                ) : (
                                  auth.admin_job_role?.replaceAll("_", " ") || "—"
                                )}
                              </td>
                              <td>
                                <Badge tone={auth.claimed_by_user_id ? "good" : "neutral"}>
                                  {auth.claimed_by_user_id
                                    ? `Claimed by #${auth.claimed_by_user_id}`
                                    : "Unclaimed"}
                                </Badge>
                              </td>
                              <td>
                                <Badge tone={auth.is_active ? "good" : "warn"}>
                                  {auth.is_active ? "Active" : "Inactive"}
                                </Badge>
                              </td>
                              <td>
                                <Button
                                  variant="secondary"
                                  disabled={busy}
                                  onClick={() => void toggleAuthorization(auth)}
                                >
                                  {auth.is_active ? "Deactivate" : "Activate"}
                                </Button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </section>
            )}

            {/* ─────────────── SETTINGS ─────────────── */}
            {activeSection === "Settings" && (
              <section className="animate-fade-in">
                <SectionHeading
                  eyebrow="Account"
                  title="Administrator Settings"
                  description="Current authenticated administrator session details."
                />
                <div className="max-w-2xl lux-card p-6 bg-[#FFFCF6] dark:bg-[#1B1B1B] border border-[#E4DDD2] dark:border-[#2D2D2D]">
                  <div className="flex items-center gap-4 border-b border-[#E4DDD2] dark:border-[#2D2D2D] pb-6">
                    <div
                      className="flex h-14 w-14 items-center justify-center rounded-2xl text-lg font-bold text-white shadow-xs"
                      style={{ background: "var(--primary-gradient)" }}
                    >
                      {initials(user.name)}
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-[#191919] dark:text-[#F7F4EF]">{user.name}</h3>
                      <p className="text-xs text-[#706C65] dark:text-[#A5A29C]">{user.email}</p>
                    </div>
                  </div>

                  <dl className="grid gap-4 py-6 sm:grid-cols-2 text-xs">
                    <div>
                      <dt className="font-bold uppercase tracking-wider text-[#706C65] dark:text-[#A5A29C]">Account Role</dt>
                      <dd className="mt-1">
                        <Badge tone="blue">{user.role}</Badge>
                      </dd>
                    </div>
                    <div>
                      <dt className="font-bold uppercase tracking-wider text-[#706C65] dark:text-[#A5A29C]">
                        Job Function
                      </dt>
                      <dd className="mt-1 font-bold text-[#191919] dark:text-[#F7F4EF]">
                        {user.admin_job_role?.replaceAll("_", " ") || "Administrator"}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-bold uppercase tracking-wider text-[#706C65] dark:text-[#A5A29C]">Staff ID</dt>
                      <dd className="mt-1 font-mono font-bold text-[#191919] dark:text-[#F7F4EF]">
                        {user.enrollment_number || "—"}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-bold uppercase tracking-wider text-[#706C65] dark:text-[#A5A29C]">Status</dt>
                      <dd className="mt-1">
                        <Badge tone={user.is_active ? "good" : "bad"}>
                          {user.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </dd>
                    </div>
                  </dl>

                  <Button variant="secondary" onClick={handleLogout} disabled={loggingOut}>
                    {loggingOut ? "Signing out…" : "Sign Out"}
                  </Button>
                </div>
              </section>
            )}

            <footer className="mt-12 text-center text-xs py-4 text-[#706C65] dark:text-[#A5A29C]">
              CredLab · University Administration Suite · 2026
            </footer>
          </div>
        </div>
      </div>

      {/* Rejection Reason Modal */}
      {rejectingApproval && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4"
          role="presentation"
        >
          <div className="w-full max-w-md lux-card p-6 bg-[#FFFCF6] dark:bg-[#1B1B1B] border border-[#E4DDD2] dark:border-[#2D2D2D] shadow-2xl animate-fade-in">
            <h3 className="text-base font-extrabold text-[#191919] dark:text-[#F7F4EF]">Reject Registration Request</h3>
            <p className="mt-1 text-xs text-[#706C65] dark:text-[#A5A29C]">
              Specify the institutional justification for rejecting {rejectingApproval.applicant_name} ({rejectingApproval.applicant_email}).
            </p>
            <form onSubmit={rejectRegistration} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-[#191919] dark:text-[#F7F4EF] mb-1.5">
                  Rejection Reason (Required)
                </label>
                <textarea
                  required
                  rows={3}
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="e.g. Employee ID does not match HR department roster."
                  className="input-field w-full text-xs"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button
                  variant="secondary"
                  disabled={busy}
                  onClick={() => setRejectingApproval(null)}
                >
                  Cancel
                </Button>
                <Button variant="danger" type="submit" disabled={busy || !rejectionReason.trim()}>
                  Confirm Rejection
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Subject Deletion Confirmation Modal (Part 13) */}
      {deletingCourse && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4"
          role="presentation"
        >
          <div className="w-full max-w-lg lux-card p-6 bg-[#FFFCF6] dark:bg-[#1B1B1B] border border-[#E4DDD2] dark:border-[#2D2D2D] shadow-2xl animate-fade-in">
            <div className="flex items-start gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl badge-danger text-lg font-bold">
                ⚠️
              </span>
              <div>
                <h3 className="text-base font-extrabold text-[#191919] dark:text-[#F7F4EF]">
                  Confirm Subject Deletion
                </h3>
                <p className="text-xs text-[#706C65] dark:text-[#A5A29C]">
                  {deletingCourse.name} ({deletingCourse.code || "No code"})
                </p>
              </div>
            </div>

            {deletingCourseBusy ? (
              <div className="mt-6 py-8 text-center text-xs text-[#706C65] dark:text-[#A5A29C]">
                Analyzing subject dependencies and candidate submissions...
              </div>
            ) : deletionPreview ? (
              <div className="mt-5 space-y-3">
                <div className="rounded-xl border border-[#E4DDD2] dark:border-[#2D2D2D] bg-[#FFFFFF] dark:bg-[#151515] p-3.5 text-xs">
                  <div className="grid grid-cols-2 gap-2 text-[#191919] dark:text-[#F7F4EF]">
                    <div>
                      <span className="text-[#706C65] dark:text-[#A5A29C]">Laboratories:</span>{" "}
                      <span className="font-bold">{deletionPreview.lab_count}</span>
                    </div>
                    <div>
                      <span className="text-[#706C65] dark:text-[#A5A29C]">Practicals:</span>{" "}
                      <span className="font-bold">{deletionPreview.practical_count}</span>
                    </div>
                    <div>
                      <span className="text-[#706C65] dark:text-[#A5A29C]">Enrolled Students:</span>{" "}
                      <span className="font-bold">{deletionPreview.enrolled_student_count}</span>
                    </div>
                    <div>
                      <span className="text-[#706C65] dark:text-[#A5A29C]">Historical Submissions:</span>{" "}
                      <span className="font-bold">{deletionPreview.historical_submissions_count}</span>
                    </div>
                  </div>
                </div>

                <div
                  className={`rounded-xl p-3.5 text-xs font-semibold ${
                    deletionPreview.has_historical_activity
                      ? "badge-warning border border-amber-300"
                      : "badge-primary"
                  }`}
                >
                  <p className="font-bold mb-1">
                    {deletionPreview.has_historical_activity ? "Safe Archival Action:" : "Permanent Deletion:"}
                  </p>
                  <p>{deletionPreview.warning_message}</p>
                </div>
              </div>
            ) : null}

            <div className="mt-6 flex justify-end gap-2 pt-2 border-t border-[#E4DDD2] dark:border-[#2D2D2D]">
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() => {
                  setDeletingCourse(null);
                  setDeletionPreview(null);
                }}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                disabled={busy || deletingCourseBusy}
                onClick={() => void confirmDeleteSubject()}
              >
                {busy
                  ? "Processing..."
                  : deletionPreview?.has_historical_activity
                  ? "Archive Subject Safely"
                  : "Delete Subject Permanently"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Student Academic Profile Modal */}
      {editingStudent && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !busy) setEditingStudent(null);
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="academic-profile-title"
            className="w-full max-w-2xl rounded-2xl lux-card p-6 shadow-2xl sm:p-7 bg-[#FFFCF6] dark:bg-[#1B1B1B] border border-[#E4DDD2] dark:border-[#2D2D2D]"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-[#FF6B2C] dark:text-[#FFB547]">
                  Student Roster
                </p>
                <h2 id="academic-profile-title" className="mt-1 text-xl font-extrabold text-[#191919] dark:text-[#F7F4EF]">
                  Edit Academic Profile
                </h2>
                <p className="mt-0.5 text-xs text-[#706C65] dark:text-[#A5A29C]">
                  {editingStudent.name} · {editingStudent.enrollment_number || "No enrollment"}
                </p>
              </div>
              <button
                type="button"
                aria-label="Close dialog"
                disabled={busy}
                onClick={() => setEditingStudent(null)}
                className="rounded-lg px-2 py-1 text-[#706C65] dark:text-[#A5A29C] hover:bg-[#FF6B2C]/10 dark:hover:bg-[#252525]"
              >
                ✕
              </button>
            </div>

            {academicProfileError && (
              <div className="mt-4">
                <Notice>{academicProfileError}</Notice>
              </div>
            )}

            <form onSubmit={saveAcademicProfile} className="mt-5 grid gap-4 sm:grid-cols-2">
              <label className="block text-xs font-bold uppercase tracking-wider text-[#191919] dark:text-[#F7F4EF]">
                <span className="mb-1.5 block">Program</span>
                <select
                  required
                  value={academicProfileForm.academic_course}
                  onChange={(event) =>
                    setAcademicProfileForm((form) => ({
                      ...form,
                      academic_course: event.target.value,
                    }))
                  }
                  className="input-field text-xs"
                >
                  <option value="" disabled>
                    Select program…
                  </option>
                  {PROGRAM_OPTIONS.map((program) => (
                    <option key={program} value={program}>
                      {program}
                    </option>
                  ))}
                </select>
              </label>

              <SelectField
                label="Year of Study"
                value={academicProfileForm.year_of_study}
                onChange={(value) =>
                  setAcademicProfileForm((form) => ({ ...form, year_of_study: value }))
                }
                options={[
                  { label: "Select year…", value: "" },
                  ...YEAR_OF_STUDY_OPTIONS.map((value) => ({ label: value, value })),
                ]}
                required
              />

              <SelectField
                label="Semester"
                value={academicProfileForm.semester}
                onChange={(value) =>
                  setAcademicProfileForm((form) => ({ ...form, semester: value }))
                }
                options={[
                  { label: "Select semester…", value: "" },
                  ...SEMESTER_OPTIONS.map((value) => ({ label: value, value })),
                ]}
                required
              />

              <Field
                label="Academic Session"
                value={academicProfileForm.academic_year}
                onChange={(value) =>
                  setAcademicProfileForm((form) => ({ ...form, academic_year: value }))
                }
                placeholder="2026-2027"
                required
                pattern="[0-9]{4}-[0-9]{4}"
                title="Enter session like 2026-2027"
              />

              <div className="flex justify-end gap-3 sm:col-span-2 mt-2">
                <Button variant="secondary" disabled={busy} onClick={() => setEditingStudent(null)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={busy}>
                  {busy ? "Saving profile…" : "Save Academic Profile"}
                </Button>
              </div>
            </form>
          </section>
        </div>
      )}
    </main>
  );
}
