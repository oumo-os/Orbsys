// ── Enums ─────────────────────────────────────────────────────────────────────

export type MemberState =
  | "probationary" | "active" | "on_leave"
  | "inactive" | "under_review" | "suspended" | "exited";

export type MotionType = "sys_bound" | "non_system" | "hybrid";

export type MotionState =
  | "draft" | "active" | "voted" | "gate1_pending" | "gate1_approved"
  | "gate1_rejected" | "revision_requested" | "pending_implementation"
  | "gate2_pending" | "enacted" | "enacted_locked" | "contested"
  | "deviated_justified" | "abandoned";

export type STFType = "xstf" | "astf_motion" | "astf_periodic" | "vstf" | "jstf" | "meta_astf";
export type STFState = "forming" | "active" | "all_filed" | "completed" | "dissolved";

export type VerdictType =
  | "approve" | "reject" | "revision_request"
  | "clear" | "concerns" | "violation"
  | "adequate" | "insufficient"
  | "finding_confirmed" | "finding_rejected";

export type CellType =
  | "deliberation" | "closed_circle" | "motion_review"
  | "stf_workspace" | "periodic_audit";

export type CellState =
  | "active" | "temporarily_closed" | "reactivated"
  | "archived" | "dissolved" | "frozen" | "suspended";

// ── Entities ──────────────────────────────────────────────────────────────────

export interface Member {
  id: string;
  handle: string;
  display_name: string;
  org_id: string;
  current_state: MemberState;
  joined_at: string;
}

export interface Dormain {
  id: string;
  name: string;
  description?: string;
  decay_fn: "exponential" | "linear" | "step";
  decay_half_life_months: number;
}

export interface CompetenceScore {
  dormain_id: string;
  dormain_name: string;
  w_s: number;
  w_s_peak: number;
  w_h: number;
  volatility_k: number;
  last_activity_at?: string;
}

export interface Circle {
  id: string;
  name: string;
  description?: string;
  dormains: { dormain_id: string; dormain_name: string; mandate_type: "primary" | "secondary" }[];
  member_count: number;
  dissolved_at?: string;
}

export interface CommonsThread {
  id: string;
  title: string;
  body: string;
  author: Pick<Member, "id" | "handle" | "display_name">;
  tags: { dormain_id: string; dormain_name: string; weight: number }[];
  state: "open" | "frozen" | "sponsored" | "closed";
  sponsored_at?: string;
  created_at: string;
  post_count: number;
  feed_relevance?: number;
}

export interface Cell {
  id: string;
  cell_type: CellType;
  state: CellState;
  visibility: "open" | "closed";
  founding_mandate?: string;
  revision_directive?: string;
  invited_circles: { circle_id: string; circle_name: string }[];
  created_at: string;
}

export interface CellMinutes {
  key_positions: string[];
  open_questions: string[];
  emerging_consensus: string[];
  points_of_contention: string[];
  generated_at: string;
}

export interface Motion {
  id: string;
  motion_type: MotionType;
  state: MotionState;
  filed_by: Pick<Member, "id" | "handle" | "display_name">;
  directive?: { body: string; commitments: string[] };
  specifications?: { parameter: string; new_value: unknown; justification: string }[];
  // Non-system / hybrid: required
  implementing_circle_ids?: string[];
  implementing_circles?: Pick<Circle, "id" | "name">[];
  created_at: string;
  crystallised_at?: string;
}

export interface Resolution {
  id: string;
  resolution_ref: string;
  state: string;
  implementation_type: string;
  implementing_circle_ids?: string[];
  gate2_agent: string;
  enacted_at?: string;
}

export interface STFInstance {
  id: string;
  stf_type: STFType;
  state: STFState;
  mandate: string;
  deadline?: string;
  assignment_count: number;
  verdicts_filed: number;
  created_at: string;
}

export interface LedgerEvent {
  id: string;
  event_type: string;
  subject_id?: string;
  subject_type?: string;
  payload: Record<string, unknown>;
  created_at: string;
  event_hash: string;
  prev_hash: string;
}

// ── Pagination ────────────────────────────────────────────────────────────────

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}
