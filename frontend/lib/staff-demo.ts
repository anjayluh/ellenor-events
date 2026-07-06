export const staffDashboard = {
  active_projects: 2,
  archived_projects: 0,
  rsvp_summary: { accepted: 18, tentative: 6, declined: 2 },
  risk_alerts: [
    { title: "Introduction - Amina & David", severity: "medium", message: "1 overdue task needs staff attention." },
    { title: "Wedding - Amina & David", severity: "high", message: "2 critical vendor category gaps detected." }
  ],
  project_health: [
    { title: "Wedding - Amina & David", risk_level: "high", pending_task_count: 4, overdue_task_count: 2, meeting_count: 3, budget_variance: 0.18 },
    { title: "Introduction - Amina & David", risk_level: "medium", pending_task_count: 2, overdue_task_count: 1, meeting_count: 2, budget_variance: 0.08 }
  ]
};
