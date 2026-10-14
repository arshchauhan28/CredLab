import Link from "next/link";

const features = [
  {
    icon: "🔬",
    title: "Curated University Laboratories",
    description:
      "Structured practical curriculums tied directly to academic programs, course modules, and real-time execution sandboxes.",
    tag: "Academic Precision",
  },
  {
    icon: "⚡",
    title: "Automated Sandbox Evaluation",
    description:
      "Run authoritative unit tests on student submissions with instant feedback, time/memory limit tracking, and compiler logs.",
    tag: "Instant Feedback",
  },
  {
    icon: "🛡️",
    title: "Academic Integrity & Anti-Tamper",
    description:
      "Enforced sequential practical unlocking, editor telemetry monitoring, and secure server-side execution prevent shortcuts.",
    tag: "High Integrity",
  },
  {
    icon: "📜",
    title: "Cryptographic Milestone Certificates",
    description:
      "Ed25519 digitally signed diplomas issued upon 100% lab completion with cryptographic QR and public key verification.",
    tag: "Verifiable Diplomas",
  },
];

const workflows = [
  {
    role: "Students",
    badge: "Interactive Learning",
    description:
      "Access enrolled courses, solve structured programming challenges in Monaco or lightweight IDEs, test solutions against test cases, and earn milestone diplomas.",
    action: "Explore Student Portal",
    link: "/register/student",
    accent: "from-[#9F1239] to-[#BE5678]",
    points: [
      "Sequential practical unlocks",
      "Monaco editor with multi-language support",
      "Live test case execution & AI assistant",
      "Personal verifiable certificate registry",
    ],
  },
  {
    role: "Faculty Instructors",
    badge: "Curriculum Oversight",
    description:
      "Create courses, publish laboratories, define hidden and visible test cases, monitor student submission analytics, and approve completion certificates with one click.",
    action: "Access Faculty Suite",
    link: "/login",
    accent: "from-[#BE5678] to-[#E879A9]",
    points: [
      "Custom test suite authoring",
      "Live student submission logs & scores",
      "One-click Ed25519 certificate minting",
      "Classroom completion metrics",
    ],
  },
  {
    role: "Institution Administrators",
    badge: "Governance & Security",
    description:
      "Manage academic sessions, provision students and professors, oversee institutional data integrity, and inspect cryptographic certificate verification logs.",
    action: "Admin Governance",
    link: "/login",
    accent: "from-[#881337] to-[#9F1239]",
    points: [
      "Centralized user & role management",
      "Academic year & course assignments",
      "Certificate verification validator",
      "System security & audit metrics",
    ],
  },
];

const stats = [
  { value: "100%", label: "Server-Verified Grading", sub: "Deterministic Sandboxes" },
  { value: "Ed25519", label: "Cryptographic Signing", sub: "Tamper-Proof Diplomas" },
  { value: "Multi-Role", label: "Academic Access", sub: "Students, Faculty & Admins" },
  { value: "< 250ms", label: "Execution Latency", sub: "Subprocess Sandbox" },
];

