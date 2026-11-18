import React, { useState } from "react";
import {
  ShieldCheck,
  Eye,
  EyeOff,
  ArrowRight,
  Sparkles,
  Lock,
  Mail,
  Activity,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  X,
  Cpu,
  UserCheck,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("clinician@confiroute.ai");
  const [password, setPassword] = useState("confiroute2026");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [forgotSubmitted, setForgotSubmitted] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const result = await login(email, password, rememberMe);
      if (!result.success) {
        setErrorMessage(result.error || "Authentication failed. Please verify your credentials.");
      }
    } catch {
      setErrorMessage("An unexpected network or service error occurred during authentication.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const fillDemoCredentials = () => {
    setEmail("clinician@confiroute.ai");
    setPassword("Clinical2026!");
    setErrorMessage(null);
  };

  return (
    <div className="relative min-h-screen w-full flex items-center justify-center overflow-hidden bg-[#F8F5EF] p-4 sm:p-6 lg:p-8">
      {/* Ambient Creamy & Champagne Luxury Gradients */}
      <div
        className="pointer-events-none absolute -top-40 -right-40 h-[580px] w-[580px] rounded-full blur-3xl opacity-40"
        style={{
          background: "radial-gradient(circle, #C5A878 0%, #E2D3B8 50%, transparent 70%)",
        }}
      />
      <div
        className="pointer-events-none absolute -bottom-48 -left-48 h-[640px] w-[640px] rounded-full blur-3xl opacity-35"
        style={{
          background: "radial-gradient(circle, #B79A68 0%, #DFD6C4 50%, transparent 70%)",
        }}
      />

      {/* Subtle Abstract AI Routing Network Canvas Overlay */}
      <div className="pointer-events-none absolute inset-0 opacity-[0.22]">
        <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="routeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#C5A878" stopOpacity="0.4" />
              <stop offset="50%" stopColor="#B79A68" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#25241F" stopOpacity="0.2" />
            </linearGradient>
            <pattern id="gridPattern" width="60" height="60" patternUnits="userSpaceOnUse">
              <path d="M 60 0 L 0 0 0 60" fill="none" stroke="#E5DEC9" strokeWidth="0.8" />
              <circle cx="0" cy="0" r="1.5" fill="#C5A878" opacity="0.6" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#gridPattern)" />

          {/* Abstract routing paths */}
          <path
            d="M 120 200 C 350 180, 500 450, 850 380 S 1100 200, 1400 320"
            fill="none"
            stroke="url(#routeGrad)"
            strokeWidth="1.8"
            strokeDasharray="6 8"
          />
          <path
            d="M 80 500 C 320 420, 600 650, 950 540 S 1250 480, 1500 620"
            fill="none"
            stroke="url(#routeGrad)"
            strokeWidth="1.4"
            strokeDasharray="4 6"
          />
        </svg>
      </div>

      {/* Main Login Container */}
      <div className="relative z-10 w-full max-w-[1020px] grid grid-cols-1 lg:grid-cols-12 gap-0 overflow-hidden rounded-3xl bg-[#FFFEFC]/95 border border-[#E8E2D5] shadow-2xl backdrop-blur-md">
        {/* Left Side: Brand Story & Interactive Routing Architecture Preview */}
        <div className="hidden lg:flex lg:col-span-5 flex-col justify-between p-10 bg-gradient-to-br from-[#25241F] via-[#2A2924] to-[#1E1D19] text-[#F8F5EF] relative overflow-hidden">
          {/* Subtle gold line accent */}
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#C5A878] to-transparent" />

          {/* Brand Header */}
          <div>
            <div className="inline-flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-[#35332B] border border-[#C5A878]/30 text-xs font-medium text-[#C5A878] tracking-wide mb-6">
              <ShieldCheck className="w-3.5 h-3.5 text-[#C5A878]" />
              <span>SAFETY-FIRST AI ARCHITECTURE</span>
            </div>

            <h2 className="text-3xl font-heading font-bold text-[#FFFEFC] tracking-tight leading-snug">
              Confidence-Aware <br />
              <span className="text-[#C5A878]">LLM Routing System</span>
            </h2>

            <p className="mt-4 text-sm text-[#DFD9CE] leading-relaxed">
              ConfiRoute rigorously analyzes model uncertainty, self-consistency, and risk keywords before
              allowing medical or critical inquiries to be delivered.
            </p>
          </div>

          {/* Interactive Routing Pipeline Flow Card */}
          <div className="my-8 rounded-2xl bg-[#1C1B17]/90 border border-[#3E3C34] p-5 shadow-inner">
            <div className="flex items-center justify-between text-xs text-[#A8A296] font-mono mb-4 pb-2 border-b border-[#333129]">
              <span>ACTIVE TRIAGE PIPELINE</span>
              <span className="inline-flex items-center gap-1.5 text-[#3E7B54]">
                <span className="w-2 h-2 rounded-full bg-[#3E7B54] animate-ping" />
                READY
              </span>
            </div>

            {/* Pipeline Step 1 */}
            <div className="flex items-center gap-3.5 py-2">
              <div className="w-7 h-7 rounded-lg bg-[#35332B] border border-[#C5A878]/30 flex items-center justify-center shrink-0">
                <Cpu className="w-3.5 h-3.5 text-[#C5A878]" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-[#EDE8DE]">Tier 1 Generation</span>
                  <span className="text-[10px] font-mono text-[#A8A296]">llama 3.2 3B</span>
                </div>
                <p className="text-[11px] text-[#A8A296] truncate">Rapid lightweight initial inference</p>
              </div>
            </div>

            {/* Pipeline Step 2 */}
            <div className="flex items-center gap-3.5 py-2">
              <div className="w-7 h-7 rounded-lg bg-[#35332B] border border-[#C5A878]/30 flex items-center justify-center shrink-0">
                <Activity className="w-3.5 h-3.5 text-[#C5A878]" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-[#EDE8DE]">Confidence Scoring</span>
                  <span className="text-[10px] font-mono text-[#C5A878]">s1 + s2 + s3</span>
                </div>
                <p className="text-[11px] text-[#A8A296] truncate">Token probs, consistency & rating</p>
              </div>
            </div>

            {/* Pipeline Step 3 */}
            <div className="flex items-center gap-3.5 py-2">
              <div className="w-7 h-7 rounded-lg bg-[#35332B] border border-[#3E7B54]/40 flex items-center justify-center shrink-0">
                <UserCheck className="w-3.5 h-3.5 text-[#3E7B54]" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-[#EDE8DE]">Clinician Review Gate</span>
                  <span className="text-[10px] font-mono text-[#3E7B54]">Human-in-the-Loop</span>
                </div>
                <p className="text-[11px] text-[#A8A296] truncate">Safety hold & expert verification</p>
              </div>
            </div>
          </div>

          {/* Footer citation */}
          <div className="pt-4 border-t border-[#333129] flex items-center justify-between text-xs text-[#A8A296]">
            <span>Version 0.3.0 · Enterprise</span>
            <span className="font-mono text-[#C5A878]">MedMCQA Calibrated</span>
          </div>
        </div>

        {/* Right Side: Luxury Authentication Form */}
        <div className="col-span-1 lg:col-span-7 p-8 sm:p-12 lg:p-14 flex flex-col justify-center bg-[#FFFEFC]">
          {/* Mobile Brand Header */}
          <div className="lg:hidden mb-8 pb-6 border-b border-[#E8E2D5]">
            <div className="flex items-center gap-2.5 mb-2">
              <div className="w-9 h-9 rounded-xl bg-[#25241F] flex items-center justify-center shadow-md">
                <ShieldCheck className="w-5 h-5 text-[#C5A878]" />
              </div>
              <span className="text-xl font-heading font-bold text-[#25241F] tracking-tight">ConfiRoute</span>
            </div>
            <p className="text-xs text-[#777267]">
              Confidence-Aware LLM Routing & Verification System
            </p>
          </div>

          {/* Form Header */}
          <div className="mb-8">
            <div className="hidden lg:flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl bg-[#25241F] flex items-center justify-center shadow-md border border-[#C5A878]/30">
                <ShieldCheck className="w-5 h-5 text-[#C5A878]" />
              </div>
              <div>
                <span className="text-2xl font-heading font-extrabold text-[#25241F] tracking-tight">ConfiRoute</span>
                <span className="ml-2.5 px-2 py-0.5 rounded text-[11px] font-mono bg-[#F0EBE2] text-[#777267] border border-[#E8E2D5]">
                  SECURE PORTAL
                </span>
              </div>
            </div>

            <h1 className="text-2xl sm:text-3xl font-heading font-bold text-[#292720] tracking-tight">
              Sign In to AI Workspace
            </h1>
            <p className="mt-2 text-sm text-[#777267] leading-relaxed">
              "Intelligence that knows when to answer, escalate, or verify."
            </p>
          </div>

          {/* Error Message Alert */}
          {errorMessage && (
            <div className="mb-6 p-4 rounded-xl bg-[#FDF1EF] border border-[#E8B6AF] flex items-start gap-3 animate-fade-in text-sm text-[#BD4C3D]">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <div className="flex-1">
                <span className="font-semibold">Authentication Notice: </span>
                {errorMessage}
              </div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email Field */}
            <div>
              <label className="block text-xs font-semibold text-[#4A473E] tracking-wider uppercase mb-1.5">
                Clinical / Enterprise Email
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[#9E988A]">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="clinician@hospital.org"
                  required
                  className="w-full pl-10 pr-4 py-3 bg-[#FAF8F5] border border-[#E8E2D5] rounded-xl text-sm text-[#292720] placeholder-[#A8A296] focus:outline-none focus:ring-2 focus:ring-[#C5A878]/50 focus:border-[#C5A878] transition-all"
                />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold text-[#4A473E] tracking-wider uppercase">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => setShowForgotModal(true)}
                  className="text-xs font-medium text-[#B79A68] hover:text-[#9E8052] transition-colors"
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[#9E988A]">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  required
                  className="w-full pl-10 pr-11 py-3 bg-[#FAF8F5] border border-[#E8E2D5] rounded-xl text-sm text-[#292720] placeholder-[#A8A296] focus:outline-none focus:ring-2 focus:ring-[#C5A878]/50 focus:border-[#C5A878] transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-[#9E988A] hover:text-[#292720] transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Remember Me & Quick Demo helper */}
            <div className="flex items-center justify-between pt-1">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="w-4 h-4 rounded border-[#D5CEBF] text-[#B79A68] focus:ring-[#C5A878] accent-[#B79A68]"
                />
                <span className="text-xs text-[#6B665A]">Remember active session</span>
              </label>

              <button
                type="button"
                onClick={fillDemoCredentials}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#8C7349] hover:text-[#64502F] underline underline-offset-2 transition-colors"
              >
                <Sparkles className="w-3.5 h-3.5" />
                Fill Test Reviewer
              </button>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3.5 px-6 rounded-xl bg-gradient-to-r from-[#292720] via-[#333129] to-[#25241F] text-[#FAF8F5] font-semibold text-sm shadow-md hover:shadow-xl hover:from-[#1E1D19] hover:to-[#181714] active:scale-[0.99] transition-all flex items-center justify-center gap-2.5 disabled:opacity-70 disabled:cursor-not-allowed group border border-[#444036]"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-[#C5A878] border-t-transparent rounded-full animate-spin" />
                  <span>Authenticating Clinician...</span>
                </>
              ) : (
                <>
                  <span>Sign In to ConfiRoute</span>
                  <ArrowRight className="w-4 h-4 text-[#C5A878] group-hover:translate-x-0.5 transition-transform" />
                </>
              )}
            </button>
          </form>

          {/* Quick Security & Architecture Footnote */}
          <div className="mt-8 pt-6 border-t border-[#F1ECE2] flex items-center justify-between text-[11px] text-[#8C877B]">
            <span className="flex items-center gap-1.5">
              <Lock className="w-3 h-3 text-[#3E7B54]" />
              End-to-end audit logging active
            </span>
            <span className="font-mono">Port 8000 REST Ready</span>
          </div>
        </div>
      </div>

      {/* Forgot Password Modal */}
      {showForgotModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#25241F]/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-md rounded-2xl bg-[#FFFEFC] border border-[#E8E2D5] p-6 shadow-2xl relative">
            <button
              onClick={() => {
                setShowForgotModal(false);
                setForgotSubmitted(false);
              }}
              className="absolute top-4 right-4 p-1.5 rounded-lg text-[#8C877B] hover:text-[#292720] hover:bg-[#F0EBE2] transition-colors"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-[#FDF6EC] border border-[#F0CCA0] flex items-center justify-center">
                <HelpCircle className="w-5 h-5 text-[#C67D26]" />
              </div>
              <div>
                <h3 className="text-lg font-heading font-bold text-[#292720]">Credential Recovery</h3>
                <p className="text-xs text-[#777267]">Hospital & Enterprise SSO</p>
              </div>
            </div>

            {forgotSubmitted ? (
              <div className="py-4 text-center">
                <CheckCircle2 className="w-10 h-10 text-[#3E7B54] mx-auto mb-3" />
                <h4 className="text-sm font-semibold text-[#292720]">Password Reset Initiated</h4>
                <p className="mt-1.5 text-xs text-[#777267] max-w-xs mx-auto">
                  If <span className="font-mono text-[#292720]">{forgotEmail || email}</span> matches a registered clinical reviewer, a secure recovery link has been dispatched.
                </p>
                <button
                  onClick={() => {
                    setShowForgotModal(false);
                    setForgotSubmitted(false);
                  }}
                  className="mt-5 w-full py-2.5 rounded-xl bg-[#25241F] text-xs font-semibold text-[#F8F5EF]"
                >
                  Return to Sign In
                </button>
              </div>
            ) : (
              <div>
                <p className="text-xs text-[#6B665A] mb-4 leading-relaxed">
                  Enter your clinician email address to receive password reset authorization or reach out to your facility's ConfiRoute administrator.
                </p>
                <input
                  type="email"
                  value={forgotEmail}
                  onChange={(e) => setForgotEmail(e.target.value)}
                  placeholder="clinician@confiroute.ai"
                  className="w-full px-3.5 py-2.5 bg-[#FAF8F5] border border-[#E8E2D5] rounded-xl text-xs text-[#292720] mb-4 focus:outline-none focus:ring-2 focus:ring-[#C5A878]"
                />
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setShowForgotModal(false)}
                    className="flex-1 py-2.5 rounded-xl border border-[#E8E2D5] text-xs font-medium text-[#6B665A] hover:bg-[#F0EBE2]"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => setForgotSubmitted(true)}
                    className="flex-1 py-2.5 rounded-xl bg-[#25241F] text-xs font-semibold text-[#F8F5EF] hover:bg-[#1A1916]"
                  >
                    Send Instructions
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
