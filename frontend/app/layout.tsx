import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { THEME_BOOT_SCRIPT } from "@/lib/theme";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "SpeechMate – AI Communication Coach",
  description:
    "Practise conversations, mock interviews and presentations with an AI partner, then get a clear report on your voice, language and body language.",
  keywords: ["speech training", "AI coach", "communication", "pronunciation", "fluency"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    // data-theme is set before paint by the boot script, so React must not "correct" it
    <html lang="en" className={`${inter.variable} h-full`} data-scroll-behavior="smooth" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOT_SCRIPT }} />
      </head>
      <body className="h-full bg-[var(--bg)] text-[var(--ink)] antialiased">{children}</body>
    </html>
  );
}
