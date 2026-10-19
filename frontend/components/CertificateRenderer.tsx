"use client";

import React, { useEffect, useId, useState } from "react";
import QRCode from "qrcode";
import { jsPDF } from "jspdf";

export interface CertificateProps {
  certificateId: string;
  studentName: string;
  courseName: string;
  courseCode?: string;
  completedPracticalsCount?: number | string;
  totalPracticalsCount?: number | string;
  completedAt?: string;
  issuedAt?: string;
  issuer?: string;
  status?: string;
  verifyUrl?: string;
  className?: string;
}

export function CertificateRenderer({
  certificateId,
  studentName,
  courseName,
  courseCode,
  completedPracticalsCount = 8,
  totalPracticalsCount = 8,
  completedAt,
  issuedAt,
  issuer = "CredLab Platform",
  status = "Verified & Issued",
  verifyUrl,
  className = "",
}: CertificateProps) {
  const uniqueId = useId().replace(/:/g, "_");
  const [qrDataUrl, setQrDataUrl] = useState<string>("");

  const effectiveVerifyUrl =
    verifyUrl ||
    (typeof window !== "undefined"
      ? `${window.location.origin}/certificates/${certificateId}`
      : `https://credlab.io/verify/${certificateId}`);

  // Generate QR Code data URL
  useEffect(() => {
    let cancelled = false;
    QRCode.toDataURL(effectiveVerifyUrl, {
      margin: 1,
      width: 200,
      color: { dark: "#0F172A", light: "#FFFFFF" },
    })
      .then((url) => {
        if (!cancelled) setQrDataUrl(url);
      })
      .catch((err) => {
        console.error("QR Code generation error", err);
      });
    return () => {
      cancelled = true;
    };
  }, [effectiveVerifyUrl]);

  // Format Date (e.g. "15 Oct 2025")
  const dateObj = issuedAt ? new Date(issuedAt) : (completedAt ? new Date(completedAt) : new Date());
  const dateStr = !isNaN(dateObj.getTime())
    ? dateObj.toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric" })
    : "15 Oct 2025";

  // Formatted Certificate ID (e.g. CL-DSA-2025-000123)
  const codePart = (courseCode || "CS").replace(/[^a-zA-Z0-9]/g, "").slice(0, 4).toUpperCase() || "SUBJ";
  const yearPart = dateObj.getFullYear() || 2026;
  const numPart = certificateId ? certificateId.replace(/[^0-9]/g, "").slice(0, 6).padStart(6, "0") || "000123" : "000123";
  const displayCertId = `CL-${codePart}-${yearPart}-${numPart}`;

  const practicalsCountStr = `${completedPracticalsCount || totalPracticalsCount || 8} / ${totalPracticalsCount || 8} Completed`;

  const topGradId = `cert-top-grad-${uniqueId}`;
  const orangeWaveGradId = `cert-orange-wave-${uniqueId}`;
  const goldWaveGradId = `cert-gold-wave-${uniqueId}`;
  const sealGradId = `cert-seal-grad-${uniqueId}`;
  const borderGradId = `cert-border-grad-${uniqueId}`;

  return (
    <div className={`relative w-full overflow-hidden select-none ${className}`} style={{ aspectRatio: "1000 / 667" }}>
      <svg
        id={`cert-svg-${uniqueId}`}
        viewBox="0 0 1000 667"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full drop-shadow-2xl"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          {/* Border Gradient */}
          <linearGradient id={borderGradId} x1="0" y1="0" x2="1000" y2="667" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#FF7A18" />
            <stop offset="50%" stopColor="#E65100" />
            <stop offset="100%" stopColor="#FF8F1C" />
          </linearGradient>

          {/* Top Banner Wave Gradient */}
          <linearGradient id={topGradId} x1="0" y1="0" x2="800" y2="250" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#141312" />
            <stop offset="60%" stopColor="#1B1A18" />
            <stop offset="100%" stopColor="#25221F" />
          </linearGradient>

          {/* Orange Wave Gradient */}
          <linearGradient id={orangeWaveGradId} x1="100" y1="120" x2="900" y2="240" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#FF7A18" />
            <stop offset="50%" stopColor="#E65100" />
            <stop offset="100%" stopColor="#BF360C" />
          </linearGradient>

          {/* Gold Amber Wave Gradient */}
          <linearGradient id={goldWaveGradId} x1="200" y1="100" x2="950" y2="280" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#FFB300" />
            <stop offset="60%" stopColor="#FFA000" />
            <stop offset="100%" stopColor="#FF6F00" />
          </linearGradient>

          {/* Seal Starburst Gradient */}
          <linearGradient id={sealGradId} x1="0" y1="0" x2="120" y2="120" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#F59E0B" />
            <stop offset="50%" stopColor="#D97706" />
            <stop offset="100%" stopColor="#B45309" />
          </linearGradient>

          {/* Outer Card Clip */}
          <clipPath id={`cert-clip-${uniqueId}`}>
            <rect x="8" y="8" width="984" height="651" rx="28" ry="28" />
          </clipPath>

          {/* Soft Shadow Filter */}
          <filter id={`cert-shadow-${uniqueId}`} x="-10%" y="-10%" width="120%" height="120%">
            <feDropShadow dx="0" dy="4" stdDeviation="6" floodColor="#000000" floodOpacity="0.25" />
          </filter>
        </defs>

        {/* ────── MAIN CLIPPED CERTIFICATE BODY ────── */}
        <g clipPath={`url(#cert-clip-${uniqueId})`}>
          {/* Base Background: Warm parchment / linen */}
          <rect x="8" y="8" width="984" height="651" fill="#FDFBF7" />

          {/* Very subtle warm linen texture gradient */}
          <linearGradient id={`parchment-grad-${uniqueId}`} x1="0" y1="0" x2="1000" y2="667" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#FFFDF9" />
            <stop offset="60%" stopColor="#FDFBF7" />
            <stop offset="100%" stopColor="#F7F1E5" />
          </linearGradient>
          <rect x="8" y="8" width="984" height="651" fill={`url(#parchment-grad-${uniqueId})`} />

          {/* ────── TOP DARK & ORANGE FLOWING WAVES BANNER ────── */}
          {/* Wave Layer 1: Gold Amber background wave */}
          <path
            d="M 8 8 L 992 8 L 992 205 C 870 215, 760 170, 640 220 C 500 275, 340 220, 180 200 C 100 190, 50 210, 8 220 Z"
            fill={`url(#${goldWaveGradId})`}
          />

          {/* Wave Layer 2: Vivid Fiery Orange mid wave */}
          <path
            d="M 8 8 L 992 8 L 992 190 C 850 190, 780 150, 660 195 C 520 248, 380 205, 210 180 C 110 165, 50 180, 8 195 Z"
            fill={`url(#${orangeWaveGradId})`}
          />

          {/* Wave Layer 3: Deep Dark Chocolate/Charcoal Banner */}
          <path
            d="M 8 8 L 992 8 L 992 155 C 870 155, 780 120, 670 165 C 530 215, 390 175, 220 150 C 120 135, 60 150, 8 165 Z"
            fill={`url(#${topGradId})`}
          />

          {/* Extra dark swoosh contour */}
          <path
            d="M 8 8 L 560 8 C 500 90, 420 150, 260 145 C 150 140, 70 160, 8 180 Z"
            fill="#0E0D0C"
            opacity="0.8"
          />

          {/* ────── TOP BRANDING & CERTIFICATE ID ────── */}
          {/* CredLab Angular Logo Chevrons */}
          <g transform="translate(56, 42)">
            {/* Left Chevron < */}
            <path
              d="M 18 10 L 6 23 L 18 36"
              stroke="#FF7A18"
              strokeWidth="5"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
            {/* Right Chevron > */}
            <path
              d="M 32 10 L 44 23 L 32 36"
              stroke="#FF7A18"
              strokeWidth="5"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
            {/* Wordmark CredLab */}
            <text
              x="56"
              y="31"
              fill="#FFFFFF"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontWeight="800"
              fontSize="28"
              letterSpacing="-0.5"
            >
              Cred<tspan fill="#FF7A18">Lab</tspan>
            </text>

            {/* Vertical Separator */}
            <line x1="205" y1="8" x2="205" y2="40" stroke="#52525B" strokeWidth="1.2" />

            {/* Subtitle Lines */}
            <text
              x="220"
              y="18"
              fill="#D4D4D8"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="11"
              fontWeight="600"
              letterSpacing="0.2"
            >
              Secure Coding
            </text>
            <text
              x="220"
              y="30"
              fill="#D4D4D8"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="11"
              fontWeight="600"
              letterSpacing="0.2"
            >
              Assessment
            </text>
            <text
              x="220"
              y="42"
              fill="#D4D4D8"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="11"
              fontWeight="600"
              letterSpacing="0.2"
            >
              Platform
            </text>
          </g>

          {/* Certificate ID on Top Right */}
          <g transform="translate(930, 48)" textAnchor="end">
            <text
              x="0"
              y="12"
              fill="#A1A1AA"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="10"
              fontWeight="700"
              letterSpacing="1"
            >
              CERTIFICATE ID
            </text>
            <text
              x="0"
              y="28"
              fill="#F4F4F5"
              fontFamily="'SF Mono', Menlo, Consolas, Monaco, monospace"
              fontSize="13"
              fontWeight="600"
              letterSpacing="0.5"
            >
              {displayCertId}
            </text>
          </g>

          {/* ────── CERTIFICATE HEADLINE ────── */}
          <g transform="translate(68, 142)">
            <text
              x="0"
              y="0"
              fill="#FFFFFF"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="44"
              fontWeight="800"
              letterSpacing="-0.8"
            >
              Certificate
            </text>
            <text
              x="0"
              y="40"
              fill="#FF6B2C"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="38"
              fontWeight="800"
              letterSpacing="-0.5"
            >
              of Subject Completion
            </text>
          </g>

          {/* ────── RECIPIENT & SUBJECT PRESENTATION ────── */}
          <g transform="translate(74, 240)">
            {/* Proudly presented to */}
            <text
              x="0"
              y="0"
              fill="#64748B"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="15"
              fontWeight="500"
            >
              This certificate is proudly presented to
            </text>

            {/* Recipient Full Name */}
            <text
              x="0"
              y="42"
              fill="#0F172A"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="40"
              fontWeight="900"
              letterSpacing="-0.5"
            >
              {studentName || "Student Name"}
            </text>

            {/* Underline accent line */}
            <line x1="0" y1="56" x2="570" y2="56" stroke="#E28639" strokeWidth="1.5" strokeOpacity="0.75" />

            {/* For successfully completing */}
            <text
              x="0"
              y="82"
              fill="#475569"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="14.5"
              fontWeight="500"
            >
              for successfully completing all required practicals and assessments in the subject
            </text>

            {/* Subject Name */}
            <text
              x="0"
              y="114"
              fill="#0F172A"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="22"
              fontWeight="800"
            >
              {courseName || "Data Structures and Algorithms"}
            </text>

            {/* Standard accredited description */}
            <text
              x="0"
              y="138"
              fill="#64748B"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="12.5"
              fontWeight="400"
            >
              This certification demonstrates proficiency in problem-solving, algorithmic thinking
            </text>
            <text
              x="0"
              y="156"
              fill="#64748B"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="12.5"
              fontWeight="400"
            >
              and practical implementation of core data structures and verified algorithms.
            </text>
          </g>

          {/* ────── 3-COLUMN METRIC BAR ────── */}
          <g transform="translate(74, 436)">
            {/* Column 1: Date */}
            <g transform="translate(0, 0)">
              {/* Calendar Icon SVG */}
              <g transform="translate(0, 4)">
                <rect x="0" y="0" width="22" height="20" rx="4" stroke="#FF6B2C" strokeWidth="2" fill="none" />
                <line x1="0" y1="6" x2="22" y2="6" stroke="#FF6B2C" strokeWidth="2" />
                <circle cx="6" cy="11" r="1.5" fill="#FF6B2C" />
                <circle cx="11" cy="11" r="1.5" fill="#FF6B2C" />
                <circle cx="16" cy="11" r="1.5" fill="#FF6B2C" />
                <line x1="5" y1="-2" x2="5" y2="2" stroke="#FF6B2C" strokeWidth="2" strokeLinecap="round" />
                <line x1="17" y1="-2" x2="17" y2="2" stroke="#FF6B2C" strokeWidth="2" strokeLinecap="round" />
              </g>
              <text
                x="32"
                y="11"
                fill="#64748B"
                fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
                fontSize="9.5"
                fontWeight="700"
                letterSpacing="0.8"
              >
                DATE OF COMPLETION
              </text>
              <text
                x="32"
                y="27"
                fill="#1E293B"
                fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
                fontSize="14"
                fontWeight="700"
              >
                {dateStr}
              </text>
            </g>

            {/* Column 1 to 2 separator */}
            <line x1="200" y1="2" x2="200" y2="34" stroke="#E2E8F0" strokeWidth="1" />

            {/* Column 2: Total Practicals */}
            <g transform="translate(230, 0)">
              {/* Book Icon SVG */}
              <g transform="translate(0, 4)">
                <path
                  d="M 2 3 C 7 1, 10 3, 11 4 C 12 3, 15 1, 20 3 L 20 18 C 15 16, 12 18, 11 19 C 10 18, 7 16, 2 18 Z"
                  stroke="#FF6B2C"
                  strokeWidth="2"
                  fill="none"
                />
                <line x1="11" y1="4" x2="11" y2="19" stroke="#FF6B2C" strokeWidth="2" />
              </g>
              <text
                x="32"
                y="11"
                fill="#64748B"
                fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
                fontSize="9.5"
                fontWeight="700"
                letterSpacing="0.8"
              >
                TOTAL PRACTICALS
              </text>
              <text
                x="32"
                y="27"
                fill="#1E293B"
                fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
                fontSize="14"
                fontWeight="700"
              >
                {practicalsCountStr}
              </text>
            </g>

            {/* Column 2 to 3 separator */}
            <line x1="430" y1="2" x2="430" y2="34" stroke="#E2E8F0" strokeWidth="1" />

            {/* Column 3: Status */}
            <g transform="translate(460, 0)">
              {/* Shield Checkmark Icon SVG */}
              <g transform="translate(0, 4)">
                <path
                  d="M 11 2 L 20 5 L 20 11 C 20 16, 16 19, 11 21 C 6 19, 2 16, 2 11 L 2 5 Z"
                  stroke="#FF6B2C"
                  strokeWidth="2"
                  fill="none"
                />
                <path d="M 7 11 L 10 14 L 15 8" stroke="#FF6B2C" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </g>
              <text
                x="30"
                y="11"
                fill="#64748B"
                fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
                fontSize="9.5"
                fontWeight="700"
                letterSpacing="0.8"
              >
                STATUS
              </text>
              <text
                x="30"
                y="27"
                fill="#1E293B"
                fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
                fontSize="14"
                fontWeight="700"
              >
                {status}
              </text>
            </g>
          </g>

          {/* ────── GOLD & BLACK MEDALLION SEAL (MID-RIGHT) ────── */}
          <g transform="translate(860, 310)" filter={`url(#cert-shadow-${uniqueId})`}>
            {/* Dual Hanging Dark Ribbon Tails with Orange Trim */}
            <g>
              {/* Left Ribbon Tail */}
              <polygon
                points="-52,38 -20,135 -38,125 -62,145 -78,45"
                fill="#161514"
                stroke="#FF7A18"
                strokeWidth="1.5"
              />
              {/* Right Ribbon Tail */}
              <polygon
                points="52,38 20,135 38,125 62,145 78,45"
                fill="#161514"
                stroke="#FF7A18"
                strokeWidth="1.5"
              />
            </g>

            {/* Serrated Starburst Gold Outer Ring (32 teeth) */}
            <path
              d={createStarburstPath(0, 0, 82, 70, 32)}
              fill={`url(#${sealGradId})`}
              stroke="#B45309"
              strokeWidth="2"
            />

            {/* Middle Gold Border Ring */}
            <circle cx="0" cy="0" r="64" fill="#0D0C0B" stroke="#F59E0B" strokeWidth="2.5" />

            {/* Inner Dark Circle */}
            <circle cx="0" cy="0" r="58" fill="#181716" />

            {/* Orange CredLab Chevrons in Center of Seal */}
            <g transform="translate(-16, -34)">
              <path
                d="M 12 4 L 4 13 L 12 22"
                stroke="#FF7A18"
                strokeWidth="3.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                fill="none"
              />
              <path
                d="M 20 4 L 28 13 L 20 22"
                stroke="#FF7A18"
                strokeWidth="3.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                fill="none"
              />
            </g>

            {/* Seal Text: CredLab */}
            <text
              x="0"
              y="-1"
              textAnchor="middle"
              fill="#FFFFFF"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="17"
              fontWeight="900"
              letterSpacing="0.2"
            >
              Cred<tspan fill="#FF7A18">Lab</tspan>
            </text>

            {/* Thin Gold Separator inside Seal */}
            <line x1="-30" y1="8" x2="30" y2="8" stroke="#D97706" strokeWidth="1" />

            {/* Seal Text: SUBJECT COMPLETION */}
            <text
              x="0"
              y="20"
              textAnchor="middle"
              fill="#E2E8F0"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="8.5"
              fontWeight="800"
              letterSpacing="1"
            >
              SUBJECT
            </text>
            <text
              x="0"
              y="31"
              textAnchor="middle"
              fill="#E2E8F0"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="8.5"
              fontWeight="800"
              letterSpacing="1"
            >
              COMPLETION
            </text>

            {/* Star ★ */}
            <text
              x="0"
              y="45"
              textAnchor="middle"
              fill="#F59E0B"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="12"
            >
              ★
            </text>
          </g>

          {/* ────── BOTTOM DARK WAVES & FOOTER ────── */}
          {/* Bottom Layer 1: Orange Wave underlay */}
          <path
            d="M 8 520 C 180 500, 320 540, 500 520 C 680 500, 820 530, 992 480 L 992 659 L 8 659 Z"
            fill={`url(#${orangeWaveGradId})`}
          />

          {/* Bottom Layer 2: Deep Dark Charcoal Footer */}
          <path
            d="M 8 535 C 180 515, 320 555, 500 535 C 680 515, 820 545, 992 505 L 992 659 L 8 659 Z"
            fill="#121110"
          />

          {/* Left Signature: Head of Department */}
          <g transform="translate(74, 538)">
            {/* Elegant Script Cursive Signature */}
            <path
              d="M 10 32 C 25 15, 45 10, 60 22 C 70 30, 65 42, 85 28 C 98 18, 105 28, 120 22 C 130 18, 140 28, 150 20"
              stroke="#FFFFFF"
              strokeWidth="2.5"
              strokeLinecap="round"
              fill="none"
              opacity="0.9"
            />
            {/* Signature Underline */}
            <line x1="0" y1="46" x2="180" y2="46" stroke="#52525B" strokeWidth="1" />
            <text
              x="0"
              y="62"
              fill="#F4F4F5"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="13"
              fontWeight="700"
            >
              Head of Department
            </text>
            <text
              x="0"
              y="76"
              fill="#A1A1AA"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="11"
              fontWeight="500"
            >
              {issuer}
            </text>
          </g>

          {/* Center Signature: Dean Academics */}
          <g transform="translate(320, 538)">
            {/* Elegant Script Cursive Signature */}
            <path
              d="M 12 36 C 25 18, 38 12, 55 24 C 65 30, 75 14, 90 28 C 105 40, 115 15, 135 22 C 145 28, 155 20, 165 24"
              stroke="#FFFFFF"
              strokeWidth="2.5"
              strokeLinecap="round"
              fill="none"
              opacity="0.9"
            />
            {/* Signature Underline */}
            <line x1="0" y1="46" x2="180" y2="46" stroke="#52525B" strokeWidth="1" />
            <text
              x="0"
              y="62"
              fill="#F4F4F5"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="13"
              fontWeight="700"
            >
              Dean Academics
            </text>
            <text
              x="0"
              y="76"
              fill="#A1A1AA"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="11"
              fontWeight="500"
            >
              {issuer}
            </text>
          </g>

          {/* Right Verification QR Code Box */}
          <g transform="translate(765, 546)">
            {/* QR Code White Container */}
            <rect x="0" y="0" width="76" height="76" rx="10" fill="#FFFFFF" />
            {qrDataUrl ? (
              <image href={qrDataUrl} x="4" y="4" width="68" height="68" />
            ) : (
              <rect x="8" y="8" width="60" height="60" fill="#E2E8F0" rx="6" />
            )}

            {/* Verification Link text beside QR Code */}
            <text
              x="88"
              y="32"
              fill="#A1A1AA"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="11"
              fontWeight="500"
            >
              Verify this certificate at
            </text>
            <text
              x="88"
              y="48"
              fill="#FF7A18"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontSize="12.5"
              fontWeight="800"
            >
              credlab.io/verify
            </text>
          </g>
        </g>

        {/* Outer Warm Gold/Orange Rim */}
        <rect
          x="8"
          y="8"
          width="984"
          height="651"
          rx="28"
          ry="28"
          fill="none"
          stroke={`url(#${borderGradId})`}
          strokeWidth="6"
        />
      </svg>
    </div>
  );
}

