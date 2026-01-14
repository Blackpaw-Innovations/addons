# -*- coding: utf-8 -*-
# Part of BP Optical POS. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_optical_pos = fields.Boolean(
        string="Enable Optical POS",
        config_parameter="BP_Optical_solution.enable_optical_pos",
        help="Toggle POS features for optical.",
    )
    enable_pos_pay_invoice = fields.Boolean(
        string="Enable POS Pay Invoice",
        config_parameter="BP_Optical_solution.enable_pos_pay_invoice",
        help="Toggle POS invoice payment features.",
    )

    def action_manage_branch_users(self):
        """ Open the branch list view to manage user assignments """
        return {
            'name': 'Manage Branch Users',
            'type': 'ir.actions.act_window',
            'res_model': 'optical.branch',
            'view_mode': 'tree,form',
            'target': 'current',
            'help': """<p class="o_view_nocontent_smiling_face">
                Create your first branch
            </p>"""
        }
