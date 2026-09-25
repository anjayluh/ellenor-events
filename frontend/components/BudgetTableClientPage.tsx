"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { apiDelete, apiGet, apiPatch, apiPost } from "../lib/api";
import type { BudgetItemSummary, Project, ProjectBudgetItem, ProjectVendorOption } from "../lib/types";
import { useActiveProject } from "../lib/useActiveProject";
import { EventScopedHeader, EventWorkspaceGuard } from "./EventWorkspaceGuard";
import { StateBlock } from "./StateBlock";

type BudgetStatus = "PLANNED" | "QUOTED" | "COMMITTED" | "PARTIALLY_PAID" | "PAID" | "CANCELLED";
type BudgetForm = {
  name: string;
  category: string;
  description: string;
  vendor_id: string;
  planned_amount: string;
  committed_amount: string;
  paid_amount: string;
  currency: string;
  due_date: string;
  status: BudgetStatus;
  notes: string;
};
type BudgetFilters = { search: string; category: string; status: string; vendor_id: string; payment_filter: string; overdue: boolean };
type BudgetPayload = {
  name: string;
  category: string;
  description: string | null;
  vendor_id: string | null;
  planned_amount: string;
  committed_amount: string;
  paid_amount: string;
  currency: string;
  due_date: string | null;
  status: BudgetStatus;
  notes: string | null;
};

const emptyForm: BudgetForm = { name: "", category: "", description: "", vendor_id: "", planned_amount: "0", committed_amount: "0", paid_amount: "0", currency: "UGX", due_date: "", status: "PLANNED", notes: "" };
const emptyFilters: BudgetFilters = { search: "", category: "", status: "", vendor_id: "", payment_filter: "", overdue: false };
const budgetCategories = ["Venue", "Catering", "Decor", "Photography", "Videography", "Attire", "Makeup", "Hair", "Transport", "Cake", "Entertainment", "Invitations", "Gifts", "Ceremony", "Reception", "Planner / Coordinator", "Other"];
const budgetStatuses: Array<{ value: BudgetStatus; label: string; hint: string }> = [
  { value: "PLANNED", label: "Planned", hint: "A cost you are estimating before quotes or commitments." },
  { value: "QUOTED", label: "Quoted", hint: "A provider or supplier has given you a quoted amount." },
  { value: "COMMITTED", label: "Committed", hint: "You have agreed this amount but not paid yet." },
  { value: "PARTIALLY_PAID", label: "Partially paid", hint: "Some payment has been made and a balance remains." },
  { value: "PAID", label: "Paid", hint: "The committed amount has been fully cleared." },
  { value: "CANCELLED", label: "Cancelled", hint: "This cost is no longer active." }
];

function canEditBudget(project?: Project | null) {
  return Boolean(project?.role === "OWNER" || project?.role === "PARTNER" || project?.permissions?.includes("budget.edit"));
}

