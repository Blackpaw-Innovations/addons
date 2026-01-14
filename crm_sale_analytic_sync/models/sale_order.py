from odoo import models, fields, api

class CrmSaleAnalyticSyncSaleOrder(models.Model):
    _inherit = 'sale.order'

    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('opportunity_id'):
            lead = self.env['crm.lead'].browse(vals['opportunity_id'])
            if lead.analytic_account_id:
                vals['analytic_account_id'] = lead.analytic_account_id.id
        return super().create(vals)

class CrmSaleAnalyticSyncSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model
    def create(self, vals):
        # Use analytic_distribution instead of analytic_account_id
        if not vals.get('analytic_distribution') and vals.get('order_id'):
            order = self.env['sale.order'].browse(vals['order_id'])
            if order.analytic_account_id:
                vals['analytic_distribution'] = {order.analytic_account_id.id: 100}
        return super().create(vals)