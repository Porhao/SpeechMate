import Link from "next/link";
import { ArrowRight } from "lucide-react";

export default function CTASection() {
  return (
    <section className="py-20 px-6 bg-white">
      <div className="max-w-[1280px] mx-auto">
        <div className="bg-[#23345C] rounded-[12px] px-10 py-14 text-center relative overflow-hidden">
          <h2 className="font-display text-[34px] text-white tracking-tight mb-4 relative">
            Start improving your communication today
          </h2>
          <p className="text-[16px] text-white/65 mb-8 max-w-[480px] mx-auto relative">
            Join thousands of students and professionals using SpeechMate to speak with confidence.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 relative">
            <Link
              href="/register"
              className="flex items-center gap-2 h-12 px-6 bg-white text-[#23345C] font-semibold rounded-[8px] hover:bg-[#F5F2EB] transition-colors"
            >
              Get started free
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/login"
              className="h-12 px-6 border border-white/30 text-white font-medium rounded-[8px] flex items-center hover:bg-white/10 transition-colors"
            >
              Sign in
            </Link>
          </div>
          <p className="mt-4 text-xs text-white/55 relative">No credit card required · Free to get started</p>
        </div>
      </div>
    </section>
  );
}
