"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { apiDelete, apiGet, apiPatch, apiPost } from "../lib/api";
import type { Project } from "../lib/types";
import { useActiveProject } from "../lib/useActiveProject";
import { EventScopedHeader, EventWorkspaceGuard } from "./EventWorkspaceGuard";
import { StateBlock } from "./StateBlock";

type ProjectGuest = {
  id: string;
  project_id: string;
  first_name: string;
  last_name?: string | null;
  display_name: string;
  email?: string | null;
  phone?: string | null;
  category?: string | null;
  group_name?: string | null;
  notes?: string | null;
  invitation_card_url?: string | null;
  invitation_status: "NOT_SENT" | "SENT" | "OPENED" | "RESPONDED";
  rsvp_status: "PENDING" | "ATTENDING" | "NOT_ATTENDING";
  rsvp_responded_at?: string | null;
  rsvp_attendee_count: number;
  rsvp_note?: string | null;
  created_at: string;
};

type Usage = { key: string; label: string; used: number; limit?: number | null; remaining?: number | null };
type GuestSummary = {
  total: number;
  invitation_sent: number;
  attending: number;
  not_attending: number;
  pending_rsvp: number;
  opened: number;
  responded: number;
  invitations_opened: number;
  rsvp_responses: number;
  guest_usage: Usage;
  invitation_email_usage: Usage;
};
type GuestForm = { first_name: string; last_name: string; email: string; phone: string; category: string; group_name: string; invitation_card_url: string; notes: string };
type GuestFilters = { search: string; invitation_status: string; rsvp_status: string; category: string; group_name: string };
type SendInviteResponse = { guest: ProjectGuest; already_sent: boolean; guest_usage: Usage; invitation_email_usage: Usage };

const emptyForm: GuestForm = { first_name: "", last_name: "", email: "", phone: "", category: "", group_name: "", invitation_card_url: "", notes: "" };
const emptyFilters: GuestFilters = { search: "", invitation_status: "", rsvp_status: "", category: "", group_name: "" };

function canManage(project?: Project | null) {
  return Boolean(project?.role === "OWNER" || project?.role === "PARTNER" || project?.role === "COMMITTEE_CHAIR" || project?.permissions?.includes("guest_invites.manage"));
}

function usageText(usage?: Usage | null) {
  if (!usage) return "Not available";
  if (usage.limit == null) return `${usage.used} used`;
  return `${usage.used} / ${usage.limit}`;
}

