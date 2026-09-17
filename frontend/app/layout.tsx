import type { Metadata } from "next";
import { Inter, Source_Serif_4 } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

// Display serif — used only for headlines, paired with Inter for body/UI text.
// This one pairing is doing a lot of work to make the app read as designed
// rather than templated, so keep it scoped to headings (see .font-display).
const sourceSerif = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-serif",
  display: "swap",
  weight: ["500", "600", "700"],
});

export const metadata: Metadata = {
  title: "SpeechMate – AI Communication Coach",
  description:
    "Improve speech fluency, pronunciation, and communication confidence through personalized AI coaching.",
  keywords: ["speech training", "AI coach", "communication", "pronunciation", "fluency"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${sourceSerif.variable} h-full`} data-scroll-behavior="smooth">
      <body className="h-full bg-[#FBFAF7] text-[#17181C] antialiased">{children}</body>
    </html>
  );
}
