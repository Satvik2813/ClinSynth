import { ApiError } from "./swr";

const NOT_READY_MESSAGES: Record<string, string> = {
  "No dataset loaded": "No dataset loaded yet. Load demo data or upload a CSV to get started.",
  "No cohort generated": "No cohort generated yet. Generate one from the Cohort Builder page.",
  "No model trained": "No model trained yet. Train a model from the Train page first.",
  "not found": "This resource hasn't been created yet.",
};

export function friendlyError(err: unknown): string {
  if (err instanceof ApiError && err.status === 404) {
    for (const [key, msg] of Object.entries(NOT_READY_MESSAGES)) {
      if (err.message.toLowerCase().includes(key.toLowerCase())) return msg;
    }
    return err.message;
  }

  if (err instanceof Error) {
    const msg = err.message;
    if (msg.includes("Failed to fetch") || msg.includes("NetworkError")) {
      return "Unable to reach the server. Please check your connection and try again.";
    }
    if (msg.includes("[object Object]")) {
      return "An unexpected error occurred. Please try again.";
    }
    if (msg.includes("Traceback") || msg.includes("File \"/")) {
      const lines = msg.split("\n");
      const last = lines[lines.length - 1]?.trim();
      return last && last.length > 10
        ? last.replace(/^(.*Error:\s*)/, "")
        : "An internal error occurred. Please try again.";
    }
    if (msg.length > 200) {
      return msg.slice(0, 180) + "...";
    }
    return msg;
  }
  return "An unexpected error occurred. Please try again.";
}
