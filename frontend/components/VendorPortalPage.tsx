"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiDelete, apiGet, apiPost, apiPut } from "../lib/api";

type VendorProfile = { user_id: string; business_name: string; category: string; contact_email?: string | null; contact_phone?: string | null; location?: string | null; bio?: string | null; payment_details?: string | null; status: string };
type Portfolio = { id: string; title: string; image_url: string; description?: string | null };
type Booking = { id: string; project_id: string; vendor_user_id: string; status: string; meeting_requested_at?: string | null; meeting_notes?: string | null; quoted_amount: number; agreed_amount: number };
type Payment = { id: string; booking_id: string; amount: number; received_at?: string | null; payment_method?: string | null; payment_reference?: string | null; notes?: string | null };

type ProfileForm = { business_name: string; category: string; contact_email: string; contact_phone: string; location: string; bio: string; payment_details: string; status: string };
const emptyProfile: ProfileForm = { business_name: "", category: "", contact_email: "", contact_phone: "", location: "", bio: "", payment_details: "", status: "active" };
const money = (value: number) => `UGX ${Number(value).toLocaleString()}`;

export function VendorPortalPage() {
  const [profile, setProfile] = useState<VendorProfile | null>(null);
  const [profileForm, setProfileForm] = useState<ProfileForm>(emptyProfile);
  const [portfolio, setPortfolio] = useState<Portfolio[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [payments, setPayments] = useState<Record<string, Payment[]>>({});
  const [portfolioForm, setPortfolioForm] = useState({ title: "", image_url: "", description: "" });
  const [paymentForm, setPaymentForm] = useState({ booking_id: "", amount: "", received_at: "", payment_method: "mobile_money", payment_reference: "", notes: "" });
  const [notice, setNotice] = useState("Create your vendor profile, showcase work, and track event bookings.");
  const [processing, setProcessing] = useState<string | null>(null);

  async function loadPortal() {
    try {
      const nextProfile = await apiGet<VendorProfile>("/vendors/portal/profile");
      setProfile(nextProfile);
      setProfileForm({
        business_name: nextProfile.business_name,
        category: nextProfile.category,
        contact_email: nextProfile.contact_email ?? "",
        contact_phone: nextProfile.contact_phone ?? "",
        location: nextProfile.location ?? "",
        bio: nextProfile.bio ?? "",
        payment_details: nextProfile.payment_details ?? "",
        status: nextProfile.status
      });
      const [nextPortfolio, nextBookings] = await Promise.all([apiGet<Portfolio[]>("/vendors/portal/portfolio"), apiGet<Booking[]>("/vendors/portal/bookings")]);
      setPortfolio(nextPortfolio);
      setBookings(nextBookings);
    } catch {
      setProfile(null);
    }
  }

  useEffect(() => { void loadPortal(); }, []);

  const nameError = profileForm.business_name && profileForm.business_name.trim().length < 2 ? "Business name must be at least 2 characters." : "";
  const categoryError = profileForm.category && profileForm.category.trim().length < 2 ? "Category must be at least 2 characters." : "";
  const profileValid = Boolean(profileForm.business_name.trim().length >= 2 && profileForm.category.trim().length >= 2 && !nameError && !categoryError && !processing);
  const portfolioValid = Boolean(portfolioForm.title.trim().length >= 2 && /^https?:\/\//.test(portfolioForm.image_url) && !processing);
  const paymentValid = Boolean(paymentForm.booking_id && Number(paymentForm.amount) >= 0 && !processing);

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!profileValid) return;
    setProcessing("profile");
    setNotice("Saving vendor profile...");
    try {
      await apiPut<VendorProfile, Record<string, string | null>>("/vendors/portal/profile", {
        business_name: profileForm.business_name.trim(),
        category: profileForm.category.trim(),
        contact_email: profileForm.contact_email.trim() || null,
        contact_phone: profileForm.contact_phone.trim() || null,
        location: profileForm.location.trim() || null,
        bio: profileForm.bio.trim() || null,
        payment_details: profileForm.payment_details.trim() || null,
        status: profileForm.status
      });
      setNotice("Vendor profile saved.");
      await loadPortal();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not save profile.");
    } finally {
      setProcessing(null);
    }
  }

  async function addPortfolio(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!portfolioValid) return;
    setProcessing("portfolio");
    try {
      await apiPost<Portfolio, typeof portfolioForm>("/vendors/portal/portfolio", portfolioForm);
      setPortfolioForm({ title: "", image_url: "", description: "" });
      setNotice("Portfolio item added.");
      await loadPortal();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not add portfolio item.");
    } finally {
      setProcessing(null);
    }
  }

  async function deletePortfolio(itemId: string) {
    if (processing || !window.confirm("Delete this portfolio photo?")) return;
    setProcessing(`portfolio-delete-${itemId}`);
    try {
      await apiDelete<{ status: string }>(`/vendors/portal/portfolio/${itemId}`);
      await loadPortal();
    } finally {
      setProcessing(null);
    }
  }

  async function loadPayments(bookingId: string) {
    const nextPayments = await apiGet<Payment[]>(`/vendors/portal/bookings/${bookingId}/payments`);
    setPayments((current) => ({ ...current, [bookingId]: nextPayments }));
  }

  async function recordPayment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!paymentValid) return;
    setProcessing("payment");
    try {
      await apiPost<Payment, Record<string, string | number | null>>(`/vendors/portal/bookings/${paymentForm.booking_id}/payments`, {
        amount: Number(paymentForm.amount),
        received_at: paymentForm.received_at || null,
        payment_method: paymentForm.payment_method || null,
        payment_reference: paymentForm.payment_reference.trim() || null,
        notes: paymentForm.notes.trim() || null
      });
      setNotice("Payment recorded.");
      await loadPayments(paymentForm.booking_id);
      setPaymentForm({ booking_id: "", amount: "", received_at: "", payment_method: "mobile_money", payment_reference: "", notes: "" });
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not record payment.");
    } finally {
      setProcessing(null);
    }
  }

  return (
    <section className="stack">
      <article className="hero compact"><p className="eyebrow">Vendor Portal</p><h1>Manage your service profile</h1><p>Vendors can add contacts, showcase photos, view booked events, and record payments received.</p></article>
      <section className="grid twoColumns">
        <article className="panel actionPanel">
          <p className="eyebrow">Profile</p><h2>{profile ? "Update vendor profile" : "Create vendor profile"}</h2>
          <form className="stack" onSubmit={saveProfile}>
            <label className="formField">Business name<input value={profileForm.business_name} onChange={(event) => setProfileForm((current) => ({ ...current, business_name: event.target.value }))} aria-invalid={Boolean(nameError)} /><span className="helperText">Required. At least 2 characters.</span>{nameError ? <span className="errorText">{nameError}</span> : null}</label>
            <label className="formField">Category<input value={profileForm.category} onChange={(event) => setProfileForm((current) => ({ ...current, category: event.target.value }))} placeholder="decor, catering, photography" aria-invalid={Boolean(categoryError)} />{categoryError ? <span className="errorText">{categoryError}</span> : null}</label>
            <div className="grid twoColumns compactGrid"><label className="formField">Email<input value={profileForm.contact_email} onChange={(event) => setProfileForm((current) => ({ ...current, contact_email: event.target.value }))} /></label><label className="formField">Phone<input value={profileForm.contact_phone} onChange={(event) => setProfileForm((current) => ({ ...current, contact_phone: event.target.value }))} /></label></div>
            <label className="formField">Location<input value={profileForm.location} onChange={(event) => setProfileForm((current) => ({ ...current, location: event.target.value }))} /></label>
            <label className="formField">Bio<input value={profileForm.bio} onChange={(event) => setProfileForm((current) => ({ ...current, bio: event.target.value }))} /></label>
            <label className="formField">Payment details<input value={profileForm.payment_details} onChange={(event) => setProfileForm((current) => ({ ...current, payment_details: event.target.value }))} placeholder="Mobile money or bank details" /></label>
            <button className="primaryButton" data-icon="✓" disabled={!profileValid} type="submit">{processing === "profile" ? "Saving..." : "Save profile"}</button>
          </form><p>{notice}</p>
        </article>
        <article className="panel actionPanel"><p className="eyebrow">Portfolio</p><h2>Add work photos</h2><form className="stack" onSubmit={addPortfolio}><label className="formField">Title<input value={portfolioForm.title} onChange={(event) => setPortfolioForm((current) => ({ ...current, title: event.target.value }))} /></label><label className="formField">Image URL<input value={portfolioForm.image_url} onChange={(event) => setPortfolioForm((current) => ({ ...current, image_url: event.target.value }))} placeholder="https://..." /><span className="helperText">Use a public image URL from free storage.</span></label><label className="formField">Description<input value={portfolioForm.description} onChange={(event) => setPortfolioForm((current) => ({ ...current, description: event.target.value }))} /></label><button className="primaryButton" data-icon="+" disabled={!portfolioValid} type="submit">{processing === "portfolio" ? "Adding..." : "Add photo"}</button></form></article>
      </section>
      <section className="grid threeColumns">{portfolio.map((item) => <article className="panel resourceCard" key={item.id}><div aria-label={item.title} className="portfolioImage imagePreview" role="img" style={{ backgroundImage: `url(${item.image_url})` }} /><h2>{item.title}</h2><p>{item.description}</p><button className="ghostButton danger" data-icon="−" disabled={Boolean(processing)} type="button" onClick={() => void deletePortfolio(item.id)}>Delete</button></article>)}</section>
      <section className="grid twoColumns">
        <article className="panel tablePanel"><p className="eyebrow">Bookings</p><h2>Events that booked you</h2><div className="tableScroller"><table className="dataTable"><thead><tr><th>Event</th><th>Status</th><th>Meeting</th><th>Amounts</th><th>Payments</th></tr></thead><tbody>{bookings.map((booking) => <tr key={booking.id}><td>{booking.project_id}</td><td>{booking.status.replaceAll("_", " ")}</td><td>{booking.meeting_requested_at ?? "Not scheduled"}<small>{booking.meeting_notes}</small></td><td>Quoted {money(booking.quoted_amount)}<small>Agreed {money(booking.agreed_amount)}</small></td><td><button className="ghostButton" data-icon="▦" type="button" onClick={() => { setPaymentForm((current) => ({ ...current, booking_id: booking.id })); void loadPayments(booking.id); }}>Payments</button></td></tr>)}</tbody></table></div></article>
        <article className="panel actionPanel"><p className="eyebrow">Payments</p><h2>Record received payment</h2><form className="stack" onSubmit={recordPayment}><label className="formField">Booking<select value={paymentForm.booking_id} onChange={(event) => setPaymentForm((current) => ({ ...current, booking_id: event.target.value }))}><option value="">Choose booking</option>{bookings.map((booking) => <option key={booking.id} value={booking.id}>{booking.project_id} · {booking.status}</option>)}</select></label><label className="formField">Amount<input inputMode="numeric" value={paymentForm.amount} onChange={(event) => setPaymentForm((current) => ({ ...current, amount: event.target.value }))} /></label><label className="formField">Received date<input type="date" value={paymentForm.received_at} onChange={(event) => setPaymentForm((current) => ({ ...current, received_at: event.target.value }))} /></label><label className="formField">Method<input value={paymentForm.payment_method} onChange={(event) => setPaymentForm((current) => ({ ...current, payment_method: event.target.value }))} /></label><label className="formField">Reference<input value={paymentForm.payment_reference} onChange={(event) => setPaymentForm((current) => ({ ...current, payment_reference: event.target.value }))} /></label><button className="primaryButton" data-icon="+" disabled={!paymentValid} type="submit">{processing === "payment" ? "Recording..." : "Record payment"}</button></form>{paymentForm.booking_id && payments[paymentForm.booking_id]?.map((payment) => <p key={payment.id}>{money(payment.amount)} · {payment.payment_method ?? "method not set"}</p>)}</article>
      </section>
    </section>
  );
}
