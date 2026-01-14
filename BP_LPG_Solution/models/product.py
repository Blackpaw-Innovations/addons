from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_lpg_cylinder = fields.Boolean(string="LPG Cylinder")
    is_lpg_gas = fields.Boolean(string="LPG Gas")
    cylinder_capacity_kg = fields.Float(string="Cylinder Capacity (kg)")
    requires_exchange = fields.Boolean(string="Requires Cylinder Exchange")

    @api.constrains("is_lpg_cylinder", "is_lpg_gas")
    def _check_lpg_flags(self):
        for record in self:
            if record.is_lpg_cylinder and record.is_lpg_gas:
                raise ValidationError(
                    _("A product cannot be both an LPG cylinder and LPG gas.")
                )

    @api.onchange("is_lpg_cylinder", "is_lpg_gas")
    def _onchange_lpg_flags(self):
        if self.is_lpg_cylinder:
            self.tracking = "serial"
            self.requires_exchange = True
        if self.is_lpg_gas:
            self.tracking = "none"

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._sanitize_lpg_vals(vals) for vals in vals_list]
        return super().create(vals_list)

    def write(self, vals):
        vals = self._sanitize_lpg_vals(vals)
        return super().write(vals)

    def _sanitize_lpg_vals(self, vals):
        vals = dict(vals)
        if vals.get("is_lpg_cylinder"):
            vals["tracking"] = "serial"
            vals.setdefault("requires_exchange", True)
        if vals.get("is_lpg_gas"):
            vals["tracking"] = "none"
        return vals


class ProductProduct(models.Model):
    _inherit = "product.product"

    is_lpg_cylinder = fields.Boolean(related="product_tmpl_id.is_lpg_cylinder", store=True)
    is_lpg_gas = fields.Boolean(related="product_tmpl_id.is_lpg_gas", store=True)
    cylinder_capacity_kg = fields.Float(
        related="product_tmpl_id.cylinder_capacity_kg", store=True
    )
    requires_exchange = fields.Boolean(related="product_tmpl_id.requires_exchange", store=True)
