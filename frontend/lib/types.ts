export type EventType = "wedding" | "introduction" | "linked";

export type ProjectRole =
  | "OWNER"
  | "PARTNER"
  | "COMMITTEE_CHAIR"
  | "COMMITTEE_MEMBER"
  | "FAMILY_VIEWER"
  | "GUEST_VIEWER";

export type BudgetVisibility = "FULL_ACCESS" | "SUMMARY_ACCESS" | "CONTRIBUTION_ONLY" | "NO_ACCESS";

export type Project = {
  id: string;
  type: EventType;
  title: string;
  event_date: string | null;
  partner_user_id?: string | null;
  owner_user_id: string;
  status: string;
  role?: ProjectRole;
  budget_visibility_mode?: BudgetVisibility;
  permissions?: string[];
};

export type AuthUser = {
  id: string;
  name?: string | null;
  phone?: string | null;
  email?: string | null;
};

export type AuthToken = {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
};

export type BudgetLineItem = {
  id: string;
  project_id: string;
  category: string;
  description: string;
  item_name?: string | null;
  unit_cost: number;
  quantity: number;
  total_cost: number;
  deposited_amount: number;
  balance: number;
  next_deposit_date?: string | null;
  payment_details?: string | null;
  estimated_amount: number;
  actual_amount: number;
  status: string;
};

export type Contribution = {
  id: string;
  project_id: string;
  contributor: string;
  pledged: number;
  paid: number;
  status: string;
};

export type BudgetResponse = {
  visibility: BudgetVisibility;
  total?: number | null;
  spent?: number | null;
  remaining?: number | null;
  contribution_progress?: number | null;
  pledged_total?: number | null;
  line_item_total_cost?: number | null;
  line_item_deposited_total?: number | null;
  line_item_balance_total?: number | null;
  line_items?: BudgetLineItem[] | null;
  contributions?: Contribution[] | null;
};

export type EventPermission =
  | "event.manage"
  | "budget.edit"
  | "committee.manage"
  | "guest_invites.manage"
  | "vendors.manage"
  | "meetings.manage"
  | "tasks.manage";
