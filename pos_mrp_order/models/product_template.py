from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    """ Inheriting 'product.template' for adding custom field and functionality.
    """
    _inherit = 'product.template'

    to_make_mrp = fields.Boolean(
        string='To Create MRP Order',
        help="Check if the product should make mrp order")

    @api.onchange('to_make_mrp')
    def onchange_to_make_mrp(self):
        """ Raise validation error if bom is not set in 'product.template'."""
        if self.to_make_mrp:
            if not self.bom_count:
                raise ValidationError(_(
                    'Please set Bill of Material for this product.'))

    def create_manufacturing_order(self, product_id, required_qty, location_id):
        # Check available stock for the product in the given location
        available_qty = self.env['stock.quant']._get_available_quantity(product_id, location_id)
        if available_qty >= required_qty:
            # Sufficient stock, do not create manufacturing order
            return False
        # Not enough stock, proceed to create manufacturing order
        # Example: create the manufacturing order (replace with your actual logic)
        mo_vals = {
            'product_id': product_id,
            'product_qty': required_qty,
            'location_src_id': location_id,
            # Add other required fields here
        }
        mo = self.env['mrp.production'].create(mo_vals)
        return mo
