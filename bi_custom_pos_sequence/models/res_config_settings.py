from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_sale_receipt = fields.Boolean(related='pos_config_id.sale_receipt', readonly=False, string='sale receipt')
    pos_sale_receipt_sequence_ids = fields.Many2one(related='pos_config_id.sale_receipt_sequence_ids', readonly=False, string='Set receipt sequence number')
