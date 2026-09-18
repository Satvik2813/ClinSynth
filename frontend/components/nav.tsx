"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: "📊" },
  { href: "/data", label: "Data", icon: "📁" },
  { href: "/train", label: "Train", icon: "⚙️" },
  { href: "/cohort-builder", label: "Cohort Builder", icon: "🔧" },
  { href: "/synthetic-cohort", label: "Synthetic Cohort", icon: "🧬" },
  { href: "/patient-journeys", label: "Patient Journeys", icon: "🩺" },
  { href: "/validation", label: "Validation", icon: "✓" },
  { href: "/privacy", label: "Privacy", icon: "🔒" },
  { href: "/privacy-fidelity", label: "Privacy vs Fidelity", icon: "⚖️" },
  { href: "/model-comparison", label: "Model Comparison", icon: "🔬" },
  { href: "/experiments", label: "Experiments", icon: "📋" },
  { href: "/export", label: "Export", icon: "💾" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <aside className="w-64 min-h-screen bg-slate-900 text-slate-200 flex flex-col shrink-0">
      <div className="p-5 border-b border-slate-700">
        <h1 className="text-xl font-bold text-white tracking-tight">ClinSynth</h1>
        <p className="text-xs text-slate-400 mt-0.5">Synthetic Patient Data Platform</p>
      </div>
      <nav className="flex-1 py-3 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2.5 px-5 py-2.5 text-sm transition-colors ${
                active
                  ? "bg-teal-600/20 text-teal-300 border-r-2 border-teal-400 font-medium"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              }`}
            >
              <span className="text-base w-5 text-center">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-4 border-t border-slate-700 text-xs text-slate-500">
        Privacy-Preserving Research Tool
      </div>
    </aside>
  );
}
