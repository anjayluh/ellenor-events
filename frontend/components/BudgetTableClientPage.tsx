"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiDelete, apiGet, apiPatch, apiPost } from "../lib/api";
import type { BudgetLineItem, BudgetResponse, Project } from "../lib/types";
import { useActiveProject } from "../lib/useActiveProject";
import { EventScopedHeader, EventWorkspaceGuard } from "./EventWorkspaceGuard";
import { StateBlock } from "./StateBlock";

type BudgetForm = {
  item_name: string;
  category: string;
  unit_cost: string;
  quantity: string;
  deposited_amount: string;
  next_deposit_date: string;
  payment_details: string;
  status: string;
};

const emptyForm: BudgetForm = { item_name: "", category: "", unit_cost: "", quantity: "1", deposited_amount: "", next_deposit_date: "", payment_details: "", status: "planned" };
const money = (value?: number | null) => value == null ? "Hidden" : `UGX ${Number(value).toLocaleString()}`;

function canEditBudget(project?: Project | null) {
  return Boolean(project?.role === "OWNER" || project?.role === "PARTNER" || project?.permissions?.includes("budget.edit"));
}

function deriveTotals(form: BudgetForm) {
  const unitCost = Number(form.unit_cost || 0);
  const quantity = Number(form.quantity || 0);
  const depositedAmount = Number(form.deposited_amount || 0);
  const totalCost = unitCost * quantity;
  return { unitCost, quantity, depositedAmount, totalCost, balance: Math.max(totalCost - depositedAmount, 0) };
}

