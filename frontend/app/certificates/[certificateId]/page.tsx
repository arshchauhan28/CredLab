"use client";
/* eslint react-hooks/set-state-in-effect: off */

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ShieldCheck, Printer, ArrowLeft, AlertCircle } from "lucide-react";
import { CredLabEmblem } from "@/components/CredLabLogo";

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
      <main className="flex min-h-screen items-center justify-center bg-[#F5F0E7] dark:bg-[#101010] text-[#191919] dark:text-[#F7F4EF]">
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 animate-spin rounded-full border-3 border-[#FF6B2C] border-t-transparent" />
          <p className="text-xs font-mono font-semibold text-[#706C65] dark:text-[#A5A29C]">
            Validating cryptographic diploma credentials...
          </p>
        </div>
      </main>
    );
  }

  if (error || !certificate) {
    return (
      <main className="flex min-h-screen items-center justify-center p-6 bg-[#F5F0E7] dark:bg-[#101010] text-[#191919] dark:text-[#F7F4EF]">
        <div className="rounded-3xl border border-[#E4DDD2] dark:border-[#353535] bg-[#FFFCF6] dark:bg-[#181818] max-w-lg p-8 text-center shadow-xl">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-[#DC2626]/10 text-[#DC2626] dark:text-[#EF4444]">
            <AlertCircle className="w-6 h-6" />
          </div>
          <h1 className="mt-4 text-xl font-extrabold">
            Certificate Record Unavailable
          </h1>
          <p className="mt-2 text-xs text-[#706C65] dark:text-[#A5A29C]">
            {error || "This completion certificate could not be located on the platform."}
          </p>
          <Link href="/student/dashboard" className="btn-primary mt-6 !py-2.5 !text-xs font-bold inline-flex items-center gap-2">
            <ArrowLeft className="w-4 h-4" />
            <span>Return to Dashboard</span>
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen p-4 sm:p-8 lg:p-12 print:p-0 print:bg-white print:text-black bg-[#101010] text-[#F7F4EF]">
      <div className="mx-auto max-w-4xl">
        {/* Navigation & Action Bar */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4 print:hidden">
          <Link
            href="/student/dashboard"
            className="inline-flex items-center gap-2 text-xs font-bold text-[#FF8A3D] hover:underline transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Return to Workspace</span>
          </Link>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => window.print()}
              className="btn-primary !py-2 !px-4 !text-xs font-bold shadow-sm flex items-center gap-1.5"
            >
              <Printer className="w-4 h-4" />
              <span>Print / Save as PDF</span>
            </button>
          </div>
        </div>

        {/* ────── Academic Certificate Document ────── */}
        <section
          className="relative overflow-hidden rounded-3xl bg-[#1A1A1A] p-6 text-[#F7F4EF] shadow-2xl sm:p-12 border-4 sm:border-8 border-[#FF6B2C] print:border-none print:shadow-none print:p-8 transition-colors"
          style={{
            boxShadow: "0 25px 50px -12px rgba(255, 107, 44, 0.2)",
          }}
        >
          {/* Ornate inner border */}
          <div className="relative border-2 border-[#353535] p-6 sm:p-10 text-center rounded-2xl bg-gradient-to-b from-[#1E1E1E] via-[#191919] to-[#141414]">
            {/* Top Emblem */}
            <div className="mx-auto flex items-center justify-center">
              <CredLabEmblem className="w-16 h-16" />
            </div>

            <p className="mt-4 text-xs font-mono font-bold uppercase tracking-[0.3em] text-[#FF8A3D]">
              {certificate.issuer || "CredLab Academic Sentinel"}
            </p>

            <h1 className="mt-3 font-serif text-3xl sm:text-5xl font-extrabold tracking-tight">
              Certificate of Completion
            </h1>

            <p className="mt-6 text-xs font-mono font-bold uppercase tracking-widest text-[#A5A29C]">
              This officially certifies that
            </p>

            <h2 className="mt-3 text-2xl sm:text-4xl font-serif font-extrabold text-[#FF6B2C] tracking-wide underline decoration-[#FFB547]/50 decoration-2 underline-offset-8">
              {certificate.student_name}
            </h2>

            <p className="mx-auto mt-6 max-w-xl text-xs sm:text-sm leading-relaxed text-[#A5A29C]">
              has satisfactorily completed all mandatory laboratory programming assessments and
              demonstrated verifiable mastery of secure coding requirements in
            </p>

            <p className="mt-3 text-xl sm:text-2xl font-serif font-extrabold">
              {certificate.lab_title}
            </p>

            <p className="mt-1 text-xs font-mono font-bold text-[#A5A29C]">
              Course:{" "}
              <span className="font-extrabold text-[#FF8A3D]">{certificate.course_code}</span>
            </p>

            {/* Credential Metrics Grid */}
            <div className="mx-auto mt-8 grid max-w-lg grid-cols-2 gap-4 rounded-xl border border-[#353535] bg-[#161616] p-4 text-xs sm:grid-cols-4 font-mono">
              <div>
                <p className="text-[10px] uppercase font-bold text-[#A5A29C]">Final Score</p>
                <p className="mt-1 font-extrabold text-[#FF6B2C] text-base">{certificate.score}%</p>
              </div>
              <div>
                <p className="text-[10px] uppercase font-bold text-[#A5A29C]">Threshold</p>
                <p className="mt-1 font-extrabold text-base">
                  {certificate.passing_threshold}%
                </p>
              </div>
              <div>
                <p className="text-[10px] uppercase font-bold text-[#A5A29C]">Completed</p>
                <p className="mt-1 font-bold text-[11px]">
                  {new Date(certificate.completed_at).toLocaleDateString()}
                </p>
              </div>
              <div>
                <p className="text-[10px] uppercase font-bold text-[#A5A29C]">Issued</p>
                <p className="mt-1 font-bold text-[11px]">
                  {new Date(certificate.issued_at).toLocaleDateString()}
                </p>
              </div>
            </div>

            {/* Signature and Verification Footer */}
            <div className="mt-10 flex flex-wrap items-end justify-between border-t border-[#353535] pt-6 text-left text-xs gap-4">
              <div>
                <p className="font-mono text-[10px] font-bold text-[#A5A29C]">
                  CREDENTIAL IDENTIFIER:
                </p>
                <p className="font-mono text-[11px] font-bold text-[#FF8A3D] break-all max-w-sm">
                  {certificate.id}
                </p>
              </div>

              <div className="text-right">
                <p className="font-serif italic text-base font-bold">
                  Verified Academic Seal
                </p>
                <p className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#FF6B2C]">
                  Ed25519 Digitally Signed
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ────── Cryptographic Verification Card ────── */}
        <section className="mt-6 rounded-3xl p-6 print:hidden bg-[#1B1B1B] border border-[#353535] shadow-lg">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-[#10B981]/15 text-[#34D399]">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-extrabold">Cryptographic Integrity Verification</h3>
                <p className="text-xs text-[#A5A29C]">
                  Mathematically verified signature issued by the institutional Ed25519 private key.
                </p>
              </div>
            </div>

            <span
              className={`rounded-full px-3 py-1 text-xs font-mono font-bold ${
                verified?.is_valid ? "badge-success" : "badge-warning"
              }`}
            >
              {verified ? verified.verification_status : "Verifying Signature..."}
            </span>
          </div>

          <p className="mt-3 text-xs leading-relaxed text-[#A5A29C]">
            {verified?.message ||
              "Cryptographic integrity is being evaluated against registered institutional public keys."}
          </p>

          <div className="mt-4 rounded-xl p-3.5 space-y-1.5 font-mono text-[11px] bg-[#121212] border border-[#292929]">
            <p className="break-all text-[#A5A29C]">
              <strong className="text-[#F7F4EF]">Payload Digest (SHA-256):</strong>{" "}
              {certificate.payload_digest}
            </p>
            <p className="text-[#A5A29C]">
              <strong className="text-[#F7F4EF]">Algorithm:</strong> {certificate.algorithm} ·{" "}
              <strong className="text-[#F7F4EF]">Key Identifier:</strong> {certificate.key_id}
            </p>
            <p className="break-all text-[#77736D]">
              <strong className="text-[#F7F4EF]">Signature:</strong> {certificate.signature}
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
        <main className="flex min-h-screen items-center justify-center bg-[#101010]">
          <p className="text-xs font-mono font-semibold text-[#A5A29C]">Loading certificate credential...</p>
        </main>
      }
    >
      <CertificatePageContent />
    </Suspense>
  );
}