export default function Home() {
  return (
    <main className="min-h-screen" style={{ backgroundColor: "var(--color-background)" }}>
      {/* ────── Top Announcement Banner ────── */}
      <aside aria-label="Academic Session Ticker" className="bg-[#9F1239] text-white text-xs py-2 px-4 text-center font-medium tracking-wide">
        <span className="inline-flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-[#E879A9] animate-pulse" />
          LabOS University Academic Session 2026–2027 · Secure Laboratory Assessment Platform Live
        </span>
      </aside>

      {/* ────── Global Header ────── */}
      <header className="sticky top-0 z-30 border-b border-[#F0DCE5] bg-[#FFFFFF]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 sm:px-8">
          <Link href="/" className="flex items-center gap-3 group">
            <span
              className="flex h-10 w-10 items-center justify-center rounded-xl text-lg font-bold text-white shadow-sm"
              style={{ background: "var(--primary-gradient)" }}
            >
              ⬡
            </span>
            <div>
              <span className="block text-base font-bold tracking-tight text-[#3F1024]">
                LabOS
              </span>
              <span className="block text-[11px] font-semibold uppercase tracking-wider text-[#BE5678]">
                University Assessment Platform
              </span>
            </div>
          </Link>

          <nav aria-label="Main Navigation" className="flex items-center gap-3 sm:gap-4">
            <Link
              href="/register/student"
              className="hidden sm:inline-flex text-xs font-semibold uppercase tracking-wider text-[#806777] hover:text-[#9F1239] transition-colors px-3 py-2"
            >
              Student Registration
            </Link>
            <Link
              href="/login"
              className="btn-primary !py-2.5 !px-5 !text-xs font-semibold uppercase tracking-wider"
            >
              Sign In
              <svg
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-3.5 w-3.5"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z"
                  clipRule="evenodd"
                />
              </svg>
            </Link>
          </nav>
        </div>
      </header>

      {/* ────── Hero Section ────── */}
      <section className="relative overflow-hidden pt-12 pb-20 sm:pt-20 sm:pb-28">
        {/* Soft Decorative Burgundy Background Blobs */}
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -left-40 h-[32rem] w-[32rem] rounded-full bg-[#FBEAF0] opacity-80 blur-[80px]" />
          <div className="absolute top-20 -right-40 h-[28rem] w-[28rem] rounded-full bg-[#FFF0F5] opacity-90 blur-[100px]" />
        </div>

        <div className="relative mx-auto max-w-7xl px-5 sm:px-8">
          <div className="grid items-center gap-12 lg:grid-cols-[1.2fr_0.8fr] lg:gap-16">
            <div className="animate-fade-in">
              <div className="inline-flex items-center gap-2 rounded-full border border-[#F0DCE5] bg-[#FFFFFF] px-3.5 py-1.5 text-xs font-semibold text-[#9F1239] shadow-xs">
                <span className="flex h-2 w-2 rounded-full bg-[#9F1239]" />
                Institutional Laboratory Infrastructure
              </div>

              <h1 className="mt-6 text-4xl font-extrabold tracking-tight text-[#3F1024] sm:text-5xl lg:text-[3.5rem] lg:leading-[1.12]">
                Secure coding assessments designed for{" "}
                <span className="text-gradient-primary">academic excellence</span>.
              </h1>

              <p className="mt-5 text-base leading-relaxed text-[#806777] sm:text-lg max-w-2xl">
                LabOS empowers universities with structured practical curricula, sandboxed
                deterministic code evaluation, tamper-proof sequential unlocks, and
                cryptographically signed milestone diplomas.
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-4">
                <Link
                  href="/login"
                  className="btn-primary !py-3.5 !px-8 !text-sm font-bold tracking-wide shadow-md"
                >
                  Enter Laboratory Portal →
                </Link>
                <Link
                  href="/register/student"
                  className="btn-secondary !py-3.5 !px-7 !text-sm font-semibold"
                >
                  New Student Registration
                </Link>
              </div>

              {/* Security assurances */}
              <div className="mt-10 flex flex-wrap items-center gap-6 text-xs font-medium text-[#806777]">
                <span className="flex items-center gap-2">
                  <span className="text-emerald-700 font-bold">✓</span> Anti-Cheat Sandboxed
                </span>
                <span className="flex items-center gap-2">
                  <span className="text-emerald-700 font-bold">✓</span> Ed25519 Signed Diplomas
                </span>
                <span className="flex items-center gap-2">
                  <span className="text-emerald-700 font-bold">✓</span> Subprocess Isolation
                </span>
              </div>
            </div>

            {/* Hero Right Visual: Elegant University Laboratory Card */}
            <div className="relative animate-fade-in">
              <div
                className="lux-card p-6 sm:p-8 relative overflow-hidden"
                style={{
                  boxShadow: "0 20px 40px rgba(159, 18, 57, 0.08)",
                  border: "1px solid #F0DCE5",
                }}
              >
                {/* Header ribbon */}
                <div className="flex items-center justify-between pb-5 border-b border-[#F0DCE5]">
                  <div>
                    <span className="badge-primary px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider rounded-md">
                      Active Lab Module
                    </span>
                    <h2 className="mt-2 text-lg font-bold text-[#3F1024]">
                      Python Programming (CS201)
                    </h2>
                    <p className="text-xs text-[#806777]">Functions, Sequences & Arrays</p>
                  </div>
                  <span className="h-10 w-10 flex items-center justify-center rounded-xl bg-[#FBEAF0] text-[#9F1239] font-bold text-sm">
                    3 / 3
                  </span>
                </div>

                {/* Practicals sequence snippet */}
                <div className="mt-5 space-y-3">
                  {[
                    { seq: 1, title: "Fibonacci Sequence Generator", status: "COMPLETED", score: "100%" },
                    { seq: 2, title: "Two Sum Search Algorithm", status: "COMPLETED", score: "100%" },
                    { seq: 3, title: "Palindrome String Verification", status: "COMPLETED", score: "100%" },
                  ].map((p) => (
                    <div
                      key={p.seq}
                      className="flex items-center justify-between p-3 rounded-xl bg-[#FFF7FA] border border-[#F0DCE5]"
                    >
                      <div className="flex items-center gap-3">
                        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#ECFDF5] text-emerald-800 text-xs font-bold">
                          ✓
                        </span>
                        <div>
                          <p className="text-xs font-bold text-[#3F1024]">
                            #{p.seq} {p.title}
                          </p>
                          <p className="text-[10px] text-[#806777]">Test Cases: 100% Passed</p>
                        </div>
                      </div>
                      <span className="badge-success px-2 py-0.5 text-[10px] font-bold rounded-md">
                        {p.score}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Certificate notification snippet */}
                <div className="mt-5 p-4 rounded-xl border border-[#F0DCE5] bg-gradient-to-r from-[#FFF7FA] to-[#FBEAF0]">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-base">🏆</span>
                      <div>
                        <p className="text-xs font-bold text-[#9F1239]">
                          Milestone Diploma Issued
                        </p>
                        <p className="text-[10px] text-[#806777]">
                          Ed25519 Cryptographically Signed
                        </p>
                      </div>
                    </div>
                    <span className="text-[10px] font-bold text-[#9F1239] underline">
                      Verified ✓
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ────── Institutional Stats Strip ────── */}
      <section className="border-y border-[#F0DCE5] bg-[#FFFFFF] py-12">
        <div className="mx-auto max-w-7xl px-5 sm:px-8">
          <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
            {stats.map((s) => (
              <div key={s.label} className="text-center sm:text-left">
                <p className="text-3xl font-extrabold text-[#9F1239] sm:text-4xl">
                  {s.value}
                </p>
                <p className="mt-1 text-sm font-bold text-[#3F1024]">{s.label}</p>
                <p className="text-xs text-[#806777]">{s.sub}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ────── Core Features Grid ────── */}
      <section className="py-20 sm:py-28">
        <div className="mx-auto max-w-7xl px-5 sm:px-8">
          <div className="text-center max-w-2xl mx-auto">
            <span className="badge-primary px-3 py-1 text-xs font-bold uppercase tracking-wider rounded-full">
              Platform Features
            </span>
            <h2 className="mt-4 text-3xl font-extrabold tracking-tight text-[#3F1024] sm:text-4xl">
              Engineered for academic rigorousness
            </h2>
            <p className="mt-3 text-sm text-[#806777]">
              Every tool in LabOS is purposeful, eliminating distraction and providing verifiable
              proof of student mastery.
            </p>
          </div>

          <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {features.map((f) => (
              <div
                key={f.title}
                className="lux-card p-6 card-hover flex flex-col justify-between"
              >
                <div>
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#FBEAF0] text-2xl text-[#9F1239]">
                    {f.icon}
                  </div>
                  <span className="mt-4 inline-block text-[10px] font-bold uppercase tracking-wider text-[#BE5678]">
                    {f.tag}
                  </span>
                  <h3 className="mt-2 text-base font-bold text-[#3F1024]">{f.title}</h3>
                  <p className="mt-2 text-xs leading-relaxed text-[#806777]">
                    {f.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ────── Role Workflows Section ────── */}
      <section className="border-t border-[#F0DCE5] bg-[#FFFFFF] py-20 sm:py-28">
        <div className="mx-auto max-w-7xl px-5 sm:px-8">
          <div className="text-center max-w-2xl mx-auto">
            <span className="badge-primary px-3 py-1 text-xs font-bold uppercase tracking-wider rounded-full">
              Workflow Synergy
            </span>
            <h2 className="mt-4 text-3xl font-extrabold tracking-tight text-[#3F1024] sm:text-4xl">
              Three synchronized roles in one platform
            </h2>
            <p className="mt-3 text-sm text-[#806777]">
              Designed to connect classroom instruction, student evaluation, and institutional
              administration seamlessly.
            </p>
          </div>

          <div className="mt-14 grid gap-8 md:grid-cols-3">
            {workflows.map((w) => (
              <div
                key={w.role}
                className="lux-card p-7 card-hover flex flex-col justify-between"
                style={{ backgroundColor: "var(--color-background)" }}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="badge-primary px-2.5 py-1 text-[11px] font-bold rounded-md">
                      {w.badge}
                    </span>
                    <span className="text-xs font-bold text-[#BE5678]">0{workflows.indexOf(w) + 1}</span>
                  </div>

                  <h3 className="mt-4 text-xl font-bold text-[#3F1024]">{w.role}</h3>
                  <p className="mt-2.5 text-xs leading-relaxed text-[#806777]">{w.description}</p>

                  <div className="mt-6 space-y-2.5">
                    {w.points.map((pt) => (
                      <div key={pt} className="flex items-start gap-2 text-xs text-[#3F1024]">
                        <span className="text-[#9F1239] font-bold">›</span>
                        <span>{pt}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="mt-8 pt-5 border-t border-[#F0DCE5]">
                  <Link
                    href={w.link}
                    className="inline-flex items-center gap-1.5 text-xs font-bold text-[#9F1239] hover:text-[#BE5678] transition-colors"
                  >
                    {w.action} →
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ────── Final Call to Action ────── */}
      <section className="py-20 sm:py-24" style={{ background: "var(--primary-gradient)" }}>
        <div className="mx-auto max-w-5xl px-5 text-center text-white sm:px-8">
          <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
            Elevate university laboratory assessments today
          </h2>
          <p className="mt-4 text-base text-rose-100 max-w-xl mx-auto">
            Sign in with your university credentials or register a student account to access the
            practical coding workspace.
          </p>
          <div className="mt-8 flex justify-center gap-4">
            <Link
              href="/login"
              className="rounded-xl bg-[#FFFFFF] px-8 py-3.5 text-sm font-bold text-[#9F1239] shadow-lg hover:bg-rose-50 transition-colors"
            >
              Sign In to LabOS
            </Link>
            <Link
              href="/register/student"
              className="rounded-xl border border-white/30 bg-white/10 px-7 py-3.5 text-sm font-semibold text-white hover:bg-white/20 transition-colors"
            >
              Student Registration
            </Link>
          </div>
        </div>
      </section>

      {/* ────── Institutional Footer ────── */}
      <footer className="border-t border-[#F0DCE5] bg-[#FFFFFF] py-12 text-xs text-[#806777]">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-6 px-5 sm:px-8">
          <div className="flex items-center gap-3">
            <span
              className="flex h-8 w-8 items-center justify-center rounded-lg text-white font-bold text-sm"
              style={{ background: "var(--primary-gradient)" }}
            >
              ⬡
            </span>
            <div>
              <p className="font-bold text-[#3F1024]">LabOS Secure Coding Assessment Platform</p>
              <p className="text-[11px]">Academic Computing & Digital Assessment Division</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-6 text-xs font-medium">
            <Link href="/login" className="hover:text-[#9F1239] transition-colors">
              Sign In
            </Link>
            <Link href="/register/student" className="hover:text-[#9F1239] transition-colors">
              Register Student
            </Link>
            <Link href="/register/faculty" className="hover:text-[#9F1239] transition-colors">
              Faculty Access
            </Link>
            <Link href="/register/admin" className="hover:text-[#9F1239] transition-colors">
              Administration
            </Link>
          </div>

          <p className="text-[11px] text-[#A38C9B]">
            © 2026 LabOS. Cryptographically Signed Digital Laboratory Platform.
          </p>
        </div>
      </footer>
    </main>
  );
}
