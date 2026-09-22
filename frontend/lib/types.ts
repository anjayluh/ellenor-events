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
  customer_account_id: string;
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

export type AuthMessage = {
  status: string;
  message: string;
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

export type CustomerAccount = {
  id: string;
  name: string;
  status: "LEAD" | "ACTIVE" | "SUSPENDED" | "CANCELLED";
  created_at: string;
  updated_at?: string | null;
};

export type CustomerAccountMember = {
  id: string;
  customer_account_id: string;
  user_id: string;
  role: "OWNER" | "MEMBER";
  status: "ACTIVE" | "INACTIVE";
  created_at: string;
};

export type AccountEntitlement = {
  id: string;
  customer_account_id: string;
  key: string;
  quantity?: number | null;
  used_quantity: number;
  status: "ACTIVE" | "INACTIVE" | "EXPIRED" | "CANCELLED";
  starts_at?: string | null;
  expires_at?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at?: string | null;
};

export type CustomerAccountOverview = {
  account: CustomerAccount;
  membership: CustomerAccountMember;
  entitlements: AccountEntitlement[];
  projects: Project[];
};

export type PackagePrice = {
  id: string;
  package_plan_id: string;
  currency: "UGX";
  amount_minor: number;
  billing_interval: "ONE_TIME" | "MONTHLY" | "YEARLY";
  status: "DRAFT" | "ACTIVE" | "INACTIVE" | "ARCHIVED";
  starts_at?: string | null;
  ends_at?: string | null;
  created_at: string;
  updated_at?: string | null;
};

export type PackageEntitlementGrant = {
  id: string;
  package_plan_id: string;
  entitlement_key: string;
  scope: "ACCOUNT" | "EVENT";
  value_type: "BOOLEAN" | "QUANTITY" | "UNLIMITED";
  quantity?: number | null;
  duration_days?: number | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at?: string | null;
};

export type CatalogPackage = {
  id: string;
  code: string;
  name: string;
  description: string;
  status?: "DRAFT" | "ACTIVE" | "INACTIVE" | "ARCHIVED";
  is_public?: boolean;
  is_add_on: boolean;
  display_order: number;
  metadata?: Record<string, unknown>;
  prices: PackagePrice[];
  entitlement_grants: PackageEntitlementGrant[];
  created_at?: string;
  updated_at?: string | null;
};

export type PaymentTransaction = {
  id: string;
  customer_account_id: string;
  subscription_id?: string | null;
  package_price_id?: string | null;
  amount_minor: number;
  currency: "UGX";
  provider: string;
  provider_reference: string;
  provider_transaction_id?: string | null;
  status: "INITIATED" | "PENDING" | "SUCCESSFUL" | "FAILED" | "CANCELLED" | "REFUNDED";
  created_at: string;
  updated_at?: string | null;
};

export type CustomerSubscription = {
  id: string;
  customer_account_id: string;
  package_plan_id: string;
  package_price_id?: string | null;
  status: "INCOMPLETE" | "ACTIVE" | "PAST_DUE" | "CANCELLED" | "EXPIRED" | "FAILED";
  access_source: "PAID" | "MARKETING";
  currency: "UGX";
  amount_minor: number;
  billing_interval: "ONE_TIME" | "MONTHLY" | "YEARLY";
  current_period_start?: string | null;
  current_period_end?: string | null;
  cancel_at_period_end: boolean;
  cancelled_at?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  provider: string;
  package_name?: string | null;
  entitlement_summary: Array<Record<string, unknown>>;
  created_at: string;
  updated_at?: string | null;
};

export type BillingOverview = {
  subscriptions: CustomerSubscription[];
  payments: PaymentTransaction[];
};

export type CheckoutResponse = {
  transaction_id: string;
  subscription_id: string;
  customer_account_id: string;
  package_price_id: string;
  amount_minor: number;
  currency: "UGX";
  billing_interval: "ONE_TIME" | "MONTHLY" | "YEARLY";
  provider: string;
  provider_reference: string;
  checkout_url: string;
  status: string;
};
