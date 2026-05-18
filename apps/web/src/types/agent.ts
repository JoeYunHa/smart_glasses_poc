export type ServiceType =
  | "scene_assistant"
  | "navigation"
  | "device_control"
  | "safety_alert"
  | "context_memory"
  | "label_reader"
  | "unknown";

export type AgentMode = "baseline" | "optimized";

export interface GpsContext {
  latitude: number;
  longitude: number;
  location_type?: string;
  place_name?: string;
}

export interface DeviceInfo {
  device_id: string;
  name: string;
  type: string;
  supported_actions: string[];
  risk_level: string;
  requires_confirmation: boolean;
  state: Record<string, unknown>;
}

export interface ContextRequest {
  user_request: string;
  gps?: GpsContext | null;
  nearby_devices: DeviceInfo[];
  mode: AgentMode;
}

export interface LatencyBreakdown {
  frame_sampling: number;
  keyframe_selection: number;
  graph_retrieval: number;
  routing: number;
  vlm: number;
  total: number;
}

export interface ActionResult {
  device_id: string;
  action: string;
  success: boolean;
  message: string;
}

export interface AgentResponse {
  request_id: string;
  selected_service: ServiceType;
  router_confidence: number;
  vlm_used: boolean;
  response_text: string;
  action_result?: ActionResult | null;
  original_frame_count: number;
  selected_keyframe_count: number;
  retrieved_graph_nodes: number;
  latency_ms: LatencyBreakdown;
  mode: AgentMode;
}

export interface GraphNode {
  id: string;
  type: string;
  [key: string]: unknown;
}

export interface ModeMetrics {
  count: number;
  avg_latency_ms: number;
  avg_vlm_calls: number;
  avg_frame_reduction_ratio: number;
  avg_graph_nodes: number;
  service_distribution: Record<string, number>;
  avg_tokens: number;
  avg_image_payload_bytes: number;
  cloud_call_ratio: number;
  fallback_distribution: Record<string, number>;
  failure_distribution: Record<string, number>;
}

export interface MetricsData {
  total: number;
  by_mode: Record<string, ModeMetrics>;
}
