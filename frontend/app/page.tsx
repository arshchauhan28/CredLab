"use client";

import React, { useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import {
  Code2,
  ShieldCheck,
  Award,
  Terminal,
  Cpu,
  Layers,
  ChevronRight,
  Menu,
  X,
  CheckCircle2,
  ArrowRight,
  GraduationCap,
  Users,
  Settings,
  Sparkles,
  Lock,
} from "lucide-react";
import { CredLabLogo } from "@/components/CredLabLogo";

// Dynamically load the 3D Hero scene with SSR disabled for optimal performance
const CredLabHero3D = dynamic(() => import("@/components/3d/CredLabHero3D"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center w-full h-[400px]">
      <div className="w-12 h-12 rounded-full border-2 border-[#FF6B2C] border-t-transparent animate-spin" />
    </div>
  ),
});

const features = [
  {
    icon: <Cpu className="w-5 h-5 text-[#FF6B2C]" />,
    title: "Curated University Laboratories",
    description:
      "Structured practical curriculums tied directly to academic programs, year of study, semester cohorts, and automated sandbox runners.",
    badge: "Curriculum Precision",
  },
  {
    icon: <Terminal className="w-5 h-5 text-[#FFB547]" />,
    title: "Deterministic Sandbox Execution",
    description:
      "Run authoritative unit tests on student submissions with instant feedback, time & memory limit constraints, and compiler diagnostics.",
    badge: "Low-Latency Grading",
  },
  {
    icon: <ShieldCheck className="w-5 h-5 text-[#FF6B2C]" />,
    title: "Anti-Tamper & Sequential Progression",
    description:
      "Enforce sequential practical unlocking, editor telemetry monitoring, and server-side execution boundaries to ensure authentic learning.",
    badge: "Academic Integrity",
  },
  {
    icon: <Award className="w-5 h-5 text-[#FFB547]" />,
    title: "Cryptographic Milestone Diplomas",
    description:
      "Ed25519 digitally signed diplomas issued upon laboratory completion, featuring public key verification and tamper-evident digests.",
    badge: "Verifiable Proof",
  },
  {
    icon: <Layers className="w-5 h-5 text-[#FF6B2C]" />,
    title: "Automated Academic Enrollment",
    description:
      "Students completing their profile are automatically enrolled in matching departmental courses with zero administrative bottleneck.",
    badge: "Smart Onboarding",
  },
  {
    icon: <Code2 className="w-5 h-5 text-[#FFB547]" />,
    title: "Multi-Language Monaco Workspace",
    description:
      "Industry-standard browser editor with full syntax highlighting, bracket matching, and standard I/O execution for Python, C, C++, and Java.",
    badge: "Developer Experience",
  },
];

const workflows = [
  {
    id: "students",
    role: "Students",
    icon: <GraduationCap className="w-5 h-5" />,
    badge: "Interactive Assessment",
    headline: "Write clean code, conquer challenges, earn credentials",
    description:
      "Access enrolled department courses, solve real programming challenges in the Monaco editor, test solutions against visible test suites, and receive cryptographic proof of your technical ability.",
    points: [
      "Sequential practical unlocks preventing skipping fundamentals",
      "Immediate execution feedback with standard I/O and custom input",
      "Focus tracking & editor integrity telemetry",
      "Personal portfolio of Ed25519 signed diplomas",
    ],
    ctaText: "Register as Student",
    ctaLink: "/register/student",
  },
  {
    id: "faculty",
    role: "Faculty Instructors",
    icon: <Users className="w-5 h-5" />,
    badge: "Curriculum Management",
    headline: "Design robust labs, evaluate submissions, approve diplomas",
    description:
      "Create university subjects, author structured lab exercises, define visible and hidden test cases, inspect student submission analytics, and approve verifiable completion certificates with one click.",
    points: [
      "Custom test suite authoring with precision time & memory limits",
      "Live student submission logs, execution times, and pass rates",
      "Safe practical archiving protecting historical student evaluations",
      "One-click Ed25519 cryptographic certificate endorsement",
    ],
    ctaText: "Register as Faculty",
    ctaLink: "/register/faculty",
  },
  {
    id: "admins",
    role: "Administrators",
    icon: <Settings className="w-5 h-5" />,
    badge: "Institutional Governance",
    headline: "Oversee academic integrity, courses, and account approvals",
    description:
      "Manage academic programs, oversee faculty course allocations, review and approve faculty registrations, and monitor institutional assessment logs.",
    points: [
      "Strict role-based governance with SUPER_ADMIN account vetting",
      "Safe course deletion with dependency checking and archival rules",
      "Automated cohort auto-enrollment across academic years",
      "Audit logs for cryptographic certificate verification",
    ],
    ctaText: "Admin Portal",
    ctaLink: "/login",
  },
];

