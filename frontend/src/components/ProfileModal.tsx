import { X, UserCheck, Mail, Building, Clock, LogOut } from "lucide-react";
import { useAuth } from "../context/AuthContext";

interface ProfileModalProps {
  onClose: () => void;
}

export default function ProfileModal({ onClose }: ProfileModalProps) {
  const { user, logout } = useAuth();

  if (!user) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#25241F]/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md rounded-3xl bg-[#FFFEFC] border border-[#E8E2D5] p-6 sm:p-8 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-xl text-[#8C877B] hover:text-[#292720] hover:bg-[#F0EBE2] transition-colors cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex flex-col items-center text-center mb-6 pb-6 border-b border-[#F1ECE2]">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[#25241F] to-[#38362E] flex items-center justify-center shadow-md mb-3 border border-[#C5A878]/40">
            <UserCheck className="w-8 h-8 text-[#C5A878]" />
          </div>
          <h3 className="text-xl font-heading font-bold text-[#292720]">{user.name}</h3>
          <p className="text-xs text-[#8C7349] font-medium mt-0.5">{user.role}</p>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-mono bg-[#EDF5F0] text-[#3E7B54] border border-[#B8D9C3] mt-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#3E7B54]" />
            Active Session Verified
          </span>
        </div>

        <div className="space-y-3 mb-6 text-xs text-[#4A473E]">
          <div className="flex items-center gap-3 p-3 rounded-xl bg-[#FAF8F5] border border-[#E8E2D5]">
            <Mail className="w-4 h-4 text-[#8C877B] shrink-0" />
            <div className="flex-1 truncate">
              <span className="text-[10px] text-[#8C877B] block font-mono">EMAIL</span>
              <span className="font-semibold text-[#292720]">{user.email}</span>
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 rounded-xl bg-[#FAF8F5] border border-[#E8E2D5]">
            <Building className="w-4 h-4 text-[#8C877B] shrink-0" />
            <div className="flex-1 truncate">
              <span className="text-[10px] text-[#8C877B] block font-mono">DEPARTMENT</span>
              <span className="font-semibold text-[#292720]">{user.department}</span>
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 rounded-xl bg-[#FAF8F5] border border-[#E8E2D5]">
            <Clock className="w-4 h-4 text-[#8C877B] shrink-0" />
            <div className="flex-1 truncate">
              <span className="text-[10px] text-[#8C877B] block font-mono">SESSION STARTED</span>
              <span className="font-semibold text-[#292720]">
                {new Date(user.sessionStartedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 py-3 rounded-xl border border-[#E8E2D5] text-xs font-semibold text-[#6B665A] hover:bg-[#F0EBE2] transition-colors cursor-pointer"
          >
            Close
          </button>
          <button
            onClick={() => {
              onClose();
              logout();
            }}
            className="py-3 px-4 rounded-xl bg-[#FDF1EF] border border-[#E8B6AF] text-xs font-semibold text-[#BD4C3D] hover:bg-[#FBE6E4] transition-colors flex items-center justify-center gap-2 cursor-pointer"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign Out</span>
          </button>
        </div>
      </div>
    </div>
  );
}
