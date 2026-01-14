from odoo import api, models, _
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    """ Inheriting 'product.product' for adding custom functionality."""
    _inherit = 'product.product'

    @api.onchange('to_make_mrp')
    def onchange_to_make_mrp(self):
        """ Raise validation error if bom is not set in 'product.product'."""
        if self.to_make_mrp:
            if not self.bom_count:
                raise Warning(
                    _('Please set Bill of Material for this product.'))

    def create_manufacturing_order(self, required_qty, location_id):
        # Get the available quantity for this product in the given location
        available_qty = self.with_context(location=location_id).qty_available
        _logger.info(f"Product {self.display_name} available_qty={available_qty}, required_qty={required_qty}, location_id={location_id}")
        if available_qty >= required_qty:
            # Sufficient stock, do not create manufacturing order
            return False
        # Not enough stock, proceed to create manufacturing order
        mo_vals = {
            'product_id': self.id,
            'product_qty': required_qty,
            'location_src_id': location_id,
            # Add other required fields here
        }
        mo = self.env['mrp.production'].create(mo_vals)
        return mo
