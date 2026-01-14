from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    cylinder_ids = fields.One2many(
        "stock.lot",
        "current_customer_id",
        string="Cylinders",
    )
    cylinder_count = fields.Integer(string="Cylinder Count", compute="_compute_cylinder_count")

    @api.depends("cylinder_ids")
    def _compute_cylinder_count(self):
        for partner in self:
            partner.cylinder_count = len(partner.cylinder_ids)
