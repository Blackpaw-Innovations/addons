from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    bp_pos_payment_ids: fields.One2many = fields.One2many(
        comodel_name="pos.order",
        inverse_name="invoice_id",
        string="POS Payments",
    )
    pos_payment_total: fields.Monetary = fields.Monetary(
        string="Total POS Payments",
        currency_field="currency_id",
        compute="_compute_pos_payment_totals",
        store=True,
        compute_sudo=True,
    )
    has_pos_payments: fields.Boolean = fields.Boolean(
        string="Has POS Payments",
        compute="_compute_pos_payment_totals",
        store=True,
        compute_sudo=True,
    )

    def _compute_pos_payment_totals(self):
        for move in self:
            total = sum(move.bp_pos_payment_ids.mapped("invoice_payment_amount"))
            move.pos_payment_total = total
            move.has_pos_payments = bool(move.bp_pos_payment_ids)
