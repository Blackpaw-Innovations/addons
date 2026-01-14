# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    prescription_validity_months = fields.Integer(
        string="Default Prescription Validity (Months)",
        default=12,
        help="Default validity in months for new optical tests when valid_until is not manually set."
    )

    enable_follow_up_reminders = fields.Boolean(
        string="Enable Follow-up Reminders",
        config_parameter="BP_Optical_solution.enable_follow_up_reminders"
    )

    enable_expiry_reminders = fields.Boolean(
        string="Enable Prescription Expiry Reminders",
        config_parameter="BP_Optical_solution.enable_expiry_reminders"
    )

    notification_group_id = fields.Many2one(
        comodel_name="res.groups",
        string="Notification Group",
        help="Users in this group will receive optical reminders (activities)."
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        notification_group_id = int(params.get_param('BP_Optical_solution.notification_group_id', default=0))
        res.update(
            prescription_validity_months=int(params.get_param('BP_Optical_solution.prescription_validity_months', default=12)),
            notification_group_id=notification_group_id if notification_group_id else False,
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('BP_Optical_solution.prescription_validity_months', self.prescription_validity_months or 12)
        params.set_param('BP_Optical_solution.notification_group_id', self.notification_group_id.id or 0)
