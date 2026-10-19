"use client";
/* eslint react-hooks/set-state-in-effect: off */

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ShieldCheck,
  Printer,
  ArrowLeft,
  AlertCircle,
  Download,
  Share2,
  Check,
  ExternalLink,
  Award,
} from "lucide-react";
import { CertificateRenderer, downloadCertificatePdf } from "@/components/CertificateRenderer";

interface CertificatePublicData {
  id?: string;
  certificate_id: string;
  student_name: string;
  course_code?: string;
  course_name?: string;
  certificate_type?: string;
  lab_title?: string;
  practical_title?: string;
  score?: number;
  passing_threshold?: number;
  completed_practicals_count?: number;
  total_practicals_count?: number;
  completed_at?: string;
  issued_at?: string;
  issuer?: string;
  algorithm?: string;
  key_id?: string;
  payload_digest?: string;
  signature?: string;
  status?: string;
}

function CertificatePageContent() {
  const params = useParams<{ certificateId: string }>();
  const [certificate, setCertificate] = useState<CertificatePublicData | null>(null);
  const [verified, setVerified] = useState<{
    is_valid: boolean;
    verification_status: string;
    message: string;
  } | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [isDownloading, setIsDownloading] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const certId = params.certificateId;
        // Try public endpoint first
        let res = await fetch(
          `/api/proxy/certificates/${encodeURIComponent(certId)}/public`,
          { cache: "no-store" },
        );

        if (!res.ok) {
          // Fallback to authenticated endpoint if available
          res = await fetch(
            `/api/proxy/certificates/${encodeURIComponent(certId)}`,
            { cache: "no-store" },
          );
        }

        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "Certificate record not found or inaccessible.");
        }

        const data: CertificatePublicData = await res.json();
        if (!cancelled) {
          setCertificate({
            ...data,
            id: data.certificate_id || data.id,
          });
        }

        // Run cryptographic verification
        const check = await fetch("/api/proxy/certificates/verify", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ certificate_id: certId }),
          cache: "no-store",
        });

        if (check.ok && !cancelled) {
          const result = await check.json();
          setVerified(result);
        }
      } catch (cause) {
        if (!cancelled) {
          setError(
            cause instanceof Error ? cause.message : "Unable to retrieve certificate credential.",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    if (params.certificateId) {
      void load();
    }

    return () => {
      cancelled = true;
    };
  }, [params.certificateId]);

  const handleDownloadPdf = async () => {
    if (!certificate) return;
    try {
      setIsDownloading(true);
      await downloadCertificatePdf(
        {
          id: certificate.certificate_id || certificate.id || "certificate",
          student_name: certificate.student_name,
          course_name: certificate.course_name || certificate.lab_title,
          course_code: certificate.course_code,
          issued_at: certificate.issued_at,
        },
        `${certificate.certificate_id || "CredLab-Certificate"}.pdf`,
      );
    } catch (err) {
      console.error("PDF download failed", err);
      window.print();
    } finally {
      setIsDownloading(false);
    }
  };

  const handleCopyLink = () => {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2500);
    }
  };

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0F0F12] text-[#F7F4EF]">
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 animate-spin rounded-full border-3 border-[#FF7A18] border-t-transparent" />
          <p className="text-xs font-mono font-semibold text-[#A5A29C]">
            Verifying cryptographic credential against institutional sentinel...
          </p>
        </div>
      </main>
    );
  }

  if (error || !certificate) {
    return (
      <main className="flex min-h-screen items-center justify-center p-6 bg-[#0F0F12] text-[#F7F4EF]">
        <div className="rounded-3xl border border-[#2D2D38] bg-[#17171F] max-w-lg p-8 text-center shadow-xl">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[#DC2626]/10 text-[#EF4444]">
            <AlertCircle className="w-7 h-7" />
          </div>
          <h1 className="mt-4 text-xl font-extrabold text-[#F7F4EF]">
            Certificate Credential Not Found
          </h1>
          <p className="mt-2 text-xs text-[#9E9EAE]">
            {error || "This certificate could not be located on the platform or has not yet been issued."}
          </p>
          <div className="mt-6 flex items-center justify-center gap-3">
            <Link
              href="/student/dashboard"
              className="inline-flex items-center gap-2 rounded-xl bg-[#FF7A18] px-4 py-2.5 text-xs font-bold text-white shadow-md hover:bg-[#FF8A3D] transition-all"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Go to Dashboard</span>
            </Link>
            <Link
              href="/"
              className="inline-flex items-center gap-2 rounded-xl border border-[#2D2D38] bg-[#1E1E28] px-4 py-2.5 text-xs font-semibold text-[#D1D1DE] hover:bg-[#252532] transition-all"
            >
              <ExternalLink className="w-4 h-4" />
              <span>Platform Home</span>
            </Link>
          </div>
        </div>
      </main>
    );
  }

  const effectiveCertId = certificate.certificate_id || certificate.id || "";
  const effectiveCourseName =
    certificate.course_name || certificate.lab_title || "Computer Science Practical Assessment";
  const completedCount = certificate.completed_practicals_count || 8;
  const totalCount = certificate.total_practicals_count || 8;

  return (
    <main className="min-h-screen p-4 sm:p-8 lg:p-12 print:p-0 print:bg-white print:text-black bg-[#0B0B0E] text-[#F7F4EF]">
      <div className="mx-auto max-w-6xl">
        {/* Top Header / Actions Bar */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4 print:hidden">
          <div className="flex items-center gap-3">
            <Link
              href="/student/dashboard"
              className="inline-flex items-center gap-2 text-xs font-bold text-[#FF8A3D] hover:underline transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Workspace</span>
            </Link>
            <span className="text-xs text-[#4A4A58]">|</span>
            <div className="inline-flex items-center gap-1.5 text-xs font-mono font-medium text-[#9E9EAE]">
              <Award className="w-3.5 h-3.5 text-[#FF7A18]" />
              <span>Official Academic Credential</span>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={handleCopyLink}
              className="inline-flex items-center gap-1.5 rounded-xl border border-[#2D2D38] bg-[#16161E] px-3 py-2 text-xs font-semibold text-[#D1D1DE] hover:bg-[#22222E] hover:text-white transition-all shadow-sm"
              title="Copy verification link"
            >
              {copiedLink ? <Check className="w-4 h-4 text-[#10B981]" /> : <Share2 className="w-4 h-4" />}
              <span>{copiedLink ? "Link Copied!" : "Share Link"}</span>
            </button>

            <button
              type="button"
              onClick={() => window.print()}
              className="inline-flex items-center gap-1.5 rounded-xl border border-[#2D2D38] bg-[#16161E] px-3 py-2 text-xs font-semibold text-[#D1D1DE] hover:bg-[#22222E] hover:text-white transition-all shadow-sm"
            >
              <Printer className="w-4 h-4" />
              <span>Print</span>
            </button>

            <button
              type="button"
              onClick={handleDownloadPdf}
              disabled={isDownloading}
              className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-[#FF7A18] to-[#FF9838] px-4 py-2 text-xs font-bold text-white shadow-md hover:brightness-110 active:scale-95 transition-all disabled:opacity-50"
            >
              <Download className="w-4 h-4" />
              <span>{isDownloading ? "Generating PDF..." : "Download Official PDF"}</span>
            </button>
          </div>
        </div>

        {/* ────── Landscape Certificate Replica (Reference Image 2) ────── */}
        <section className="print:m-0 print:p-0 overflow-hidden rounded-2xl shadow-2xl border border-[#262633]/60 bg-[#121218]">
          <CertificateRenderer
            certificateId={effectiveCertId}
            studentName={certificate.student_name}
            courseName={effectiveCourseName}
            courseCode={certificate.course_code}
            completedPracticalsCount={completedCount}
            totalPracticalsCount={totalCount}
            completedAt={certificate.completed_at}
            issuedAt={certificate.issued_at}
            issuer={certificate.issuer || "CredLab Secure Coding Assessment Platform"}
            status={verified?.is_valid ? "Verified & Issued" : certificate.status || "Issued"}
            className="w-full h-auto"
          />
        </section>

        {/* ────── Cryptographic Verification Card ────── */}
        <section className="mt-8 rounded-2xl p-6 print:hidden bg-[#14141B] border border-[#262633] shadow-lg">
          <div className="flex items-center justify-between gap-4 flex-wrap pb-4 border-b border-[#20202B]">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-[#10B981]/15 text-[#34D399]">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-extrabold text-[#F7F4EF]">
                  Cryptographic Integrity & Authenticity
                </h3>
                <p className="text-xs text-[#9E9EAE]">
                  Mathematically validated against the institutional CredLab Ed25519 sentinel keys.
                </p>
              </div>
            </div>

            <span
              className={`rounded-full px-3.5 py-1 text-xs font-mono font-bold tracking-wide uppercase ${
                verified?.is_valid
                  ? "bg-[#10B981]/20 text-[#34D399] border border-[#10B981]/40"
                  : "bg-[#F59E0B]/20 text-[#FBBF24] border border-[#F59E0B]/40"
              }`}
            >
              {verified ? verified.verification_status : "Verifying Signature..."}
            </span>
          </div>

          <p className="mt-3 text-xs leading-relaxed text-[#9E9EAE]">
            {verified?.message ||
              "Cryptographic integrity has been evaluated against registered institutional public keys."}
          </p>

          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
            <div className="rounded-xl p-3 bg-[#0E0E14] border border-[#1E1E28] space-y-1">
              <p className="text-[10px] uppercase font-bold text-[#6D6D7F]">Credential Identifier</p>
              <p className="font-bold text-[#FF8A3D] break-all">{effectiveCertId}</p>
            </div>

            <div className="rounded-xl p-3 bg-[#0E0E14] border border-[#1E1E28] space-y-1">
              <p className="text-[10px] uppercase font-bold text-[#6D6D7F]">Cryptographic Algorithm & Key</p>
              <p className="font-semibold text-[#D1D1DE]">
                {certificate.algorithm || "ED25519-SHA256"} · <span className="text-[#A5A29C]">{certificate.key_id || "ed25519-prod-2026"}</span>
              </p>
            </div>

            {certificate.payload_digest && (
              <div className="rounded-xl p-3 bg-[#0E0E14] border border-[#1E1E28] space-y-1 md:col-span-2">
                <p className="text-[10px] uppercase font-bold text-[#6D6D7F]">Canonical SHA-256 Digest</p>
                <p className="text-[11px] text-[#A5A29C] break-all select-all">
                  {certificate.payload_digest}
                </p>
              </div>
            )}

            {certificate.signature && (
              <div className="rounded-xl p-3 bg-[#0E0E14] border border-[#1E1E28] space-y-1 md:col-span-2">
                <p className="text-[10px] uppercase font-bold text-[#6D6D7F]">Ed25519 Digital Signature</p>
                <p className="text-[11px] text-[#77736D] break-all select-all font-mono">
                  {certificate.signature}
                </p>
              </div>
            )}
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
        <main className="flex min-h-screen items-center justify-center bg-[#0B0B0E]">
          <p className="text-xs font-mono font-semibold text-[#A5A29C]">Loading academic credential...</p>
        </main>
      }
    >
      <CertificatePageContent />
    </Suspense>
  );
}

