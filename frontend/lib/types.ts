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

export type BudgetResponse = {
  visibility: BudgetVisibility;
  total?: number | null;
  spent?: number | null;
  remaining?: number | null;
  contribution_progress?: number | null;
  pledged_total?: number | null;
};
