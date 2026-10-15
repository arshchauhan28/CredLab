"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Lock,
  ArrowRight,
  GraduationCap,
  Users,
  Eye,
  EyeOff,
  AlertCircle,
} from "lucide-react";
import { CredLabLogo } from "@/components/CredLabLogo";

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
    <main className="relative flex min-h-screen flex-1 items-center justify-center overflow-hidden px-4 py-8 sm:px-6 sm:py-14 bg-[#101010] text-[#F7F4EF]">
      {/* Top Navigation Bar with Logo */}
      <header className="absolute top-0 left-0 right-0 p-4 sm:p-6 flex items-center justify-between max-w-7xl mx-auto z-20">
        <Link href="/" aria-label="CredLab Home">
          <CredLabLogo size="sm" showWordmark={true} />
        </Link>
      </header>

      {/* Ambient Lighting Gradients */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute top-1/4 left-1/4 h-[30rem] w-[30rem] rounded-full bg-[#FF6B2C]/10 blur-[130px]" />
        <div className="absolute bottom-1/4 right-1/4 h-[28rem] w-[28rem] rounded-full bg-[#FFB547]/8 blur-[120px]" />
      </div>

      <div className="relative z-10 w-full max-w-5xl overflow-hidden rounded-3xl border border-[#353535] bg-[#1B1B1B] shadow-2xl mt-12 sm:mt-8">
        <div className="grid lg:grid-cols-12">
          {/* Left Panel: Information & Brand Context */}
          <section className="hidden lg:flex lg:col-span-6 flex-col justify-between p-10 xl:p-14 bg-[#141414] border-b lg:border-b-0 lg:border-r border-[#292929]">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-[#FF6B2C]/25 bg-[#FF6B2C]/10 px-3.5 py-1.5 text-xs font-mono font-semibold text-[#FF8A3D]">
                <span className="h-2 w-2 rounded-full bg-[#FF6B2C] animate-pulse" />
                Institutional Terminal Access
              </div>

              <h1 className="mt-8 text-3xl font-extrabold leading-tight tracking-tight text-[#F7F4EF] xl:text-4xl">
                Continuous Assessment &{" "}
                <span className="bg-gradient-to-r from-[#FF6B2C] to-[#FFB547] bg-clip-text text-transparent">
                  Verified Skills
                </span>
              </h1>

              <p className="mt-4 text-sm leading-relaxed text-[#A5A29C]">
                Deterministic sandbox grading, sequential practical progress, and cryptographic Ed25519 digital diplomas.
              </p>
            </div>

            {/* Credential Format Guides */}
            <div className="mt-10 space-y-3 font-mono text-xs">
              <div className="flex items-center gap-3.5 rounded-2xl p-3.5 bg-[#161616] border border-[#292929]">
                <div className="p-2 rounded-xl bg-[#FF6B2C]/10 text-[#FF6B2C]">
                  <GraduationCap className="w-4 h-4" />
                </div>
                <div>
                  <p className="font-bold text-[#F7F4EF]">Student Account ID</p>
                  <p className="text-[11px] text-[#A5A29C]">
                    Pattern: <code className="font-semibold text-[#FF8A3D]">MUR2502214</code>
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3.5 rounded-2xl p-3.5 bg-[#161616] border border-[#292929]">
                <div className="p-2 rounded-xl bg-[#FFB547]/10 text-[#FFB547]">
                  <Users className="w-4 h-4" />
                </div>
                <div>
                  <p className="font-bold text-[#F7F4EF]">Faculty & Administrator ID</p>
                  <p className="text-[11px] text-[#A5A29C]">
                    Pattern: <code className="font-semibold text-[#FF8A3D]">EMP0000001</code>
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Right Panel: Sign In Form */}
          <section className="lg:col-span-6 flex flex-col justify-center p-7 sm:p-10 lg:p-12 xl:p-14 bg-[#1B1B1B]">
            <div className="mb-8 flex items-center justify-between">
              <div>
                <p className="text-xs font-mono font-bold uppercase tracking-widest text-[#FF8A3D]">
                  Secure Authentication
                </p>
                <h2 className="mt-1 text-2xl font-extrabold sm:text-3xl tracking-tight text-[#F7F4EF]">
                  Sign In
                </h2>
              </div>
              <Link
                href="/"
                className="text-xs font-semibold text-[#A5A29C] hover:text-[#FF6B2C] transition-colors"
              >
                ← Back home
              </Link>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label
                  htmlFor="enrollmentNumber"
                  className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#F7F4EF]"
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
                  className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#F7F4EF]"
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
                    className="input-field pr-12"
                  />

                  <button
                    type="button"
                    onClick={() => setShowPassword((current) => !current)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    className="absolute inset-y-0 right-2 my-auto h-8 px-2.5 text-[#A5A29C] hover:text-[#FF6B2C] transition-colors flex items-center justify-center"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {error && (
                <div
                  role="alert"
                  aria-live="polite"
                  className="rounded-xl p-3 text-xs leading-relaxed badge-danger animate-fade-in flex items-start gap-2"
                >
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-[#EF4444]" />
                  <span>{error}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full !py-3.5 !text-sm font-bold tracking-wide flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                    <span>Verifying session...</span>
                  </>
                ) : (
                  <>
                    <Lock className="w-4 h-4" />
                    <span>Sign In to CredLab</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            <div className="divider my-7" />

            {/* Registration Links */}
            <div>
              <p className="text-center text-xs font-semibold text-[#A5A29C]">
                New to the platform? Create an account
              </p>
              <div className="mt-3 grid grid-cols-3 gap-2">
                <Link
                  href="/register/student"
                  className="rounded-xl px-2 py-2.5 text-center text-xs font-bold transition-all bg-[#202020] border border-[#353535] text-[#F7F4EF] hover:border-[#FF6B2C] hover:text-[#FF6B2C]"
                >
                  Student
                </Link>
                <Link
                  href="/register/faculty"
                  className="rounded-xl px-2 py-2.5 text-center text-xs font-bold transition-all bg-[#202020] border border-[#353535] text-[#F7F4EF] hover:border-[#FF6B2C] hover:text-[#FF6B2C]"
                >
                  Faculty
                </Link>
                <Link
                  href="/register/admin"
                  className="rounded-xl px-2 py-2.5 text-center text-xs font-bold transition-all bg-[#202020] border border-[#353535] text-[#F7F4EF] hover:border-[#FF6B2C] hover:text-[#FF6B2C]"
                >
                  Admin
                </Link>
              </div>
            </div>

            <p className="mt-6 text-center text-[11px] font-mono text-[#77736D]">
              CredLab · Cryptographically Secured University Platform
            </p>
          </section>
        </div>
      </div>
    </main>
  );
}