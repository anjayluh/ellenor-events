"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { apiDelete, apiGet, apiPatch, apiPost } from "../lib/api";
import type { Project } from "../lib/types";
import { useActiveProject } from "../lib/useActiveProject";
import { EventScopedHeader, EventWorkspaceGuard } from "./EventWorkspaceGuard";
import { StateBlock } from "./StateBlock";

type Usage = { key: string; label: string; used: number; limit?: number | null; remaining?: number | null };
type VendorStatus = "PROSPECT" | "SHORTLISTED" | "CONTACTED" | "QUOTED" | "BOOKED" | "CONFIRMED" | "COMPLETED" | "CANCELLED";
type VendorFinancialSummary = {
  planned_total: string | number;
  committed_total: string | number;
  actual_total: string | number;
  paid_total: string | number;
  outstanding_total: string | number;
  variance_amount: string | number;
  payment_percentage: number;
  linked_budget_items_count: number;
};
type VendorBudgetItem = {
  id: string;
  name: string;
  category: string;
  planned_amount: string | number;
  committed_amount: string | number;
  actual_amount: string | number;
  paid_amount: string | number;
  outstanding_amount: string | number;
  currency: string;
  status: string;
  due_date?: string | null;
};
type Vendor = {
  id: string;
  project_id: string;
  name: string;
  category: string;
  contact_person?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  website?: string | null;
  service_description?: string | null;
  status: VendorStatus;
  notes?: string | null;
  event_day_contact?: string | null;
  booking_date?: string | null;
  financial_summary: VendorFinancialSummary;
  budget_items: VendorBudgetItem[];
  created_at?: string | null;
  updated_at?: string | null;
};
type VendorSummary = {
  total: number;
  confirmed: number;
  booked: number;
  needs_attention: number;
  with_outstanding_balance: number;
  outstanding_balance: string | number;
  planned_total: string | number;
  committed_total: string | number;
  actual_total: string | number;
  paid_total: string | number;
  variance_amount: string | number;
  vendor_usage: Usage;
};
type VendorForm = {
  name: string;
  category: string;
  contact_person: string;
  phone: string;
  email: string;
  address: string;
  website: string;
  service_description: string;
  status: VendorStatus;
  event_day_contact: string;
  booking_date: string;
  notes: string;
};
type VendorFilters = { search: string; category: string; status: string; outstanding: boolean };
type VendorPayload = {
  name: string;
  category: string;
  contact_person: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  website: string | null;
  service_description: string | null;
  status: VendorStatus;
  event_day_contact: string | null;
  booking_date: string | null;
  notes: string | null;
};

const emptyForm: VendorForm = { name: "", category: "DECOR", contact_person: "", phone: "", email: "", address: "", website: "", service_description: "", status: "SHORTLISTED", event_day_contact: "", booking_date: "", notes: "" };
const emptyFilters: VendorFilters = { search: "", category: "", status: "", outstanding: false };
const vendorCategories: Array<{ value: string; label: string }> = [
  { value: "VENUE", label: "Venue" },
  { value: "CATERING", label: "Catering" },
  { value: "DECOR", label: "Decor" },
  { value: "PHOTOGRAPHY", label: "Photography" },
  { value: "VIDEOGRAPHY", label: "Videography" },
  { value: "MC", label: "MC" },
  { value: "DJ_ENTERTAINMENT", label: "DJ / Entertainment" },
  { value: "PA_SOUND", label: "PA / Sound" },
  { value: "MAKEUP_BEAUTY", label: "Makeup / Beauty" },
  { value: "TRANSPORT", label: "Transport" },
  { value: "CAKE", label: "Cake" },
  { value: "ATTIRE", label: "Attire" },
  { value: "FLORIST", label: "Florist" },
  { value: "STATIONERY", label: "Stationery" },
  { value: "ACCOMMODATION", label: "Accommodation" },
  { value: "SECURITY", label: "Security" },
  { value: "OTHER", label: "Other" }
];
const vendorStatuses: Array<{ value: VendorStatus; label: string; description: string }> = [
  { value: "PROSPECT", label: "Prospect", description: "A provider you may consider." },
  { value: "SHORTLISTED", label: "Shortlisted", description: "A possible provider still being evaluated." },
  { value: "CONTACTED", label: "Contacted", description: "You have reached out and are waiting for next steps." },
  { value: "QUOTED", label: "Quoted", description: "A price or proposal has been received." },
  { value: "BOOKED", label: "Booked", description: "The provider is booked for the event." },
  { value: "CONFIRMED", label: "Confirmed", description: "The provider is confirmed and ready." },
  { value: "COMPLETED", label: "Completed", description: "The service has been completed." },
  { value: "CANCELLED", label: "Cancelled", description: "This vendor is no longer active for the event." }
];

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

