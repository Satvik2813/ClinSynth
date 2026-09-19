"use client";

import { Toaster } from "sonner";

export function ToasterProvider() {
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        style: {
          background: "#FFFFFF",
          border: "1px solid #DCE7E3",
          color: "#17211F",
          fontFamily: "var(--font-geist-sans), system-ui, sans-serif",
          fontSize: "0.875rem",
        },
        classNames: {
          success: "toast-success",
          error: "toast-error",
          warning: "toast-warning",
          info: "toast-info",
        },
      }}
      richColors={false}
      duration={4000}
    />
  );
}