/**
 * Creates SVG path for a circular serrated starburst seal
 */
function createStarburstPath(cx: number, cy: number, rOuter: number, rInner: number, points: number): string {
  let path = "";
  const step = Math.PI / points;
  for (let i = 0; i < 2 * points; i++) {
    const r = i % 2 === 0 ? rOuter : rInner;
    const angle = i * step - Math.PI / 2;
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);
    if (i === 0) {
      path += `M ${x.toFixed(2)} ${y.toFixed(2)}`;
    } else {
      path += ` L ${x.toFixed(2)} ${y.toFixed(2)}`;
    }
  }
  path += " Z";
  return path;
}

/**
 * High-definition PDF generation using jsPDF
 */
export async function downloadCertificatePdf(
  cert: {
    id: string;
    student_name?: string;
    course_name?: string;
    course_code?: string;
    issued_at?: string;
  },
  filename = "CredLab-Certificate.pdf"
): Promise<void> {
  const svgEl = document.querySelector(`svg[id^="cert-svg-"]`) as SVGSVGElement | null;
  if (!svgEl) {
    window.print();
    return;
  }

  // Serialize the SVG into a data URL
  const serializer = new XMLSerializer();
  let svgStr = serializer.serializeToString(svgEl);

  // Ensure xmlns is present
  if (!svgStr.match(/^<svg[^>]+xmlns="http:\/\/www\.w3\.org\/2000\/svg"/)) {
    svgStr = svgStr.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
  }

  const canvas = document.createElement("canvas");
  canvas.width = 2000;
  canvas.height = 1334;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const blob = new Blob([svgStr], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const img = new Image();

  return new Promise<void>((resolve, reject) => {
    img.onload = () => {
      ctx.drawImage(img, 0, 0, 2000, 1334);
      URL.revokeObjectURL(url);

      const imgData = canvas.toDataURL("image/jpeg", 0.95);
      const pdf = new jsPDF({
        orientation: "landscape",
        unit: "pt",
        format: [1000, 667],
      });

      pdf.addImage(imgData, "JPEG", 0, 0, 1000, 667);
      pdf.save(filename);
      resolve();
    };
    img.onerror = (e) => {
      URL.revokeObjectURL(url);
      reject(e);
    };
    img.src = url;
  });
}