export function BudgetTableClientPage() {
  const { projects, project, state, message, selectProject, reload } = useActiveProject();
  const [budget, setBudget] = useState<BudgetResponse | null>(null);
  const [items, setItems] = useState<BudgetLineItem[]>([]);
  const [form, setForm] = useState<BudgetForm>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [notice, setNotice] = useState("Add budget items with deposits, balances, and payment details.");
  const [processing, setProcessing] = useState<string | null>(null);

  async function loadBudget(activeProject: Project) {
    const nextBudget = await apiGet<BudgetResponse>(`/projects/${activeProject.id}/budget`);
    setBudget(nextBudget);
    setItems(nextBudget.line_items ?? []);
  }

  useEffect(() => {
    if (!project) return;
    void loadBudget(project).catch(() => {
      setBudget(null);
      setItems([]);
    });
  }, [project]);

  const { unitCost, quantity, depositedAmount, totalCost, balance } = deriveTotals(form);
  const itemNameError = form.item_name && form.item_name.trim().length < 2 ? "Item name must be at least 2 characters." : "";
  const categoryError = form.category && form.category.trim().length < 2 ? "Category must be at least 2 characters." : "";
  const amountError = unitCost < 0 || quantity < 0 || depositedAmount < 0 ? "Costs, quantity, and deposits must be zero or more." : "";
  const canSubmit = Boolean(project && canEditBudget(project) && form.item_name.trim().length >= 2 && form.category.trim().length >= 2 && !amountError && !processing);

  function payloadFromForm() {
    return {
      category: form.category.trim(),
      description: form.item_name.trim(),
      item_name: form.item_name.trim(),
      unit_cost: unitCost,
      quantity,
      total_cost: totalCost,
      deposited_amount: depositedAmount,
      balance,
      next_deposit_date: form.next_deposit_date || null,
      payment_details: form.payment_details.trim() || null,
      estimated_amount: totalCost,
      actual_amount: depositedAmount,
      status: form.status
    };
  }

  async function saveItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !canSubmit) return;
    setProcessing(editingId ? `update-${editingId}` : "create");
    setNotice(editingId ? "Saving budget item..." : "Adding budget item...");
    try {
      if (editingId) await apiPatch<BudgetLineItem, ReturnType<typeof payloadFromForm>>(`/projects/${project.id}/budget/line-items/${editingId}`, payloadFromForm());
      else await apiPost<BudgetLineItem, ReturnType<typeof payloadFromForm>>(`/projects/${project.id}/budget/line-items`, payloadFromForm());
      setForm(emptyForm);
      setEditingId(null);
      setNotice(editingId ? "Budget item updated." : "Budget item added.");
      await loadBudget(project);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not save budget item.");
    } finally {
      setProcessing(null);
    }
  }

  function editItem(item: BudgetLineItem) {
    setEditingId(item.id);
    setForm({
      item_name: item.item_name ?? item.description,
      category: item.category,
      unit_cost: String(item.unit_cost ?? 0),
      quantity: String(item.quantity ?? 1),
      deposited_amount: String(item.deposited_amount ?? 0),
      next_deposit_date: item.next_deposit_date ?? "",
      payment_details: item.payment_details ?? "",
      status: item.status
    });
  }

  async function deleteItem(itemId: string) {
    if (!project || processing || !window.confirm("Delete this budget item?")) return;
    setProcessing(`delete-${itemId}`);
    setNotice("Deleting budget item...");
    try {
      await apiDelete<{ status: string }>(`/projects/${project.id}/budget/line-items/${itemId}`);
      setNotice("Budget item deleted.");
      await loadBudget(project);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not delete budget item.");
    } finally {
      setProcessing(null);
    }
  }

  if (state !== "ready") return <EventWorkspaceGuard state={state} message={message} projects={projects} onSelect={selectProject} onCreated={() => void reload()} />;
  if (!budget) return <StateBlock title="Budget unavailable" message="Budget details are not available for your account on this event." />;

  return (
    <>
      <EventScopedHeader projects={projects} project={project} onSelect={selectProject} />
      <section className="grid threeColumns">
        <article className="metric"><span>Total cost</span><strong>{money(budget.line_item_total_cost ?? budget.total)}</strong></article>
        <article className="metric"><span>Total deposited</span><strong>{money(budget.line_item_deposited_total ?? budget.spent)}</strong></article>
        <article className="metric"><span>Total balance</span><strong>{money(budget.line_item_balance_total ?? budget.remaining)}</strong></article>
      </section>
      <section className="grid twoColumns">
        <article className="panel actionPanel">
          <p className="eyebrow">Budget Table</p>
          <h2>{editingId ? "Edit budget item" : "Add budget item"}</h2>
          {canEditBudget(project) ? (
            <form className="stack" onSubmit={saveItem}>
              <label className="formField">Item name<input value={form.item_name} onChange={(event) => setForm((current) => ({ ...current, item_name: event.target.value }))} placeholder="Decor stage" aria-invalid={Boolean(itemNameError)} /><span className="helperText">Required. At least 2 characters.</span>{itemNameError ? <span className="errorText">{itemNameError}</span> : null}</label>
              <label className="formField">Category<input value={form.category} onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))} placeholder="Decor" aria-invalid={Boolean(categoryError)} /><span className="helperText">Required. Example: decor, food, attire, transport.</span>{categoryError ? <span className="errorText">{categoryError}</span> : null}</label>
              <div className="grid twoColumns compactGrid">
                <label className="formField">Unit cost<input inputMode="numeric" value={form.unit_cost} onChange={(event) => setForm((current) => ({ ...current, unit_cost: event.target.value }))} /></label>
                <label className="formField">Quantity<input inputMode="numeric" value={form.quantity} onChange={(event) => setForm((current) => ({ ...current, quantity: event.target.value }))} /></label>
              </div>
              <label className="formField">Deposited amount<input inputMode="numeric" value={form.deposited_amount} onChange={(event) => setForm((current) => ({ ...current, deposited_amount: event.target.value }))} aria-invalid={Boolean(amountError)} /><span className="helperText">Total: {money(totalCost)} · Balance: {money(balance)}</span>{amountError ? <span className="errorText">{amountError}</span> : null}</label>
              <label className="formField">Next deposit date<input type="date" value={form.next_deposit_date} onChange={(event) => setForm((current) => ({ ...current, next_deposit_date: event.target.value }))} /></label>
              <label className="formField">Payment details<input value={form.payment_details} onChange={(event) => setForm((current) => ({ ...current, payment_details: event.target.value }))} placeholder="MTN MoMo +256... or bank account" /></label>
              <div className="buttonRow">
                <button className="primaryButton" data-icon="✓" disabled={!canSubmit} type="submit">{processing?.startsWith("update") ? "Saving..." : editingId ? "Save changes" : "Add item"}</button>
                {editingId ? <button className="ghostButton" data-icon="×" disabled={Boolean(processing)} type="button" onClick={() => { setEditingId(null); setForm(emptyForm); }}>Cancel</button> : null}
              </div>
            </form>
          ) : <p>You can view this budget, but editing is not enabled for your account.</p>}
          <p>{notice}</p>
        </article>
        <article className="panel tablePanel">
          <p className="eyebrow">Line Items</p>
          <h2>{project?.title} budget</h2>
          <div className="tableScroller">
            <table className="dataTable">
              <thead><tr><th>Item</th><th>Unit</th><th>Total</th><th>Deposited</th><th>Balance</th><th>Next deposit</th><th>Payment details</th><th>Actions</th></tr></thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td><strong>{item.item_name ?? item.description}</strong><small>{item.category}</small></td>
                    <td>{money(item.unit_cost)} × {item.quantity}</td>
                    <td>{money(item.total_cost)}</td>
                    <td>{money(item.deposited_amount)}</td>
                    <td>{money(item.balance)}</td>
                    <td>{item.next_deposit_date ?? "Not set"}</td>
                    <td>{item.payment_details ?? "Not set"}</td>
                    <td><div className="buttonRow tableActions"><button className="ghostButton" data-icon="✎" disabled={!canEditBudget(project) || Boolean(processing)} type="button" onClick={() => editItem(item)}>Edit</button><button className="ghostButton danger" data-icon="−" disabled={!canEditBudget(project) || Boolean(processing)} type="button" onClick={() => void deleteItem(item.id)}>{processing === `delete-${item.id}` ? "Deleting..." : "Delete"}</button></div></td>
                  </tr>
                ))}
                {!items.length ? <tr><td colSpan={8}>No budget items yet.</td></tr> : null}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    </>
  );
}
