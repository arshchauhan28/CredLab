"use client";

import React, { useState } from "react";
import { X, Download, Share2, Check, Award, Calendar, BookOpen } from "lucide-react";
import { BadgeRenderer, downloadBadgePng } from "./BadgeRenderer";

export interface BadgeModalProps {
  badge: {
    id: number;
    name: string;
    description?: string;
    icon: string;
    earned_at: string;
    practical_id: number;
    course_id?: number | null;
    course_name?: string;
    course_code?: string;
    practical_title?: string;
  } | null;
  onClose: () => void;
}

export function BadgeModal({ badge, onClose }: BadgeModalProps) {
  const [downloading, setDownloading] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!badge) return null;

  const subject = badge.course_name || badge.name || "Curriculum Lab";
  const practical = badge.practical_title || "Practical Assessment";
  const dateFormatted = new Date(badge.earned_at).toLocaleDateString("en-US", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  const handleDownload = async () => {
    try {
      setDownloading(true);
      const cleanName = (practical || "practical").toLowerCase().replace(/[^a-z0-9]/g, "-");
      await downloadBadgePng(badge, `credlab-badge-${cleanName}.png`);
    } catch (err) {
      console.error("Failed to download badge", err);
    } finally {
      setDownloading(false);
    }
  };

  const handleCopyLink = () => {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="badge-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-lg rounded-3xl bg-[#141416] border border-[#2E2E32] p-6 sm:p-8 shadow-2xl text-white"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          aria-label="Close modal"
          className="absolute top-5 right-5 p-2 rounded-full text-zinc-400 hover:text-white hover:bg-zinc-800 transition"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-2.5 text-xs font-semibold uppercase tracking-wider text-[#FF7A18]">
          <Award className="w-4 h-4" />
          <span>CredLab Practical Achievement</span>
        </div>
        <h2 id="badge-modal-title" className="mt-1 text-xl font-extrabold text-white">
          {practical}
        </h2>

        {/* Badge Visual Render */}
        <div className="mt-6 flex justify-center py-2">
          <div className="w-64 sm:w-72 drop-shadow-2xl">
            <BadgeRenderer
              subjectName={subject}
              practicalTitle={practical}
              courseCode={badge.course_code}
              earnedAt={badge.earned_at}
            />
          </div>
        </div>

        {/* Badge Metadata Bar */}
        <div className="mt-6 grid grid-cols-2 gap-3 p-3.5 rounded-2xl bg-[#1B1B1E] border border-zinc-800/80 text-xs">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-orange-500/10 text-[#FF7A18]">
              <BookOpen className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[10px] uppercase font-bold text-zinc-400">Subject</div>
              <div className="font-semibold text-zinc-200 truncate">{subject}</div>
            </div>
          </div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-orange-500/10 text-[#FF7A18]">
              <Calendar className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[10px] uppercase font-bold text-zinc-400">Unlocked On</div>
              <div className="font-semibold text-zinc-200">{dateFormatted}</div>
            </div>
          </div>
        </div>

        {/* Verification Status Banner */}
        <div className="mt-4 flex items-center justify-between px-4 py-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-400">
          <div className="flex items-center gap-2 font-medium">
            <Check className="w-4 h-4" />
            <span>Passed Automated Assessment &amp; Tests (100% Score)</span>
          </div>
          <span className="font-mono text-[10px] text-emerald-500 font-semibold">VERIFIED</span>
        </div>

        {/* Actions */}
        <div className="mt-6 flex flex-col sm:flex-row items-center gap-3">
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="w-full sm:flex-1 py-3 px-4 rounded-xl font-bold text-sm bg-gradient-to-r from-[#FF7A18] to-[#E65100] text-white hover:brightness-110 shadow-lg shadow-orange-500/20 flex items-center justify-center gap-2 transition cursor-pointer disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            <span>{downloading ? "Exporting PNG..." : "Download Badge (PNG)"}</span>
          </button>
          <button
            onClick={handleCopyLink}
            className="w-full sm:w-auto py-3 px-4 rounded-xl font-semibold text-sm bg-zinc-800 text-zinc-200 hover:bg-zinc-700 hover:text-white border border-zinc-700 flex items-center justify-center gap-2 transition cursor-pointer"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Share2 className="w-4 h-4" />}
            <span>{copied ? "Link Copied!" : "Share"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
