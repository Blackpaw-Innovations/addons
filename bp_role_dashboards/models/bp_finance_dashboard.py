# -*- coding: utf-8 -*-
import datetime
from odoo import api, models


class BpFinanceDashboard(models.TransientModel):
    _name = "bp.finance.dashboard"
    _description = "Finance Intelligence Dashboard"

    @api.model
    def get_dashboard_data(self):
        today = datetime.date.today()
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)
        prev_month_end = month_start - datetime.timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)
        currency = self.env.company.currency_id

        Move = self.env["account.move"]

        # ── KPIs ──────────────────────────────────────────────────────────────

        def _sum_moves(domain):
            recs = Move.search(domain)
            return sum(recs.mapped("amount_untaxed"))

        revenue_mtd = _sum_moves([
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("invoice_date", ">=", month_start),
            ("company_id", "=", self.env.company.id),
        ])
        expenses_mtd = _sum_moves([
            ("move_type", "=", "in_invoice"),
            ("state", "=", "posted"),
            ("invoice_date", ">=", month_start),
            ("company_id", "=", self.env.company.id),
        ])
        gp = revenue_mtd - expenses_mtd
        gp_pct = round((gp / revenue_mtd * 100) if revenue_mtd else 0, 1)

        # Cash in bank
        Account = self.env["account.account"]
        cash_accounts = Account.search([
            ("account_type", "in", ["asset_cash", "asset_bank_and_cash"]),
            ("company_ids", "in", [self.env.company.id]),
        ])
        cash_balance = sum(cash_accounts.mapped("current_balance")) if cash_accounts else 0.0

        # AR outstanding
        ar_moves = Move.search([
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "in", ["not_paid", "partial"]),
            ("company_id", "=", self.env.company.id),
        ])
        ar_outstanding = sum(ar_moves.mapped("amount_residual"))
        overdue_moves = ar_moves.filtered(
            lambda m: m.invoice_date_due and m.invoice_date_due < (today - datetime.timedelta(days=30))
        )
        overdue_30 = sum(overdue_moves.mapped("amount_residual"))

        # ── AR Aging table ────────────────────────────────────────────────────
        aging = {}
        for m in ar_moves:
            if not m.partner_id:
                continue
            pid = m.partner_id.id
            pname = m.partner_id.name or "Unknown"
            if pid not in aging:
                aging[pid] = {"name": pname, "current": 0.0, "d30": 0.0, "d60": 0.0}
            due = m.invoice_date_due or today
            age = (today - due).days
            residual = m.amount_residual
            if age <= 0:
                aging[pid]["current"] += residual
            elif age <= 30:
                aging[pid]["d30"] += residual
            else:
                aging[pid]["d60"] += residual

        aging_rows = sorted(aging.values(), key=lambda r: r["current"] + r["d30"] + r["d60"], reverse=True)[:10]

        # ── Revenue concentration (top clients) ───────────────────────────────
        rev_by_partner = {}
        for m in Move.search([
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("invoice_date", ">=", month_start),
            ("company_id", "=", self.env.company.id),
        ]):
            pid = m.partner_id.id if m.partner_id else 0
            pname = m.partner_id.name if m.partner_id else "Unknown"
            rev_by_partner.setdefault(pid, {"name": pname, "amount": 0.0})
            rev_by_partner[pid]["amount"] += m.amount_untaxed

        total_rev = sum(v["amount"] for v in rev_by_partner.values()) or 1
        concentration = sorted(rev_by_partner.values(), key=lambda r: r["amount"], reverse=True)[:5]
        for c in concentration:
            c["pct"] = round(c["amount"] / total_rev * 100, 1)

        # ── Payables watchlist ────────────────────────────────────────────────
        payables = Move.search([
            ("move_type", "=", "in_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "in", ["not_paid", "partial"]),
            ("company_id", "=", self.env.company.id),
        ], order="invoice_date_due asc", limit=8)
        payables_rows = [{
            "partner": p.partner_id.name or "—",
            "ref": p.ref or p.name or "—",
            "amount": p.amount_residual,
            "due": str(p.invoice_date_due) if p.invoice_date_due else "—",
            "overdue": bool(p.invoice_date_due and p.invoice_date_due < today),
        } for p in payables]

        # ── Revenue trend (6 months) ──────────────────────────────────────────
        trend = []
        for i in range(5, -1, -1):
            ref = today.replace(day=1) - datetime.timedelta(days=1)
            for _ in range(i):
                ref = ref.replace(day=1) - datetime.timedelta(days=1)
            m_start = ref.replace(day=1)
            m_end = ref
            label = m_start.strftime("%b")
            rev = _sum_moves([
                ("move_type", "=", "out_invoice"), ("state", "=", "posted"),
                ("invoice_date", ">=", m_start), ("invoice_date", "<=", m_end),
                ("company_id", "=", self.env.company.id),
            ])
            exp = _sum_moves([
                ("move_type", "=", "in_invoice"), ("state", "=", "posted"),
                ("invoice_date", ">=", m_start), ("invoice_date", "<=", m_end),
                ("company_id", "=", self.env.company.id),
            ])
            trend.append({"label": label, "revenue": rev, "expenses": exp})

        # ── Signals ───────────────────────────────────────────────────────────
        signals = []

        # BLD: 3-month cash decline (revenue dropping)
        rev_3mo = [t["revenue"] for t in trend[-3:]]
        if len(rev_3mo) == 3 and rev_3mo[0] > 0 and rev_3mo[2] < rev_3mo[0]:
            decline_pct = round((rev_3mo[0] - rev_3mo[2]) / rev_3mo[0] * 100, 1)
            if decline_pct > 5:
                signals.append({
                    "code": "BLD",
                    "color": "#dc2626",
                    "name": "Revenue Has Declined Over 3 Consecutive Months",
                    "desc": f"Revenue has dropped {decline_pct}% over the last 3 months. If expenses hold, margin erosion will accelerate.",
                    "nums": [
                        {"label": "3mo ago", "value": _fmt(rev_3mo[0])},
                        {"label": "This month", "value": _fmt(rev_3mo[2])},
                        {"label": "Decline", "value": f"{decline_pct}%"},
                    ],
                    "perspective": "Risk",
                    "perspective_color": "#ef4444",
                    "action": "Review top clients for reduced order frequency. Check for deals stalled in pipeline.",
                })

        # FRG: revenue concentration — top client >35%
        if concentration and concentration[0]["pct"] > 35:
            top = concentration[0]
            signals.append({
                "code": "FRG",
                "color": "#dc2626",
                "name": f"Revenue Is Fragile — {top['name']} Drives {top['pct']}% of Billings",
                "desc": "Single-client concentration above 35% creates critical vulnerability. One payment delay becomes a cash crisis.",
                "nums": [
                    {"label": "Top client %", "value": f"{top['pct']}%"},
                    {"label": "Client revenue", "value": _fmt(top['amount'])},
                    {"label": "Total MTD", "value": _fmt(revenue_mtd)},
                ],
                "perspective": "Risk",
                "perspective_color": "#ef4444",
                "action": "Prioritise 2–3 new mid-size accounts this quarter. Set internal alert if this client drops >20% MoM.",
            })

        # LKG: overdue AR >20% of total AR
        if ar_outstanding > 0 and (overdue_30 / ar_outstanding) > 0.20:
            lkg_pct = round(overdue_30 / ar_outstanding * 100, 1)
            signals.append({
                "code": "LKG",
                "color": "#f59e0b",
                "name": "Overdue Receivables Are Leaking Cash Flow",
                "desc": f"{lkg_pct}% of outstanding AR is overdue by more than 30 days. Collections are not keeping pace with billings.",
                "nums": [
                    {"label": "Total AR", "value": _fmt(ar_outstanding)},
                    {"label": "Overdue >30d", "value": _fmt(overdue_30)},
                    {"label": "Overdue %", "value": f"{lkg_pct}%"},
                ],
                "perspective": "Operations",
                "perspective_color": "#f59e0b",
                "action": "Run collections call on top 5 overdue accounts this week. Consider proforma or upfront payment terms for repeat offenders.",
            })

        if not signals:
            signals.append({
                "code": "THR",
                "color": "#22c55e",
                "name": "No Critical Financial Signals Detected",
                "desc": "All key indicators are within acceptable thresholds. Continue monitoring cash, AR aging and revenue concentration.",
                "nums": [],
                "perspective": "Healthy",
                "perspective_color": "#22c55e",
                "action": "Maintain current collections cadence and review concentration monthly.",
            })

        kpis = [
            {"label": "Revenue MTD", "value": _fmt_short(revenue_mtd), "variant": "primary", "sub": currency.name},
            {"label": "Expenses MTD", "value": _fmt_short(expenses_mtd), "variant": "default", "sub": currency.name},
            {"label": "Gross Profit", "value": f"{gp_pct}%", "variant": "success" if gp_pct >= 20 else "warn", "sub": _fmt_short(gp)},
            {"label": "Cash in Bank", "value": _fmt_short(cash_balance), "variant": "primary" if cash_balance > 0 else "danger", "sub": currency.name},
            {"label": "AR Outstanding", "value": _fmt_short(ar_outstanding), "variant": "warn" if ar_outstanding > 0 else "default", "sub": currency.name},
            {"label": "Overdue >30d", "value": _fmt_short(overdue_30), "variant": "danger" if overdue_30 > 0 else "default", "sub": currency.name},
        ]

        return {
            "kpis": kpis,
            "signals": signals,
            "tables": {
                "aging": aging_rows,
                "concentration": concentration,
                "payables": payables_rows,
                "trend": trend,
            },
            "currency": currency.name,
            "period": today.strftime("%B %Y"),
        }


def _fmt(val):
    if val is None:
        return "0"
    return f"{val:,.0f}"


def _fmt_short(val):
    if not val:
        return "0"
    if abs(val) >= 1_000_000:
        return f"{val/1_000_000:.2f}M"
    if abs(val) >= 1_000:
        return f"{val/1_000:.1f}K"
    return f"{val:,.0f}"
