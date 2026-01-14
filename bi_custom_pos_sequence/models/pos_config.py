from odoo import models, fields


class PosConfig(models.Model):
    _inherit = 'pos.config'

    sale_receipt = fields.Boolean(string='sale receipt')
    sale_receipt_sequence_ids = fields.Many2one(
        'ir.sequence', string="Set receipt sequence number")