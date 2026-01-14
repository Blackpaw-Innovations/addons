# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BarberSchedule(models.Model):
    _name = 'bp.barber.schedule'
    _description = 'Barber Working Hours'
    _order = 'barber_id, weekday, start_time'

    name = fields.Char(
        string='Schedule Name',
        compute='_compute_name',
        store=True
    )
    barber_id = fields.Many2one(
        'bp.barber.barber',
        string='Barber',
        required=True,
        ondelete='cascade',
        index=True
    )
    weekday = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ], string='Weekday', required=True)
    
    start_time = fields.Float(
        string='Start Time',
        required=True,
        help='Start time in hours (e.g., 9.0 for 09:00)'
    )
    end_time = fields.Float(
        string='End Time',
        required=True,
        help='End time in hours (e.g., 17.0 for 17:00)'
    )
    
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        index=True
    )

    _sql_constraints = [
        ('unique_barber_weekday', 'unique (barber_id, weekday, company_id)',
         'A barber can only have one schedule per weekday per company!'),
        ('valid_time_range', 'check (end_time > start_time)',
         'End time must be after start time!')
    ]

    # @api.depends('barber_id', 'weekday', 'start_time', 'end_time')
    def _compute_name(self):
        """DISABLED to prevent _unknown object errors"""
        for record in self:
            record.name = "Schedule"

    @api.constrains('start_time', 'end_time')
    def _check_time_range(self):
        for record in self:
            if record.end_time <= record.start_time:
                raise ValidationError(_('End time must be after start time.'))
            if record.start_time < 0 or record.start_time >= 24:
                raise ValidationError(_('Start time must be between 0.0 and 23.99.'))
            if record.end_time <= 0 or record.end_time > 24:
                raise ValidationError(_('End time must be between 0.01 and 24.0.'))