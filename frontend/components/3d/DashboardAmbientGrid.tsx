"use client";

import React from "react";

/**
 * DashboardAmbientGrid provides industrial futurism ambient lighting,
 * subtle orange radial gradients, and restrained geometric accents
 * across dashboard overview pages. Non-interactive, lightweight SVG.
 */
export function DashboardAmbientGrid({ className = "" }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}
    >
      {/* Ambient Orange & Amber Radial Gradients */}
      <div className="absolute -top-24 -left-24 h-96 w-96 rounded-full bg-[#FF6B2C]/8 blur-[120px]" />
      <div className="absolute top-1/2 -right-32 h-96 w-96 rounded-full bg-[#FFB547]/6 blur-[130px]" />
      <div className="absolute -bottom-24 left-1/3 h-80 w-80 rounded-full bg-[#FF6B2C]/5 blur-[100px]" />

      {/* Subtle Technical Geometric Grid Overlay */}
      <svg
        className="absolute inset-0 h-full w-full opacity-[0.035]"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <pattern
            id="credlab-circuit-grid"
            width="48"
            height="48"
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M 48 0 L 0 0 0 48"
              fill="none"
              stroke="#FF8A3D"
              strokeWidth="0.75"
            />
            <circle cx="24" cy="24" r="1" fill="#FFB547" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#credlab-circuit-grid)" />
      </svg>
    </div>
  );
}

export default DashboardAmbientGrid;
