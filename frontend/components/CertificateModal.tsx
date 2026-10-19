"use client";

import React, { useState } from "react";
import { X, Download, ExternalLink, ShieldCheck, Check } from "lucide-react";
import { CertificateRenderer, downloadCertificatePdf } from "./CertificateRenderer";

export interface CertificateModalProps {
  certificate: {
    id: string;
    student_name?: string;
    course_name?: string;
    course_code?: string;
    completed_practicals_count?: number;
    total_practicals_count?: number;
    completed_at?: string;
    issued_at?: string;
    issuer?: string;
    status?: string;
  } | null;
  onClose: () => void;
}

export function CertificateModal({ certificate, onClose }: CertificateModalProps) {
  const [downloading, setDownloading] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!certificate) return null;

  const handleDownloadPdf = async () => {
    try {
      setDownloading(true);
      const cleanName = (certificate.course_code || certificate.course_name || "certificate")
        .toLowerCase()
        .replace(/[^a-z0-9]/g, "-");
      await downloadCertificatePdf(certificate, `CredLab-Certificate-${cleanName}.pdf`);
    } catch (err) {
      console.error("Failed to generate PDF", err);
      // Fallback to window.print if needed
      window.print();
    } finally {
      setDownloading(false);
    }
  };

  const handleCopyVerifyUrl = () => {
    if (typeof window !== "undefined") {
      const url = `${window.location.origin}/certificates/${certificate.id}`;
      navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="cert-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/85 backdrop-blur-md animate-fade-in overflow-y-auto"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-4xl rounded-3xl bg-[#141416] border border-[#2E2E32] p-5 sm:p-7 shadow-2xl text-white my-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          aria-label="Close modal"
          className="absolute top-4 right-4 p-2 rounded-full text-zinc-400 hover:text-white hover:bg-zinc-800 transition"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#FF7A18]">
          <ShieldCheck className="w-4 h-4" />
          <span>Official Digital Completion Credential</span>
        </div>
        <h2 id="cert-modal-title" className="mt-1 text-lg sm:text-xl font-extrabold text-white">
          {certificate.course_name || "Subject Completion Certificate"}
        </h2>

        {/* Certificate Landscape Renderer */}
        <div className="mt-4 sm:mt-6 rounded-2xl overflow-hidden shadow-2xl border border-zinc-800/80 bg-[#1A1A1C]">
          <CertificateRenderer
            certificateId={certificate.id}
            studentName={certificate.student_name || "Student"}
            courseName={certificate.course_name || "Subject Assessment"}
            courseCode={certificate.course_code}
            completedPracticalsCount={certificate.completed_practicals_count}
            totalPracticalsCount={certificate.total_practicals_count}
            completedAt={certificate.completed_at}
            issuedAt={certificate.issued_at}
            issuer={certificate.issuer || "CredLab Academic Sentinel"}
            status="Verified & Issued"
          />
        </div>

        {/* Footer Actions */}
        <div className="mt-5 sm:mt-6 flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-zinc-800/80">
          <div className="text-xs text-zinc-400 flex items-center gap-1.5 font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Ed25519 Cryptographically Signed &amp; Tamper-Evident</span>
          </div>

          <div className="flex items-center gap-2.5 w-full sm:w-auto">
            <button
              onClick={handleCopyVerifyUrl}
              className="flex-1 sm:flex-none py-2.5 px-3.5 rounded-xl text-xs font-semibold bg-zinc-800 text-zinc-200 hover:bg-zinc-700 hover:text-white border border-zinc-700 transition flex items-center justify-center gap-1.5 cursor-pointer"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <ExternalLink className="w-3.5 h-3.5" />}
              <span>{copied ? "Verification Link Copied!" : "Copy Verification URL"}</span>
            </button>
            <button
              onClick={handleDownloadPdf}
              disabled={downloading}
              className="flex-1 sm:flex-none py-2.5 px-4 rounded-xl text-xs font-bold bg-gradient-to-r from-[#FF7A18] to-[#E65100] text-white hover:brightness-110 shadow-lg shadow-orange-500/20 transition flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
            >
              <Download className="w-3.5 h-3.5" />
              <span>{downloading ? "Generating PDF..." : "Download Official PDF"}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