function statusLabel(value: string) {
  return value.toLowerCase().replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function rsvpProgress(summary: GuestSummary | null) {
  if (!summary?.total) return 0;
  return Math.round((summary.rsvp_responses / summary.total) * 100);
}

function invitationProgress(summary: GuestSummary | null) {
  if (!summary?.total) return 0;
  return Math.round((summary.invitation_sent / summary.total) * 100);
}

function buildQuery(filters: GuestFilters) {
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

export function GuestInvitesClientPage() {
  const { projects, project, state, message, selectProject, reload } = useActiveProject();
  const [guests, setGuests] = useState<ProjectGuest[]>([]);
  const [summary, setSummary] = useState<GuestSummary | null>(null);
  const [form, setForm] = useState<GuestForm>(emptyForm);
  const [filters, setFilters] = useState<GuestFilters>(emptyFilters);
  const [editingGuestId, setEditingGuestId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<GuestForm>(emptyForm);
  const [notice, setNotice] = useState("Guests are attendance records only; they do not receive internal event workspace access.");
  const [processing, setProcessing] = useState<string | null>(null);

  const loadGuests = useCallback(async (activeProject: Project, nextFilters: GuestFilters) => {
    const [nextGuests, nextSummary] = await Promise.all([
      apiGet<ProjectGuest[]>(`/projects/${activeProject.id}/guests${buildQuery(nextFilters)}`),
      apiGet<GuestSummary>(`/projects/${activeProject.id}/guests/summary`)
    ]);
    setGuests(nextGuests);
    setSummary(nextSummary);
  }, []);

  useEffect(() => {
    if (!project || !canManage(project)) {
      setGuests([]);
      setSummary(null);
      return;
    }
    void loadGuests(project, filters).catch(() => {
      setGuests([]);
      setNotice("Guests could not be loaded for this event.");
    });
  }, [project, filters, loadGuests]);

  const categories = useMemo(() => [...new Set(guests.map((guest) => guest.category).filter(Boolean))] as string[], [guests]);
  const groups = useMemo(() => [...new Set(guests.map((guest) => guest.group_name).filter(Boolean))] as string[], [guests]);
  const firstNameError = form.first_name && form.first_name.trim().length < 1 ? "First name is required." : "";
  const emailError = form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email) ? "Enter a valid email address." : "";
  const contactError = !form.email.trim() && !form.phone.trim() ? "Add an email or phone number." : "";
  const canSubmit = Boolean(project && canManage(project) && form.first_name.trim() && !emailError && !contactError && !processing);

  async function createGuest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !canSubmit) return;
    setProcessing("create");
    setNotice("Adding guest...");
    try {
      await apiPost<ProjectGuest, Record<string, string | null>>(`/projects/${project.id}/guests`, {
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim() || null,
        email: form.email.trim().toLowerCase() || null,
        phone: form.phone.trim() || null,
        category: form.category.trim() || null,
        group_name: form.group_name.trim() || null,
        invitation_card_url: form.invitation_card_url.trim() || null,
        notes: form.notes.trim() || null
      });
      setForm(emptyForm);
      setNotice("Guest added. Send the invitation when the card and email are ready.");
      await loadGuests(project, filters);
    } catch (error) {
      setNotice(normalizeApiMessage(error));
    } finally {
      setProcessing(null);
    }
  }

  async function applyFilters(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    if (!project) return;
    setProcessing("filter");
    try {
      await loadGuests(project, filters);
    } finally {
      setProcessing(null);
    }
  }

  function startEdit(guest: ProjectGuest) {
    setEditingGuestId(guest.id);
    setEditForm({
      first_name: guest.first_name,
      last_name: guest.last_name ?? "",
      email: guest.email ?? "",
      phone: guest.phone ?? "",
      category: guest.category ?? "",
      group_name: guest.group_name ?? "",
      invitation_card_url: guest.invitation_card_url ?? "",
      notes: guest.notes ?? ""
    });
  }

  async function updateGuest(guestId: string) {
    if (!project || processing) return;
    setProcessing(`update-${guestId}`);
    try {
      await apiPatch<ProjectGuest, Record<string, string | null>>(`/projects/${project.id}/guests/${guestId}`, {
        first_name: editForm.first_name.trim(),
        last_name: editForm.last_name.trim() || null,
        email: editForm.email.trim().toLowerCase() || null,
        phone: editForm.phone.trim() || null,
        category: editForm.category.trim() || null,
        group_name: editForm.group_name.trim() || null,
        invitation_card_url: editForm.invitation_card_url.trim() || null,
        notes: editForm.notes.trim() || null
      });
      setEditingGuestId(null);
      setNotice("Guest updated.");
      await loadGuests(project, filters);
    } catch (error) {
      setNotice(normalizeApiMessage(error));
    } finally {
      setProcessing(null);
    }
  }

  async function deleteGuest(guestId: string) {
    if (!project || processing || !window.confirm("Remove this guest from the event? Invitation history will no longer be shown for them.")) return;
    setProcessing(`delete-${guestId}`);
    try {
      await apiDelete<{ status: string }>(`/projects/${project.id}/guests/${guestId}`);
      setNotice("Guest removed.");
      await loadGuests(project, filters);
    } catch (error) {
      setNotice(normalizeApiMessage(error));
    } finally {
      setProcessing(null);
    }
  }

  async function sendGuest(guest: ProjectGuest, resend = false) {
    if (!project || processing) return;
    setProcessing(`send-${guest.id}`);
    setNotice(resend ? "Resending invitation..." : "Sending invitation...");
    try {
      const result = await apiPost<SendInviteResponse, { resend: boolean }>(`/projects/${project.id}/guests/${guest.id}/invite`, { resend });
      setNotice(result.already_sent ? "This guest already has a sent invitation. Use resend only when you intentionally want another email." : "Invitation email prepared and usage updated.");
      await loadGuests(project, filters);
    } catch (error) {
      setNotice(normalizeApiMessage(error));
    } finally {
      setProcessing(null);
    }
  }

  async function updateRsvp(guestId: string, rsvp_status: ProjectGuest["rsvp_status"]) {
    if (!project || processing) return;
    setProcessing(`rsvp-${guestId}`);
    try {
      await apiPatch<ProjectGuest, { rsvp_status: string }>(`/projects/${project.id}/guests/${guestId}`, { rsvp_status });
      setNotice("RSVP status updated.");
      await loadGuests(project, filters);
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
        <article className="metric"><span>Total guests</span><strong>{summary?.total ?? 0}</strong><p>{usageText(summary?.guest_usage)} guests</p></article>
        <article className="metric"><span>Invitations sent</span><strong>{summary?.invitation_sent ?? 0}</strong><p>{summary?.invitations_opened ?? summary?.opened ?? 0} opened · {usageText(summary?.invitation_email_usage)} emails</p></article>
        <article className="metric"><span>RSVP responses</span><strong>{summary?.rsvp_responses ?? summary?.responded ?? 0}</strong><p>{summary?.attending ?? 0} attending · {summary?.not_attending ?? 0} not attending</p></article>
        <article className="metric"><span>Pending RSVP</span><strong>{summary?.pending_rsvp ?? 0}</strong><p>{rsvpProgress(summary)}% response completion</p></article>
      </section>

      <section className="panel resourceCard">
        <div className="cardTitleRow"><div><p className="eyebrow">Guest insights</p><h2>Invitation and RSVP progress</h2></div><span className="badge softBadge">Live event data</span></div>
        <div className="grid twoColumns compactGrid">
          <div>
            <p className="helperText">Invitations sent</p>
            <div className="progressTrack" aria-label="Invitation completion"><div className="progressFill" style={{ width: `${invitationProgress(summary)}%` }} /></div>
            <p>{invitationProgress(summary)}% of guests have been sent an invitation.</p>
          </div>
          <div>
            <p className="helperText">RSVP responses</p>
            <div className="progressTrack" aria-label="RSVP completion"><div className="progressFill" style={{ width: `${rsvpProgress(summary)}%` }} /></div>
            <p>{rsvpProgress(summary)}% of guests have responded.</p>
          </div>
        </div>
      </section>

      <section className="grid twoColumns">
        <article className="panel actionPanel">
          <p className="eyebrow">Guests</p>
          <h2>Add a guest</h2>
          {canManage(project) ? (
            <form className="stack" onSubmit={createGuest}>
              <div className="grid twoColumns compactGrid">
                <label className="formField">First name<input value={form.first_name} onChange={(event) => setForm((current) => ({ ...current, first_name: event.target.value }))} aria-invalid={Boolean(firstNameError)} />{firstNameError ? <span className="errorText">{firstNameError}</span> : null}</label>
                <label className="formField">Last name<input value={form.last_name} onChange={(event) => setForm((current) => ({ ...current, last_name: event.target.value }))} /></label>
              </div>
              <div className="grid twoColumns compactGrid">
                <label className="formField">Email<input value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} type="email" aria-invalid={Boolean(emailError || contactError)} />{emailError || contactError ? <span className="errorText">{emailError || contactError}</span> : null}</label>
                <label className="formField">Phone<input value={form.phone} onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))} /></label>
              </div>
              <div className="grid twoColumns compactGrid">
                <label className="formField">Category<input value={form.category} onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))} placeholder="Bride family" /></label>
                <label className="formField">Group<input value={form.group_name} onChange={(event) => setForm((current) => ({ ...current, group_name: event.target.value }))} placeholder="VIP table" /></label>
              </div>
              <label className="formField">Invitation card URL<input value={form.invitation_card_url} onChange={(event) => setForm((current) => ({ ...current, invitation_card_url: event.target.value }))} placeholder="https://.../card.png" /><span className="helperText">This card will be shown on the guest RSVP page. Upload storage can be connected later without changing guest records.</span></label>
              {form.invitation_card_url ? <div aria-label="Invitation card preview" className="inviteCardPreview imagePreview contain" role="img" style={{ backgroundImage: `url(${form.invitation_card_url})` }} /> : null}
              <label className="formField">Notes<input value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} placeholder="Dietary needs, family role, transport note" /></label>
              <button className="primaryButton" data-icon="+" disabled={!canSubmit} type="submit">{processing === "create" ? "Adding..." : "Add guest"}</button>
            </form>
          ) : <p>You can view this event, but managing guests is not enabled for your account.</p>}
          <p>{notice}</p>
        </article>

        <article className="panel">
          <p className="eyebrow">Find guests</p>
          <h2>Search and filter</h2>
          <form className="stack" onSubmit={(event) => void applyFilters(event)}>
            <label className="formField">Search<input value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} placeholder="Name, email, phone" /></label>
            <div className="grid twoColumns compactGrid">
              <label className="formField">Invitation status<select value={filters.invitation_status} onChange={(event) => setFilters((current) => ({ ...current, invitation_status: event.target.value }))}><option value="">All</option><option value="NOT_SENT">Not sent</option><option value="SENT">Sent</option><option value="OPENED">Opened</option><option value="RESPONDED">Responded</option></select></label>
              <label className="formField">RSVP status<select value={filters.rsvp_status} onChange={(event) => setFilters((current) => ({ ...current, rsvp_status: event.target.value }))}><option value="">All</option><option value="PENDING">Pending</option><option value="ATTENDING">Attending</option><option value="NOT_ATTENDING">Not attending</option></select></label>
            </div>
            <div className="grid twoColumns compactGrid">
              <label className="formField">Category<input list="guest-categories" value={filters.category} onChange={(event) => setFilters((current) => ({ ...current, category: event.target.value }))} /><datalist id="guest-categories">{categories.map((category) => <option key={category} value={category} />)}</datalist></label>
              <label className="formField">Group<input list="guest-groups" value={filters.group_name} onChange={(event) => setFilters((current) => ({ ...current, group_name: event.target.value }))} /><datalist id="guest-groups">{groups.map((group) => <option key={group} value={group} />)}</datalist></label>
            </div>
            <div className="buttonRow compactButtons">
              <button className="ghostButton" data-icon="⌕" disabled={processing === "filter"} type="submit">Apply filters</button>
              <button className="ghostButton" data-icon="×" disabled={processing === "filter"} type="button" onClick={() => { setFilters(emptyFilters); if (project) void loadGuests(project, emptyFilters); }}>Clear</button>
            </div>
          </form>
        </article>
      </section>

      <section className="stack">
        {canManage(project) && guests.length ? guests.map((guest) => (
          <article className="panel resourceCard" key={guest.id}>
            {editingGuestId === guest.id ? (
              <div className="stack">
                <p className="eyebrow">Edit guest</p>
                <div className="grid twoColumns compactGrid">
                  <label className="formField">First name<input value={editForm.first_name} onChange={(event) => setEditForm((current) => ({ ...current, first_name: event.target.value }))} /></label>
                  <label className="formField">Last name<input value={editForm.last_name} onChange={(event) => setEditForm((current) => ({ ...current, last_name: event.target.value }))} /></label>
                </div>
                <div className="grid twoColumns compactGrid">
                  <label className="formField">Email<input value={editForm.email} onChange={(event) => setEditForm((current) => ({ ...current, email: event.target.value }))} /></label>
                  <label className="formField">Phone<input value={editForm.phone} onChange={(event) => setEditForm((current) => ({ ...current, phone: event.target.value }))} /></label>
                </div>
                <div className="grid twoColumns compactGrid">
                  <label className="formField">Category<input value={editForm.category} onChange={(event) => setEditForm((current) => ({ ...current, category: event.target.value }))} /></label>
                  <label className="formField">Group<input value={editForm.group_name} onChange={(event) => setEditForm((current) => ({ ...current, group_name: event.target.value }))} /></label>
                </div>
                <label className="formField">Invitation card URL<input value={editForm.invitation_card_url} onChange={(event) => setEditForm((current) => ({ ...current, invitation_card_url: event.target.value }))} /></label>
                <label className="formField">Notes<input value={editForm.notes} onChange={(event) => setEditForm((current) => ({ ...current, notes: event.target.value }))} /></label>
                <div className="buttonRow">
                  <button className="primaryButton" data-icon="✓" disabled={!editForm.first_name.trim() || Boolean(processing)} type="button" onClick={() => void updateGuest(guest.id)}>{processing === `update-${guest.id}` ? "Saving..." : "Save guest"}</button>
                  <button className="ghostButton" data-icon="×" disabled={Boolean(processing)} type="button" onClick={() => setEditingGuestId(null)}>Cancel</button>
                </div>
              </div>
            ) : (
              <>
                <div className="cardTitleRow"><div><p className="eyebrow">Invitation: {statusLabel(guest.invitation_status)} · RSVP: {statusLabel(guest.rsvp_status)}</p><h2>{guest.display_name}</h2></div><span className="badge softBadge">{guest.category || "Guest"}</span></div>
                <div className="planningAreaList"><span className="badge softBadge">Invitation {statusLabel(guest.invitation_status)}</span><span className={guest.rsvp_status === "ATTENDING" ? "badge successBadge" : "badge softBadge"}>RSVP {statusLabel(guest.rsvp_status)}</span></div>
                <p>{guest.email ?? "No email"}{guest.phone ? ` · ${guest.phone}` : ""}</p>
                <p>{guest.group_name ? `Group: ${guest.group_name}` : "No group assigned yet."}{guest.rsvp_status !== "PENDING" ? ` · ${guest.rsvp_attendee_count} attending` : ""}</p>
                {guest.rsvp_note ? <p className="helperText">RSVP note: {guest.rsvp_note}</p> : null}
                {guest.notes ? <p className="helperText">{guest.notes}</p> : null}
                {guest.invitation_card_url ? <p className="helperText">Invitation card attached for this guest.</p> : null}
                <div className="buttonRow compactButtons">
                  <button className="ghostButton" data-icon="✉" disabled={!guest.email || Boolean(processing)} type="button" onClick={() => void sendGuest(guest, guest.invitation_status !== "NOT_SENT")}>{processing === `send-${guest.id}` ? "Sending..." : guest.invitation_status === "NOT_SENT" ? "Send invitation" : "Resend invitation"}</button>
                  {!guest.email ? <span className="helperText">Add an email to send an invitation.</span> : null}
                  <button className="ghostButton" data-icon="✎" disabled={Boolean(processing)} type="button" onClick={() => startEdit(guest)}>Edit</button>
                  <button className="ghostButton danger" data-icon="−" disabled={Boolean(processing)} type="button" onClick={() => void deleteGuest(guest.id)}>{processing === `delete-${guest.id}` ? "Removing..." : "Delete"}</button>
                  <select aria-label="RSVP status" disabled={Boolean(processing)} value={guest.rsvp_status} onChange={(event) => void updateRsvp(guest.id, event.target.value as ProjectGuest["rsvp_status"])}>
                    <option value="PENDING">Pending</option>
                    <option value="ATTENDING">Attending</option>
                    <option value="NOT_ATTENDING">Not attending</option>
                  </select>
                </div>
              </>
            )}
          </article>
        )) : <StateBlock title="No guests added yet" message={canManage(project) ? "Add guests to prepare invitation emails and track RSVP responses." : "Guest management is available to event owners and approved planning leads."} />}
      </section>
    </>
  );
}
