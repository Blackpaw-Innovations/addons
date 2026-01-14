from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    lpg_exchange_required = fields.Boolean(
        string="LPG Exchange Required",
        compute="_compute_lpg_exchange_stats",
    )
    lpg_exchange_required_qty = fields.Float(
        string="Required Returned Cylinders",
        compute="_compute_lpg_exchange_stats",
    )
    lpg_exchange_returned_qty = fields.Float(
        string="Returned Cylinders Selected",
        compute="_compute_lpg_exchange_stats",
    )
    lpg_exchange_missing_qty = fields.Float(
        string="Missing Returned Cylinders",
        compute="_compute_lpg_exchange_stats",
    )

    def _compute_lpg_exchange_stats(self):
        for order in self:
            stats = order._get_lpg_exchange_stats()
            order.lpg_exchange_required = stats["required_qty"] > 0
            order.lpg_exchange_required_qty = stats["required_qty"]
            order.lpg_exchange_returned_qty = stats["returned_qty"]
            order.lpg_exchange_missing_qty = stats["missing_qty"]

    def _get_lpg_exchange_stats(self):
        self.ensure_one()
        gas_lines = self.order_line.filtered(
            lambda line: line.product_id.requires_exchange and line.product_id.is_lpg_gas
        )
        cylinder_lines = self.order_line.filtered(
            lambda line: line.product_id.is_lpg_cylinder
        )
        exchange_qty = sum(gas_lines.mapped("product_uom_qty"))
        cylinder_sold_qty = sum(cylinder_lines.mapped("product_uom_qty"))
        required_qty = max(exchange_qty - cylinder_sold_qty, 0.0)
        returned_qty = sum(
            gas_lines.filtered(lambda line: line.returned_cylinder_lot_id).mapped(
                "product_uom_qty"
            )
        )
        missing_qty = max(required_qty - returned_qty, 0.0)
        return {
            "required_qty": required_qty,
            "returned_qty": returned_qty,
            "missing_qty": missing_qty,
        }

    def _check_lpg_exchange(self):
        for order in self:
            gas_lines = order.order_line.filtered(
                lambda line: line.product_id.requires_exchange and line.product_id.is_lpg_gas
            )
            for line in gas_lines:
                if line.product_uom_qty != 1:
                    raise UserError(
                        _(
                            "LPG exchange lines must have quantity 1 so each returned cylinder has a serial."
                        )
                    )
            stats = order._get_lpg_exchange_stats()
            if stats["required_qty"] > 0:
                missing_lines = gas_lines.filtered(lambda line: not line.returned_cylinder_lot_id)
                if missing_lines:
                    raise UserError(
                        _(
                            "Select the returned cylinder serial for each exchange line before confirming the order."
                        )
                    )
            if stats["missing_qty"] > 0:
                raise UserError(
                    _(
                        "Not enough returned cylinders selected for LPG exchange. Please add returned cylinders."
                    )
                )

    def action_confirm(self):
        for order in self:
            order._check_lpg_exchange()
        return super().action_confirm()


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    returned_cylinder_lot_id = fields.Many2one(
        "stock.lot",
        string="Returned Cylinder Serial",
        domain=[("product_id.is_lpg_cylinder", "=", True)],
    )
    lpg_exchange_line = fields.Boolean(
        string="LPG Exchange Line",
        compute="_compute_lpg_exchange_line",
    )

    @api.depends("product_id")
    def _compute_lpg_exchange_line(self):
        for line in self:
            line.lpg_exchange_line = (
                line.product_id.is_lpg_gas and line.product_id.requires_exchange
            )

    @api.constrains("returned_cylinder_lot_id", "product_id")
    def _check_returned_cylinder(self):
        for line in self:
            if line.returned_cylinder_lot_id and not line.returned_cylinder_lot_id.product_id.is_lpg_cylinder:
                raise ValidationError(_("Returned cylinder serial must be an LPG cylinder."))
