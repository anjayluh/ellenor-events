import type { BudgetResponse, Project } from "./types";

export const demoProjects: Project[] = [
  {
    id: "10000000-0000-0000-0000-000000000002",
    title: "Wedding - Amina & David",
    type: "wedding",
    event_date: "2026-09-12",
    owner_user_id: "00000000-0000-0000-0000-000000000101",
    partner_user_id: "00000000-0000-0000-0000-000000000102",
    status: "active",
    role: "OWNER",
    budget_visibility_mode: "FULL_ACCESS"
  },
  {
    id: "10000000-0000-0000-0000-000000000001",
    title: "Introduction - Amina & David",
    type: "introduction",
    event_date: "2026-08-15",
    owner_user_id: "00000000-0000-0000-0000-000000000101",
    partner_user_id: "00000000-0000-0000-0000-000000000102",
    status: "active",
    role: "COMMITTEE_CHAIR",
    budget_visibility_mode: "SUMMARY_ACCESS"
  }
];

export const demoBudgetByVisibility: Record<string, BudgetResponse> = {
  FULL_ACCESS: {
    visibility: "FULL_ACCESS",
    total: 42000000,
    spent: 7500000,
    remaining: 34500000,
    contribution_progress: 4500000,
    pledged_total: 12000000
  },
  SUMMARY_ACCESS: {
    visibility: "SUMMARY_ACCESS",
    total: 18000000,
    contribution_progress: 3000000,
    pledged_total: 5000000
  },
  CONTRIBUTION_ONLY: {
    visibility: "CONTRIBUTION_ONLY",
    contribution_progress: 3000000
  },
  NO_ACCESS: {
    visibility: "NO_ACCESS"
  }
};
