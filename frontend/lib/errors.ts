export function friendlyError(err: unknown): string {
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
