import { ApiError } from "./swr";

const NOT_READY_MESSAGES: Record<string, string> = {
  "No dataset loaded": "No dataset loaded yet. Load demo data or upload a CSV to get started.",
  "No cohort generated": "No cohort generated yet. Generate one from the Cohort Builder page.",
  "No model trained": "No model trained yet. Train a model from the Train page first.",
  "not found": "This resource hasn't been created yet.",
};

export function friendlyError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 404) {
      for (const [key, msg] of Object.entries(NOT_READY_MESSAGES)) {
        if (err.message.toLowerCase().includes(key.toLowerCase())) return msg;
      }
      return "This resource hasn't been created yet.";
    }
    if (err.status >= 500) {
      return "The server is temporarily unavailable. Please try again.";
    }
    if (err.status >= 400 && err.status < 500) {
      // Clean backend detail
      const msg = err.message;
      if (msg.includes("Failed to fetch") || msg.includes("NetworkError") || msg.includes("[object Object]") || msg.includes("Traceback") || msg.includes("<!DOCTYPE html>")) {
         return "An unexpected error occurred. Please try again.";
      }
      return msg.length > 200 ? msg.slice(0, 180) + "..." : msg;
    }
  }

  if (err instanceof Error) {
    const msg = err.message;
    if (msg.includes("Failed to fetch") || msg.includes("NetworkError") || msg.includes("Load failed")) {
      return "Unable to reach the server. Please try again.";
    }
    if (msg.includes("[object Object]") || msg.includes("<!DOCTYPE html>")) {
      return "An unexpected error occurred. Please try again.";
    }
    if (msg.includes("Traceback") || msg.includes("File \"/") || msg.includes("Exception:")) {
      return "An internal error occurred. Please try again.";
    }
    return msg.length > 200 ? msg.slice(0, 180) + "..." : msg;
  }
  return "An unexpected error occurred. Please try again.";
}
