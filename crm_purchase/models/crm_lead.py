from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = "crm.lead"

    purchase_order_ids = fields.One2many(
        "purchase.order", "crm_lead_id", string="Purchase Orders"
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account", string="Analytic Account"
    )

    def action_open_purchase_order(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Purchase Orders",
            "res_model": "purchase.order",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_crm_lead_id": self.id,
                "default_partner_id": self.partner_id.id if self.partner_id else False,
            },
        }

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    crm_lead_id = fields.Many2one("crm.lead", string="Opportunity")

    @api.model
    def create(self, vals):
        order = super().create(vals)
        if order.crm_lead_id and order.crm_lead_id.analytic_account_id:
            for line in order.order_line:
                # Set analytic_distribution to 100% for the opportunity's analytic account
                line.analytic_distribution = {
                    order.crm_lead_id.analytic_account_id.id: 100.0
                }
        return order