function numericValue(value: string | number | null | undefined) {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatMoney(value: string | number | null | undefined, currency = "UGX") {
  return new Intl.NumberFormat("en-UG", { style: "currency", currency, maximumFractionDigits: 0 }).format(numericValue(value));
}

function titleCase(value: string) {
  return value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function statusLabel(value: string) {
  return budgetStatuses.find((status) => status.value === value)?.label ?? titleCase(value);
}

function statusHint(value: string) {
  return budgetStatuses.find((status) => status.value === value)?.hint ?? "Budget stage imported for continuity.";
}

function buildQuery(filters: BudgetFilters) {
  const params = new URLSearchParams();
  if (filters.search.trim()) params.set("search", filters.search.trim());
  if (filters.category.trim()) params.set("category", filters.category.trim());
  if (filters.status.trim()) params.set("status", filters.status.trim());
  if (filters.vendor_id.trim()) params.set("vendor_id", filters.vendor_id.trim());
  if (filters.payment_filter.trim()) params.set("payment_filter", filters.payment_filter.trim());
  if (filters.overdue) params.set("overdue", "true");
  const query = params.toString();
  return query ? `?${query}` : "";
}

function normalizeApiMessage(error: unknown) {
  return error instanceof Error ? error.message : "We could not complete that request.";
}

function toPayload(form: BudgetForm): BudgetPayload {
  return {
    name: form.name.trim(),
    category: form.category.trim(),
    description: form.description.trim() || null,
    vendor_id: form.vendor_id || null,
    planned_amount: form.planned_amount.trim() || "0",
    committed_amount: form.committed_amount.trim() || "0",
    paid_amount: form.paid_amount.trim() || "0",
    currency: form.currency.trim().toUpperCase() || "UGX",
    due_date: form.due_date || null,
    status: form.status,
    notes: form.notes.trim() || null
  };
}

function formFromItem(item: ProjectBudgetItem): BudgetForm {
  return {
    name: item.name,
    category: item.category,
    description: item.description ?? "",
    vendor_id: item.vendor_id ?? "",
    planned_amount: String(item.planned_amount ?? "0"),
    committed_amount: String(item.committed_amount ?? "0"),
    paid_amount: String(item.paid_amount ?? "0"),
    currency: item.currency ?? "UGX",
    due_date: item.due_date ?? "",
    status: item.status as BudgetStatus,
    notes: item.notes ?? ""
  };
}

function validateForm(form: BudgetForm) {
  const planned = numericValue(form.planned_amount);
  const committed = numericValue(form.committed_amount);
  const paid = numericValue(form.paid_amount);
  if (planned < 0 || committed < 0 || paid < 0) return "Budget amounts cannot be negative.";
  if (paid > committed) return "Paid amount cannot exceed the committed amount.";
  if (form.status === "PAID" && committed !== paid) return "Paid items must have paid amount equal to committed amount.";
  if (form.status === "PARTIALLY_PAID" && !(paid > 0 && paid < committed)) return "Partially paid items need a payment below the committed amount.";
  if ((form.status === "PLANNED" || form.status === "QUOTED") && paid > 0) return "Planned or quoted items cannot have payments recorded yet.";
  return "";
}

export function BudgetTableClientPage() {
  const { projects, project, state, message, selectProject, reload } = useActiveProject();
  const [items, setItems] = useState<ProjectBudgetItem[]>([]);
  const [summary, setSummary] = useState<BudgetItemSummary | null>(null);
  const [vendors, setVendors] = useState<ProjectVendorOption[]>([]);
  const [form, setForm] = useState<BudgetForm>(emptyForm);
  const [filters, setFilters] = useState<BudgetFilters>(emptyFilters);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [notice, setNotice] = useState("Track planned costs, commitments, deposits, balances, and upcoming payment dates for this event.");
  const [processing, setProcessing] = useState<string | null>(null);

  const loadBudget = useCallback(async (activeProject: Project, nextFilters: BudgetFilters) => {
    const [nextItems, nextSummary, nextVendors] = await Promise.all([
      apiGet<ProjectBudgetItem[]>(`/projects/${activeProject.id}/budget/items${buildQuery(nextFilters)}`),
      apiGet<BudgetItemSummary>(`/projects/${activeProject.id}/budget/summary`),
      apiGet<ProjectVendorOption[]>(`/projects/${activeProject.id}/vendors`)
    ]);
    setItems(nextItems);
    setSummary(nextSummary);
    setVendors(nextVendors);
  }, []);

  useEffect(() => {
    if (!project) {
      setItems([]);
      setSummary(null);
      setVendors([]);
      return;
    }
    void loadBudget(project, filters).catch((error) => {
      setItems([]);
      setSummary(null);
      setNotice(normalizeApiMessage(error));
    });
  }, [project, filters, loadBudget]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const vendorId = params.get("vendor");
    if (vendorId) setForm((current) => ({ ...current, vendor_id: vendorId }));
  }, []);

  const canManage = canEditBudget(project);
  const categories = useMemo(() => [...new Set([...budgetCategories, ...items.map((item) => item.category).filter(Boolean)])], [items]);
  const amountError = validateForm(form);
  const nameError = form.name && form.name.trim().length < 2 ? "Budget item name must be at least 2 characters." : "";
  const categoryError = form.category && form.category.trim().length < 2 ? "Category must be at least 2 characters." : "";
  const canSubmit = Boolean(project && canManage && form.name.trim().length >= 2 && form.category.trim().length >= 2 && !nameError && !categoryError && !amountError && !processing);
  const committed = numericValue(form.committed_amount);
  const paid = numericValue(form.paid_amount);
  const outstanding = Math.max(committed - paid, 0);
  const paidProgress = summary?.paid_percentage ?? 0;
  const committedProgress = summary?.utilization_percentage ?? 0;

  async function saveItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !canSubmit) return;
    setProcessing(editingId ? `update-${editingId}` : "create");
    setNotice(editingId ? "Saving budget item..." : "Adding budget item...");
    try {
      if (editingId) await apiPatch<ProjectBudgetItem, BudgetPayload>(`/projects/${project.id}/budget/${editingId}`, toPayload(form));
      else await apiPost<ProjectBudgetItem, BudgetPayload>(`/projects/${project.id}/budget`, toPayload(form));
      setForm(emptyForm);
      setEditingId(null);
      setNotice(editingId ? "Budget item updated." : "Budget item added.");
      await loadBudget(project, filters);
    } catch (error) {
      setNotice(normalizeApiMessage(error));
    } finally {
      setProcessing(null);
    }
  }

  function startEdit(item: ProjectBudgetItem) {
    setEditingId(item.id);
    setForm(formFromItem(item));
  }

  async function deleteItem(itemId: string) {
    if (!project || processing || !window.confirm("Delete this budget item?")) return;
    setProcessing(`delete-${itemId}`);
    setNotice("Deleting budget item...");
    try {
      await apiDelete<{ status: string }>(`/projects/${project.id}/budget/${itemId}`);
      setNotice("Budget item deleted.");
      await loadBudget(project, filters);
    } catch (error) {
      setNotice(normalizeApiMessage(error));
    } finally {
      setProcessing(null);
    }
  }

  if (state !== "ready") return <EventWorkspaceGuard state={state} message={message} projects={projects} onSelect={selectProject} onCreated={() => void reload()} />;
  if (!project) return <StateBlock title="Choose an event" message="Open an event to manage its budget." />;

  return (
    <>
      <EventScopedHeader projects={projects} project={project} onSelect={selectProject} />
      <section className="grid fourColumns">
        <article className="metric"><span>Planned</span><strong>{formatMoney(summary?.total_planned ?? 0, summary?.currency)}</strong><p>{summary?.total_items ?? 0} budget item{summary?.total_items === 1 ? "" : "s"}</p></article>
        <article className="metric"><span>Committed</span><strong>{formatMoney(summary?.total_committed ?? 0, summary?.currency)}</strong><p>{committedProgress}% of planned budget committed</p></article>
        <article className="metric"><span>Paid</span><strong>{formatMoney(summary?.total_paid ?? 0, summary?.currency)}</strong><p>{paidProgress}% of committed costs cleared</p></article>
        <article className="metric"><span>Outstanding</span><strong>{formatMoney(summary?.total_outstanding ?? 0, summary?.currency)}</strong><p>{summary?.overdue_items ?? 0} overdue · {summary?.upcoming_payments_count ?? 0} upcoming</p></article>
      </section>

      <section className="grid twoColumns">
        <article className="panel resourceCard overviewPanel">
          <p className="eyebrow">Budget overview</p>
          <h2>Financial readiness</h2>
          {summary && summary.total_items > 0 ? (
            <div className="stack">
              <div>
                <p className="helperText">Paid progress</p>
                <div className="progressTrack" aria-label="Budget paid progress"><div className="progressFill" style={{ width: `${Math.min(paidProgress, 100)}%` }} /></div>
                <p>{formatMoney(summary.total_paid, summary.currency)} paid of {formatMoney(summary.total_committed, summary.currency)} committed.</p>
              </div>
              <div>
                <p className="helperText">Category breakdown</p>
                <div className="planningAreaList">
                  {summary.category_breakdown.map((category) => <span className="badge softBadge" key={category.category}>{category.category}: {formatMoney(category.committed_amount, summary.currency)}</span>)}
                </div>
              </div>
              {summary.upcoming_payments.length ? (
                <div className="attentionList">
                  {summary.upcoming_payments.map((payment) => (
                    <div className="attentionItem" key={payment.id}>
                      <strong>{payment.name}</strong>
                      <span>{formatMoney(payment.outstanding_amount, payment.currency)} due on {payment.due_date}</span>
                    </div>
                  ))}
                </div>
              ) : <p>No upcoming unpaid balances are visible yet.</p>}
            </div>
          ) : <p>Start adding venues, decor, catering, attire, and other planning costs to see progress and upcoming balances here.</p>}
        </article>

        <article className="panel actionPanel">
          <p className="eyebrow">Budget item</p>
          <h2>{editingId ? "Edit budget item" : "Add budget item"}</h2>
          {canManage ? (
            <form className="stack" onSubmit={saveItem}>
              <label className="formField">Item name<input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} placeholder="Reception catering" aria-invalid={Boolean(nameError)} />{nameError ? <span className="errorText">{nameError}</span> : <span className="helperText">Required. Use a name your planning team will recognize.</span>}</label>
              <div className="grid twoColumns compactGrid">
                <label className="formField">Category<input list="budget-categories" value={form.category} onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))} placeholder="Catering" aria-invalid={Boolean(categoryError)} />{categoryError ? <span className="errorText">{categoryError}</span> : null}</label>
                <label className="formField">Vendor<select value={form.vendor_id} onChange={(event) => setForm((current) => ({ ...current, vendor_id: event.target.value }))}><option value="">No vendor linked</option>{vendors.map((vendor) => <option key={vendor.id} value={vendor.id}>{vendor.name} · {vendor.category}</option>)}</select></label>
              </div>
              <datalist id="budget-categories">{categories.map((category) => <option key={category} value={category} />)}</datalist>
              <label className="formField">Description<textarea value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} placeholder="What is included in this cost?" /></label>
              <div className="grid twoColumns compactGrid">
                <label className="formField">Planned amount<input inputMode="decimal" value={form.planned_amount} onChange={(event) => setForm((current) => ({ ...current, planned_amount: event.target.value }))} /></label>
                <label className="formField">Committed amount<input inputMode="decimal" value={form.committed_amount} onChange={(event) => setForm((current) => ({ ...current, committed_amount: event.target.value }))} /></label>
              </div>
              <div className="grid twoColumns compactGrid">
                <label className="formField">Paid amount<input inputMode="decimal" value={form.paid_amount} onChange={(event) => setForm((current) => ({ ...current, paid_amount: event.target.value }))} aria-invalid={Boolean(amountError)} /><span className="helperText">Outstanding: {formatMoney(outstanding, form.currency)}</span>{amountError ? <span className="errorText">{amountError}</span> : null}</label>
                <label className="formField">Due date<input type="date" value={form.due_date} onChange={(event) => setForm((current) => ({ ...current, due_date: event.target.value }))} /></label>
              </div>
              <label className="formField">Status<select value={form.status} onChange={(event) => setForm((current) => ({ ...current, status: event.target.value as BudgetStatus }))}>{budgetStatuses.map((status) => <option key={status.value} value={status.value}>{status.label}</option>)}</select><span className="helperText">{statusHint(form.status)}</span></label>
              <label className="formField">Notes<textarea value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} placeholder="Payment details, committee notes, or follow-up reminders." /></label>
              <div className="buttonRow">
                <button className="primaryButton" data-icon="✓" disabled={!canSubmit} type="submit">{processing?.startsWith("update") ? "Saving..." : editingId ? "Save changes" : "Add item"}</button>
                {editingId ? <button className="ghostButton" data-icon="×" disabled={Boolean(processing)} type="button" onClick={() => { setEditingId(null); setForm(emptyForm); }}>Cancel</button> : null}
              </div>
            </form>
          ) : <p>You can view this budget, but editing is not enabled for your event role.</p>}
          <p>{notice}</p>
        </article>
      </section>

      <section className="panel tablePanel">
        <div className="sectionHeaderRow">
          <div><p className="eyebrow">Budget register</p><h2>{project.title} financial tracker</h2></div>
          <div className="buttonRow"><button className="ghostButton" data-icon="↺" type="button" onClick={() => setFilters(emptyFilters)}>Clear filters</button></div>
        </div>
        <div className="filterGrid">
          <label className="formField">Search<input value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} placeholder="Search item, category, notes" /></label>
          <label className="formField">Category<select value={filters.category} onChange={(event) => setFilters((current) => ({ ...current, category: event.target.value }))}><option value="">All categories</option>{categories.map((category) => <option key={category} value={category}>{category}</option>)}</select></label>
          <label className="formField">Status<select value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}><option value="">All statuses</option>{budgetStatuses.map((status) => <option key={status.value} value={status.value}>{status.label}</option>)}</select></label>
          <label className="formField">Payment<select value={filters.payment_filter} onChange={(event) => setFilters((current) => ({ ...current, payment_filter: event.target.value }))}><option value="">All payments</option><option value="paid">Paid</option><option value="unpaid">Unpaid balance</option></select></label>
          <label className="formField">Vendor<select value={filters.vendor_id} onChange={(event) => setFilters((current) => ({ ...current, vendor_id: event.target.value }))}><option value="">All vendors</option>{vendors.map((vendor) => <option key={vendor.id} value={vendor.id}>{vendor.name}</option>)}</select></label>
          <label className="formField checkboxField"><input checked={filters.overdue} onChange={(event) => setFilters((current) => ({ ...current, overdue: event.target.checked }))} type="checkbox" /> Overdue only</label>
        </div>
        <div className="tableScroller">
          <table className="dataTable">
            <thead><tr><th>Item</th><th>Vendor</th><th>Status</th><th>Planned</th><th>Committed</th><th>Paid</th><th>Outstanding</th><th>Due</th><th>Actions</th></tr></thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td><strong>{item.name}</strong><small>{item.category}{item.description ? ` · ${item.description}` : ""}</small></td>
                  <td>{item.vendor_name ?? "Not linked"}</td>
                  <td><span className={item.status === "PAID" ? "badge successBadge" : item.is_overdue ? "badge warningBadge" : "badge softBadge"}>{statusLabel(item.status)}</span></td>
                  <td>{formatMoney(item.planned_amount, item.currency)}</td>
                  <td>{formatMoney(item.committed_amount, item.currency)}</td>
                  <td>{formatMoney(item.paid_amount, item.currency)}</td>
                  <td>{formatMoney(item.outstanding_amount, item.currency)}</td>
                  <td>{item.due_date ?? "Not set"}</td>
                  <td><div className="buttonRow tableActions"><button className="ghostButton" data-icon="✎" disabled={!canManage || Boolean(processing)} type="button" onClick={() => startEdit(item)}>Edit</button><button className="ghostButton danger" data-icon="−" disabled={!canManage || Boolean(processing)} type="button" onClick={() => void deleteItem(item.id)}>{processing === `delete-${item.id}` ? "Deleting..." : "Delete"}</button></div></td>
                </tr>
              ))}
              {!items.length ? <tr><td colSpan={9}>No budget items yet. Add venue, catering, decor, attire, transport, and other event costs to begin tracking payment readiness.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
