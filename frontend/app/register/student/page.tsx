"use client";

import { FormEvent, useState, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api/client";
import { registerUser } from "@/lib/api/auth";
import { PROGRAM_OPTIONS } from "@/lib/academic-options";

// Year → valid semesters mapping for a 4-year BTech program
const YEAR_SEMESTER_MAP: Record<string, string[]> = {
  "1st Year": ["Semester 1", "Semester 2"],
  "2nd Year": ["Semester 3", "Semester 4"],
  "3rd Year": ["Semester 5", "Semester 6"],
  "4th Year": ["Semester 7", "Semester 8"],
};

const YEAR_OPTIONS = Object.keys(YEAR_SEMESTER_MAP);

export default function StudentRegistrationPage() {
  const router = useRouter();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [enrollmentNumber, setEnrollmentNumber] = useState("");
  const [academicCourse, setAcademicCourse] = useState<string>(
    PROGRAM_OPTIONS[2] || "B.Tech (AI & DS)",
  );
  const [yearOfStudy, setYearOfStudy] = useState("1st Year");
  const [semester, setSemester] = useState("Semester 1");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Dynamically compute valid semester options when year changes
  const semesterOptions = useMemo(() => {
    return YEAR_SEMESTER_MAP[yearOfStudy] ?? ["Semester 1"];
  }, [yearOfStudy]);

  const handleYearChange = (newYear: string) => {
    setYearOfStudy(newYear);
    // Auto-select first valid semester for that year
    const firstSemester = (YEAR_SEMESTER_MAP[newYear] ?? ["Semester 1"])[0];
    setSemester(firstSemester);
  };

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setError("");
    setSuccess("");

    const normalizedEnrollment = enrollmentNumber.trim().toUpperCase();

    if (!/^[A-Z]{3}[0-9]{7}$/.test(normalizedEnrollment)) {
      setError(
        "Enter a valid enrollment number with three letters followed by seven digits (e.g. MUR2502214).",
      );
      return;
    }

    if (!academicCourse.trim()) {
      setError("Please select your academic program.");
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
      await registerUser({
        name: name.trim(),
        email: email.trim(),
        enrollment_number: normalizedEnrollment,
        academic_course: academicCourse.trim(),
        year_of_study: yearOfStudy,
        semester: semester,
        password,
      });

      setSuccess(
        "Your student account has been created successfully! Redirecting to login...",
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
    <main
      className="relative flex min-h-screen flex-1 items-center justify-center overflow-hidden px-4 py-12 sm:px-6"
      style={{ backgroundColor: "var(--color-background)" }}
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 overflow-hidden"
      >
        <div className="absolute -left-36 -top-36 h-[32rem] w-[32rem] rounded-full bg-[#FBEAF0] opacity-80 blur-[100px]" />
        <div className="absolute -bottom-36 -right-36 h-[34rem] w-[34rem] rounded-full bg-[#FFF0F5] opacity-90 blur-[120px]" />
      </div>

      <section className="relative z-10 w-full max-w-2xl lux-card p-6 shadow-xl sm:p-10 border border-[#F0DCE5]">
        <div className="flex items-center justify-between">
          <Link
            href="/login"
            className="inline-flex items-center gap-2 text-xs font-semibold text-[#806777] hover:text-[#9F1239] transition-colors"
          >
            ← Back to sign in
          </Link>

          {/* Role switcher pills */}
          <div className="flex gap-1.5 rounded-xl p-1 bg-[#FFF7FA] border border-[#F0DCE5]">
            <span
              className="rounded-lg px-2.5 py-1 text-xs font-bold text-white shadow-xs"
              style={{ background: "var(--primary-gradient)" }}
            >
              Student
            </span>
            <Link
              href="/register/faculty"
              className="rounded-lg px-2.5 py-1 text-xs font-semibold text-[#806777] hover:text-[#9F1239] transition-colors"
            >
              Faculty
            </Link>
            <Link
              href="/register/admin"
              className="rounded-lg px-2.5 py-1 text-xs font-semibold text-[#806777] hover:text-[#9F1239] transition-colors"
            >
              Admin
            </Link>
          </div>
        </div>

        <div className="mt-8">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#BE5678]">
            New Student Enrollment
          </p>
          <h1 className="mt-1 text-2xl font-extrabold text-[#3F1024] sm:text-3xl">
            Create Student Account
          </h1>
          <p className="mt-2 text-sm text-[#806777]">
            Register with your university-assigned enrollment number to automatically enroll in your
            practical courses.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="name"
                className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#3F1024]"
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
                placeholder="e.g. Jane Doe"
                className="input-field"
              />
            </div>

            <div>
              <label
                htmlFor="email"
                className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#3F1024]"
              >
                Email Address
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
                placeholder="you@university.edu"
                className="input-field"
              />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="enrollmentNumber"
                className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#3F1024]"
              >
                Enrollment Number
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
                title="Enter 3 letters followed by 7 digits (e.g. MUR2502214)."
                value={enrollmentNumber}
                onChange={(event) =>
                  setEnrollmentNumber(event.target.value.toUpperCase())
                }
                disabled={loading}
                placeholder="e.g. MUR2502214"
                className="input-field font-mono"
              />
            </div>

            <div>
              <label
                htmlFor="academicCourse"
                className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#3F1024]"
              >
                Academic Program
              </label>
              <select
                id="academicCourse"
                name="academic_course"
                required
                value={academicCourse}
                onChange={(event) => setAcademicCourse(event.target.value)}
                disabled={loading}
                className="input-field"
              >
                {PROGRAM_OPTIONS.map((prog) => (
                  <option key={prog} value={prog} className="bg-white text-[#3F1024]">
                    {prog}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Year and Semester row */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="yearOfStudy"
                className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#3F1024]"
              >
                Year of Study
              </label>
              <select
                id="yearOfStudy"
                name="year_of_study"
                required
                value={yearOfStudy}
                onChange={(event) => handleYearChange(event.target.value)}
                disabled={loading}
                className="input-field"
              >
                {YEAR_OPTIONS.map((yr) => (
                  <option key={yr} value={yr} className="bg-white text-[#3F1024]">
                    {yr}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label
                htmlFor="semester"
                className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#3F1024]"
              >
                Current Semester
              </label>
              <select
                id="semester"
                name="semester"
                required
                value={semester}
                onChange={(event) => setSemester(event.target.value)}
                disabled={loading}
                className="input-field"
              >
                {semesterOptions.map((sem) => (
                  <option key={sem} value={sem} className="bg-white text-[#3F1024]">
                    {sem}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="password"
                className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#3F1024]"
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
                  className="input-field pr-16"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((current) => !current)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute inset-y-0 right-2 my-auto h-8 px-2 text-xs font-semibold text-[#806777] hover:text-[#9F1239]"
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </div>

            <div>
              <label
                htmlFor="confirmPassword"
                className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#3F1024]"
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
              className="rounded-xl p-3.5 text-xs leading-5 badge-danger animate-fade-in"
            >
              {error}
            </div>
          )}

          {success && (
            <div
              role="status"
              aria-live="polite"
              className="rounded-xl p-3.5 text-xs leading-5 badge-success animate-fade-in"
            >
              {success}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full !py-3.5 !text-sm mt-3 font-bold tracking-wide"
          >
            {loading ? "Registering student account..." : "Complete Student Registration"}
          </button>
        </form>

        <p className="mt-7 text-center text-xs text-[#806777]">
          Already enrolled?{" "}
          <Link href="/login" className="font-bold text-[#9F1239] hover:underline">
            Sign in here
          </Link>
        </p>
      </section>
    </main>
  );
}