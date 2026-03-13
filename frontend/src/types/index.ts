export interface ProxyRequest {
  id: number;
  method: string;
  host: string;
  path: string;
  url: string;
  status_code: number;
  content_type: string;
  response_time: number;
  timestamp: string;
  request_headers: Record<string, string>;
  request_body: string;
  response_headers: Record<string, string>;
  response_body: string;
  tags: string[];
  notes: string;
}

export interface Stats {
  total_requests: number;
  unique_hosts: number;
  vulnerabilities_found: number;
  active_connections: number;
  method_distribution: Record<string, number>;
  recent_requests: ProxyRequest[];
}

export interface ScanResult {
  id: number;
  request_id: number;
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  description: string;
  evidence: string;
  url: string;
  parameter: string;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  offset: number;
  limit: number;
}

export interface WebSocketMessage {
  type: 'new_request' | 'scan_result' | 'status';
  data: unknown;
}
