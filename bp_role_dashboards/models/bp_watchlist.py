# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BpIntelligenceWatchlist(models.Model):
    _name = "bp.intelligence.watchlist"
    _description = "Blackpaw Intelligence Watchlist"
    _order = "watch_type, priority, name"

    company_id = fields.Many2one(
        "res.company", string="Company",
        default=lambda self: self.env.company, required=True, index=True)
    watch_type = fields.Selection([
        ("customer", "Customer / Debtor"),
        ("supplier", "Supplier / Creditor"),
        ("product", "Product"),
        ("employee", "Employee"),
    ], string="Track As", required=True)
    priority = fields.Selection([
        ("high",   "High"),
        ("medium", "Medium"),
        ("low",    "Low"),
    ], default="medium", required=True)
    active = fields.Boolean(default=True)
    notes = fields.Text("Alert Notes / Threshold Context")

    # ── Linked records (only one populated per row) ──────────────────────────
    partner_id = fields.Many2one("res.partner", string="Partner")
    product_id = fields.Many2one("product.product", string="Product")
    employee_id = fields.Many2one("hr.employee", string="Employee")

    # ── Computed display name ─────────────────────────────────────────────────
    name = fields.Char(compute="_compute_name", store=True, string="Watched Item")

    @api.depends("partner_id", "product_id", "employee_id", "watch_type")
    def _compute_name(self):
        for rec in self:
            if rec.partner_id:
                rec.name = rec.partner_id.name
            elif rec.product_id:
                rec.name = rec.product_id.display_name
            elif rec.employee_id:
                rec.name = rec.employee_id.name
            else:
                rec.name = "—"

    # ── Optional numeric thresholds ───────────────────────────────────────────
    ar_threshold = fields.Float(
        "AR Alert Threshold",
        help="Flag this debtor in Finance brief if outstanding AR exceeds this amount.")
    days_overdue_threshold = fields.Integer(
        "Overdue Days Alert",
        help="Flag if any invoice from this partner is overdue by more than N days.",
        default=30)

    # ── Public read method ────────────────────────────────────────────────────
    @api.model
    def get_watchlist(self, watch_type=None):
        """Return current company's active watchlist, optionally filtered by type."""
        domain = [("company_id", "=", self.env.company.id), ("active", "=", True)]
        if watch_type:
            domain.append(("watch_type", "=", watch_type))
        items = self.search(domain, order="priority, name")
        return [
            {
                "id": r.id,
                "name": r.name,
                "type": r.watch_type,
                "priority": r.priority,
                "partner_id": r.partner_id.id if r.partner_id else None,
                "product_id": r.product_id.id if r.product_id else None,
                "employee_id": r.employee_id.id if r.employee_id else None,
                "ar_threshold": r.ar_threshold,
                "days_overdue_threshold": r.days_overdue_threshold,
                "notes": r.notes or "",
            }
            for r in items
        ]
