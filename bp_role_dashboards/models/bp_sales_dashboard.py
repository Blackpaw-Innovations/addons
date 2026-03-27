# -*- coding: utf-8 -*-
import datetime
from odoo import api, models


class BpSalesDashboard(models.TransientModel):
    _name = "bp.sales.dashboard"
    _description = "Sales Intelligence Dashboard"

    @api.model
    def get_dashboard_data(self):
        today = datetime.date.today()
        month_start = today.replace(day=1)
        ninety_days_ago = today - datetime.timedelta(days=90)
        company_id = self.env.company.id
        currency = self.env.company.currency_id

        Lead = self.env["crm.lead"]

        # ── Active pipeline ───────────────────────────────────────────────────
        active_leads = Lead.search([
            ("active", "=", True),
            ("probability", "not in", [0, 100]),
            ("company_id", "=", company_id),
        ])
        pipeline_value = sum(active_leads.mapped("expected_revenue"))
        active_count = len(active_leads)

        # ── Win rate (rolling 90 days) ────────────────────────────────────────
        won = Lead.search_count([
            ("active", "=", False), ("probability", "=", 100),
            ("date_closed", ">=", ninety_days_ago),
            ("company_id", "=", company_id),
        ])
        lost = Lead.search_count([
            ("active", "=", False), ("probability", "=", 0),
            ("date_closed", ">=", ninety_days_ago),
            ("company_id", "=", company_id),
        ])
        win_rate = round(won / (won + lost) * 100, 1) if (won + lost) else 0

        # ── Deals closed MTD ──────────────────────────────────────────────────
        deals_mtd = Lead.search([
            ("active", "=", False), ("probability", "=", 100),
            ("date_closed", ">=", month_start),
            ("company_id", "=", company_id),
        ])
        deals_closed_mtd = len(deals_mtd)
        avg_deal_size = round(sum(deals_mtd.mapped("expected_revenue")) / deals_closed_mtd, 0) if deals_closed_mtd else 0

        # ── Proposals sent MTD (sale orders in draft/sent) ────────────────────
        proposals_mtd = 0
        try:
            SaleOrder = self.env["sale.order"]
            proposals_mtd = SaleOrder.search_count([
                ("state", "in", ["draft", "sent"]),
                ("create_date", ">=", datetime.datetime.combine(month_start, datetime.time.min)),
                ("company_id", "=", company_id),
            ])
        except Exception:
            pass

        # ── Churn risk: clients with no new order >90 days ────────────────────
        churn_risk = 0
        try:
            SaleOrder = self.env["sale.order"]
            all_partners = SaleOrder.search([("company_id", "=", company_id)]).mapped("partner_id.id")
            recent_partners = SaleOrder.search([
                ("company_id", "=", company_id),
                ("confirmation_date", ">=", datetime.datetime.combine(ninety_days_ago, datetime.time.min)),
            ]).mapped("partner_id.id")
            churn_risk = len(set(all_partners) - set(recent_partners))
        except Exception:
            pass

        # ── Pipeline by stage ─────────────────────────────────────────────────
        Stage = self.env["crm.stage"]
        stages = Stage.search([], order="sequence asc")
        funnel = []
        for stage in stages:
            leads_in_stage = active_leads.filtered(lambda l: l.stage_id.id == stage.id)
            if leads_in_stage:
                funnel.append({
                    "stage": stage.name,
                    "count": len(leads_in_stage),
                    "value": sum(leads_in_stage.mapped("expected_revenue")),
                })

        # ── Win rate trend (4 months) ─────────────────────────────────────────
        wr_trend = []
        for i in range(3, -1, -1):
            ref = today.replace(day=1) - datetime.timedelta(days=1)
            for _ in range(i):
                ref = ref.replace(day=1) - datetime.timedelta(days=1)
            ms = ref.replace(day=1)
            me = datetime.datetime.combine(ref, datetime.time.max)
            ms_dt = datetime.datetime.combine(ms, datetime.time.min)
            w = Lead.search_count([("active", "=", False), ("probability", "=", 100), ("date_closed", ">=", ms_dt), ("date_closed", "<=", me), ("company_id", "=", company_id)])
            l_ = Lead.search_count([("active", "=", False), ("probability", "=", 0), ("date_closed", ">=", ms_dt), ("date_closed", "<=", me), ("company_id", "=", company_id)])
            wr = round(w / (w + l_) * 100, 1) if (w + l_) else 0
            wr_trend.append({"label": ms.strftime("%b"), "win_rate": wr, "won": w, "lost": l_})

        # ── Loss reasons ──────────────────────────────────────────────────────
        lost_leads = Lead.search([
            ("active", "=", False), ("probability", "=", 0),
            ("date_closed", ">=", ninety_days_ago),
            ("company_id", "=", company_id),
        ], limit=50)
        loss_reasons = {}
        for l in lost_leads:
            reason = l.lost_reason_id.name if l.lost_reason_id else "No reason given"
            loss_reasons.setdefault(reason, {"count": 0, "impact": 0.0})
            loss_reasons[reason]["count"] += 1
            loss_reasons[reason]["impact"] += l.expected_revenue
        loss_reason_rows = sorted(loss_reasons.items(), key=lambda x: -x[1]["count"])[:6]
        loss_reason_rows = [{"reason": k, "count": v["count"], "impact": v["impact"]} for k, v in loss_reason_rows]

        # ── Rep performance ───────────────────────────────────────────────────
        rep_data = {}
        for l in active_leads:
            uid = l.user_id.id if l.user_id else 0
            uname = l.user_id.name if l.user_id else "Unassigned"
            rep_data.setdefault(uid, {"name": uname, "pipeline": 0, "deals_won": 0, "revenue_won": 0})
            rep_data[uid]["pipeline"] += l.expected_revenue
        for l in deals_mtd:
            uid = l.user_id.id if l.user_id else 0
            uname = l.user_id.name if l.user_id else "Unassigned"
            rep_data.setdefault(uid, {"name": uname, "pipeline": 0, "deals_won": 0, "revenue_won": 0})
            rep_data[uid]["deals_won"] += 1
            rep_data[uid]["revenue_won"] += l.expected_revenue
        rep_rows = sorted(rep_data.values(), key=lambda r: -r["revenue_won"])[:8]

        # ── Proposals not followed up (>14 days no activity) ─────────────────
        stale_proposals = []
        try:
            SaleOrder = self.env["sale.order"]
            cutoff = datetime.datetime.combine(today - datetime.timedelta(days=14), datetime.time.max)
            stale = SaleOrder.search([
                ("state", "=", "sent"),
                ("write_date", "<=", cutoff),
                ("company_id", "=", company_id),
            ], limit=8)
            stale_proposals = [{
                "partner": s.partner_id.name if s.partner_id else "—",
                "ref": s.name,
                "rep": s.user_id.name if s.user_id else "—",
                "age_days": (today - s.write_date.date()).days,
                "amount": s.amount_untaxed,
            } for s in stale]
        except Exception:
            pass

        # ── Monthly revenue target (rough: pipeline / coverage) ───────────────
        coverage = round(pipeline_value / (sum(t["revenue_won"] for t in rep_rows) or 1), 1) if rep_rows else 0

        # ── Signals ───────────────────────────────────────────────────────────
        signals = []

        # DEC: 4-month win rate decline
        if len(wr_trend) >= 3:
            rates = [t["win_rate"] for t in wr_trend]
            if rates[0] > 0 and rates[-1] < rates[0] and all(rates[i] >= rates[i+1] for i in range(len(rates)-1)):
                signals.append({
                    "code": "DEC",
                    "color": "#ef4444",
                    "name": f"Win Rate Has Fallen {len(rates)} Consecutive Months",
                    "desc": f"Win rate has dropped from {rates[0]}% to {rates[-1]}%. Compounding losses compound faster than pipeline growth.",
                    "nums": [
                        {"label": wr_trend[0]["label"], "value": f"{rates[0]}%"},
                        {"label": wr_trend[-1]["label"], "value": f"{rates[-1]}%"},
                        {"label": "Won 90d", "value": str(won)},
                        {"label": "Lost 90d", "value": str(lost)},
                    ],
                    "perspective": "Revenue",
                    "perspective_color": "#ef4444",
                    "action": "Pull last 10 lost deals. Find the common loss pattern. Adjust qualifying criteria or proposal quality before adding more volume.",
                })

        # STV: pipeline coverage < 3×
        monthly_rev = sum(t["revenue_won"] for t in rep_rows) or 1
        coverage_ratio = round(pipeline_value / monthly_rev, 1)
        if coverage_ratio < 3 and pipeline_value > 0:
            signals.append({
                "code": "STV",
                "color": "#f59e0b",
                "name": "Pipeline Is Below Safe Coverage Threshold",
                "desc": f"Pipeline is {coverage_ratio}× monthly revenue. Healthy pipeline requires 3× or more to absorb normal loss rates.",
                "nums": [
                    {"label": "Pipeline value", "value": _fmt_short(pipeline_value)},
                    {"label": "Monthly revenue", "value": _fmt_short(monthly_rev)},
                    {"label": "Coverage", "value": f"{coverage_ratio}×"},
                ],
                "perspective": "Revenue",
                "perspective_color": "#f59e0b",
                "action": "Prioritise top-of-funnel activities. Each rep should target 3 new discovery calls this week.",
            })

        # IGN: stale proposals
        if len(stale_proposals) >= 3:
            signals.append({
                "code": "IGN",
                "color": "#8b5cf6",
                "name": f"{len(stale_proposals)} Proposals Are Leaking Through Follow-Up Gaps",
                "desc": "Proposals sent but not followed up within 14 days have a 70%+ loss probability. This is silent pipeline destruction.",
                "nums": [
                    {"label": "Stale proposals", "value": str(len(stale_proposals))},
                    {"label": "Threshold", "value": ">14 days"},
                ],
                "perspective": "Execution",
                "perspective_color": "#8b5cf6",
                "action": "Assign each stale proposal to a rep for same-day follow-up. Add CRM reminder rule for all sent proposals.",
            })

        if not signals:
            signals.append({
                "code": "THR",
                "color": "#22c55e",
                "name": "Sales Metrics Within Healthy Range",
                "desc": "Pipeline coverage, win rate and follow-up cadence are all within acceptable thresholds.",
                "nums": [],
                "perspective": "Healthy",
                "perspective_color": "#22c55e",
                "action": "Maintain current prospecting and follow-up rhythm.",
            })

        kpis = [
            {"label": "Pipeline Value", "value": _fmt_short(pipeline_value), "variant": "primary", "sub": currency.name},
            {"label": "Win Rate MTD", "value": f"{win_rate}%", "variant": "success" if win_rate >= 40 else ("warn" if win_rate >= 25 else "danger"), "sub": "rolling 90 days"},
            {"label": "Deals Closed MTD", "value": str(deals_closed_mtd), "variant": "primary", "sub": "this month"},
            {"label": "Avg Deal Size", "value": _fmt_short(avg_deal_size), "variant": "default", "sub": currency.name},
            {"label": "Proposals Sent", "value": str(proposals_mtd), "variant": "default", "sub": "this month"},
            {"label": "Churn Risk", "value": str(churn_risk), "variant": "danger" if churn_risk >= 5 else ("warn" if churn_risk >= 2 else "default"), "sub": "clients >90d silent"},
        ]

        return {
            "kpis": kpis,
            "signals": signals,
            "tables": {
                "funnel": funnel,
                "wr_trend": wr_trend,
                "loss_reasons": loss_reason_rows,
                "reps": rep_rows,
                "stale_proposals": stale_proposals,
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
