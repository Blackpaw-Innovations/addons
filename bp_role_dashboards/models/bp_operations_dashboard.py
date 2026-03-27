# -*- coding: utf-8 -*-
import datetime
from odoo import api, models


class BpOperationsDashboard(models.TransientModel):
    _name = "bp.operations.dashboard"
    _description = "Operations Intelligence Dashboard"

    @api.model
    def get_dashboard_data(self):
        today = datetime.date.today()
        month_start = today.replace(day=1)
        company_id = self.env.company.id
        currency = self.env.company.currency_id

        # ── Job cards (bp_jobcards_app) ───────────────────────────────────────
        jobs_open = 0
        jobs_active = 0
        jobs_overdue = 0
        jobs_completed_mtd = 0
        revenue_mtd = 0.0
        avg_gp_pct = 0.0
        jobs_active_rows = []
        jobs_awaiting = []
        technician_rows = []
        signals = []

        try:
            Job = self.env["bp.job.card"]

            jobs_open = Job.search_count([
                ("state", "=", "draft"),
                ("company_id", "=", company_id),
            ])
            active_jobs = Job.search([
                ("state", "=", "in_progress"),
                ("company_id", "=", company_id),
            ])
            jobs_active = len(active_jobs)

            jobs_overdue = Job.search_count([
                ("state", "in", ["draft", "in_progress"]),
                ("scheduled_date", "<", today),
                ("company_id", "=", company_id),
            ])

            completed = Job.search([
                ("state", "=", "done"),
                ("date_done", ">=", month_start),
                ("company_id", "=", company_id),
            ])
            jobs_completed_mtd = len(completed)
            revenue_mtd = sum(completed.mapped("amount_total"))

            # GP% estimate
            costs = sum(completed.mapped("cost_total")) if completed else 0
            avg_gp_pct = round((revenue_mtd - costs) / revenue_mtd * 100, 1) if revenue_mtd else 0

            # Active jobs detail
            jobs_active_rows = [{
                "name": j.name,
                "client": j.partner_id.name if j.partner_id else "—",
                "tech": j.technician_id.name if j.technician_id else "—",
                "progress": j.progress if hasattr(j, "progress") else 0,
                "due": str(j.scheduled_date) if j.scheduled_date else "—",
            } for j in active_jobs[:8]]

            # Awaiting sign-off
            awaiting = Job.search([
                ("state", "=", "awaiting_approval"),
                ("company_id", "=", company_id),
            ], limit=8)
            jobs_awaiting = [{
                "name": j.name,
                "client": j.partner_id.name if j.partner_id else "—",
                "tech": j.technician_id.name if j.technician_id else "—",
            } for j in awaiting]

            # Signals
            if jobs_overdue > 5:
                signals.append({
                    "code": "CHK",
                    "color": "#f59e0b",
                    "name": "Overdue Jobs Are Piling Up — Capacity Constraint",
                    "desc": f"{jobs_overdue} jobs are past their scheduled date. This signals scheduling tightness or technician bottleneck.",
                    "nums": [
                        {"label": "Overdue", "value": str(jobs_overdue)},
                        {"label": "Active", "value": str(jobs_active)},
                    ],
                    "perspective": "Operations",
                    "perspective_color": "#f59e0b",
                    "action": "Triage overdue queue. Reassign jobs where technician is blocked. Contact affected clients proactively.",
                })

            if len(jobs_awaiting) >= 3:
                signals.append({
                    "code": "LKG",
                    "color": "#ef4444",
                    "name": "Sign-Off Backlog Is Delaying Invoice Release",
                    "desc": f"{len(jobs_awaiting)} jobs are awaiting client sign-off. Until signed off, invoices cannot be raised — revenue is locked.",
                    "nums": [
                        {"label": "Awaiting sign-off", "value": str(len(jobs_awaiting))},
                    ],
                    "perspective": "Revenue",
                    "perspective_color": "#ef4444",
                    "action": "Call each awaiting client today. Send digital sign-off link if available. Escalate to Account Manager.",
                })

        except Exception:
            # Model not available — fall back to account.move data
            try:
                Move = self.env["account.move"]
                rev_moves = Move.search([
                    ("move_type", "=", "out_invoice"),
                    ("state", "=", "posted"),
                    ("invoice_date", ">=", month_start),
                    ("company_id", "=", company_id),
                ])
                revenue_mtd = sum(rev_moves.mapped("amount_untaxed"))
            except Exception:
                pass

        if not signals:
            signals.append({
                "code": "THR",
                "color": "#22c55e",
                "name": "Operations Running Within Normal Parameters",
                "desc": "Job completion, overdue rates and sign-off queue are within acceptable ranges.",
                "nums": [],
                "perspective": "Healthy",
                "perspective_color": "#22c55e",
                "action": "Continue daily job board review. Monitor technician utilisation weekly.",
            })

        kpis = [
            {"label": "Open Jobs", "value": str(jobs_open), "variant": "default", "sub": "scheduled"},
            {"label": "Active Jobs", "value": str(jobs_active), "variant": "primary", "sub": "in progress"},
            {"label": "Overdue", "value": str(jobs_overdue), "variant": "danger" if jobs_overdue > 5 else ("warn" if jobs_overdue > 0 else "default"), "sub": "past due date"},
            {"label": "Completed MTD", "value": str(jobs_completed_mtd), "variant": "success", "sub": "this month"},
            {"label": "Revenue MTD", "value": _fmt_short(revenue_mtd), "variant": "primary", "sub": currency.name},
            {"label": "Avg GP%", "value": f"{avg_gp_pct}%", "variant": "success" if avg_gp_pct >= 30 else ("warn" if avg_gp_pct >= 15 else "danger"), "sub": "gross margin"},
        ]

        return {
            "kpis": kpis,
            "signals": signals,
            "tables": {
                "active_jobs": jobs_active_rows,
                "awaiting": jobs_awaiting,
                "technicians": technician_rows,
            },
            "currency": currency.name,
            "period": today.strftime("%B %Y"),
        }


def _fmt_short(val):
    if not val:
        return "0"
    if abs(val) >= 1_000_000:
        return f"{val/1_000_000:.2f}M"
    if abs(val) >= 1_000:
        return f"{val/1_000:.1f}K"
    return f"{val:,.0f}"
