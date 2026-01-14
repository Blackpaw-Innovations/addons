from typing import List

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PosInvoicePaymentWizard(models.TransientModel):
    _name = "bp.pos.invoice.payment.wizard"
    _description = "POS Invoice Payment Wizard"

    partner_id: fields.Many2one = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        required=True,
    )
    invoice_id: fields.Many2one = fields.Many2one(
        comodel_name="account.move",
        string="Invoice",
        domain=lambda self: [
            ("move_type", "=", "out_invoice"),
            ("payment_state", "!=", "paid"),
            ("partner_id", "=", self.env.context.get("default_partner_id")),
        ],
    )
    payment_amount: fields.Monetary = fields.Monetary(
        string="Payment Amount",
        required=True,
        currency_field="currency_id",
        default=0.0,
    )
    payment_mode: fields.Selection = fields.Selection(
        selection=[
            ("deposit", "Deposit"),
            ("balance", "Balance"),
            ("full", "Full"),
            ("partial", "Partial"),
        ],
        string="Payment Mode",
    )
    payment_journal_id: fields.Many2one = fields.Many2one(
        comodel_name="account.journal",
        string="Payment Journal",
        required=True,
        domain=[("type", "in", ("bank", "cash"))],
    )
    session_id: fields.Many2one = fields.Many2one(
        comodel_name="pos.session",
        string="POS Session",
    )
    pos_order_id: fields.Many2one = fields.Many2one(
        comodel_name="pos.order",
        string="POS Order",
    )
    currency_id: fields.Many2one = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id.id,
    )

    @api.constrains("payment_amount", "invoice_id")
    def _check_payment_amount(self):
        for wizard in self:
            if wizard.payment_amount <= 0:
                raise ValidationError(_("Payment amount must be greater than zero."))
            if wizard.invoice_id and wizard.payment_amount > wizard.invoice_id.amount_residual:
                raise ValidationError(
                    _("Payment amount cannot exceed the invoice residual (%s).")
                    % wizard.invoice_id.amount_residual
                )

    @api.model
    def get_open_invoices_for_partner(self, partner_id: int) -> List[dict]:
        if not partner_id:
            return []
        invoices = self.env["account.move"].search(
            [
                ("move_type", "=", "out_invoice"),
                ("partner_id", "=", partner_id),
                ("payment_state", "not in", ("paid", "reversed")),
            ]
        )
        return [
            {
                "id": invoice.id,
                "name": invoice.name,
                "amount_total": invoice.amount_total,
                "amount_residual": invoice.amount_residual,
                "invoice_date": invoice.invoice_date,
            }
            for invoice in invoices
        ]

    def action_load_open_invoices(self) -> List[dict]:
        self.ensure_one()
        return self.get_open_invoices_for_partner(self.partner_id.id)

    def action_confirm_payment(self):
        self.ensure_one()
        if not self.partner_id:
            raise ValidationError(_("Please select a customer."))
        if not self.invoice_id:
            raise ValidationError(_("Please select an invoice to pay."))
        if not self.payment_journal_id:
            raise ValidationError(_("Please select a payment journal."))
        if self.payment_amount <= 0:
            raise ValidationError(_("Payment amount must be greater than zero."))
        if self.payment_amount > self.invoice_id.amount_residual:
            raise ValidationError(
                _("Payment amount cannot exceed the invoice residual (%s).")
                % self.invoice_id.amount_residual
            )

        return {
            "invoice_id": self.invoice_id.id,
            "payment_amount": self.payment_amount,
            "payment_mode": self.payment_mode,
        }
