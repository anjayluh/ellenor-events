"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { apiDelete, apiGet, apiPatch, apiPost } from "../lib/api";
import type { Project } from "../lib/types";
import { useActiveProject } from "../lib/useActiveProject";
import { EventScopedHeader, EventWorkspaceGuard } from "./EventWorkspaceGuard";
import { StateBlock } from "./StateBlock";

type Usage = { key: string; label: string; used: number; limit?: number | null; remaining?: number | null };
type VendorStatus = "shortlisted" | "contacted" | "confirmed" | "declined" | "cancelled" | "quote_requested" | "preferred" | "booked" | "rejected" | "completed";
type PaymentStatus = "not_applicable" | "unpaid" | "partially_paid" | "paid";
type Vendor = {
  id: string;
  project_id: string;
  name: string;
  category: string;
  contact?: string | null;
  contact_name?: string | null;
  phone?: string | null;
  email?: string | null;
  status: VendorStatus;
  notes?: string | null;
  external_url?: string | null;
  agreed_amount: string | number;
  amount_paid: string | number;
  balance_amount: string | number;
  payment_status: PaymentStatus;
  created_at?: string | null;
  updated_at?: string | null;
};
type VendorSummary = {
  total: number;
  confirmed: number;
  needs_attention: number;
  outstanding_balance: string | number;
  vendor_usage: Usage;
};
type VendorForm = {
  name: string;
  category: string;
  contact_name: string;
  phone: string;
  email: string;
  contact: string;
  status: VendorStatus;
  agreed_amount: string;
  amount_paid: string;
  notes: string;
};
type VendorFilters = { search: string; category: string; status: string; payment_status: string };
type VendorPayload = {
  name: string;
  category: string;
  contact_name: string | null;
  phone: string | null;
  email: string | null;
  contact: string | null;
  status: VendorStatus;
  agreed_amount: string;
  amount_paid: string;
  notes: string | null;
};

const emptyForm: VendorForm = { name: "", category: "", contact_name: "", phone: "", email: "", contact: "", status: "shortlisted", agreed_amount: "0", amount_paid: "0", notes: "" };
const emptyFilters: VendorFilters = { search: "", category: "", status: "", payment_status: "" };
const vendorCategories = ["Decor", "Photography", "Videography", "Catering", "Venue", "MC", "PA / Sound", "Makeup", "Hair", "Transport", "Cake", "Planner / Coordinator", "Florist", "Entertainment", "Security", "Other"];
const vendorStatuses: Array<{ value: VendorStatus; label: string; description: string }> = [
  { value: "shortlisted", label: "Shortlisted", description: "A possible provider you are still considering." },
  { value: "contacted", label: "Contacted", description: "You have reached out and are waiting for next steps." },
  { value: "confirmed", label: "Confirmed", description: "This provider is selected for the event." },
  { value: "declined", label: "Declined", description: "The provider is not moving forward." },
  { value: "cancelled", label: "Cancelled", description: "The engagement was cancelled." }
];
const legacyStatusLabels: Record<string, string> = { quote_requested: "Waiting for quote", preferred: "Preferred", booked: "Booked", rejected: "Rejected", completed: "Completed" };
const paymentLabels: Record<PaymentStatus, string> = { not_applicable: "Not applicable", unpaid: "Unpaid", partially_paid: "Partially paid", paid: "Paid" };

function canManageVendors(project?: Project | null) {
  return Boolean(project?.role === "OWNER" || project?.role === "PARTNER" || project?.role === "COMMITTEE_CHAIR" || project?.permissions?.includes("vendors.manage"));
}

function usageText(usage?: Usage | null) {
  if (!usage) return "Not available";
  if (usage.limit == null) return `${usage.used} used`;
  return `${usage.used} / ${usage.limit}`;
}

