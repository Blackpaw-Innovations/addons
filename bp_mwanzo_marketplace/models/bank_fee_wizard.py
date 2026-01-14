from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MwanzoBankFeeWizard(models.TransientModel):
    _name = "mwanzo.bank.fee.wizard"
    _description = "Record Bank Fee"

    journal_id = fields.Many2one(
        "account.journal",
        string="Bank Journal",
        domain=[("type", "=", "bank")],
        required=True,
    )
    amount = fields.Monetary(string="Fee Amount", required=True, currency_field="currency_id")
    date = fields.Date(string="Date", default=fields.Date.context_today, required=True)
    name = fields.Char(string="Description", default="Bank Fee", required=True)
    account_id = fields.Many2one(
        "account.account",
        string="Expense Account",
        domain=[("account_type", "=", "expense")],
        required=True,
        default=lambda self: self.env.company.mwanzo_bank_fee_account_id,
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="journal_id.currency_id",
        readonly=True,
    )

    @api.onchange("journal_id")
    def _onchange_journal_id(self):
        if self.journal_id and not self.currency_id:
            self.currency_id = self.journal_id.company_id.currency_id

    def action_post_fee(self):
        self.ensure_one()
        if self.amount <= 0:
            raise UserError(_("Fee amount must be positive."))

        # Ensure we have a valid currency (fallback to company currency if journal has none)
        currency_id = self.currency_id.id or self.company_id.currency_id.id

        # Create Payment to ensure it appears in "Payments" on the dashboard
        payment_vals = {
            'date': self.date,
            'amount': self.amount,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'ref': self.name,
            'journal_id': self.journal_id.id,
            'currency_id': currency_id,
            'partner_id': False,
            'destination_account_id': self.account_id.id,
            'company_id': self.company_id.id,
        }
        
        payment = self.env['account.payment'].create(payment_vals)
        payment.action_post()
        
        return {
            "name": _("Bank Fee"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "res_id": payment.id,
            "view_mode": "form",
        }
