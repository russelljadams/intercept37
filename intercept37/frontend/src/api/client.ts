import axios from 'axios';
import type { ProxyRequest, Stats, ScanResult, PaginatedResponse } from '../types';

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface RequestFilters {
  limit?: number;
  offset?: number;
  method?: string;
  host?: string;
  status?: number;
  search?: string;
}

export async function fetchRequests(filters: RequestFilters = {}): Promise<PaginatedResponse<ProxyRequest>> {
  const params = new URLSearchParams();
  if (filters.limit) params.set('limit', String(filters.limit));
  if (filters.offset) params.set('offset', String(filters.offset));
  if (filters.method) params.set('method', filters.method);
  if (filters.host) params.set('host', filters.host);
  if (filters.status) params.set('status', String(filters.status));
  if (filters.search) params.set('search', filters.search);
  const { data } = await api.get(`/requests?${params.toString()}`);
  return data.results || data;
}

export async function fetchRequestDetail(id: number): Promise<ProxyRequest> {
  const { data } = await api.get(`/requests/${id}`);
  return data.results || data;
}

export async function repeatRequest(id: number): Promise<ProxyRequest> {
  const { data } = await api.post(`/requests/${id}/repeat`);
  return data.results || data;
}

export async function tagRequest(id: number, tags: string[]): Promise<void> {
  await api.post(`/requests/${id}/tag`, tags);
}

export async function noteRequest(id: number, note: string): Promise<void> {
  await api.post(`/requests/${id}/note`, note);
}

export async function fetchStats(): Promise<Stats> {
  const { data } = await api.get('/stats');
  return data.results || data;
}

export async function fetchScanResults(severity?: string): Promise<ScanResult[]> {
  const params = severity ? `?severity=${severity}` : '';
  const { data } = await api.get(`/scan-results${params}`);
  return data.results || data;
}

export async function sendManualRequest(req: {
  method: string;
  url: string;
  headers: Record<string, string>;
  body: string;
}): Promise<ProxyRequest> {
  const { data } = await api.post('/requests/send', req);
  return data.results || data;
}

export default api;
