// ─── Volunteer Types ───

export interface VolunteerLocation {
  city: string;
  district: string;
  state: string;
  lat: number;
  lon: number;
  raw_address?: string;
}

export interface Volunteer {
  id: string;
  name: string;
  phone?: string;
  email?: string;
  location: VolunteerLocation;
  skills: string[];
  skills_raw: string[];
  languages: string[];
  availability: {
    days: string[];
    hours: string;
    notes?: string;
  };
  source: {
    type: string;
    file_name: string;
    confidence: number;
  };
  created_at: any;
}

// ─── Threat Types ───

export interface EvidenceItem {
  source: string;
  timestamp: any;
  content: string;
  url?: string;
  weight: number;
}

export interface Threat {
  id: string;
  type: string;
  severity: number;
  confidence: number;
  location: VolunteerLocation & { radius_km: number };
  detected_at: any;
  est_escalation_window_min: number;
  evidence_chain: EvidenceItem[];
  watcher_reasoning: string;
  grounded_facts: string[];
  status: "monitoring" | "pre_staged" | "confirmed" | "resolved" | "false_positive";
  pre_staged_plan_id?: string;
  created_at: any;
}

// ─── Response Plan Types ───

export interface MatchedVolunteer {
  volunteer_id: string;
  name?: string;
  match_score: number;
  match_reasons: string[];
  distance_km: number;
  assigned_role?: string;
  outreach_status: string;
}

export interface OutreachMessage {
  volunteer_id: string;
  language: string;
  channel: string;
  message: string;
  generated_at: any;
  sent_at?: any;
}

export interface ResponsePlan {
  id: string;
  threat_id: string;
  status: string;
  matched_volunteers: MatchedVolunteer[];
  outreach_messages: Record<string, OutreachMessage>;
  coordinator_reasoning: string;
  timeline: Array<{
    timestamp: any;
    event: string;
    actor: string;
  }>;
  created_at: any;
}

// ─── Agent Activity Types ───

export interface AgentActivity {
  id: string;
  agent: "ingestor" | "watcher" | "coordinator";
  action: string;
  reasoning: string;
  input_summary: string;
  output_summary: string;
  duration_ms: number;
  timestamp: any;
  related_entity?: {
    type: string;
    id: string;
  };
}

// ─── Replay Types ───

export interface ReplayEvent {
  time: string;
  source: string;
  type: string;
  data: Record<string, any>;
}

export interface ReplayTimeline {
  scenario: string;
  replay_start: string;
  replay_end: string;
  ground_truth: {
    first_news_article: string;
    first_govt_advisory: string;
    prahari_alert_time: string;
    time_advantage_vs_news: string;
    time_advantage_vs_govt: string;
  };
  events: ReplayEvent[];
}
