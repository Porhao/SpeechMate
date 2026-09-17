"use client";

import Link from "next/link";
import { Zap } from "lucide-react";

export default function LandingNav() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-[#E6E2D8]">
      <div className="max-w-[1280px] mx-auto px-6 h-[64px] flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-[#23345C] rounded-lg flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" strokeWidth={2.5} />
          </div>
          <span className="text-[#17181C] font-semibold text-[17px] tracking-tight">SpeechMate</span>
        </Link>

        {/* Links */}
        <div className="hidden md:flex items-center gap-6">
          <Link href="#features" className="text-sm text-[#6E6C63] hover:text-[#17181C] transition-colors">Features</Link>
          <Link href="#how-it-works" className="text-sm text-[#6E6C63] hover:text-[#17181C] transition-colors">How it works</Link>
          <Link href="#testimonials" className="text-sm text-[#6E6C63] hover:text-[#17181C] transition-colors">Testimonials</Link>
        </div>

        {/* CTA */}
        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className="text-sm font-medium text-[#6E6C63] hover:text-[#17181C] transition-colors"
          >
            Sign in
          </Link>
          <Link
            href="/register"
            className="h-9 px-4 bg-[#23345C] text-white text-sm font-medium rounded-[10px] flex items-center hover:bg-[#17233E] transition-colors"
          >
            Get started free
          </Link>
        </div>
      </div>
    </nav>
  );
}
