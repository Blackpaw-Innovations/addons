from odoo import fields, models


class StockLot(models.Model):
    _inherit = "stock.lot"

    cylinder_status = fields.Selection(
        [
            ("filled", "Filled"),
            ("empty", "Empty"),
            ("damaged", "Damaged"),
            ("maintenance", "Maintenance"),
        ],
        string="Cylinder Status",
        default="empty",
    )
    current_customer_id = fields.Many2one(
        "res.partner",
        string="Current Customer",
        index=True,
    )
    last_movement_date = fields.Datetime(string="Last Movement Date")
