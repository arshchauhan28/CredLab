"use client";

import React from "react";

interface CredLabLogoProps {
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  showWordmark?: boolean;
  showTagline?: boolean;
  className?: string;
}

export function CredLabEmblem({
  className = "w-9 h-9",
}: {
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <defs>
        {/* Core Brand Gradients */}
        <linearGradient id="credlab-bracket-left" x1="4" y1="8" x2="20" y2="40" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#FF6B2C" />
          <stop offset="100%" stopColor="#D94F16" />
        </linearGradient>

        <linearGradient id="credlab-bracket-right" x1="28" y1="8" x2="44" y2="40" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#FF8533" />
          <stop offset="100%" stopColor="#FF6B2C" />
        </linearGradient>

        <linearGradient id="credlab-check" x1="16" y1="20" x2="38" y2="38" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#FFC837" />
          <stop offset="60%" stopColor="#FF9F1C" />
          <stop offset="100%" stopColor="#FF6B2C" />
        </linearGradient>

        <filter id="credlab-glow" x="-20%" y="-20%" width="140%" height="140%" filterUnits="userSpaceOnUse">
          <feGaussianBlur stdDeviation="1.5" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>

      {/* Hexagonal / Chamfered Background Shield */}
      <rect
        x="2"
        y="2"
        width="44"
        height="44"
        rx="10"
        fill="#181818"
      />
      <rect
        x="2.5"
        y="2.5"
        width="43"
        height="43"
        rx="9.5"
        stroke="#353535"
        strokeWidth="1"
      />

      {/* Left Code Bracket < */}
      <path
        d="M17 14L9 24L17 34"
        stroke="url(#credlab-bracket-left)"
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Right Code Bracket > */}
      <path
        d="M31 14L39 24L31 34"
        stroke="url(#credlab-bracket-right)"
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.45"
      />

      {/* Integrated Verification Checkmark Motif ✓ with Subtle Glow */}
      <path
        d="M17 25L23.5 31.5L37.5 17"
        stroke="url(#credlab-check)"
        strokeWidth="4"
        strokeLinecap="round"
        strokeLinejoin="round"
        filter="url(#credlab-glow)"
      />

      {/* Verification Terminal Core Dot */}
      <circle cx="23.5" cy="31.5" r="1.5" fill="#FFF9F5" />
    </svg>
  );
}

export function CredLabLogo({
  size = "md",
  showWordmark = true,
  showTagline = false,
  className = "",
}: CredLabLogoProps) {
  const sizeMap = {
    xs: { icon: "w-6 h-6", text: "text-base", sub: "text-[9px]" },
    sm: { icon: "w-8 h-8", text: "text-lg", sub: "text-[10px]" },
    md: { icon: "w-10 h-10", text: "text-xl", sub: "text-[11px]" },
    lg: { icon: "w-12 h-12", text: "text-2xl", sub: "text-xs" },
    xl: { icon: "w-16 h-16", text: "text-4xl", sub: "text-sm" },
  };

  const currentSize = sizeMap[size];

  return (
    <div className={`inline-flex items-center gap-3 select-none ${className}`}>
      <CredLabEmblem className={currentSize.icon} />

      {showWordmark && (
        <div className="flex flex-col">
          <div className="flex items-baseline tracking-tight font-extrabold leading-none">
            <span className={`${currentSize.text} text-[#F7F4EF] font-sans tracking-tight`}>
              Cred
            </span>
            <span
              className={`${currentSize.text} font-sans tracking-tight bg-gradient-to-r from-[#FF6B2C] to-[#FFB547] bg-clip-text text-transparent`}
            >
              Lab
            </span>
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#FF6B2C] ml-0.5 mb-0.5 animate-pulse" />
          </div>

          {showTagline && (
            <span
              className={`${currentSize.sub} font-mono tracking-widest uppercase font-semibold text-[#A5A29C] mt-0.5`}
            >
              Verified Assessment Platform
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export default CredLabLogo;
