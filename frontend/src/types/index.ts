export type Role = "citizen" | "district_officer" | "state_admin" | "system_admin";

export interface State {
  id: number;
  name: string;
  code: string;
}

export interface District {
  id: number;
  state_id: number;
  name: string;
  code: string;
  center_lat: number;
  center_lon: number;
  boundary_geojson?: any;
}

export interface Facility {
  id: number;
  district_id: number;
  name: string;
  category: "hospital" | "shelter" | "police" | "fire_station";
  latitude: number;
  longitude: number;
  contact_number?: string;
  capacity?: number;
  details?: Record<string, any>;
}

export interface AlertArea {
  id: number;
  alert_id: number;
  district_id?: number;
  boundary_geojson?: any;
}

export interface Alert {
  id: number;
  type: string;
  title: string;
  description: string;
  severity: "low" | "medium" | "high" | "critical";
  issuer: string;
  is_official: boolean;
  valid_from: string;
  valid_to: string;
  status: "draft" | "active" | "cancelled" | "expired";
  created_at: string;
  updated_at?: string;
  areas?: AlertArea[];
}

export interface HazardObservation {
  id: number;
  hazard_type: string;
  source: string;
  values: Record<string, any>;
  observed_at: string;
  district_id?: number;
}

export interface DistrictOverview {
  district: District;
  overall_status: {
    highest_alert_severity: string;
    active_alerts_count: number;
    last_updated: string;
  };
  observations: {
    weather?: Record<string, any>;
    earthquake?: Record<string, any>;
    fire?: Record<string, any>;
    source_count: number;
  };
  applicable_alerts: Alert[];
  risk_estimates: {
    composite_risk_level: "low" | "medium" | "high" | "critical";
    calculated_score: number;
    factors: Record<string, any>;
    is_indicative: boolean;
  };
  safety_guidance: Array<{
    title: string;
    summary: string;
    instruction: string;
  }>;
  data_sources_status: Array<{
    source: string;
    mode: "live" | "demo";
    status: "healthy" | "degraded" | "failing";
    last_sync: string;
  }>;
}

export interface CitizenReport {
  id: number;
  user_id?: number;
  district_id?: number;
  assigned_officer_id?: number;
  type: string;
  description: string;
  latitude: number;
  longitude: number;
  status: "submitted" | "under_review" | "verified" | "rejected" | "resolved" | "reopened";
  confidence_score?: number;
  reopened_count?: number;
  created_at: string;
  updated_at?: string;
  media?: Array<{
    id: number;
    file_path: string;
    file_name?: string;
    content_type: string;
    file_size_bytes?: number;
  }>;
  reviews?: Array<{
    id: number;
    reviewer_id: number;
    decision: string;
    notes?: string;
    timestamp: string;
  }>;
}

export interface AwarenessItem {
  id: number;
  hazard: string;
  stage: "before" | "during" | "after";
  language: "en" | "hi";
  title: string;
  instructions: string[];
}

export interface NotificationSubscription {
  id: number;
  endpoint: string;
  district_id?: number;
  is_active: boolean;
  created_at: string;
}