const stats = [
  { value: "100%", label: "Server-Verified Grading", sub: "Deterministic Sandboxes" },
  { value: "Ed25519", label: "Cryptographic Signing", sub: "Tamper-Proof Diplomas" },
  { value: "4+", label: "Supported Languages", sub: "Python, C, C++, Java" },
  { value: "< 250ms", label: "Sandbox Latency", sub: "Isolated Subprocess Worker" },
];

const steps = [
  {
    number: "01",
    title: "Access Practical",
    description: "Open active course laboratories structured according to your university syllabus.",
  },
  {
    number: "02",
    title: "Code in Secure IDE",
    description: "Implement your solution in the browser Monaco editor with standard I/O support.",
  },
  {
    number: "03",
    title: "Execute Test Cases",
    description: "Run code against authoritative test suites with instant time and memory analytics.",
  },
  {
    number: "04",
    title: "Submit with Integrity",
    description: "Submit for server evaluation with sequential unlocking and telemetry recording.",
  },
  {
    number: "05",
    title: "Earn Credibility",
    description: "Receive cryptographic milestone certificates verifiable by universities and employers.",
  },
];

export default function LandingPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeRole, setActiveRole] = useState(workflows[0].id);

  const selectedWorkflow = workflows.find((w) => w.id === activeRole) || workflows[0];

  return (
    <div className="min-h-screen bg-[#F5F0E7] dark:bg-[#101010] text-[#191919] dark:text-[#F7F4EF] transition-colors duration-200">
      {/* ────── Academic Session Ticker ────── */}
      <aside
        aria-label="Academic Session Ticker"
        className="bg-[#191919] dark:bg-[#171717] text-[#F7F4EF] text-xs py-2 px-4 text-center font-mono border-b border-[#E4DDD2]/40 dark:border-[#2D2D2D]"
      >
        <div className="mx-auto max-w-7xl flex items-center justify-center gap-2">
          <span className="h-2 w-2 rounded-full bg-[#FF6B2C] animate-pulse" />
          <span>
            CredLab Academic Session 2026–2027 · High-Integrity Coding Assessment Platform Active
          </span>
        </div>
      </aside>

      {/* ────── Header & Global Navigation ────── */}
      <header className="sticky top-0 z-40 border-b border-[#E4DDD2] dark:border-[#262626] bg-[#F5F0E7]/90 dark:bg-[#101010]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 sm:px-8 py-3.5">
          <Link href="/" className="group" aria-label="CredLab Home">
            <CredLabLogo size="md" showWordmark={true} showTagline={true} />
          </Link>

          {/* Desktop Navigation Links */}
          <nav aria-label="Main Navigation" className="hidden md:flex items-center gap-6 text-sm font-medium">
            <a
              href="#features"
              className="text-[#706C65] dark:text-[#A5A29C] hover:text-[#D94F16] dark:hover:text-[#FF6B2C] transition-colors"
            >
              Capabilities
            </a>
            <a
              href="#how-it-works"
              className="text-[#706C65] dark:text-[#A5A29C] hover:text-[#D94F16] dark:hover:text-[#FF6B2C] transition-colors"
            >
              How It Works
            </a>
            <a
              href="#roles"
              className="text-[#706C65] dark:text-[#A5A29C] hover:text-[#D94F16] dark:hover:text-[#FF6B2C] transition-colors"
            >
              Roles
            </a>
            <a
              href="#verification"
              className="text-[#706C65] dark:text-[#A5A29C] hover:text-[#D94F16] dark:hover:text-[#FF6B2C] transition-colors"
            >
              Verification
            </a>
          </nav>

          {/* Desktop Actions */}
          <div className="hidden md:flex items-center gap-3">
            <Link
              href="/login"
              className="px-4 py-2 text-xs font-semibold rounded-xl text-[#F7F4EF] hover:bg-[#222222] border border-[#353535] transition-colors"
            >
              Sign In
            </Link>
            <Link
              href="/register/student"
              className="btn-primary text-xs !py-2 !px-4"
            >
              Get Started
            </Link>
          </div>

          {/* Mobile Menu Toggle */}
          <div className="flex items-center gap-2 md:hidden">
            <button
              type="button"
              onClick={() => setMobileMenuOpen((prev) => !prev)}
              aria-label="Toggle menu"
              className="p-2 rounded-xl text-[#F7F4EF] hover:bg-[#222222]"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-[#E4DDD2] dark:border-[#2D2D2D] bg-[#FFFCF6] dark:bg-[#161616] px-5 py-4 space-y-3 animate-slide-down">
            <nav className="flex flex-col gap-2.5 text-sm font-medium">
              <a
                href="#features"
                onClick={() => setMobileMenuOpen(false)}
                className="py-1.5 text-[#706C65] dark:text-[#A5A29C] hover:text-[#FF6B2C]"
              >
                Capabilities
              </a>
              <a
                href="#how-it-works"
                onClick={() => setMobileMenuOpen(false)}
                className="py-1.5 text-[#706C65] dark:text-[#A5A29C] hover:text-[#FF6B2C]"
              >
                How It Works
              </a>
              <a
                href="#roles"
                onClick={() => setMobileMenuOpen(false)}
                className="py-1.5 text-[#706C65] dark:text-[#A5A29C] hover:text-[#FF6B2C]"
              >
                Roles & Workflows
              </a>
              <a
                href="#verification"
                onClick={() => setMobileMenuOpen(false)}
                className="py-1.5 text-[#706C65] dark:text-[#A5A29C] hover:text-[#FF6B2C]"
              >
                Diploma Verification
              </a>
            </nav>
            <div className="pt-3 border-t border-[#E4DDD2] dark:border-[#2D2D2D] flex flex-col gap-2">
              <Link
                href="/login"
                onClick={() => setMobileMenuOpen(false)}
                className="w-full text-center py-2.5 text-xs font-semibold rounded-xl border border-[#E4DDD2] dark:border-[#353535]"
              >
                Sign In
              </Link>
              <Link
                href="/register/student"
                onClick={() => setMobileMenuOpen(false)}
                className="btn-primary w-full text-center text-xs !py-2.5"
              >
                Get Started
              </Link>
            </div>
          </div>
        )}
      </header>

      {/* ────── Section B: Hero Section ────── */}
      <section className="relative overflow-hidden pt-8 pb-16 sm:pt-14 sm:pb-24 border-b border-[#E4DDD2] dark:border-[#242424]">
        {/* Subtle Background Accent Lighting */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-gradient-to-tr from-[#FF6B2C]/10 via-[#FFB547]/5 to-transparent blur-3xl pointer-events-none rounded-full" />

        <div className="mx-auto max-w-7xl px-4 sm:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
            {/* Left Column: Headline and Positioning */}
            <div className="lg:col-span-7 flex flex-col items-start space-y-6 z-10">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#FF6B2C]/10 border border-[#FF6B2C]/20 text-xs font-mono font-semibold text-[#D94F16] dark:text-[#FF8533]">
                <Sparkles className="w-3.5 h-3.5 text-[#FF6B2C]" />
                <span>Next-Gen Secure Practical Assessment</span>
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight leading-[1.1]">
                Build skills. <br />
                Prove knowledge. <br />
                <span className="bg-gradient-to-r from-[#FF6B2C] via-[#FF8533] to-[#FFB547] bg-clip-text text-transparent">
                  Earn credibility.
                </span>
              </h1>

              <p className="text-base sm:text-lg text-[#706C65] dark:text-[#A5A29C] max-w-2xl leading-relaxed">
                One unified platform for university coding laboratories, deterministic sandbox assessments,
                and tamper-evident cryptographic proof of technical ability.
              </p>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center gap-3 pt-2">
                <Link
                  href="/login"
                  className="btn-primary !px-6 !py-3 text-sm font-semibold flex items-center gap-2"
                >
                  <span>Enter CredLab</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>

                <a
                  href="#how-it-works"
                  className="btn-secondary !px-5 !py-3 text-sm font-semibold"
                >
                  Explore Platform
                </a>
              </div>

              {/* Quick Role Links */}
              <div className="pt-4 flex flex-wrap items-center gap-4 text-xs font-mono text-[#706C65] dark:text-[#A5A29C]">
                <span>Register as:</span>
                <Link
                  href="/register/student"
                  className="text-[#D94F16] dark:text-[#FF8533] hover:underline flex items-center gap-1 font-semibold"
                >
                  <span>Student</span>
                  <ChevronRight className="w-3 h-3" />
                </Link>
                <span className="text-[#E4DDD2] dark:text-[#333333]">|</span>
                <Link
                  href="/register/faculty"
                  className="text-[#D94F16] dark:text-[#FF8533] hover:underline flex items-center gap-1 font-semibold"
                >
                  <span>Faculty</span>
                  <ChevronRight className="w-3 h-3" />
                </Link>
                <span className="text-[#E4DDD2] dark:text-[#333333]">|</span>
                <Link
                  href="/register/admin"
                  className="text-[#D94F16] dark:text-[#FF8533] hover:underline flex items-center gap-1 font-semibold"
                >
                  <span>Admin</span>
                  <ChevronRight className="w-3 h-3" />
                </Link>
              </div>

              {/* Feature Pills */}
              <div className="grid grid-cols-2 sm:grid-cols-2 gap-3 pt-4 w-full max-w-xl">
                <div className="flex items-center gap-2 text-xs font-medium text-[#706C65] dark:text-[#A5A29C]">
                  <CheckCircle2 className="w-4 h-4 text-[#FF6B2C] shrink-0" />
                  <span>Sequential Practical Unlocks</span>
                </div>
                <div className="flex items-center gap-2 text-xs font-medium text-[#706C65] dark:text-[#A5A29C]">
                  <CheckCircle2 className="w-4 h-4 text-[#FF6B2C] shrink-0" />
                  <span>Ed25519 Signed Diplomas</span>
                </div>
                <div className="flex items-center gap-2 text-xs font-medium text-[#706C65] dark:text-[#A5A29C]">
                  <CheckCircle2 className="w-4 h-4 text-[#FF6B2C] shrink-0" />
                  <span>Subprocess Sandbox Defense</span>
                </div>
                <div className="flex items-center gap-2 text-xs font-medium text-[#706C65] dark:text-[#A5A29C]">
                  <CheckCircle2 className="w-4 h-4 text-[#FF6B2C] shrink-0" />
                  <span>Zero-Setup In-Browser IDE</span>
                </div>
              </div>
            </div>

            {/* Right Column: 3D Code-Verification Centerpiece */}
            <div className="lg:col-span-5 flex items-center justify-center relative">
              <CredLabHero3D />
            </div>
          </div>
        </div>
      </section>

      {/* ────── Stats Band ────── */}
      <section className="border-b border-[#E4DDD2] dark:border-[#242424] bg-[#EEE8DE]/50 dark:bg-[#141414]/60 py-8">
        <div className="mx-auto max-w-7xl px-4 sm:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
            {stats.map((s) => (
              <div key={s.label} className="flex flex-col items-center">
                <span className="text-2xl sm:text-3xl font-extrabold text-[#D94F16] dark:text-[#FF6B2C] font-mono">
                  {s.value}
                </span>
                <span className="text-xs sm:text-sm font-semibold text-[#191919] dark:text-[#F7F4EF] mt-1">
                  {s.label}
                </span>
                <span className="text-[11px] text-[#706C65] dark:text-[#A5A29C]">
                  {s.sub}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ────── Section C: Product Preview ────── */}
      <section className="py-16 sm:py-24 border-b border-[#E4DDD2] dark:border-[#242424]">
        <div className="mx-auto max-w-7xl px-4 sm:px-8">
          <div className="text-center max-w-3xl mx-auto mb-12">
            <span className="text-xs font-mono uppercase tracking-widest text-[#D94F16] dark:text-[#FF8533] font-bold">
              Authentic Workspace
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight mt-2">
              Engineered for Real Coding, Not Simple Multiple-Choice
            </h2>
            <p className="text-sm sm:text-base text-[#706C65] dark:text-[#A5A29C] mt-3">
              CredLab provides an authentic developer environment with Monaco code editing, standard input/output execution, and strict sequential unlocking.
            </p>
          </div>

          {/* Realistic Platform Preview Mockup */}
          <div className="rounded-2xl border border-[#E4DDD2] dark:border-[#353535] bg-[#FFFCF6] dark:bg-[#161616] shadow-xl overflow-hidden">
            {/* Editor Top Bar */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#E4DDD2] dark:border-[#2D2D2D] bg-[#EEE8DE]/70 dark:bg-[#1A1A1A]">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-[#EF4444]/80" />
                  <span className="w-3 h-3 rounded-full bg-[#F59E0B]/80" />
                  <span className="w-3 h-3 rounded-full bg-[#10B981]/80" />
                </div>
                <span className="text-xs font-mono font-semibold text-[#706C65] dark:text-[#A5A29C]">
                  practical_02_binary_search.py
                </span>
              </div>

              <div className="flex items-center gap-3">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-mono bg-[#10B981]/15 text-[#059669] dark:text-[#34D399] border border-[#10B981]/30">
                  <Lock className="w-3 h-3" />
                  Sequential Unlock: #2 Active
                </span>
                <span className="text-xs font-mono text-[#D94F16] dark:text-[#FF8533] font-bold">
                  Python 3.12
                </span>
              </div>
            </div>

            {/* Split Screen Workspace Preview */}
            <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[360px]">
              {/* Problem Statement Panel */}
              <div className="lg:col-span-5 p-5 border-b lg:border-b-0 lg:border-r border-[#E4DDD2] dark:border-[#2D2D2D] bg-[#FFFCF6] dark:bg-[#171717] space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold uppercase tracking-wider text-[#D94F16] dark:text-[#FF8533]">
                    Practical 2 of 8
                  </span>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-[#E4DDD2] dark:bg-[#252525] text-[#191919] dark:text-[#F7F4EF]">
                    Passing Threshold: 80%
                  </span>
                </div>

                <h3 className="text-base font-bold text-[#191919] dark:text-[#F7F4EF]">
                  Optimized Binary Search & Range Queries
                </h3>

                <p className="text-xs text-[#706C65] dark:text-[#A5A29C] leading-relaxed">
                  Given a sorted array of unique integers and a set of query targets, implement an algorithm with O(log N) runtime complexity. Return the exact target index or -1 if the element is absent.
                </p>

                <div className="p-3 rounded-xl bg-[#EEE8DE]/60 dark:bg-[#1E1E1E] border border-[#E4DDD2] dark:border-[#333333] font-mono text-xs space-y-2">
                  <div className="text-[11px] font-semibold text-[#706C65] dark:text-[#A5A29C]">
                    Sample Input:
                  </div>
                  <div className="text-[#191919] dark:text-[#F7F4EF]">
                    5 3<br />
                    1 3 5 7 9<br />
                    3 4 7
                  </div>
                  <div className="text-[11px] font-semibold text-[#706C65] dark:text-[#A5A29C] pt-1">
                    Expected Output:
                  </div>
                  <div className="text-[#10B981] font-bold">
                    1 -1 3
                  </div>
                </div>
              </div>

              {/* Code & Terminal Results Panel */}
              <div className="lg:col-span-7 flex flex-col bg-[#121212] text-[#F7F4EF]">
                <div className="p-4 font-mono text-xs overflow-x-auto flex-1 leading-relaxed text-[#D4D4D4]">
                  <span className="text-[#6A9955]"># CredLab Sandboxed Practical Solution</span><br />
                  <span className="text-[#C586C0]">def</span> <span className="text-[#DCDCAA]">binary_search</span>(arr, target):<br />
                  &nbsp;&nbsp;&nbsp;&nbsp;left, right = 0, len(arr) - 1<br />
                  &nbsp;&nbsp;&nbsp;&nbsp;<span className="text-[#C586C0]">while</span> left &lt;= right:<br />
                  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;mid = (left + right) // 2<br />
                  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-[#C586C0]">if</span> arr[mid] == target:<br />
                  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-[#C586C0]">return</span> mid<br />
                  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-[#C586C0]">elif</span> arr[mid] &lt; target:<br />
                  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;left = mid + 1<br />
                  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-[#C586C0]">else</span>:<br />
                  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;right = mid - 1<br />
                  &nbsp;&nbsp;&nbsp;&nbsp;<span className="text-[#C586C0]">return</span> -1<br />
                </div>

                {/* Execution Results Footer */}
                <div className="p-3 border-t border-[#2A2A2A] bg-[#181818] flex items-center justify-between text-xs font-mono">
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1.5 text-[#34D399] font-bold">
                      <CheckCircle2 className="w-4 h-4 text-[#10B981]" />
                      All Test Cases Passed (4/4)
                    </span>
                    <span className="text-[#A5A29C] text-[11px]">
                      Time: 38ms · Memory: 8.2MB
                    </span>
                  </div>

                  <span className="px-3 py-1 rounded-md bg-[#FF6B2C] text-white font-semibold text-xs shadow-xs">
                    Score: 100%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ────── Section D: How It Works ────── */}
      <section id="how-it-works" className="py-16 sm:py-24 border-b border-[#E4DDD2] dark:border-[#242424] bg-[#EEE8DE]/30 dark:bg-[#141414]/40">
        <div className="mx-auto max-w-7xl px-4 sm:px-8">
          <div className="text-center max-w-3xl mx-auto mb-14">
            <span className="text-xs font-mono uppercase tracking-widest text-[#D94F16] dark:text-[#FF8533] font-bold">
              Structured Methodology
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight mt-2">
              From Curriculum Exercise to Verified Proof
            </h2>
            <p className="text-sm sm:text-base text-[#706C65] dark:text-[#A5A29C] mt-3">
              A five-step continuous assessment model ensuring genuine skill development without shortcuts.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {steps.map((st) => (
              <div
                key={st.number}
                className="p-5 rounded-2xl bg-[#FFFCF6] dark:bg-[#1B1B1B] border border-[#E4DDD2] dark:border-[#353535] shadow-xs flex flex-col justify-between"
              >
                <div>
                  <span className="font-mono text-2xl font-black text-[#D94F16] dark:text-[#FF6B2C]">
                    {st.number}
                  </span>
                  <h3 className="text-sm font-bold mt-2 text-[#191919] dark:text-[#F7F4EF]">
                    {st.title}
                  </h3>
                  <p className="text-xs text-[#706C65] dark:text-[#A5A29C] mt-1.5 leading-relaxed">
                    {st.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ────── Section E: Features / Platform Capabilities ────── */}
      <section id="features" className="py-16 sm:py-24 border-b border-[#E4DDD2] dark:border-[#242424]">
        <div className="mx-auto max-w-7xl px-4 sm:px-8">
          <div className="text-center max-w-3xl mx-auto mb-14">
            <span className="text-xs font-mono uppercase tracking-widest text-[#D94F16] dark:text-[#FF8533] font-bold">
              Complete Capabilities
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight mt-2">
              Built for Modern Universities & Technical Institutions
            </h2>
            <p className="text-sm sm:text-base text-[#706C65] dark:text-[#A5A29C] mt-3">
              CredLab eliminates manual grading overhead while elevating institutional trust and student accountability.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f) => (
              <div
                key={f.title}
                className="p-6 rounded-2xl bg-[#FFFCF6] dark:bg-[#1B1B1B] border border-[#E4DDD2] dark:border-[#353535] hover:border-[#FF6B2C]/50 transition-all duration-200 shadow-xs flex flex-col justify-between space-y-4"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="p-2.5 rounded-xl bg-[#EEE8DE] dark:bg-[#252525]">
                      {f.icon}
                    </div>
                    <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-md bg-[#FF6B2C]/10 text-[#D94F16] dark:text-[#FF8533] border border-[#FF6B2C]/20">
                      {f.badge}
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-[#191919] dark:text-[#F7F4EF]">
                    {f.title}
                  </h3>
                  <p className="text-xs text-[#706C65] dark:text-[#A5A29C] leading-relaxed">
                    {f.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ────── Section F: Role-based Experience ────── */}
      <section id="roles" className="py-16 sm:py-24 border-b border-[#E4DDD2] dark:border-[#242424] bg-[#EEE8DE]/20 dark:bg-[#141414]/30">
        <div className="mx-auto max-w-7xl px-4 sm:px-8">
          <div className="text-center max-w-3xl mx-auto mb-12">
            <span className="text-xs font-mono uppercase tracking-widest text-[#D94F16] dark:text-[#FF8533] font-bold">
              Tailored Experiences
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight mt-2">
              A Purpose-Built Workflow for Every Stakeholder
            </h2>
          </div>

          {/* Role Tabs */}
          <div className="flex justify-center mb-8">
            <div className="inline-flex p-1.5 rounded-2xl bg-[#E4DDD2]/60 dark:bg-[#1E1E1E] border border-[#D4CBBD] dark:border-[#333333]">
              {workflows.map((w) => {
                const isActive = activeRole === w.id;
                return (
                  <button
                    key={w.id}
                    type="button"
                    onClick={() => setActiveRole(w.id)}
                    className={`flex items-center gap-2 px-4 py-2 text-xs sm:text-sm font-semibold rounded-xl transition-all ${
                      isActive
                        ? "bg-[#FFFFFF] dark:bg-[#2A2A2A] text-[#D94F16] dark:text-[#FF6B2C] shadow-sm"
                        : "text-[#706C65] dark:text-[#A5A29C] hover:text-[#191919] dark:hover:text-[#F7F4EF]"
                    }`}
                  >
                    {w.icon}
                    <span>{w.role}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Role Detail Card */}
          <div className="max-w-4xl mx-auto p-6 sm:p-8 rounded-3xl bg-[#FFFCF6] dark:bg-[#1B1B1B] border border-[#E4DDD2] dark:border-[#353535] shadow-lg">
            <div className="space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-mono px-3 py-1 rounded-full bg-[#FF6B2C]/10 text-[#D94F16] dark:text-[#FF8533] font-semibold border border-[#FF6B2C]/20">
                  {selectedWorkflow.badge}
                </span>
                <span className="text-xs font-mono text-[#706C65] dark:text-[#A5A29C]">
                  Role: {selectedWorkflow.role}
                </span>
              </div>

              <div>
                <h3 className="text-2xl font-extrabold text-[#191919] dark:text-[#F7F4EF]">
                  {selectedWorkflow.headline}
                </h3>
                <p className="text-sm text-[#706C65] dark:text-[#A5A29C] mt-2 leading-relaxed">
                  {selectedWorkflow.description}
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                {selectedWorkflow.points.map((pt) => (
                  <div key={pt} className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-[#FF6B2C] mt-0.5 shrink-0" />
                    <span className="text-xs text-[#191919] dark:text-[#F7F4EF] leading-relaxed">
                      {pt}
                    </span>
                  </div>
                ))}
              </div>

              <div className="pt-4 border-t border-[#E4DDD2] dark:border-[#2E2E2E] flex justify-end">
                <Link
                  href={selectedWorkflow.ctaLink}
                  className="btn-primary text-xs !py-2.5 !px-5 flex items-center gap-2"
                >
                  <span>{selectedWorkflow.ctaText}</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ────── Section G: Final CTA & Footer ────── */}
      <section id="verification" className="py-16 sm:py-20 border-b border-[#E4DDD2] dark:border-[#242424] bg-gradient-to-b from-transparent via-[#FF6B2C]/5 to-transparent">
        <div className="mx-auto max-w-5xl px-4 sm:px-8 text-center space-y-6">
          <div className="inline-flex p-3 rounded-2xl bg-[#FF6B2C]/10 text-[#FF6B2C] border border-[#FF6B2C]/20">
            <Award className="w-8 h-8" />
          </div>

          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
            Elevate Your Technical Assessments with CredLab
          </h2>

          <p className="text-sm sm:text-base text-[#706C65] dark:text-[#A5A29C] max-w-xl mx-auto leading-relaxed">
            Join institutions delivering tamper-proof digital coding labs and verifiable milestone certificates.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
            <Link
              href="/login"
              className="btn-primary !px-7 !py-3 text-sm font-semibold flex items-center gap-2"
            >
              <span>Sign In to CredLab</span>
              <ArrowRight className="w-4 h-4" />
            </Link>

            <Link
              href="/register/student"
              className="btn-secondary !px-6 !py-3 text-sm font-semibold"
            >
              Create Student Account
            </Link>
          </div>
        </div>
      </section>

      {/* ────── Footer ────── */}
      <footer className="py-10 bg-[#FFFCF6] dark:bg-[#121212] text-[#706C65] dark:text-[#A5A29C] text-xs">
        <div className="mx-auto max-w-7xl px-4 sm:px-8 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <CredLabLogo size="sm" showWordmark={true} />
            <span className="text-[#E4DDD2] dark:text-[#333333]">|</span>
            <span className="font-mono text-[11px]">
              Institutional Assessment Suite
            </span>
          </div>

          <div className="flex items-center gap-6 text-xs">
            <Link href="/login" className="hover:text-[#D94F16] dark:hover:text-[#FF6B2C]">
              Portal Login
            </Link>
            <Link href="/register/student" className="hover:text-[#D94F16] dark:hover:text-[#FF6B2C]">
              Student Registration
            </Link>
            <Link href="/register/faculty" className="hover:text-[#D94F16] dark:hover:text-[#FF6B2C]">
              Faculty Registration
            </Link>
            <Link href="/register/admin" className="hover:text-[#D94F16] dark:hover:text-[#FF6B2C]">
              Admin Registration
            </Link>
          </div>

          <div className="text-[11px] font-mono text-center md:text-right">
            © 2026 CredLab. Cryptographically Signed University Assessments.
          </div>
        </div>
      </footer>
    </div>
  );
}
