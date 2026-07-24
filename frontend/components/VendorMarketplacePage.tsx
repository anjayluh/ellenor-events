"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../lib/api";
import type { Project } from "../lib/types";
import { useActiveProject } from "../lib/useActiveProject";
import { EventScopedHeader } from "./EventWorkspaceGuard";

type VendorProfile = { user_id: string; business_name: string; category: string; contact_email?: string | null; contact_phone?: string | null; location?: string | null; bio?: string | null; payment_details?: string | null; status: string };
type Portfolio = { id: string; title: string; image_url: string; description?: string | null };

function canBook(project?: Project | null) {
  return Boolean(project?.role === "OWNER" || project?.role === "PARTNER" || project?.role === "COMMITTEE_CHAIR" || project?.permissions?.includes("vendors.manage"));
}

export function VendorMarketplacePage() {
  const { projects, project, selectProject } = useActiveProject();
  const [vendors, setVendors] = useState<VendorProfile[]>([]);
  const [portfolio, setPortfolio] = useState<Record<string, Portfolio[]>>({});
  const [notice, setNotice] = useState("Browse active service providers and request meetings for the selected event.");
  const [processing, setProcessing] = useState<string | null>(null);

  useEffect(() => {
    void apiGet<VendorProfile[]>("/vendors/marketplace").then(setVendors).catch(() => setVendors([]));
  }, []);

  async function loadPortfolio(vendorUserId: string) {
    const items = await apiGet<Portfolio[]>(`/vendors/marketplace/${vendorUserId}/portfolio`);
    setPortfolio((current) => ({ ...current, [vendorUserId]: items }));
  }

  async function requestMeeting(vendorUserId: string) {
    if (!project || processing) return;
    setProcessing(`book-${vendorUserId}`);
    setNotice("Requesting vendor meeting...");
    try {
      await apiPost(`/vendors/projects/${project.id}/bookings`, { vendor_user_id: vendorUserId, status: "meeting_requested", meeting_notes: `Meeting requested for ${project.title}` });
      setNotice("Meeting request recorded. The vendor can see it in their portal.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not request vendor meeting.");
    } finally {
      setProcessing(null);
    }
  }

  return (
    <section className="stack">
      <article className="hero compact"><p className="eyebrow">Vendor Marketplace</p><h1>Find trusted service providers</h1><p>Select an event, review vendor work, and request a meeting without mixing vendors into guest invites or committee access.</p></article>
      {projects.length ? <EventScopedHeader projects={projects} project={project} onSelect={selectProject} /> : null}
      <p>{notice}</p>
      <section className="grid threeColumns">
        {vendors.map((vendor) => (
          <article className="panel resourceCard" key={vendor.user_id}>
            <p className="eyebrow">{vendor.category}</p>
            <h2>{vendor.business_name}</h2>
            <p>{vendor.bio ?? "No vendor description yet."}</p>
            <p>Contact: {vendor.contact_email ?? vendor.contact_phone ?? "Ask via meeting request"}</p>
            <p>Location: {vendor.location ?? "Not specified"}</p>
            <div className="buttonRow">
              <button className="ghostButton" data-icon="▦" type="button" onClick={() => void loadPortfolio(vendor.user_id)}>View work</button>
              <button className="primaryButton" data-icon="✉" disabled={!canBook(project) || Boolean(processing)} type="button" onClick={() => void requestMeeting(vendor.user_id)}>{processing === `book-${vendor.user_id}` ? "Requesting..." : "Request meeting"}</button>
            </div>
            {portfolio[vendor.user_id]?.length ? <div className="portfolioGrid">{portfolio[vendor.user_id].map((item) => <figure key={item.id}><div aria-label={item.title} className="portfolioThumb imagePreview" role="img" style={{ backgroundImage: `url(${item.image_url})` }} /><figcaption>{item.title}</figcaption></figure>)}</div> : null}
          </article>
        ))}
        {!vendors.length ? <article className="panel"><h2>No active vendors yet</h2><p>Vendors can create profiles from Vendor Portal.</p></article> : null}
      </section>
    </section>
  );
}
