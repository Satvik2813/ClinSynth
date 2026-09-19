"use client";

export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="card" style={{ padding: "1.5rem" }}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          style={{
            height: i === 0 ? "1.25rem" : "0.875rem",
            width: i === 0 ? "40%" : `${60 + (i * 13) % 30}%`,
            background: "var(--border)",
            borderRadius: "0.375rem",
            marginBottom: i < lines - 1 ? "0.75rem" : 0,
            animation: "pulse 1.5s ease-in-out infinite",
          }}
        />
      ))}
      <style>{`@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }`}</style>
    </div>
  );
}

export function SkeletonMetrics({ count = 4 }: { count?: number }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: `repeat(auto-fit, minmax(180px, 1fr))`, gap: "1rem" }}>
      {Array.from({ length: count }).map((_, i) => (
        <div className="card" key={i} style={{ padding: "1.25rem" }}>
          <div
            style={{
              height: "2rem",
              width: "50%",
              background: "var(--border)",
              borderRadius: "0.375rem",
              marginBottom: "0.5rem",
              animation: "pulse 1.5s ease-in-out infinite",
            }}
          />
          <div
            style={{
              height: "0.75rem",
              width: "70%",
              background: "var(--border)",
              borderRadius: "0.375rem",
              animation: "pulse 1.5s ease-in-out infinite",
            }}
          />
        </div>
      ))}
      <style>{`@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }`}</style>
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="card">
      <div
        style={{
          height: "1rem",
          width: "30%",
          background: "var(--border)",
          borderRadius: "0.375rem",
          marginBottom: "1rem",
          animation: "pulse 1.5s ease-in-out infinite",
        }}
      />
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} style={{ display: "flex", gap: "1rem", marginBottom: "0.75rem" }}>
          {Array.from({ length: cols }).map((_, c) => (
            <div
              key={c}
              style={{
                height: "0.875rem",
                flex: c === 0 ? 2 : 1,
                background: "var(--border)",
                borderRadius: "0.375rem",
                animation: "pulse 1.5s ease-in-out infinite",
                opacity: r === 0 ? 0.8 : 0.5,
              }}
            />
          ))}
        </div>
      ))}
      <style>{`@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }`}</style>
    </div>
  );
}
