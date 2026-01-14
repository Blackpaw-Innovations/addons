from odoo import api, fields, models, _


class CustomerStatementWizard(models.TransientModel):
    _name = "bp.customer.statement.wizard"
    _description = "Customer Statement Wizard"

    partner_id = fields.Many2one("res.partner", string="Customer", required=True)
    date_from = fields.Date(string="Start Date")
    date_to = fields.Date(string="End Date")

    def _get_statement_lines(self):
        self.ensure_one()
        domain = [
            ("partner_id", "=", self.partner_id.id),
            ("account_id.internal_type", "=", "receivable"),
            ("parent_state", "=", "posted"),
        ]
        if self.date_from:
            domain.append(("date", ">=", self.date_from))
        if self.date_to:
            domain.append(("date", "<=", self.date_to))

        lines = self.env["account.move.line"].search(domain, order="date, id")
        running_balance = 0.0
        statement_lines = []
        for line in lines:
            move = line.move_id
            doc_type = ""
            if move.move_type in ("out_invoice", "out_refund"):
                doc_type = _("Invoice") if move.move_type == "out_invoice" else _("Refund")
            elif line.payment_id:
                doc_type = _("Payment")
            else:
                doc_type = _("Journal Entry")

            amount = line.debit - line.credit
            running_balance += amount
            statement_lines.append(
                {
                    "date": line.date,
                    "doc_type": doc_type,
                    "name": move.name or move.ref or "",
                    "origin": move.invoice_origin or move.ref or line.name or "",
                    "debit": line.debit,
                    "credit": line.credit,
                    "balance": running_balance,
                    "currency": line.company_currency_id,
                }
            )
        return statement_lines

    def action_print_statement(self):
        self.ensure_one()
        return self.env.ref("BP_Optical_solution.action_customer_statement_report").report_action(self)
