import useSWR, { SWRConfiguration } from "swr";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function swrFetcher<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

const defaultConfig: SWRConfiguration = {
  revalidateOnFocus: false,
  dedupingInterval: 10000,
  errorRetryCount: 2,
};

export function useApi<T>(path: string | null, config?: SWRConfiguration) {
  return useSWR<T>(path, swrFetcher, { ...defaultConfig, ...config });
}

export { swrFetcher };
