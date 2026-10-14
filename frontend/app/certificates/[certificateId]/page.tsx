"use client";
/* eslint react-hooks/set-state-in-effect: off */

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

type Certificate = {
  id: string;
  student_name: string;
  course_code: string;
  lab_title: string;
  practical_title: string;
  score: number;
  passing_threshold: number;
  issuer: string;
  algorithm: string;
  key_id: string;
  payload_digest: string;
  signature: string;
  status: string;
  completed_at: string;
  issued_at: string;
};

function CertificatePageContent() {
  const params = useParams<{ certificateId: string }>();
  const router = useRouter();
  const [certificate, setCertificate] = useState<Certificate | null>(null);
  const [verified, setVerified] = useState<{
    is_valid: boolean;
    verification_status: string;
    message: string;
  } | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const response = await fetch(
          `/api/admin/certificates/${encodeURIComponent(params.certificateId)}`,
          { cache: "no-store" },
        );
        if (response.status === 401) {
          router.replace("/login");
          return;
        }
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Certificate record not found.");
        if (!cancelled) setCertificate(data as Certificate);

        const check = await fetch("/api/admin/certificates/verify", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ certificate_id: params.certificateId }),
          cache: "no-store",
        });
        const result = await check.json();
        if (check.ok && !cancelled) setVerified(result);
      } catch (cause) {
        if (!cancelled)
          setError(
            cause instanceof Error ? cause.message : "Unable to retrieve certificate record.",
          );
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [params.certificateId, router]);

  if (loading) {
    return (
      <main
        className="flex min-h-screen items-center justify-center"
        style={{ backgroundColor: "var(--color-background)" }}
      >
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 animate-spin rounded-full border-3 border-[#9F1239] border-t-transparent" />
          <p className="text-sm font-semibold text-[#806777]">
            Validating cryptographic diploma credentials...
          </p>
        </div>
      </main>
    );
  }

  if (error || !certificate) {
    return (
      <main
        className="flex min-h-screen items-center justify-center p-6"
        style={{ backgroundColor: "var(--color-background)" }}
      >
        <div className="lux-card max-w-lg p-8 text-center shadow-xl border border-[#F0DCE5]">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl badge-danger text-xl">
            ⚠
          </div>
          <h1 className="mt-4 text-xl font-extrabold text-[#3F1024]">
            Certificate Record Unavailable
          </h1>
          <p className="mt-2 text-sm text-[#806777]">
            {error || "This completion certificate could not be located on the platform."}
          </p>
          <Link href="/student/dashboard" className="btn-primary mt-6 !py-2.5 !text-xs font-bold">
            ← Return to Dashboard
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main
      className="min-h-screen p-4 sm:p-8 lg:p-12 print:p-0 print:bg-white print:text-black"
      style={{ backgroundColor: "var(--color-background)" }}
    >
      <div className="mx-auto max-w-4xl">
        {/* Navigation / Actions Bar */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4 print:hidden">
          <Link
            href="/student/dashboard"
            className="inline-flex items-center gap-2 text-xs font-bold text-[#9F1239] hover:underline transition-colors"
          >
            ← Back to Student Workspace
          </Link>

          <div className="flex items-center gap-3">
            <button
              onClick={() => window.print()}
              className="btn-primary !py-2 !px-4 !text-xs font-bold shadow-sm"
            >
              🖨 Print / Save as PDF
            </button>
          </div>
        </div>

        {/* ────── Academic Certificate Document ────── */}
        <section
          className="relative overflow-hidden rounded-3xl bg-[#FFFFFF] p-8 text-[#3F1024] shadow-2xl sm:p-14 border-8 border-[#9F1239] print:border-none print:shadow-none print:p-8"
          style={{
            boxShadow: "0 25px 50px -12px rgba(159, 18, 57, 0.15)",
          }}
        >
          {/* Ornate inner border */}
          <div className="relative border-4 border-[#F0DCE5] p-8 sm:p-12 text-center bg-gradient-to-b from-[#FFFFFF] via-[#FFFDFE] to-[#FFF7FA]">
            {/* Top Emblem */}
            <div
              className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl text-2xl font-bold text-white shadow-sm"
              style={{ background: "var(--primary-gradient)" }}
            >
              ⬡
            </div>

            <p className="mt-4 text-xs font-bold uppercase tracking-[0.3em] text-[#9F1239]">
              {certificate.issuer || "LabOS Academic Sentinel"}
            </p>

            <h1 className="mt-4 font-serif text-3xl sm:text-5xl font-extrabold tracking-tight text-[#3F1024]">
              Certificate of Completion
            </h1>

            <p className="mt-6 text-xs font-bold uppercase tracking-widest text-[#806777]">
              This officially certifies that
            </p>

            <h2 className="mt-3 text-2xl sm:text-4xl font-serif font-extrabold text-[#9F1239] tracking-wide underline decoration-[#BE5678]/40 decoration-2 underline-offset-8">
              {certificate.student_name}
            </h2>

            <p className="mx-auto mt-6 max-w-xl text-sm leading-relaxed text-[#3F1024]">
              has satisfactorily completed all mandatory laboratory programming assessments and
              demonstrated mastery of secure coding requirements in
            </p>

            <p className="mt-3 text-xl sm:text-2xl font-serif font-extrabold text-[#3F1024]">
              {certificate.lab_title}
            </p>

            <p className="mt-1 text-xs font-bold text-[#806777]">
              Course:{" "}
              <span className="font-extrabold text-[#9F1239]">{certificate.course_code}</span>
            </p>

            {/* Credential Metrics Grid */}
            <div className="mx-auto mt-8 grid max-w-lg grid-cols-2 gap-4 rounded-xl border border-[#F0DCE5] bg-[#FFF7FA] p-4 text-xs sm:grid-cols-4">
              <div>
                <p className="text-[10px] uppercase font-bold text-[#806777]">Final Score</p>
                <p className="mt-1 font-extrabold text-[#9F1239] text-base">{certificate.score}%</p>
              </div>
              <div>
                <p className="text-[10px] uppercase font-bold text-[#806777]">Threshold</p>
                <p className="mt-1 font-extrabold text-[#3F1024] text-base">
                  {certificate.passing_threshold}%
                </p>
              </div>
              <div>
                <p className="text-[10px] uppercase font-bold text-[#806777]">Completed</p>
                <p className="mt-1 font-bold text-[#3F1024] text-[11px]">
                  {new Date(certificate.completed_at).toLocaleDateString()}
                </p>
              </div>
              <div>
                <p className="text-[10px] uppercase font-bold text-[#806777]">Issued</p>
                <p className="mt-1 font-bold text-[#3F1024] text-[11px]">
                  {new Date(certificate.issued_at).toLocaleDateString()}
                </p>
              </div>
            </div>

            {/* Signature and Verification Footer */}
            <div className="mt-12 flex flex-wrap items-end justify-between border-t border-[#F0DCE5] pt-6 text-left text-xs">
              <div>
                <p className="font-mono text-[10px] font-bold text-[#806777]">
                  CREDENTIAL IDENTIFIER:
                </p>
                <p className="font-mono text-[11px] font-bold text-[#9F1239] break-all max-w-sm">
                  {certificate.id}
                </p>
              </div>

              <div className="text-right">
                <p className="font-serif italic text-base font-bold text-[#3F1024]">
                  Verified Academic Seal
                </p>
                <p className="text-[10px] font-bold uppercase tracking-wider text-[#BE5678]">
                  Ed25519 Digitally Signed
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ────── Cryptographic Verification Card ────── */}
        <section className="mt-6 lux-card p-6 print:hidden bg-[#FFFFFF] border border-[#F0DCE5]">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-extrabold text-[#3F1024]">Cryptographic Verification</h3>
              <p className="text-xs text-[#806777]">
                Mathematically verified signature issued by the institutional private key.
              </p>
            </div>

            <span
              className={`rounded-full px-3 py-1 text-xs font-bold ${
                verified?.is_valid ? "badge-success" : "badge-warning"
              }`}
            >
              {verified ? verified.verification_status : "Verifying Signature..."}
            </span>
          </div>

          <p className="mt-3 text-xs leading-relaxed text-[#3F1024]">
            {verified?.message ||
              "Cryptographic integrity is being evaluated against registered public keys."}
          </p>

          <div className="mt-4 rounded-xl p-3.5 space-y-1.5 font-mono text-[11px] bg-[#FFF7FA] border border-[#F0DCE5]">
            <p className="break-all text-[#806777]">
              <strong className="text-[#3F1024]">Payload Digest (SHA-256):</strong>{" "}
              {certificate.payload_digest}
            </p>
            <p className="text-[#806777]">
              <strong className="text-[#3F1024]">Algorithm:</strong> {certificate.algorithm} ·{" "}
              <strong className="text-[#3F1024]">Key Identifier:</strong> {certificate.key_id}
            </p>
            <p className="break-all text-[#A38C9B]">
              <strong className="text-[#3F1024]">Signature:</strong> {certificate.signature}
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}

export default function CertificatePage() {
  return (
    <Suspense
      fallback={
        <main
          className="flex min-h-screen items-center justify-center"
          style={{ backgroundColor: "var(--color-background)" }}
        >
          <p className="text-sm font-semibold text-[#806777]">Loading certificate credential...</p>
        </main>
      }
    >
      <CertificatePageContent />
    </Suspense>
  );
}
