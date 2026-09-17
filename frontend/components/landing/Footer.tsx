import Link from "next/link";
import { Zap } from "lucide-react";

export default function Footer() {
  return (
    <footer className="bg-[#F5F2EB] border-t border-[#E6E2D8] py-10 px-6">
      <div className="max-w-[1280px] mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2">
          <div className="w-7 h-7 bg-[#23345C] rounded-lg flex items-center justify-center">
            <Zap className="w-3.5 h-3.5 text-white" strokeWidth={2.5} />
          </div>
          <span className="text-[#17181C] font-semibold text-[15px]">SpeechMate</span>
        </Link>

        {/* Links */}
        <div className="flex items-center gap-6 text-sm text-[#6E6C63]">
          <Link href="#" className="hover:text-[#17181C] transition-colors">Privacy Policy</Link>
          <Link href="#" className="hover:text-[#17181C] transition-colors">Terms of Service</Link>
          <Link href="#" className="hover:text-[#17181C] transition-colors">Contact</Link>
        </div>

        <p className="text-sm text-[#9B988E]">
          © {new Date().getFullYear()} SpeechMate. FYP Project · UTP
        </p>
      </div>
    </footer>
  );
}
