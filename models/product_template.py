# -*- coding: utf-8 -*-
"""Product Template extensions for minimum stock quantity tracking.

This module extends the product.template model to add minimum quantity
threshold tracking and automated below-minimum detection.
"""

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = "product.template"

    minimum_qty = fields.Float(
        string="Minimum Quantity",
        store=True,
        help="Trigger level for below-minimum flag."
    )
    
    below_minimum = fields.Boolean(
        string="Below Minimum",
        store=True,
        index=True,
        default=False,
        compute="_compute_below_minimum",
        help="True when on-hand quantity is at or below minimum."
    )

    @api.depends('minimum_qty', 'qty_available')
    def _compute_below_minimum(self):
        """Compute the below_minimum flag based on current stock and minimum quantity."""
        for product in self:
            minimum = product.minimum_qty or 0.0
            product.below_minimum = product.qty_available <= minimum

    def action_recompute_below_minimum(self):
        """Manual action to recompute the below_minimum flag for selected products."""
        for record in self:
            minimum = record.minimum_qty or 0.0
            below_min = record.qty_available <= minimum
            record.write({'below_minimum': below_min})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Below minimum flags recomputed for {len(self)} product(s).',
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def cron_recompute_below_minimum(self):
        """Cron job method to recompute below_minimum flags for all products."""
        products = self.sudo().search([])
        
        for product in products:
            minimum = product.minimum_qty or 0.0
            below_min = product.qty_available <= minimum
            product.write({'below_minimum': below_min})