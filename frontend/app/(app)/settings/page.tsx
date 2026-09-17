"use client";

import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Shield, Bell, User, Lock, Eye, EyeOff, Check, Trash2, Download } from "lucide-react";
import { useUserStore } from "@/store/useUserStore";
import { useRouter } from "next/navigation";
import { Slider } from "@/components/ui/Slider";

const RETENTION_OPTIONS = ["90 days", "180 days", "1 year", "Forever"];

function Toggle({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!value)}
      className="relative w-10 h-5 rounded-full transition-colors flex-shrink-0"
      style={{ background: value ? "#23345C" : "#E6E2D8" }}
    >
      <span
        className="absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform"
        style={{ transform: value ? "translateX(20px)" : "translateX(0)" }}
      />
    </button>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="glass-card rounded-2xl overflow-hidden">
      <div className="px-6 py-4" style={{ borderBottom: "1px solid #F0EDE5" }}>
        <h2 className="text-sm font-semibold" style={{ color: "#17181C" }}>{title}</h2>
      </div>
      <div className="px-6 py-5 space-y-5">{children}</div>
    </div>
  );
}

function Row({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 sm:gap-4">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium" style={{ color: "#17181C" }}>{label}</p>
        {description && <p className="text-xs mt-0.5" style={{ color: "#9B988E" }}>{description}</p>}
      </div>
      <div className="flex-shrink-0">{children}</div>
    </div>
  );
}

// A destructive action with a real confirm step and a real undo window — not
// just a color change. Nothing is actually deleted here (there's no backend
// call wired up); this is the interaction pattern a real delete would sit
// behind, mirrored from Settings > Account > Delete.
type DeleteStage = "idle" | "confirm" | "scheduled";

function DeleteAccountRow() {
  const [stage, setStage] = useState<DeleteStage>("idle");
  const undoTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const schedule = () => {
    setStage("scheduled");
    undoTimer.current = setTimeout(() => setStage("idle"), 6000);
  };
  const undo = () => {
    if (undoTimer.current) clearTimeout(undoTimer.current);
    setStage("idle");
  };

  return (
    <div>
      <AnimatePresence mode="wait" initial={false}>
        {stage === "idle" && (
          <motion.div
            key="idle"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="flex items-center justify-between gap-3 sm:gap-4"
          >
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium" style={{ color: "#17181C" }}>Delete Account</p>
              <p className="text-xs mt-0.5" style={{ color: "#9B988E" }}>Permanently delete your account and all data</p>
            </div>
            <button
              onClick={() => setStage("confirm")}
              className="flex-shrink-0 flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg press-effect"
              style={{ background: "rgba(140,59,50,0.06)", border: "1px solid rgba(140,59,50,0.25)", color: "#8C3B32" }}
            >
              <Trash2 className="w-3.5 h-3.5" /> Delete
            </button>
          </motion.div>
        )}

        {stage === "confirm" && (
          <motion.div
            key="confirm"
            initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 6 }}
            transition={{ type: "spring", stiffness: 500, damping: 30 }}
            className="flex items-center justify-between gap-3 rounded-xl px-3 py-2.5"
            style={{ background: "rgba(140,59,50,0.06)", border: "1px solid rgba(140,59,50,0.25)" }}
          >
            <p className="text-xs font-medium min-w-0 flex-1" style={{ color: "#8C3B32" }}>
              This can&apos;t be undone after 6 seconds. Sure?
            </p>
            <div className="flex items-center gap-2 flex-shrink-0">
              <button
                onClick={() => setStage("idle")}
                className="text-xs font-semibold px-3 py-1.5 rounded-lg press-effect"
                style={{ background: "#FFFFFF", border: "1px solid #E6E2D8", color: "#4B4C52" }}
              >
                Cancel
              </button>
              <button
                onClick={schedule}
                className="text-xs font-semibold px-3 py-1.5 rounded-lg text-white press-effect"
                style={{ background: "#8C3B32" }}
              >
                Yes, delete
              </button>
            </div>
          </motion.div>
        )}

        {stage === "scheduled" && (
          <motion.div
            key="scheduled"
            initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.96 }}
            transition={{ type: "spring", stiffness: 400, damping: 26 }}
            className="flex items-center justify-between gap-3 rounded-xl px-3 py-2.5"
            style={{ background: "#F5F2EB", border: "1px solid #E6E2D8" }}
          >
            <div className="flex items-center gap-2 min-w-0 flex-1">
              <motion.span
                className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                style={{ background: "#8C3B32" }}
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 1.1, repeat: Infinity }}
              />
              <p className="text-xs font-medium truncate" style={{ color: "#4B4C52" }}>Account scheduled for deletion…</p>
            </div>
            <button
              onClick={undo}
              className="flex-shrink-0 text-xs font-semibold px-3 py-1.5 rounded-lg press-effect"
              style={{ color: "#23345C" }}
            >
              Undo
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

