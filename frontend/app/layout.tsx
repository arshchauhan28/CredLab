import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { ThemeScript } from "@/components/theme/ThemeScript";
import "./globals.css";

const inter = Inter({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "CredLab — Secure Coding & Practical Assessment Platform",
  description:
    "Your Code. Your Skills. Your Credibility. High-integrity institutional laboratory assessment platform with automated deterministic sandboxes and Ed25519 cryptographic credentials.",
  icons: {
    icon: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`dark ${inter.variable} ${jetbrainsMono.variable} h-full antialiased`}
      data-theme="dark"
      style={{ colorScheme: "dark" }}
    >
      <head>
        <ThemeScript />
      </head>
      <body className="min-h-full flex flex-col antialiased bg-[#101010] text-[#F7F4EF] selection:bg-[#FF6B2C]/20 selection:text-[#FF6B2C]">
        {children}
      </body>
    </html>
  );
}