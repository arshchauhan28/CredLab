"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

type LoginResponse = {
  user?: {
    id: number;
    name: string;
    role: "STUDENT" | "FACULTY" | "ADMIN";
    profile_completed: boolean;
  };
  detail?: string;
};

const dashboardRoutes = {
  STUDENT: "/student/dashboard",
  FACULTY: "/faculty/dashboard",
  ADMIN: "/admin/dashboard",
} as const;

export default function LoginPage() {
  const router = useRouter();

  const [enrollmentNumber, setEnrollmentNumber] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function redirectExistingSession() {
      try {
        const response = await fetch("/api/auth/session", { cache: "no-store" });
        if (!response.ok) return;
        const result = (await response.json()) as LoginResponse;
        if (
          !cancelled &&
          result.user &&
          ["STUDENT", "FACULTY", "ADMIN"].includes(result.user.role)
        ) {
          router.replace(dashboardRoutes[result.user.role]);
        }
      } catch {
        // Ignored in check
      }
    }
    void redirectExistingSession();
    return () => {
      cancelled = true;
    };
  }, [router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    const normalizedEnrollment = enrollmentNumber.trim().toUpperCase();

    if (!/^[A-Z]{3}[0-9]{7}$/.test(normalizedEnrollment)) {
      setError(
        "Enter a valid enrollment number (3 letters followed by 7 digits, e.g. MUR2502214 or EMP0000001).",
      );
      return;
    }

    if (!password) {
      setError("Please enter your password.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          enrollment_number: normalizedEnrollment,
          password,
        }),
      });

      const result = (await response.json()) as LoginResponse;

      if (!response.ok) {
        setError(result.detail ?? "Unable to sign in. Please verify your credentials.");
        return;
      }

      if (
        !result.user ||
        !["STUDENT", "FACULTY", "ADMIN"].includes(result.user.role)
      ) {
        setError("The server returned an unrecognized user role.");
        return;
      }

      const destination = dashboardRoutes[result.user.role];
      router.replace(destination);
    } catch {
      setError(
        "Unable to connect to the authentication server. Please check your network connection.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main
      className="relative flex min-h-screen flex-1 items-center justify-center overflow-hidden px-4 py-10 sm:px-6 sm:py-16"
      style={{ backgroundColor: "var(--color-background)" }}
    >
      {/* Soft Ambient Burgundy Glows */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-36 -top-36 h-[32rem] w-[32rem] rounded-full bg-[#FBEAF0] opacity-80 blur-[100px]" />
        <div className="absolute -bottom-36 -right-36 h-[34rem] w-[34rem] rounded-full bg-[#FFF0F5] opacity-90 blur-[120px]" />
      </div>

      <div className="relative z-10 w-full max-w-5xl overflow-hidden lux-card shadow-xl border border-[#F0DCE5]">
        <div className="grid lg:grid-cols-[1.1fr_1fr]">
          {/* Left panel: Info & Institutional Branding */}
          <section className="hidden flex-col justify-between p-10 lg:flex xl:p-14 bg-[#FFF7FA] border-r border-[#F0DCE5]">
            <div>
              <Link href="/" className="inline-flex items-center gap-3 group">
                <span
                  className="flex h-11 w-11 items-center justify-center rounded-2xl text-xl font-bold text-white shadow-sm"
                  style={{ background: "var(--primary-gradient)" }}
                >
                  ⬡
                </span>
                <div>
                  <span className="block font-bold tracking-tight text-[#3F1024]">LabOS</span>
                  <span className="block text-[11px] font-semibold uppercase tracking-wider text-[#BE5678]">
                    University Assessment Platform
                  </span>
                </div>
              </Link>

              <div className="mt-16">
                <div className="inline-flex items-center gap-2 rounded-full border border-[#F0DCE5] bg-[#FFFFFF] px-3.5 py-1.5 text-xs font-semibold text-[#9F1239]">
                  <span className="h-2 w-2 rounded-full bg-[#9F1239] animate-pulse" />
                  Academic Session 2026–2027
                </div>

                <h1 className="mt-6 text-3xl font-extrabold leading-tight tracking-tight text-[#3F1024] xl:text-4xl">
                  Unified Platform for{" "}
                  <span className="text-gradient-primary">Digital Laboratories</span>
                </h1>

                <p className="mt-4 text-sm leading-relaxed text-[#806777]">
                  Automated code grading, anti-cheat sandbox execution, sequential practical
                  roadmaps, and cryptographically signed completion diplomas.
                </p>
              </div>
            </div>

            <div className="mt-12 space-y-3">
              <div className="flex items-center gap-3 rounded-xl p-3.5 bg-[#FFFFFF] border border-[#F0DCE5]">
                <span className="text-xl">🎓</span>
                <div>
                  <p className="text-xs font-bold text-[#3F1024]">Student Accounts</p>
                  <p className="text-[11px] text-[#806777]">
                    Enrollment format: <code className="font-semibold text-[#9F1239]">MUR2502214</code>
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 rounded-xl p-3.5 bg-[#FFFFFF] border border-[#F0DCE5]">
                <span className="text-xl">👨‍🏫</span>
                <div>
                  <p className="text-xs font-bold text-[#3F1024]">Faculty & Administrators</p>
                  <p className="text-[11px] text-[#806777]">
                    Staff ID format: <code className="font-semibold text-[#BE5678]">EMP0000001</code>
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Right panel: Sign In Form */}
          <section className="flex flex-col justify-center p-7 sm:p-10 lg:p-12 xl:p-14 bg-[#FFFFFF]">
            <div className="mb-8 flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#BE5678]">
                  Secure Access
                </p>
                <h2 className="mt-1 text-2xl font-extrabold text-[#3F1024] sm:text-3xl">
                  Sign In
                </h2>
              </div>
              <Link
                href="/"
                className="text-xs font-semibold text-[#806777] hover:text-[#9F1239] transition-colors"
              >
                ← Back home
              </Link>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label
                  htmlFor="enrollmentNumber"
                  className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#3F1024]"
                >
                  Enrollment Number / Staff ID
                </label>

                <input
                  id="enrollmentNumber"
                  name="enrollment_number"
                  type="text"
                  autoComplete="username"
                  autoCapitalize="characters"
                  spellCheck={false}
                  required
                  maxLength={10}
                  placeholder="e.g. MUR2502214 or EMP0000001"
                  value={enrollmentNumber}
                  onChange={(event) =>
                    setEnrollmentNumber(event.target.value.toUpperCase())
                  }
                  disabled={loading}
                  className="input-field font-mono"
                />
              </div>

              <div>
                <label
                  htmlFor="password"
                  className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#3F1024]"
                >
                  Password
                </label>

                <div className="relative">
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    required
                    maxLength={128}
                    placeholder="Enter your password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    disabled={loading}
                    className="input-field pr-16"
                  />

                  <button
                    type="button"
                    onClick={() => setShowPassword((current) => !current)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    className="absolute inset-y-0 right-2 my-auto h-8 px-2.5 text-xs font-semibold text-[#806777] hover:text-[#9F1239] transition-colors"
                  >
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>
              </div>

              {error && (
                <div
                  role="alert"
                  aria-live="polite"
                  className="rounded-xl p-3.5 text-xs leading-5 badge-danger animate-fade-in"
                >
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full !py-3.5 !text-sm font-bold tracking-wide"
              >
                {loading ? (
                  <>
                    <svg
                      className="h-4 w-4 animate-spin text-white"
                      viewBox="0 0 24 24"
                      fill="none"
                      aria-hidden="true"
                    >
                      <circle
                        cx="12"
                        cy="12"
                        r="9"
                        stroke="currentColor"
                        strokeWidth="3"
                        className="opacity-25"
                      />
                      <path
                        d="M21 12a9 9 0 0 0-9-9"
                        stroke="currentColor"
                        strokeWidth="3"
                        strokeLinecap="round"
                      />
                    </svg>
                    <span>Authenticating credentials...</span>
                  </>
                ) : (
                  <>
                    <span>Sign In Securely</span>
                    <svg
                      viewBox="0 0 20 20"
                      fill="currentColor"
                      className="h-4 w-4"
                      aria-hidden="true"
                    >
                      <path
                        fillRule="evenodd"
                        d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </>
                )}
              </button>
            </form>

            <div className="divider my-7" />

            {/* Registration Pathways */}
            <div>
              <p className="text-center text-xs font-semibold text-[#806777]">
                New user? Register an account
              </p>
              <div className="mt-3 grid grid-cols-3 gap-2">
                <Link
                  href="/register/student"
                  className="rounded-xl px-2 py-2.5 text-center text-xs font-bold transition-all bg-[#FFF7FA] border border-[#F0DCE5] text-[#3F1024] hover:bg-[#FBEAF0] hover:text-[#9F1239]"
                >
                  Student
                </Link>
                <Link
                  href="/register/faculty"
                  className="rounded-xl px-2 py-2.5 text-center text-xs font-bold transition-all bg-[#FFF7FA] border border-[#F0DCE5] text-[#3F1024] hover:bg-[#FBEAF0] hover:text-[#9F1239]"
                >
                  Faculty
                </Link>
                <Link
                  href="/register/admin"
                  className="rounded-xl px-2 py-2.5 text-center text-xs font-bold transition-all bg-[#FFF7FA] border border-[#F0DCE5] text-[#3F1024] hover:bg-[#FBEAF0] hover:text-[#9F1239]"
                >
                  Admin
                </Link>
              </div>
            </div>

            <p className="mt-7 text-center text-[11px] text-[#A38C9B]">
              LabOS · End-to-End Cryptographically Secured University Platform
            </p>
          </section>
        </div>
      </div>
    </main>
  );
}