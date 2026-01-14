# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Notification settings
    bp_barber_notify_on_confirm = fields.Boolean(
        string='Send Confirmation Email',
        default=True,
        help='Send email when appointment is confirmed'
    )
    
    bp_barber_notify_reminder_enabled = fields.Boolean(
        string='Enable Appointment Reminders',
        default=True,
        help='Send reminder emails before appointments'
    )
    
    bp_barber_notify_reminder_hours_primary = fields.Integer(
        string='Primary Reminder Hours',
        default=24,
        help='Hours before appointment to send first reminder'
    )
    
    bp_barber_notify_reminder_hours_secondary = fields.Integer(
        string='Secondary Reminder Hours',
        default=2,
        help='Hours before appointment to send second reminder (0 = disabled)'
    )
    
    bp_barber_notify_send_ics = fields.Boolean(
        string='Attach Calendar Invite',
        default=True,
        help='Attach ICS calendar file to confirmation emails'
    )
    
    bp_barber_notify_followup_noshow = fields.Boolean(
        string='Send No-Show Follow-up',
        default=True,
        help='Send follow-up email and create activity for no-shows'
    )

    @api.constrains('bp_barber_notify_reminder_hours_primary', 'bp_barber_notify_reminder_hours_secondary')
    def _check_reminder_hours(self):
        """Validate reminder hour settings"""
        for record in self:
            if record.bp_barber_notify_reminder_hours_primary < 1:
                raise ValidationError('Primary reminder hours must be at least 1 hour.')
            
            if (record.bp_barber_notify_reminder_hours_secondary > 0 and 
                record.bp_barber_notify_reminder_hours_secondary >= record.bp_barber_notify_reminder_hours_primary):
                raise ValidationError('Secondary reminder must be fewer hours than primary reminder.')

    def set_values(self):
        super().set_values()
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        
        IrConfigParameter.set_param(
            'bp_barber_management.notify_on_confirm',
            self.bp_barber_notify_on_confirm
        )
        IrConfigParameter.set_param(
            'bp_barber_management.notify_reminder_enabled',
            self.bp_barber_notify_reminder_enabled
        )
        IrConfigParameter.set_param(
            'bp_barber_management.notify_reminder_hours_primary',
            self.bp_barber_notify_reminder_hours_primary
        )
        IrConfigParameter.set_param(
            'bp_barber_management.notify_reminder_hours_secondary',
            self.bp_barber_notify_reminder_hours_secondary
        )
        IrConfigParameter.set_param(
            'bp_barber_management.notify_send_ics',
            self.bp_barber_notify_send_ics
        )
        IrConfigParameter.set_param(
            'bp_barber_management.notify_followup_noshow',
            self.bp_barber_notify_followup_noshow
        )

    @api.model
    def get_values(self):
        res = super().get_values()
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        
        res.update({
            'bp_barber_notify_on_confirm': IrConfigParameter.get_param(
                'bp_barber_management.notify_on_confirm', 
                default='True'
            ).lower() == 'true',
            'bp_barber_notify_reminder_enabled': IrConfigParameter.get_param(
                'bp_barber_management.notify_reminder_enabled', 
                default='True'
            ).lower() == 'true',
            'bp_barber_notify_reminder_hours_primary': int(IrConfigParameter.get_param(
                'bp_barber_management.notify_reminder_hours_primary', 
                default=24
            )),
            'bp_barber_notify_reminder_hours_secondary': int(IrConfigParameter.get_param(
                'bp_barber_management.notify_reminder_hours_secondary', 
                default=2
            )),
            'bp_barber_notify_send_ics': IrConfigParameter.get_param(
                'bp_barber_management.notify_send_ics', 
                default='True'
            ).lower() == 'true',
            'bp_barber_notify_followup_noshow': IrConfigParameter.get_param(
                'bp_barber_management.notify_followup_noshow', 
                default='True'
            ).lower() == 'true',
        })
        return res


class BarberNotificationService(models.AbstractModel):
    """Service class for notification settings"""
    _name = 'bp.barber.notification.service'
    _description = 'Barber Notification Service'

    @api.model
    def get_notification_settings(self):
        """Get notification configuration settings"""
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        
        return {
            'notify_on_confirm': IrConfigParameter.get_param(
                'bp_barber_management.notify_on_confirm', 
                default='True'
            ).lower() == 'true',
            'reminder_enabled': IrConfigParameter.get_param(
                'bp_barber_management.notify_reminder_enabled', 
                default='True'
            ).lower() == 'true',
            'reminder_hours_primary': int(IrConfigParameter.get_param(
                'bp_barber_management.notify_reminder_hours_primary', 
                default=24
            )),
            'reminder_hours_secondary': int(IrConfigParameter.get_param(
                'bp_barber_management.notify_reminder_hours_secondary', 
                default=2
            )),
            'send_ics': IrConfigParameter.get_param(
                'bp_barber_management.notify_send_ics', 
                default='True'
            ).lower() == 'true',
            'followup_noshow': IrConfigParameter.get_param(
                'bp_barber_management.notify_followup_noshow', 
                default='True'
            ).lower() == 'true',
        }