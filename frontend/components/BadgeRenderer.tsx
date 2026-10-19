"use client";

import React, { useId } from "react";

export interface BadgeProps {
  subjectName: string;
  practicalTitle: string;
  courseCode?: string;
  earnedAt?: string;
  className?: string;
  size?: number | string;
}

export function BadgeRenderer({
  subjectName,
  practicalTitle,
  className = "",
  size = "100%",
}: BadgeProps) {
  const uniqueId = useId().replace(/:/g, "_");
  const borderGradId = `badge-border-${uniqueId}`;
  const goldGradId = `gold-grad-${uniqueId}`;
  const orangeGradId = `orange-grad-${uniqueId}`;
  const peachGradId = `peach-grad-${uniqueId}`;
  const shadowFilterId = `swoop-shadow-${uniqueId}`;

  // Truncate cleanly if string is too long for the badge
  const displaySubject = subjectName && subjectName.length > 28 ? subjectName.slice(0, 26) + "..." : (subjectName || "Curriculum Lab");
  const displayPractical = practicalTitle && practicalTitle.length > 34 ? practicalTitle.slice(0, 32) + "..." : (practicalTitle || "Practical Milestone");

  return (
    <div
      className={`relative inline-block select-none ${className}`}
      style={{ width: size, height: typeof size === "number" ? size : undefined, aspectRatio: "1/1" }}
    >
      <svg
        viewBox="0 0 500 500"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full drop-shadow-xl"
        preserveAspectRatio="xMidYMid meet"
        id={`svg-badge-${uniqueId}`}
      >
        <defs>
          {/* Outer Border Gradient */}
          <linearGradient id={borderGradId} x1="0" y1="0" x2="500" y2="500" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#FF7A18" />
            <stop offset="50%" stopColor="#FF6B2C" />
            <stop offset="100%" stopColor="#E65100" />
          </linearGradient>

          {/* Golden Amber Wave Gradient */}
          <linearGradient id={goldGradId} x1="50" y1="200" x2="450" y2="350" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#FFA737" />
            <stop offset="50%" stopColor="#FF8F1C" />
            <stop offset="100%" stopColor="#F57C00" />
          </linearGradient>

          {/* Fiery Orange Wave Gradient */}
          <linearGradient id={orangeGradId} x1="50" y1="240" x2="450" y2="400" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#F26A1B" />
            <stop offset="50%" stopColor="#E65100" />
            <stop offset="100%" stopColor="#C83B00" />
          </linearGradient>

          {/* Peach Highlight Gradient */}
          <linearGradient id={peachGradId} x1="25" y1="180" x2="475" y2="240" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#FDE6CE" />
            <stop offset="70%" stopColor="#FBD7B5" />
            <stop offset="100%" stopColor="#F5C096" />
          </linearGradient>

          {/* Drop shadow for the bottom white card */}
          <filter id={shadowFilterId} x="-10%" y="-10%" width="120%" height="130%" filterUnits="userSpaceOnUse">
            <feDropShadow dx="0" dy="-4" stdDeviation="6" floodColor="#000000" floodOpacity="0.35" />
          </filter>

          {/* Clip path for badge boundary */}
          <clipPath id={`badge-clip-${uniqueId}`}>
            <rect x="6" y="6" width="488" height="488" rx="46" ry="46" />
          </clipPath>
        </defs>

        {/* Group with squircle clip path */}
        <g clipPath={`url(#badge-clip-${uniqueId})`}>
          {/* Background Dark Charcoal */}
          <rect x="6" y="6" width="488" height="488" fill="#121111" />

          {/* Subtle radial ambient glow on top */}
          <radialGradient id={`ambient-${uniqueId}`} cx="50%" cy="0%" r="60%">
            <stop offset="0%" stopColor="#301B10" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#121111" stopOpacity="0" />
          </radialGradient>
          <rect x="6" y="6" width="488" height="240" fill={`url(#ambient-${uniqueId})`} />

          {/* ────── HEADER AREA ────── */}
          {/* CredLab Angular Logo Chevrons */}
          <g transform="translate(42, 34)">
            {/* Left Chevron < */}
            <path
              d="M 16 10 L 4 24 L 16 38"
              stroke="#FF7A18"
              strokeWidth="5.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
            {/* Right Chevron > */}
            <path
              d="M 30 10 L 42 24 L 30 38"
              stroke="#FF7A18"
              strokeWidth="5.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
            {/* Wordmark CredLab */}
            <text
              x="54"
              y="32"
              fill="#FFFFFF"
              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              fontWeight="800"
              fontSize="29"
              letterSpacing="-0.5"
            >
              Cred<tspan fill="#FF7A18">Lab</tspan>
            </text>

            {/* Vertical Separator */}
            <line x1="205" y1="8" x2="205" y2="40" stroke="#505050" strokeWidth="1.2" />

            {/* Subtitle Lines */}
            <text
              x="218"
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
              x="218"
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
              x="218"
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

          {/* ────── "COMPLETED" BANNER ────── */}
          <rect
            x="20"
            y="98"
            width="460"
            height="58"
            rx="14"
            fill="#1E1E20"
            stroke="#2E2E32"
            strokeWidth="1.5"
          />
          {/* Subtle top reflection */}
          <path d="M 34 99 L 466 99" stroke="#444448" strokeWidth="1" opacity="0.6" />
          <text
            x="48"
            y="138"
            fill="#FFFFFF"
            fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
            fontSize="32"
            fontWeight="800"
            letterSpacing="-0.5"
          >
            Completed
          </text>

          {/* ────── CENTER FLUID WAVES ART ────── */}
          {/* Layer 1: Dark chocolate background foundation */}
          <path
            d="M 6 156 L 494 156 L 494 450 Q 250 380 6 450 Z"
            fill="#32160A"
          />

          {/* Layer 2: Deep burnt sienna wave */}
          <path
            d="M 6 170 C 120 180, 200 230, 310 205 C 400 185, 450 160, 494 156 L 494 280 C 400 290, 310 320, 200 300 C 100 280, 50 240, 6 230 Z"
            fill="#4F230E"
          />

          {/* Layer 3: Cream / Peach flowing ribbon */}
          <path
            d="M 6 215 C 90 220, 150 255, 270 235 C 370 215, 420 180, 494 165 L 494 225 C 430 245, 360 280, 260 295 C 160 308, 90 260, 6 252 Z"
            fill={`url(#${peachGradId})`}
          />

          {/* Layer 4: Radiant Golden Amber Wave */}
          <path
            d="M 6 248 C 110 258, 170 308, 275 292 C 370 278, 420 232, 494 212 L 494 325 C 410 355, 330 375, 220 345 C 130 320, 70 305, 6 316 Z"
            fill={`url(#${goldGradId})`}
          />

          {/* Layer 5: Vivid fiery orange main wave */}
          <path
            d="M 6 280 C 120 280, 165 350, 285 352 C 375 355, 430 295, 494 278 L 494 400 C 420 420, 330 430, 230 390 C 130 348, 70 365, 6 390 Z"
            fill={`url(#${orangeGradId})`}
          />

          {/* Layer 6: Deep shadow wave behind bottom white card */}
          <path
            d="M 6 370 C 120 370, 230 435, 494 350 L 494 494 L 6 494 Z"
            fill="#271107"
          />

          {/* ────── BOTTOM WHITE SWOOP CARD ────── */}
          {/* Pure clean white fluid swoosh card */}
          <path
            d="M 6 438 C 120 410, 240 378, 494 330 L 494 494 L 6 494 Z"
            fill="#FFFFFF"
            filter={`url(#${shadowFilterId})`}
          />

          {/* Subject Name (Dark Navy / Black, Bold) */}
          <text
            x="465"
            y="422"
            textAnchor="end"
            fill="#0F172A"
            fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
            fontSize="26"
            fontWeight="800"
            letterSpacing="-0.3"
          >
            {displaySubject}
          </text>

          {/* Practical Title (Medium Slate Grey) */}
          <text
            x="465"
            y="452"
            textAnchor="end"
            fill="#5A6B82"
            fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
            fontSize="17"
            fontWeight="500"
          >
            {displayPractical}
          </text>
        </g>

        {/* Outer Squircle Border (Layered above clip) */}
        <rect
          x="6"
          y="6"
          width="488"
          height="488"
          rx="46"
          ry="46"
          fill="none"
          stroke={`url(#${borderGradId})`}
          strokeWidth="9"
        />
      </svg>
    </div>
  );
}