function moneyValue(value: string | number | null | undefined) {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatMoney(value: string | number | null | undefined) {
  return new Intl.NumberFormat("en-UG", { style: "currency", currency: "UGX", maximumFractionDigits: 0 }).format(moneyValue(value));
}

function statusLabel(value: string) {
  return vendorStatuses.find((status) => status.value === value)?.label ?? legacyStatusLabels[value] ?? value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function statusDescription(value: string) {
  return vendorStatuses.find((status) => status.value === value)?.description ?? "Imported vendor stage kept for continuity.";
}

function buildQuery(filters: VendorFilters) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value.trim()) params.set(key, value.trim());
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

function normalizeApiMessage(error: unknown) {
  return error instanceof Error ? error.message : "We could not complete that request.";
}

function toPayload(form: VendorForm): VendorPayload {
  return {
    name: form.name.trim(),
    category: form.category.trim(),
    contact_name: form.contact_name.trim() || null,
    phone: form.phone.trim() || null,
    email: form.email.trim().toLowerCase() || null,
    contact: form.contact.trim() || null,
    status: form.status,
    agreed_amount: form.agreed_amount.trim() || "0",
    amount_paid: form.amount_paid.trim() || "0",
    notes: form.notes.trim() || null
  };
}

function formFromVendor(vendor: Vendor): VendorForm {
  return {
    name: vendor.name,
    category: vendor.category,
    contact_name: vendor.contact_name ?? "",
    phone: vendor.phone ?? "",
    email: vendor.email ?? "",
    contact: vendor.contact ?? "",
    status: vendor.status,
    agreed_amount: String(vendor.agreed_amount ?? "0"),
    amount_paid: String(vendor.amount_paid ?? "0"),
    notes: vendor.notes ?? ""
  };
}

export function VendorsClientPage() {
  const { projects, project, state, message, selectProject, reload } = useActiveProject();
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [summary, setSummary] = useState<VendorSummary | null>(null);
  const [form, setForm] = useState<VendorForm>(emptyForm);
  const [editForm, setEditForm] = useState<VendorForm>(emptyForm);
  const [filters, setFilters] = useState<VendorFilters>(emptyFilters);
  const [editingVendorId, setEditingVendorId] = useState<string | null>(null);
  const [notice, setNotice] = useState("Track vendors, contacts, engagement decisions, deposits, and balances for this event.");
  const [processing, setProcessing] = useState<string | null>(null);

  const loadVendors = useCallback(async (activeProject: Project, nextFilters: VendorFilters) => {
    const [nextVendors, nextSummary] = await Promise.all([
      apiGet<Vendor[]>(`/projects/${activeProject.id}/vendors${buildQuery(nextFilters)}`),
      apiGet<VendorSummary>(`/projects/${activeProject.id}/vendors/summary`)
    ]);
    setVendors(nextVendors);
    setSummary(nextSummary);
  }, []);

  useEffect(() => {
    if (!project) {
      setVendors([]);
      setSummary(null);
      return;
    }
    void loadVendors(project, filters).catch((error) => {
      setVendors([]);
      setSummary(null);
      setNotice(normalizeApiMessage(error));
    });
  }, [project, filters, loadVendors]);

  const categories = useMemo(() => [...new Set([...vendorCategories, ...vendors.map((vendor) => vendor.category).filter(Boolean)])], [vendors]);
  const nameError = form.name && form.name.trim().length < 2 ? "Vendor name must be at least 2 characters." : "";
  const categoryError = form.category && form.category.trim().length < 2 ? "Category must be at least 2 characters." : "";
  const emailError = form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email) ? "Enter a valid email address." : "";
  const amountError = moneyValue(form.amount_paid) > moneyValue(form.agreed_amount) ? "Amount paid cannot exceed the agreed amount." : "";
  const canSubmit = Boolean(project && canManageVendors(project) && form.name.trim().length >= 2 && form.category.trim().length >= 2 && !nameError && !categoryError && !emailError && !amountError && !processing);

  async function createVendor(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !canSubmit) return;
    setProcessing("create");
    setNotice("Adding vendor...");
    try {
      await apiPost<Vendor, VendorPayload>(`/projects/${project.id}/vendors`, toPayload(form));
      setForm(emptyForm);
      setNotice("Vendor added. Keep engagement and payment details updated as decisions progress.");
      await loadVendors(project, filters);
    } catch (error) {
      setNotice(normalizeApiMessage(error));
    } finally {
      setProcessing(null);
    }
  }

  function startEdit(vendor: Vendor) {
    setEditingVendorId(vendor.id);
    setEditForm(formFromVendor(vendor));
  }

  async function updateVendor(vendorId: string) {
    if (!project || processing) return;
    setProcessing(`update-${vendorId}`);
    setNotice("Saving vendor changes...");
    try {
      await apiPatch<Vendor, VendorPayload>(`/projects/${project.id}/vendors/${vendorId}`, toPayload(editForm));
      setEditingVendorId(null);
      setNotice("Vendor updated.");
      await loadVendors(project, filters);
    } catch (error) {
      setNotice(normalizeApiMessage(error));
    } finally {
      setProcessing(null);
    }
  }

  async function deleteVendor(vendorId: string) {
    if (!project || processing || !window.confirm("Remove this vendor from the event?")) return;
    setProcessing(`delete-${vendorId}`);
    setNotice("Removing vendor...");
    try {
      await apiDelete<{ status: string }>(`/projects/${project.id}/vendors/${vendorId}`);
      setNotice("Vendor removed.");
      await loadVendors(project, filters);
    } catch (error) {
      setNotice(normalizeApiMessage(error));
    } finally {
      setProcessing(null);
    }
  }

  if (state !== "ready") return <EventWorkspaceGuard state={state} message={message} projects={projects} onSelect={selectProject} onCreated={() => void reload()} />;
  const canManage = canManageVendors(project);

  return (
    <>
      <EventScopedHeader projects={projects} project={project} onSelect={selectProject} />
      <section className="grid fourColumns">
        <article className="metric"><span>Total vendors</span><strong>{summary?.total ?? 0}</strong><p>{usageText(summary?.vendor_usage)} vendors</p></article>
        <article className="metric"><span>Confirmed</span><strong>{summary?.confirmed ?? 0}</strong><p>{summary?.needs_attention ?? 0} still need a decision</p></article>
        <article className="metric"><span>Needs attention</span><strong>{summary?.needs_attention ?? 0}</strong><p>Vendors not yet confirmed</p></article>
        <article className="metric"><span>Outstanding balance</span><strong>{formatMoney(summary?.outstanding_balance ?? 0)}</strong><p>Across current vendor records</p></article>
      </section>

      <section className="grid twoColumns">
        <article className="panel actionPanel">
          <p className="eyebrow">Vendor directory</p>
          <h2>Add vendor</h2>
          {canManage ? (
            <form className="stack" onSubmit={createVendor}>
              <label className="formField">Business or vendor name<input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} placeholder="Pearl Gardens Catering" aria-invalid={Boolean(nameError)} />{nameError ? <span className="errorText">{nameError}</span> : <span className="helperText">Use the name your family or committee will recognize.</span>}</label>
              <label className="formField">Service category<input list="vendor-categories" value={form.category} onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))} placeholder="Catering, Decor, Photography" aria-invalid={Boolean(categoryError)} />{categoryError ? <span className="errorText">{categoryError}</span> : null}</label>
              <datalist id="vendor-categories">{categories.map((category) => <option value={category} key={category} />)}</datalist>
              <div className="grid twoColumns compactGrid">
                <label className="formField">Contact person<input value={form.contact_name} onChange={(event) => setForm((current) => ({ ...current, contact_name: event.target.value }))} placeholder="Amina" /></label>
                <label className="formField">Phone<input value={form.phone} onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))} placeholder="+256..." /></label>
              </div>
              <label className="formField">Email<input value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} placeholder="vendor@example.com" aria-invalid={Boolean(emailError)} />{emailError ? <span className="errorText">{emailError}</span> : null}</label>
              <label className="formField">Engagement status<select value={form.status} onChange={(event) => setForm((current) => ({ ...current, status: event.target.value as VendorStatus }))}>{vendorStatuses.map((status) => <option value={status.value} key={status.value}>{status.label}</option>)}</select><span className="helperText">{statusDescription(form.status)}</span></label>
              <div className="grid twoColumns compactGrid">
                <label className="formField">Agreed amount<input inputMode="decimal" value={form.agreed_amount} onChange={(event) => setForm((current) => ({ ...current, agreed_amount: event.target.value }))} /></label>
                <label className="formField">Amount paid<input inputMode="decimal" value={form.amount_paid} onChange={(event) => setForm((current) => ({ ...current, amount_paid: event.target.value }))} aria-invalid={Boolean(amountError)} />{amountError ? <span className="errorText">{amountError}</span> : null}</label>
              </div>
              <label className="formField">Notes<input value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} placeholder="Deposit terms, quote notes, next call..." /></label>
              <button className="primaryButton" data-icon="+" disabled={!canSubmit} type="submit">{processing === "create" ? "Adding..." : "Add vendor"}</button>
            </form>
          ) : <p>You can view vendors for this event, but vendor management is limited to event owners and authorized coordinators.</p>}
          <p>{notice}</p>
        </article>

        <article className="panel resourceCard">
          <p className="eyebrow">Search and filters</p>
          <h2>Find the right provider quickly</h2>
          <div className="stack">
            <label className="formField">Search<input value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} placeholder="Business, contact, email, phone" /></label>
            <div className="grid twoColumns compactGrid">
              <label className="formField">Category<select value={filters.category} onChange={(event) => setFilters((current) => ({ ...current, category: event.target.value }))}><option value="">All categories</option>{categories.map((category) => <option value={category} key={category}>{category}</option>)}</select></label>
              <label className="formField">Status<select value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}><option value="">All statuses</option>{vendorStatuses.map((status) => <option value={status.value} key={status.value}>{status.label}</option>)}</select></label>
            </div>
            <label className="formField">Payment status<select value={filters.payment_status} onChange={(event) => setFilters((current) => ({ ...current, payment_status: event.target.value }))}><option value="">All payment states</option>{Object.entries(paymentLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
            <button className="ghostButton" data-icon="×" type="button" onClick={() => setFilters(emptyFilters)}>Clear filters</button>
          </div>
        </article>
      </section>

      <section className="panel tablePanel">
        <div className="sectionHeader"><div><p className="eyebrow">Event vendors</p><h2>Providers and payment readiness</h2></div><span className="badge softBadge">{vendors.length} shown</span></div>
        {vendors.length ? (
          <div className="tableScroller">
            <table className="dataTable">
              <thead><tr><th>Vendor</th><th>Contact</th><th>Status</th><th>Financials</th><th>Actions</th></tr></thead>
              <tbody>
                {vendors.map((vendor) => (
                  <tr key={vendor.id}>
                    <td>{editingVendorId === vendor.id ? <div className="stack"><input value={editForm.name} onChange={(event) => setEditForm((current) => ({ ...current, name: event.target.value }))} /><input list="vendor-categories" value={editForm.category} onChange={(event) => setEditForm((current) => ({ ...current, category: event.target.value }))} /></div> : <><strong>{vendor.name}</strong><small>{vendor.category}</small>{vendor.notes ? <small>{vendor.notes}</small> : null}</>}</td>
                    <td>{editingVendorId === vendor.id ? <div className="stack"><input value={editForm.contact_name} onChange={(event) => setEditForm((current) => ({ ...current, contact_name: event.target.value }))} placeholder="Contact person" /><input value={editForm.phone} onChange={(event) => setEditForm((current) => ({ ...current, phone: event.target.value }))} placeholder="Phone" /><input value={editForm.email} onChange={(event) => setEditForm((current) => ({ ...current, email: event.target.value }))} placeholder="Email" /></div> : <>{vendor.contact_name ?? vendor.contact ?? "Contact not set"}<small>{vendor.phone ?? "No phone"} · {vendor.email ?? "No email"}</small></>}</td>
                    <td>{editingVendorId === vendor.id ? <select value={editForm.status} onChange={(event) => setEditForm((current) => ({ ...current, status: event.target.value as VendorStatus }))}>{vendorStatuses.map((status) => <option value={status.value} key={status.value}>{status.label}</option>)}</select> : <><span className="badge softBadge">{statusLabel(vendor.status)}</span><small>{statusDescription(vendor.status)}</small></>}</td>
                    <td>{editingVendorId === vendor.id ? <div className="stack"><input inputMode="decimal" value={editForm.agreed_amount} onChange={(event) => setEditForm((current) => ({ ...current, agreed_amount: event.target.value }))} /><input inputMode="decimal" value={editForm.amount_paid} onChange={(event) => setEditForm((current) => ({ ...current, amount_paid: event.target.value }))} /></div> : <><strong>{formatMoney(vendor.balance_amount)} balance</strong><small>{formatMoney(vendor.amount_paid)} paid of {formatMoney(vendor.agreed_amount)}</small><small>{paymentLabels[vendor.payment_status]}</small></>}</td>
                    <td>{canManage ? <div className="buttonRow tableActions">{editingVendorId === vendor.id ? <><button className="primaryButton" data-icon="✓" disabled={Boolean(processing)} type="button" onClick={() => void updateVendor(vendor.id)}>{processing === `update-${vendor.id}` ? "Saving..." : "Save"}</button><button className="ghostButton" data-icon="×" disabled={Boolean(processing)} type="button" onClick={() => setEditingVendorId(null)}>Cancel</button></> : <><Link className="ghostButton" data-icon="₵" href={`/budget?project=${project?.id}&vendor=${vendor.id}`}>Add to budget</Link><button className="ghostButton" data-icon="✎" disabled={Boolean(processing)} type="button" onClick={() => startEdit(vendor)}>Edit</button><button className="ghostButton danger" data-icon="−" disabled={Boolean(processing)} type="button" onClick={() => void deleteVendor(vendor.id)}>{processing === `delete-${vendor.id}` ? "Removing..." : "Delete"}</button></>}</div> : <span className="helperText">View only</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <StateBlock title="No vendors added yet" message={canManage ? "Add venues, decorators, caterers, photographers, and other providers as decisions take shape." : "Vendor records will appear here once the event team adds them."} />}
      </section>
    </>
  );
}