function categoryLabel(value: string) {
  return vendorCategories.find((category) => category.value === value)?.label ?? value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function statusLabel(value: string) {
  return vendorStatuses.find((status) => status.value === value)?.label ?? value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function statusDescription(value: string) {
  return vendorStatuses.find((status) => status.value === value)?.description ?? "Vendor stage kept for continuity.";
}

function buildQuery(filters: VendorFilters) {
  const params = new URLSearchParams();
  if (filters.search.trim()) params.set("search", filters.search.trim());
  if (filters.category.trim()) params.set("category", filters.category.trim());
  if (filters.status.trim()) params.set("status", filters.status.trim());
  if (filters.outstanding) params.set("outstanding", "true");
  const query = params.toString();
  return query ? `?${query}` : "";
}

function normalizeApiMessage(error: unknown) {
  return error instanceof Error ? error.message : "We could not complete that request.";
}

function toPayload(form: VendorForm): VendorPayload {
  return {
    name: form.name.trim(),
    category: form.category,
    contact_person: form.contact_person.trim() || null,
    phone: form.phone.trim() || null,
    email: form.email.trim().toLowerCase() || null,
    address: form.address.trim() || null,
    website: form.website.trim() || null,
    service_description: form.service_description.trim() || null,
    status: form.status,
    event_day_contact: form.event_day_contact.trim() || null,
    booking_date: form.booking_date || null,
    notes: form.notes.trim() || null
  };
}

function formFromVendor(vendor: Vendor): VendorForm {
  return {
    name: vendor.name,
    category: vendor.category,
    contact_person: vendor.contact_person ?? "",
    phone: vendor.phone ?? "",
    email: vendor.email ?? "",
    address: vendor.address ?? "",
    website: vendor.website ?? "",
    service_description: vendor.service_description ?? "",
    status: vendor.status,
    event_day_contact: vendor.event_day_contact ?? "",
    booking_date: vendor.booking_date ?? "",
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
  const [expandedVendorId, setExpandedVendorId] = useState<string | null>(null);
  const [vendorDetails, setVendorDetails] = useState<Record<string, Vendor>>({});
  const [notice, setNotice] = useState("Track providers, contact details, booking status, and budget-linked balances for this event.");
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

  const categoryOptions = useMemo(() => {
    const existing = vendors.map((vendor) => ({ value: vendor.category, label: categoryLabel(vendor.category) }));
    const merged = new Map<string, string>();
    [...vendorCategories, ...existing].forEach((category) => merged.set(category.value, category.label));
    return Array.from(merged, ([value, label]) => ({ value, label }));
  }, [vendors]);
  const nameError = form.name && form.name.trim().length < 2 ? "Vendor name must be at least 2 characters." : "";
  const emailError = form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email) ? "Enter a valid email address." : "";
  const canSubmit = Boolean(project && canManageVendors(project) && form.name.trim().length >= 2 && !nameError && !emailError && !processing);
  const canManage = canManageVendors(project);

  async function createVendor(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !canSubmit) return;
    setProcessing("create");
    setNotice("Adding vendor...");
    try {
      await apiPost<Vendor, VendorPayload>(`/projects/${project.id}/vendors`, toPayload(form));
      setForm(emptyForm);
      setNotice("Vendor added. Link budget items to this vendor to track financial readiness.");
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
      const updated = await apiPatch<Vendor, VendorPayload>(`/projects/${project.id}/vendors/${vendorId}`, toPayload(editForm));
      setEditingVendorId(null);
      setVendorDetails((current) => ({ ...current, [vendorId]: updated }));
      setNotice("Vendor updated.");
      await loadVendors(project, filters);
    } catch (error) {
      setNotice(normalizeApiMessage(error));
    } finally {
      setProcessing(null);
    }
  }

  async function toggleDetails(vendorId: string) {
    if (!project) return;
    if (expandedVendorId === vendorId) {
      setExpandedVendorId(null);
      return;
    }
    setExpandedVendorId(vendorId);
    if (vendorDetails[vendorId]) return;
    setProcessing(`detail-${vendorId}`);
    try {
      const detail = await apiGet<Vendor>(`/projects/${project.id}/vendors/${vendorId}`);
      setVendorDetails((current) => ({ ...current, [vendorId]: detail }));
    } catch (error) {
      setNotice(normalizeApiMessage(error));
    } finally {
      setProcessing(null);
    }
  }

  async function deleteVendor(vendorId: string) {
    if (!project || processing || !window.confirm("Remove this vendor from the event? Vendors linked to budget items must be unlinked first.")) return;
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

  return (
    <>
      <EventScopedHeader projects={projects} project={project} onSelect={selectProject} />
      <section className="grid fourColumns">
        <article className="metric"><span>Total vendors</span><strong>{summary?.total ?? 0}</strong><p>{usageText(summary?.vendor_usage)} vendors</p></article>
        <article className="metric"><span>Confirmed</span><strong>{summary?.confirmed ?? 0}</strong><p>{summary?.needs_attention ?? 0} still need a decision</p></article>
        <article className="metric"><span>Booked / ready</span><strong>{summary?.booked ?? 0}</strong><p>Booked, confirmed, or completed</p></article>
        <article className="metric"><span>Outstanding</span><strong>{formatMoney(summary?.outstanding_balance ?? 0)}</strong><p>{summary?.with_outstanding_balance ?? 0} vendor{summary?.with_outstanding_balance === 1 ? "" : "s"} with balances</p></article>
      </section>

      <section className="grid twoColumns">
        <article className="panel actionPanel">
          <p className="eyebrow">Vendor directory</p>
          <h2>Add vendor</h2>
          {canManage ? (
            <form className="stack" onSubmit={createVendor}>
              <label className="formField">Business or vendor name<input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} placeholder="Pearl Gardens Catering" aria-invalid={Boolean(nameError)} />{nameError ? <span className="errorText">{nameError}</span> : <span className="helperText">Use the name your family or committee will recognize.</span>}</label>
              <div className="grid twoColumns compactGrid">
                <label className="formField">Service category<select value={form.category} onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))}>{vendorCategories.map((category) => <option value={category.value} key={category.value}>{category.label}</option>)}</select></label>
                <label className="formField">Engagement status<select value={form.status} onChange={(event) => setForm((current) => ({ ...current, status: event.target.value as VendorStatus }))}>{vendorStatuses.map((status) => <option value={status.value} key={status.value}>{status.label}</option>)}</select><span className="helperText">{statusDescription(form.status)}</span></label>
              </div>
              <div className="grid twoColumns compactGrid">
                <label className="formField">Contact person<input value={form.contact_person} onChange={(event) => setForm((current) => ({ ...current, contact_person: event.target.value }))} placeholder="Amina" /></label>
                <label className="formField">Phone<input value={form.phone} onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))} placeholder="+256..." /></label>
              </div>
              <label className="formField">Email<input value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} placeholder="vendor@example.com" aria-invalid={Boolean(emailError)} />{emailError ? <span className="errorText">{emailError}</span> : null}</label>
              <div className="grid twoColumns compactGrid">
                <label className="formField">Website<input value={form.website} onChange={(event) => setForm((current) => ({ ...current, website: event.target.value }))} placeholder="https://..." /></label>
                <label className="formField">Booking date<input type="date" value={form.booking_date} onChange={(event) => setForm((current) => ({ ...current, booking_date: event.target.value }))} /></label>
              </div>
              <label className="formField">Address<input value={form.address} onChange={(event) => setForm((current) => ({ ...current, address: event.target.value }))} placeholder="Office, shop, or meeting location" /></label>
              <label className="formField">Service description<textarea value={form.service_description} onChange={(event) => setForm((current) => ({ ...current, service_description: event.target.value }))} placeholder="What this vendor is expected to provide" /></label>
              <label className="formField">Event-day contact<input value={form.event_day_contact} onChange={(event) => setForm((current) => ({ ...current, event_day_contact: event.target.value }))} placeholder="Person to call during setup" /></label>
              <label className="formField">Notes<textarea value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} placeholder="Quote notes, follow-up reminders, family preferences..." /></label>
              <button className="primaryButton" data-icon="+" disabled={!canSubmit} type="submit">{processing === "create" ? "Adding..." : "Add vendor"}</button>
            </form>
          ) : <p>You can view vendors for this event, but vendor management is limited to event owners and authorized coordinators.</p>}
          <p>{notice}</p>
        </article>

        <article className="panel resourceCard">
          <p className="eyebrow">Search and filters</p>
          <h2>Find the right provider quickly</h2>
          <div className="stack">
            <label className="formField">Search<input value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} placeholder="Business, contact, service, email, phone" /></label>
            <div className="grid twoColumns compactGrid">
              <label className="formField">Category<select value={filters.category} onChange={(event) => setFilters((current) => ({ ...current, category: event.target.value }))}><option value="">All categories</option>{categoryOptions.map((category) => <option value={category.value} key={category.value}>{category.label}</option>)}</select></label>
              <label className="formField">Status<select value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}><option value="">All statuses</option>{vendorStatuses.map((status) => <option value={status.value} key={status.value}>{status.label}</option>)}</select></label>
            </div>
            <label className="formField checkboxField"><input checked={filters.outstanding} onChange={(event) => setFilters((current) => ({ ...current, outstanding: event.target.checked }))} type="checkbox" /> Vendors with outstanding budget balances</label>
            <button className="ghostButton" data-icon="×" type="button" onClick={() => setFilters(emptyFilters)}>Clear filters</button>
          </div>
        </article>
      </section>

      <section className="panel tablePanel">
        <div className="sectionHeader"><div><p className="eyebrow">Event vendors</p><h2>Service providers and budget readiness</h2></div><span className="badge softBadge">{vendors.length} shown</span></div>
        {vendors.length ? (
          <div className="tableScroller">
            <table className="dataTable">
              <thead><tr><th>Vendor</th><th>Contact</th><th>Status</th><th>Budget-linked financials</th><th>Actions</th></tr></thead>
              <tbody>
                {vendors.map((vendor) => {
                  const detail = vendorDetails[vendor.id] ?? vendor;
                  const financials = detail.financial_summary;
                  return (
                    <tr key={vendor.id}>
                      <td>{editingVendorId === vendor.id ? <div className="stack"><input value={editForm.name} onChange={(event) => setEditForm((current) => ({ ...current, name: event.target.value }))} /><select value={editForm.category} onChange={(event) => setEditForm((current) => ({ ...current, category: event.target.value }))}>{vendorCategories.map((category) => <option value={category.value} key={category.value}>{category.label}</option>)}</select><textarea value={editForm.service_description} onChange={(event) => setEditForm((current) => ({ ...current, service_description: event.target.value }))} placeholder="Service description" /></div> : <><strong>{vendor.name}</strong><small>{categoryLabel(vendor.category)}</small>{vendor.service_description ? <small>{vendor.service_description}</small> : null}</>}</td>
                      <td>{editingVendorId === vendor.id ? <div className="stack"><input value={editForm.contact_person} onChange={(event) => setEditForm((current) => ({ ...current, contact_person: event.target.value }))} placeholder="Contact person" /><input value={editForm.phone} onChange={(event) => setEditForm((current) => ({ ...current, phone: event.target.value }))} placeholder="Phone" /><input value={editForm.email} onChange={(event) => setEditForm((current) => ({ ...current, email: event.target.value }))} placeholder="Email" /><input value={editForm.address} onChange={(event) => setEditForm((current) => ({ ...current, address: event.target.value }))} placeholder="Address" /></div> : <>{vendor.contact_person ?? "Contact not set"}<small>{vendor.phone ?? "No phone"} · {vendor.email ?? "No email"}</small>{vendor.address ? <small>{vendor.address}</small> : null}</>}</td>
                      <td>{editingVendorId === vendor.id ? <div className="stack"><select value={editForm.status} onChange={(event) => setEditForm((current) => ({ ...current, status: event.target.value as VendorStatus }))}>{vendorStatuses.map((status) => <option value={status.value} key={status.value}>{status.label}</option>)}</select><input type="date" value={editForm.booking_date} onChange={(event) => setEditForm((current) => ({ ...current, booking_date: event.target.value }))} /><input value={editForm.event_day_contact} onChange={(event) => setEditForm((current) => ({ ...current, event_day_contact: event.target.value }))} placeholder="Event-day contact" /></div> : <><span className={vendor.status === "CONFIRMED" || vendor.status === "BOOKED" || vendor.status === "COMPLETED" ? "badge successBadge" : "badge softBadge"}>{statusLabel(vendor.status)}</span><small>{statusDescription(vendor.status)}</small>{vendor.booking_date ? <small>Booked {vendor.booking_date}</small> : null}</>}</td>
                      <td><strong>{formatMoney(financials.outstanding_total)} outstanding</strong><small>{formatMoney(financials.paid_total)} paid of {formatMoney(moneyValue(financials.actual_total) > 0 ? financials.actual_total : financials.committed_total)}</small><small>{financials.linked_budget_items_count} linked budget item{financials.linked_budget_items_count === 1 ? "" : "s"}</small></td>
                      <td>{canManage ? <div className="buttonRow tableActions">{editingVendorId === vendor.id ? <><button className="primaryButton" data-icon="✓" disabled={Boolean(processing)} type="button" onClick={() => void updateVendor(vendor.id)}>{processing === `update-${vendor.id}` ? "Saving..." : "Save"}</button><button className="ghostButton" data-icon="×" disabled={Boolean(processing)} type="button" onClick={() => setEditingVendorId(null)}>Cancel</button></> : <><button className="ghostButton" data-icon="◷" disabled={Boolean(processing)} type="button" onClick={() => void toggleDetails(vendor.id)}>{expandedVendorId === vendor.id ? "Hide details" : "Details"}</button><Link className="ghostButton" data-icon="₵" href={`/budget?project=${project?.id}&vendor=${vendor.id}`}>Link budget</Link><button className="ghostButton" data-icon="✎" disabled={Boolean(processing)} type="button" onClick={() => startEdit(detail)}>Edit</button><button className="ghostButton danger" data-icon="−" disabled={Boolean(processing)} type="button" onClick={() => void deleteVendor(vendor.id)}>{processing === `delete-${vendor.id}` ? "Removing..." : "Delete"}</button></>}</div> : <button className="ghostButton" data-icon="◷" disabled={Boolean(processing)} type="button" onClick={() => void toggleDetails(vendor.id)}>{expandedVendorId === vendor.id ? "Hide details" : "Details"}</button>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {expandedVendorId && vendorDetails[expandedVendorId] ? (
              <article className="panel resourceCard inlineDisclosure">
                <p className="eyebrow">Vendor detail</p>
                <h2>{vendorDetails[expandedVendorId].name}</h2>
                <p>{vendorDetails[expandedVendorId].service_description ?? "Service description has not been added yet."}</p>
                <div className="grid fourColumns">
                  <span className="badge softBadge">Planned {formatMoney(vendorDetails[expandedVendorId].financial_summary.planned_total)}</span>
                  <span className="badge softBadge">Committed {formatMoney(vendorDetails[expandedVendorId].financial_summary.committed_total)}</span>
                  <span className="badge softBadge">Paid {formatMoney(vendorDetails[expandedVendorId].financial_summary.paid_total)}</span>
                  <span className="badge softBadge">Open {formatMoney(vendorDetails[expandedVendorId].financial_summary.outstanding_total)}</span>
                </div>
                {vendorDetails[expandedVendorId].budget_items.length ? (
                  <div className="tableScroller">
                    <table className="dataTable"><thead><tr><th>Budget item</th><th>Category</th><th>Committed</th><th>Actual</th><th>Paid</th><th>Balance</th><th>Status</th></tr></thead><tbody>{vendorDetails[expandedVendorId].budget_items.map((item) => <tr key={item.id}><td><Link href={`/budget?project=${project?.id}&vendor=${expandedVendorId}`}>{item.name}</Link></td><td>{item.category}</td><td>{formatMoney(item.committed_amount)}</td><td>{formatMoney(item.actual_amount)}</td><td>{formatMoney(item.paid_amount)}</td><td>{formatMoney(item.outstanding_amount)}</td><td>{item.status}</td></tr>)}</tbody></table>
                  </div>
                ) : <p>No budget items are linked to this vendor yet. Use Link budget to connect planned costs.</p>}
              </article>
            ) : null}
          </div>
        ) : <StateBlock title="No vendors added yet" message={canManage ? "Add venues, decorators, caterers, photographers, and other providers as decisions take shape." : "Vendor records will appear here once the event team adds them."} />}
      </section>
    </>
  );
}
