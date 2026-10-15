"use client";

import React from "react";

export type Theme = "dark";
export type ResolvedTheme = "dark";

export interface ThemeContextType {
  theme: "dark";
  resolvedTheme: "dark";
  setTheme: (theme: string) => void;
}

const permanentDarkContext: ThemeContextType = {
  theme: "dark",
  resolvedTheme: "dark",
  setTheme: () => {},
};

/**
 * ThemeProvider is neutralized. CredLab uses one permanent dark theme.
 * Renders children directly without theme-switching context or localStorage logic.
 */
export function ThemeProvider({
  children,
}: {
  children: React.ReactNode;
  [key: string]: unknown;
}) {
  return <>{children}</>;
}

export function useTheme(): ThemeContextType {
  return permanentDarkContext;
}
