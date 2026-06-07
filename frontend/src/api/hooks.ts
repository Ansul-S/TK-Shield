import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { SLOW_TIMEOUT_MS, apiDelete, apiGet, apiPost } from "./client";
import { HEALTH_REFETCH_MS } from "@/config";
import type {
  AnalyzeBody,
  AnalyzeResult,
  CreateTKBody,
  Health,
  MonitorBody,
  MonitorResult,
  NoveltyBody,
  NoveltyResult,
  ReportResult,
  Stats,
  TKEntry,
  TKListResponse,
} from "./types";

// Query keys kept in one place so mutations can invalidate precisely.
export const qk = {
  health: ["health"] as const,
  stats: ["stats"] as const,
  tkList: (q: string, limit: number, offset: number) =>
    ["tk", "list", q, limit, offset] as const,
  tkEntry: (id: string) => ["tk", "entry", id] as const,
};

// ---- queries ----

// Drives the header status dots; polled so the UI reflects the LLM / live-patent
// availability flipping on or off without a reload.
export function useHealth() {
  return useQuery({
    queryKey: qk.health,
    queryFn: () => apiGet<Health>("/api/health"),
    refetchInterval: HEALTH_REFETCH_MS,
  });
}

export function useTkEntries(q: string, limit: number, offset: number) {
  return useQuery({
    queryKey: qk.tkList(q, limit, offset),
    queryFn: () =>
      apiGet<TKListResponse>(
        `/api/tk?q=${encodeURIComponent(q)}&limit=${limit}&offset=${offset}`,
      ),
    placeholderData: (prev) => prev, // keep the list visible while paging/searching
  });
}

export function useTkEntry(id: string | undefined) {
  return useQuery({
    queryKey: qk.tkEntry(id ?? ""),
    queryFn: () => apiGet<TKEntry>(`/api/tk/${id}`),
    enabled: !!id,
  });
}

export function useStats() {
  return useQuery({
    queryKey: qk.stats,
    queryFn: () => apiGet<Stats>("/api/stats"),
  });
}

// ---- mutations (writes / slow compute) ----

export function useCreateTk() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateTKBody) => apiPost<TKEntry>("/api/tk", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tk"] }),
  });
}

export function useDeleteTk() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiDelete<{ deleted: string }>(`/api/tk/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tk"] }),
  });
}

// Fast: hybrid search + risk score, no LLM/network.
export function useAnalyze() {
  return useMutation({
    mutationFn: (body: AnalyzeBody) =>
      apiPost<AnalyzeResult>("/api/analyze", body),
  });
}

// Slow (tens of seconds, up to ~2 min on a small local model): live enrichment
// + LLM generation. Uses the long client timeout so a hung call fails cleanly.
export function useReport() {
  return useMutation({
    mutationFn: (body: AnalyzeBody) =>
      apiPost<ReportResult>("/api/report?format=json", body, SLOW_TIMEOUT_MS),
  });
}

export function useNovelty() {
  return useMutation({
    mutationFn: (body: NoveltyBody) =>
      apiPost<NoveltyResult>("/api/novelty", body, SLOW_TIMEOUT_MS),
  });
}

export function useMonitor() {
  return useMutation({
    mutationFn: (body: MonitorBody) =>
      apiPost<MonitorResult>("/api/monitor", body),
  });
}
