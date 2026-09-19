import useSWR, { SWRConfiguration } from "swr";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function swrFetcher<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(body.detail || `Request failed: ${res.status}`, res.status);
  }
  return res.json();
}

const defaultConfig: SWRConfiguration = {
  revalidateOnFocus: false,
  dedupingInterval: 10000,
  onErrorRetry: (error, key, config, revalidate, { retryCount }) => {
    if (error instanceof ApiError && error.status >= 400 && error.status < 500) return;
    if (retryCount >= 2) return;
    setTimeout(() => revalidate({ retryCount }), 5000);
  },
};

export function useApi<T>(path: string | null, config?: SWRConfiguration) {
  return useSWR<T>(path, swrFetcher, { ...defaultConfig, ...config });
}

export function isExpected404(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}

export function isServerError(error: unknown): boolean {
  if (error instanceof ApiError) return error.status >= 500;
  if (error instanceof Error) {
    return error.message.includes("Failed to fetch") || error.message.includes("NetworkError");
  }
  return false;
}

export { swrFetcher, ApiError };
