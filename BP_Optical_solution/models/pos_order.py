from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = "pos.order"

    is_invoice_payment: fields.Boolean = fields.Boolean(
        string="Is Invoice Payment",
        default=False,
        help="Indicates this POS order only records a payment on an invoice.",
    )
    invoice_id: fields.Many2one = fields.Many2one(
        comodel_name="account.move",
        string="Invoice",
        domain=lambda self: [
            ("move_type", "=", "out_invoice"),
            ("payment_state", "!=", "paid"),
        ],
    )
    invoice_payment_amount: fields.Monetary = fields.Monetary(
        string="Invoice Payment Amount",
        currency_field="currency_id",
        default=0.0,
    )
    invoice_payment_mode: fields.Selection = fields.Selection(
        selection=[
            ("deposit", "Deposit"),
            ("balance", "Balance"),
            ("full", "Full"),
            ("partial", "Partial"),
        ],
        string="Invoice Payment Mode",
    )
    invoice_residual_before: fields.Monetary = fields.Monetary(
        string="Residual Before Payment",
        currency_field="currency_id",
        default=0.0,
    )
    invoice_residual_after: fields.Monetary = fields.Monetary(
        string="Residual After Payment",
        currency_field="currency_id",
        default=0.0,
    )
    invoice_payment_processed: fields.Boolean = fields.Boolean(
        string="Invoice Payment Processed",
        default=False,
        help="Technical flag to avoid creating duplicate payments for the same POS order.",
    )

    @api.model
    def _order_fields(self, ui_order):
        res = super()._order_fields(ui_order)
        res.update(
            {
                "is_invoice_payment": ui_order.get("is_invoice_payment", False),
                "invoice_id": ui_order.get("invoice_id") or False,
                "invoice_payment_amount": ui_order.get("invoice_payment_amount") or 0.0,
                "invoice_payment_mode": ui_order.get("invoice_payment_mode") or False,
            }
        )
        return res

    @api.model
    def _process_order(self, order, draft, existing_order):
        """Override to process invoice payments after order creation."""
        order_id = super()._process_order(order, draft, existing_order)
        if order_id:
            pos_order = self.browse(order_id)
            pos_order._process_invoice_payments()
        return order_id

    def _create_order_picking(self):
        """Override to prevent picking creation for invoice payment orders."""
        if self.is_invoice_payment:
            return self.env['stock.picking']
        return super()._create_order_picking()

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        self._process_invoice_payments()
        return res

    def _process_invoice_payments(self):
        for order in self:
            if (
                not order.is_invoice_payment
                or not order.invoice_id
                or order.invoice_payment_processed
                or order.invoice_payment_amount <= 0
            ):
                continue

            if not order.partner_id:
                raise UserError(_("A customer is required to register an invoice payment."))

            invoice = order.invoice_id
            before_residual = invoice.amount_residual
            payment = order._create_invoice_payment(invoice)
            order.invoice_residual_before = before_residual
            order.invoice_residual_after = invoice.amount_residual
            order.invoice_payment_processed = bool(payment)

    def _create_invoice_payment(self, invoice):
        self.ensure_one()
        currency = invoice.currency_id or self.pricelist_id.currency_id or self.company_id.currency_id
        journal = self._get_invoice_payment_journal()
        if not journal:
            raise UserError(_("Please configure a bank or cash journal for invoice payments."))

        payment_method_line = journal._get_available_payment_method_lines("inbound")[:1]
        if not payment_method_line:
            raise UserError(
                _("The journal %s has no inbound payment method.") % journal.display_name
            )

        payment_vals = {
            "amount": self.invoice_payment_amount,
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": self.partner_id.id,
            "currency_id": currency.id,
            "date": fields.Date.to_date(self.date_order),
            "journal_id": journal.id,
            "payment_method_line_id": payment_method_line.id,
            "payment_reference": self.name or invoice.name,
            "ref": _("POS %s - Invoice Payment") % (self.name or invoice.name),
        }
        payment = self.env["account.payment"].create(payment_vals)
        payment.action_post()

        receivable_lines = (invoice.line_ids + payment.move_id.line_ids).filtered(
            lambda line: line.account_id.account_type == "asset_receivable" and not line.reconciled
        )
        if receivable_lines:
            receivable_lines.reconcile()
        
        # Refresh invoice to get updated payment state and residual
        invoice.invalidate_recordset(["amount_residual", "payment_state"])
        return payment

    def _get_invoice_payment_journal(self):
        self.ensure_one()
        payment = self.payment_ids[:1]
        if payment and payment.payment_method_id.journal_id:
            return payment.payment_method_id.journal_id

        # Fallback: any inbound journal from the session's payment methods
        session_methods = self.session_id.payment_method_ids.filtered("journal_id")
        if session_methods:
            inbound = session_methods.filtered(lambda m: m.journal_id.type in ("bank", "cash"))
            if inbound:
                return inbound[0].journal_id
            return session_methods[0].journal_id

        # Last resort: any company bank/cash journal
        return self.env["account.journal"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("type", "in", ["bank", "cash"]),
            ],
            limit=1,
        )
