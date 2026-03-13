import { useState, useEffect, useCallback } from 'react';
import {
  fetchRequests,
  fetchRequestDetail,
  fetchStats,
  fetchScanResults,
  type RequestFilters,
} from '../api/client';
import type { ProxyRequest, Stats, ScanResult, PaginatedResponse } from '../types';

export function useRequests(filters: RequestFilters = {}) {
  const [data, setData] = useState<PaginatedResponse<ProxyRequest> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchRequests(filters);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch requests');
    } finally {
      setLoading(false);
    }
  }, [JSON.stringify(filters)]);

  useEffect(() => { load(); }, [load]);

  return { data, loading, error, refetch: load };
}

export function useRequestDetail(id: number | null) {
  const [data, setData] = useState<ProxyRequest | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id === null) { setData(null); return; }
    setLoading(true);
    setError(null);
    fetchRequestDetail(id)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed'))
      .finally(() => setLoading(false));
  }, [id]);

  return { data, loading, error };
}

export function useStats() {
  const [data, setData] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const result = await fetchStats();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch stats');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); const i = setInterval(load, 5000); return () => clearInterval(i); }, [load]);

  return { data, loading, error, refetch: load };
}

export function useScanResults(severity?: string) {
  const [data, setData] = useState<ScanResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchScanResults(severity);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch scan results');
    } finally {
      setLoading(false);
    }
  }, [severity]);

  useEffect(() => { load(); }, [load]);

  return { data, loading, error, refetch: load };
}