const TABS = [
  { id: "account",       label: "Account",       icon: User   },
  { id: "notifications", label: "Notifications", icon: Bell   },
  { id: "privacy",       label: "Privacy",       icon: Shield },
  { id: "security",      label: "Security",      icon: Lock   },
] as const;

type Tab = (typeof TABS)[number]["id"];

export default function SettingsPage() {
  const { logout } = useUserStore();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("account");

  const [notifs, setNotifs] = useState({
    emailSummary:    true,
    weeklyReport:    true,
    sessionReminder: false,
    achievements:    true,
    tips:            false,
  });

  const [privacy, setPrivacy] = useState({
    shareAnonymous: false,
    storeAudio:     true,
    storeVideo:     false,
  });

  const [retention, setRetention] = useState(0);
  const [pwForm, setPwForm] = useState({ current: "", next: "", confirm: "" });
  const [showPw, setShowPw]   = useState({ current: false, next: false, confirm: false });
  const [pwSaved, setPwSaved] = useState(false);

  const handleLogout = () => { logout(); router.push("/login"); };

  const handleSavePw = (e: React.FormEvent) => {
    e.preventDefault();
    if (pwForm.next !== pwForm.confirm) return;
    setPwSaved(true);
    setPwForm({ current: "", next: "", confirm: "" });
    setTimeout(() => setPwSaved(false), 3000);
  };

  return (
    <div className="px-4 sm:px-6 py-6 sm:py-8 max-w-[900px] mx-auto space-y-6">

      {/* Header */}
      <div>
        <h1 className="font-display text-2xl" style={{ color: "#17181C" }}>Settings</h1>
        <p className="text-sm mt-1" style={{ color: "#9B988E" }}>
          Manage your account preferences and privacy
        </p>
      </div>

      {/* Tabs */}
      <div
        className="flex gap-1 rounded-2xl p-1"
        style={{ background: "#F5F2EB", border: "1px solid #E6E2D8" }}
      >
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className="relative flex-1 flex items-center justify-center gap-2 py-2 rounded-xl text-sm font-semibold whitespace-nowrap transition-colors"
            style={{ color: tab === id ? "#17233E" : "#6E6C63" }}
          >
            {tab === id && (
              <motion.div
                layoutId="settings-tab-pill"
                className="absolute inset-0 rounded-xl"
                style={{ background: "#FFFFFF", boxShadow: "0 0 0 1px rgba(35,52,92,0.25), 0 2px 8px rgba(35,52,92,0.10)" }}
                transition={{ type: "spring", stiffness: 480, damping: 34 }}
              />
            )}
            <Icon className="relative w-4 h-4 flex-shrink-0" />
            <span className="relative hidden sm:inline">{label}</span>
          </button>
        ))}
      </div>

      {/* Account */}
      {tab === "account" && (
        <div className="space-y-4">
          <Section title="Account">
            <Row label="Full Name" description="Your display name across the app">
              <span className="text-sm" style={{ color: "#4B4C52" }}>Ahmad Rizwan</span>
            </Row>
            <div style={{ borderTop: "1px solid #F0EDE5" }} />
            <Row label="Email Address" description="Used for login and reports">
              <span className="text-sm" style={{ color: "#4B4C52" }}>ahmad@example.com</span>
            </Row>
            <div style={{ borderTop: "1px solid #F0EDE5" }} />
            <Row label="Edit Profile" description="Update name, language, and goals">
              <button
                onClick={() => router.push("/profile")}
                className="text-xs font-semibold transition-colors"
                style={{ color: "#23345C" }}
              >
                Go to Profile →
              </button>
            </Row>
          </Section>

          <Section title="Danger Zone">
            <Row label="Sign Out" description="Log out from all devices">
              <button
                onClick={handleLogout}
                className="text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
                style={{ background: "#F5F2EB", border: "1px solid #E6E2D8", color: "#4B4C52" }}
              >
                Sign Out
              </button>
            </Row>
            <div style={{ borderTop: "1px solid #F0EDE5" }} />
            <DeleteAccountRow />
          </Section>
        </div>
      )}

      {/* Notifications */}
      {tab === "notifications" && (
        <Section title="Notification Preferences">
          {([
            { key: "emailSummary",    label: "Email Session Summary",   desc: "Receive an email after each practice session" },
            { key: "weeklyReport",    label: "Weekly Progress Report",  desc: "Get a weekly digest of your improvement" },
            { key: "sessionReminder", label: "Daily Practice Reminder", desc: "Reminder notification if you haven't practiced" },
            { key: "achievements",    label: "Achievement Alerts",      desc: "Notify when you unlock new achievements" },
            { key: "tips",            label: "AI Coaching Tips",        desc: "Daily personalized tips from your AI coach" },
          ] as const).map(({ key, label, desc }, i) => (
            <div key={key}>
              {i > 0 && <div style={{ borderTop: "1px solid #F0EDE5" }} />}
              <Row label={label} description={desc}>
                <Toggle value={notifs[key]} onChange={(v) => setNotifs((n) => ({ ...n, [key]: v }))} />
              </Row>
            </div>
          ))}
        </Section>
      )}

      {/* Privacy */}
      {tab === "privacy" && (
        <div className="space-y-4">
          <Section title="Data Usage">
            {([
              { key: "shareAnonymous", label: "Share Anonymous Usage Data", desc: "Help improve SpeechMate by sharing anonymized usage statistics" },
              { key: "storeAudio",     label: "Store Audio Recordings",     desc: "Keep audio recordings for AI model training (anonymized)" },
              { key: "storeVideo",     label: "Store Video Recordings",     desc: "Keep video recordings for posture/eye contact AI analysis" },
            ] as const).map(({ key, label, desc }, i) => (
              <div key={key}>
                {i > 0 && <div style={{ borderTop: "1px solid #F0EDE5" }} />}
                <Row label={label} description={desc}>
                  <Toggle value={privacy[key]} onChange={(v) => setPrivacy((p) => ({ ...p, [key]: v }))} />
                </Row>
              </div>
            ))}
          </Section>

          <Section title="Your Data">
            <Row label="Export My Data" description="Download all your session data, scores, and history as CSV">
              <button
                className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg"
                style={{ background: "#F5F2EB", border: "1px solid #E6E2D8", color: "#4B4C52" }}
              >
                <Download className="w-3.5 h-3.5" /> Export
              </button>
            </Row>
            <div style={{ borderTop: "1px solid #F0EDE5" }} />
            <div>
              <p className="text-sm font-medium" style={{ color: "#17181C" }}>Data Retention</p>
              <p className="text-xs mt-0.5 mb-4" style={{ color: "#9B988E" }}>
                Session data is kept for <strong style={{ color: "#34343A" }}>{RETENTION_OPTIONS[retention]}</strong> before automatic deletion
              </p>
              <div className="max-w-[360px]">
                <Slider
                  value={retention}
                  min={0}
                  max={RETENTION_OPTIONS.length - 1}
                  onChange={setRetention}
                  formatValue={(v) => RETENTION_OPTIONS[v]}
                />
                <div className="flex justify-between mt-1.5">
                  {RETENTION_OPTIONS.map((label) => (
                    <span key={label} className="text-[10px]" style={{ color: "#CDC9BE" }}>{label}</span>
                  ))}
                </div>
              </div>
            </div>
          </Section>

          <div
            className="rounded-2xl px-5 py-4"
            style={{ background: "rgba(35,52,92,0.06)", border: "1px solid rgba(35,52,92,0.16)" }}
          >
            <p className="text-xs leading-relaxed" style={{ color: "#4B4C52" }}>
              SpeechMate complies with <strong style={{ color: "#17181C" }}>Malaysia PDPA</strong>. Your personal data is encrypted at rest (AES-256) and in transit (TLS 1.3). We never sell your data to third parties.
            </p>
          </div>
        </div>
      )}

      {/* Security */}
      {tab === "security" && (
        <Section title="Change Password">
          <form onSubmit={handleSavePw} className="space-y-4">
            {(["current", "next", "confirm"] as const).map((field) => {
              const labels = { current: "Current Password", next: "New Password", confirm: "Confirm New Password" };
              return (
                <div key={field}>
                  <label className="block text-xs font-medium mb-1.5" style={{ color: "#6E6C63" }}>
                    {labels[field]}
                  </label>
                  <div className="relative">
                    <input
                      type={showPw[field] ? "text" : "password"}
                      value={pwForm[field]}
                      onChange={(e) => setPwForm((p) => ({ ...p, [field]: e.target.value }))}
                      placeholder="••••••••"
                      className="w-full pr-10 px-3 py-2.5 rounded-xl text-sm outline-none transition-all placeholder:text-slate-400"
                      style={{ background: "#F5F2EB", border: "1px solid #E6E2D8", color: "#17181C" }}
                      onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(35,52,92,0.5)"; }}
                      onBlur={(e) => { e.currentTarget.style.borderColor = "#E6E2D8"; }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPw((p) => ({ ...p, [field]: !p[field] }))}
                      className="absolute right-3 top-1/2 -translate-y-1/2"
                      style={{ color: "#9B988E" }}
                    >
                      {showPw[field] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              );
            })}

            {pwForm.next && pwForm.confirm && pwForm.next !== pwForm.confirm && (
              <p className="text-xs" style={{ color: "#8C3B32" }}>Passwords do not match.</p>
            )}

            <div className="flex items-center justify-between pt-2">
              <p className="text-xs" style={{ color: "#9B988E" }}>Minimum 8 characters required.</p>
              <button
                type="submit"
                disabled={!pwForm.current || !pwForm.next || pwForm.next !== pwForm.confirm}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                style={{ background: pwSaved ? "#3F6B4C" : "#23345C" }}
              >
                {pwSaved ? <><Check className="w-4 h-4" /> Updated!</> : "Update Password"}
              </button>
            </div>
          </form>
        </Section>
      )}

    </div>
  );
}
