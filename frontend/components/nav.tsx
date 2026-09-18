"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavItem {
  href: string;
  label: string;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    title: "PLATFORM",
    items: [
      { href: "/", label: "Overview" },
      { href: "/data", label: "Data" },
      { href: "/train", label: "Train" },
      { href: "/cohort-builder", label: "Cohort Builder" },
      { href: "/synthetic-cohort", label: "Synthetic Cohort" },
    ],
  },
  {
    title: "ANALYSIS",
    items: [
      { href: "/patient-journeys", label: "Patient Journeys" },
      { href: "/validation", label: "Validation" },
      { href: "/privacy", label: "Privacy" },
      { href: "/privacy-fidelity", label: "Privacy vs Fidelity" },
      { href: "/model-comparison", label: "Model Comparison" },
    ],
  },
  {
    title: "RESEARCH",
    items: [
      { href: "/research-readiness", label: "Research Readiness" },
      { href: "/experiments", label: "Experiments" },
      { href: "/export", label: "Export" },
    ],
  },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <aside
      className="w-64 min-h-screen flex flex-col shrink-0"
      style={{ background: "#0F2F2C", color: "#B8CFC8" }}
    >
      <div className="p-5 border-b" style={{ borderColor: "rgba(255,255,255,0.1)" }}>
        <h1 className="text-xl font-bold tracking-tight" style={{ color: "#FFFFFF" }}>
          ClinSynth
        </h1>
        <p className="text-xs mt-0.5" style={{ color: "#4FAE8A" }}>
          Clinical Research Twin Engine
        </p>
      </div>
      <nav className="flex-1 py-2 overflow-y-auto">
        {NAV_GROUPS.map((group) => (
          <div key={group.title} className="mb-1">
            <p
              className="px-5 pt-4 pb-1.5 text-xs font-semibold tracking-widest"
              style={{ color: "rgba(255,255,255,0.35)" }}
            >
              {group.title}
            </p>
            {group.items.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className="flex items-center gap-2.5 px-5 py-2 text-sm transition-colors"
                  style={
                    active
                      ? {
                          background: "rgba(79,174,138,0.15)",
                          color: "#4FAE8A",
                          borderRight: "2px solid #4FAE8A",
                          fontWeight: 500,
                        }
                      : {
                          color: "#B8CFC8",
                        }
                  }
                  onMouseEnter={(e) => {
                    if (!active) {
                      e.currentTarget.style.background = "rgba(255,255,255,0.05)";
                      e.currentTarget.style.color = "#FFFFFF";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!active) {
                      e.currentTarget.style.background = "transparent";
                      e.currentTarget.style.color = "#B8CFC8";
                    }
                  }}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
      <div
        className="p-4 border-t text-xs"
        style={{ borderColor: "rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.3)" }}
      >
        Privacy-Preserving Research Tool
      </div>
    </aside>
  );
}
