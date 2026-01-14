from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_done(self, cancel_backorder=False):
        res = super()._action_done(cancel_backorder=cancel_backorder)
        self._update_lpg_cylinder_lots()
        self._check_lpg_exchange_on_delivery()
        return res

    def _update_lpg_cylinder_lots(self):
        moves = self.filtered(lambda move: move.product_id.is_lpg_cylinder)
        if not moves:
            return
        now = fields.Datetime.now()
        for move in moves:
            picking_partner = move.picking_id.partner_id or move.partner_id
            for line in move.move_line_ids.filtered("lot_id"):
                dest = line.location_dest_id
                source = line.location_id
                vals = {"last_movement_date": now}
                if dest.scrap_location:
                    vals.update({"cylinder_status": "damaged", "current_customer_id": False})
                elif dest.usage == "customer":
                    vals.update(
                        {
                            "cylinder_status": "filled",
                            "current_customer_id": picking_partner,
                        }
                    )
                elif source.usage == "customer" and dest.usage == "internal":
                    vals.update({"cylinder_status": "empty", "current_customer_id": False})
                if vals:
                    line.lot_id.write(vals)

    def _check_lpg_exchange_on_delivery(self):
        orders = self.mapped("picking_id.sale_id")
        if orders:
            orders._check_lpg_exchange()
