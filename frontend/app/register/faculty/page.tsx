"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, AlertCircle, CheckCircle2, ArrowRight } from "lucide-react";
import { CredLabLogo } from "@/components/CredLabLogo";
import { ApiError } from "@/lib/api/client";
import { registerFaculty } from "@/lib/api/auth";

export default function FacultyRegistrationPage() {
  const router = useRouter();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [enrollmentNumber, setEnrollmentNumber] = useState("");
  const [subjectsInput, setSubjectsInput] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setError("");
    setSuccess("");

    const normalizedEnrollment = enrollmentNumber.trim().toUpperCase();

    if (!/^[A-Z]{3}[0-9]{7}$/.test(normalizedEnrollment)) {
      setError("Enter a valid authorized employee number (e.g. EMP0000001).");
      return;
    }

    const teachingSubjects = [
      ...new Set(
        subjectsInput
          .split(",")
          .map((subject) => subject.trim())
          .filter(Boolean),
      ),
    ];

    if (teachingSubjects.length === 0) {
      setError("Enter at least one teaching subject (e.g. Data Structures, Algorithms).");
      return;
    }

    if (teachingSubjects.length > 20) {
      setError("Enter no more than 20 teaching subjects.");
      return;
    }

    if (password.length < 8) {
      setError("Your password must contain at least 8 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setError("The passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      await registerFaculty({
        name: name.trim(),
        email: email.trim(),
        enrollment_number: normalizedEnrollment,
        teaching_subjects: teachingSubjects,
        password,
      });

      setSuccess(
        "Your faculty account has been created successfully! Redirecting to login...",
      );

      window.setTimeout(() => {
        router.replace("/login");
      }, 1200);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(
          "Unable to connect to the server. Please verify the backend is running.",
        );
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="relative flex min-h-screen flex-1 items-center justify-center overflow-hidden px-4 py-8 sm:px-6 sm:py-14 bg-[#101010] text-[#F7F4EF]">
      {/* Top Navigation */}
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

      <section className="relative z-10 w-full max-w-2xl rounded-3xl border border-[#353535] bg-[#1B1B1B] p-6 shadow-2xl sm:p-10 mt-14 sm:mt-10">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <Link
            href="/login"
            className="inline-flex items-center gap-2 text-xs font-semibold text-[#A5A29C] hover:text-[#FF6B2C] transition-colors"
          >
            ← Back to sign in
          </Link>

          {/* Role Switcher Pills */}
          <div className="flex gap-1 rounded-xl p-1 bg-[#222222] border border-[#353535]">
            <Link
              href="/register/student"
              className="rounded-lg px-2.5 py-1 text-xs font-semibold text-[#A5A29C] hover:text-[#F7F4EF] transition-colors"
            >
              Student
            </Link>
            <span className="rounded-lg px-2.5 py-1 text-xs font-bold text-white bg-[#FF6B2C] shadow-xs">
              Faculty
            </span>
            <Link
              href="/register/admin"
              className="rounded-lg px-2.5 py-1 text-xs font-semibold text-[#A5A29C] hover:text-[#F7F4EF] transition-colors"
            >
              Admin
            </Link>
          </div>
        </div>

        <div className="mt-8">
          <p className="text-xs font-mono font-bold uppercase tracking-widest text-[#FF8A3D]">
            Faculty Onboarding
          </p>
          <h1 className="mt-1 text-2xl font-extrabold sm:text-3xl tracking-tight text-[#F7F4EF]">
            Register Faculty Account
          </h1>
          <p className="mt-2 text-xs sm:text-sm text-[#A5A29C]">
            Register with your institutional EMP number to manage courses, laboratory practicals, and grade approvals.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="name"
                className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#F7F4EF]"
              >
                Full Name
              </label>
              <input
                id="name"
                name="name"
                type="text"
                autoComplete="name"
                required
                maxLength={100}
                value={name}
                onChange={(event) => setName(event.target.value)}
                disabled={loading}
                placeholder="e.g. Dr. Alan Turing"
                className="input-field"
              />
            </div>

            <div>
              <label
                htmlFor="email"
                className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#F7F4EF]"
              >
                Institutional Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                maxLength={254}
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                disabled={loading}
                placeholder="faculty@university.edu"
                className="input-field"
              />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="enrollmentNumber"
                className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#F7F4EF]"
              >
                Authorized Employee ID
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
                pattern="[A-Za-z]{3}[0-9]{7}"
                title="Enter three letters followed by seven digits (e.g. EMP0000001)."
                value={enrollmentNumber}
                onChange={(event) =>
                  setEnrollmentNumber(event.target.value.toUpperCase())
                }
                disabled={loading}
                placeholder="e.g. EMP0000001"
                className="input-field font-mono"
              />
            </div>

            <div>
              <label
                htmlFor="subjects"
                className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#F7F4EF]"
              >
                Teaching Subjects (comma separated)
              </label>
              <input
                id="subjects"
                name="teaching_subjects"
                type="text"
                required
                value={subjectsInput}
                onChange={(event) => setSubjectsInput(event.target.value)}
                disabled={loading}
                placeholder="e.g. Data Structures, AI, Python"
                className="input-field"
              />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="password"
                className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#F7F4EF]"
              >
                Password (min 8 chars)
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="new-password"
                  required
                  minLength={8}
                  maxLength={128}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  disabled={loading}
                  placeholder="Create password"
                  className="input-field pr-12"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((current) => !current)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute inset-y-0 right-2 my-auto h-8 px-2 text-[#A5A29C] hover:text-[#FF6B2C] flex items-center justify-center"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div>
              <label
                htmlFor="confirmPassword"
                className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#F7F4EF]"
              >
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                name="confirm_password"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                required
                minLength={8}
                maxLength={128}
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                disabled={loading}
                placeholder="Confirm password"
                className="input-field"
              />
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

          {success && (
            <div
              role="status"
              aria-live="polite"
              className="rounded-xl p-3 text-xs leading-relaxed badge-success animate-fade-in flex items-start gap-2"
            >
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-[#34D399]" />
              <span>{success}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full !py-3.5 !text-sm mt-3 font-bold tracking-wide flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                <span>Registering faculty account...</span>
              </>
            ) : (
              <>
                <span>Complete Faculty Registration</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <p className="mt-7 text-center text-xs text-[#A5A29C]">
          Already have a faculty account?{" "}
          <Link href="/login" className="font-bold text-[#FF6B2C] hover:underline">
            Sign in here
          </Link>
        </p>
      </section>
    </main>
  );
}