/**
 * Utility to download the badge as a high-definition 1024x1024 PNG
 */
export async function downloadBadgePng(
  badge: {
    name?: string;
    course_name?: string;
    practical_title?: string;
    earned_at?: string;
  },
  filename = "credlab-badge.png"
): Promise<void> {
  const canvas = document.createElement("canvas");
  canvas.width = 1024;
  canvas.height = 1024;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const subject = badge.course_name || badge.name || "Curriculum Subject";
  const practical = badge.practical_title || "Practical Assessment";

  // Create an SVG data URL string
  const svgData = `
    <svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 500 500">
      <defs>
        <linearGradient id="bgrad" x1="0" y1="0" x2="500" y2="500" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#FF7A18"/>
          <stop offset="50%" stop-color="#FF6B2C"/>
          <stop offset="100%" stop-color="#E65100"/>
        </linearGradient>
        <linearGradient id="gold" x1="50" y1="200" x2="450" y2="350" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#FFA737"/>
          <stop offset="50%" stop-color="#FF8F1C"/>
          <stop offset="100%" stop-color="#F57C00"/>
        </linearGradient>
        <linearGradient id="orange" x1="50" y1="240" x2="450" y2="400" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#F26A1B"/>
          <stop offset="50%" stop-color="#E65100"/>
          <stop offset="100%" stop-color="#C83B00"/>
        </linearGradient>
        <linearGradient id="peach" x1="25" y1="180" x2="475" y2="240" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#FDE6CE"/>
          <stop offset="70%" stop-color="#FBD7B5"/>
          <stop offset="100%" stop-color="#F5C096"/>
        </linearGradient>
        <clipPath id="bclip">
          <rect x="6" y="6" width="488" height="488" rx="46" ry="46"/>
        </clipPath>
      </defs>
      <g clip-path="url(#bclip)">
        <rect x="6" y="6" width="488" height="488" fill="#121111"/>
        
        <!-- Header -->
        <g transform="translate(42, 34)">
          <path d="M 16 10 L 4 24 L 16 38" stroke="#FF7A18" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          <path d="M 30 10 L 42 24 L 30 38" stroke="#FF7A18" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          <text x="54" y="32" fill="#FFFFFF" font-family="Arial, sans-serif" font-weight="800" font-size="29">Cred<tspan fill="#FF7A18">Lab</tspan></text>
          <line x1="205" y1="8" x2="205" y2="40" stroke="#505050" stroke-width="1.2"/>
          <text x="218" y="18" fill="#D4D4D8" font-family="Arial, sans-serif" font-size="11" font-weight="600">Secure Coding</text>
          <text x="218" y="30" fill="#D4D4D8" font-family="Arial, sans-serif" font-size="11" font-weight="600">Assessment</text>
          <text x="218" y="42" fill="#D4D4D8" font-family="Arial, sans-serif" font-size="11" font-weight="600">Platform</text>
        </g>

        <!-- Completed banner -->
        <rect x="20" y="98" width="460" height="58" rx="14" fill="#1E1E20" stroke="#2E2E32" stroke-width="1.5"/>
        <text x="48" y="138" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="32" font-weight="800">Completed</text>

        <!-- Waves -->
        <path d="M 6 156 L 494 156 L 494 450 Q 250 380 6 450 Z" fill="#32160A"/>
        <path d="M 6 170 C 120 180, 200 230, 310 205 C 400 185, 450 160, 494 156 L 494 280 C 400 290, 310 320, 200 300 C 100 280, 50 240, 6 230 Z" fill="#4F230E"/>
        <path d="M 6 215 C 90 220, 150 255, 270 235 C 370 215, 420 180, 494 165 L 494 225 C 430 245, 360 280, 260 295 C 160 308, 90 260, 6 252 Z" fill="url(#peach)"/>
        <path d="M 6 248 C 110 258, 170 308, 275 292 C 370 278, 420 232, 494 212 L 494 325 C 410 355, 330 375, 220 345 C 130 320, 70 305, 6 316 Z" fill="url(#gold)"/>
        <path d="M 6 280 C 120 280, 165 350, 285 352 C 375 355, 430 295, 494 278 L 494 400 C 420 420, 330 430, 230 390 C 130 348, 70 365, 6 390 Z" fill="url(#orange)"/>
        <path d="M 6 370 C 120 370, 230 435, 494 350 L 494 494 L 6 494 Z" fill="#271107"/>

        <!-- Bottom white swoosh -->
        <path d="M 6 438 C 120 410, 240 378, 494 330 L 494 494 L 6 494 Z" fill="#FFFFFF"/>
        <text x="465" y="422" text-anchor="end" fill="#0F172A" font-family="Arial, sans-serif" font-size="26" font-weight="800">${escapeXml(subject)}</text>
        <text x="465" y="452" text-anchor="end" fill="#5A6B82" font-family="Arial, sans-serif" font-size="17" font-weight="500">${escapeXml(practical)}</text>
      </g>
      <rect x="6" y="6" width="488" height="488" rx="46" ry="46" fill="none" stroke="url(#bgrad)" stroke-width="9"/>
    </svg>
  `;

  return new Promise<void>((resolve, reject) => {
    const img = new Image();
    const blob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);

    img.onload = () => {
      ctx.drawImage(img, 0, 0, 1024, 1024);
      URL.revokeObjectURL(url);
      const a = document.createElement("a");
      a.download = filename;
      a.href = canvas.toDataURL("image/png");
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      resolve();
    };
    img.onerror = (e) => {
      URL.revokeObjectURL(url);
      reject(e);
    };
    img.src = url;
  });
}

function escapeXml(unsafe: string): string {
  return unsafe.replace(/[<>&'"]/g, (c) => {
    switch (c) {
      case "<": return "&lt;";
      case ">": return "&gt;";
      case "&": return "&amp;";
      case "'": return "&apos;";
      case '"': return "&quot;";
      default: return c;
    }
  });
}
