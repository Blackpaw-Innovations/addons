# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bp_barber_kiosk_public_enabled = fields.Boolean(
        string='Enable Public Kiosk',
        default=True,
        help='Allow public access to the barber kiosk screen'
    )
    
    bp_barber_kiosk_token = fields.Char(
        string='Access Token',
        help='Optional token for securing public kiosk access. If set, the token must be included in the URL.'
    )
    
    bp_barber_kiosk_refresh_seconds = fields.Integer(
        string='Refresh Interval (seconds)',
        default=10,
        help='How often the kiosk screen refreshes automatically'
    )

    @api.constrains('bp_barber_kiosk_refresh_seconds')
    def _check_refresh_interval(self):
        """Validate refresh interval is within acceptable range"""
        for record in self:
            if record.bp_barber_kiosk_refresh_seconds and (
                record.bp_barber_kiosk_refresh_seconds < 5 or 
                record.bp_barber_kiosk_refresh_seconds > 120
            ):
                raise ValidationError('Refresh interval must be between 5 and 120 seconds.')

    def set_values(self):
        super().set_values()
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        
        IrConfigParameter.set_param(
            'bp_barber_management.kiosk_public_enabled',
            self.bp_barber_kiosk_public_enabled
        )
        IrConfigParameter.set_param(
            'bp_barber_management.kiosk_token',
            self.bp_barber_kiosk_token or ''
        )
        IrConfigParameter.set_param(
            'bp_barber_management.kiosk_refresh_seconds',
            self.bp_barber_kiosk_refresh_seconds
        )

    @api.model
    def get_values(self):
        res = super().get_values()
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        
        res.update({
            'bp_barber_kiosk_public_enabled': IrConfigParameter.get_param(
                'bp_barber_management.kiosk_public_enabled', 
                default=True
            ),
            'bp_barber_kiosk_token': IrConfigParameter.get_param(
                'bp_barber_management.kiosk_token', 
                default=''
            ),
            'bp_barber_kiosk_refresh_seconds': int(IrConfigParameter.get_param(
                'bp_barber_management.kiosk_refresh_seconds', 
                default=10
            )),
        })
        return res


class BarberKioskService(models.AbstractModel):
    """Service class for kiosk data generation"""
    _name = 'bp.barber.kiosk.service'
    _description = 'Barber Kiosk Data Service'

    @api.model
    def get_kiosk_settings(self):
        """Get kiosk configuration settings"""
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        
        return {
            'public_enabled': IrConfigParameter.get_param(
                'bp_barber_management.kiosk_public_enabled', 
                default='True'
            ).lower() == 'true',
            'access_token': IrConfigParameter.get_param(
                'bp_barber_management.kiosk_token', 
                default=''
            ),
            'refresh_seconds': int(IrConfigParameter.get_param(
                'bp_barber_management.kiosk_refresh_seconds', 
                default=10
            )),
        }

    @api.model
    def get_kiosk_data(self, company_id=None, barber_ids=None):
        """
        Generate kiosk data showing current and upcoming appointments
        
        Args:
            company_id: Optional company filter
            barber_ids: Optional list of barber IDs to filter
            
        Returns:
            dict: Structured kiosk data with barber information
        """
        from datetime import datetime, date, timedelta
        import pytz
        
        # Use current company if not specified
        if not company_id:
            company_id = self.env.company.id
            
        # Get today's date range
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        # Build barber domain
        barber_domain = [
            ('active', '=', True),
            ('company_id', '=', company_id)
        ]
        if barber_ids:
            barber_domain.append(('id', 'in', barber_ids))
            
        # Get active barbers
        barbers = self.env['bp.barber.barber'].search(barber_domain, order='name')
        
        result_barbers = []
        current_time = datetime.utcnow()
        
        for barber in barbers:
            # Get current appointment (in_service)
            current_apt = self.env['bp.barber.appointment'].search([
                ('barber_id', '=', barber.id),
                ('state', '=', 'in_service'),
                ('start_datetime', '>=', today_start),
                ('start_datetime', '<=', today_end)
            ], limit=1, order='start_datetime')
            
            # Get next appointments (confirmed, today, future)
            next_apts = self.env['bp.barber.appointment'].search([
                ('barber_id', '=', barber.id),
                ('state', '=', 'confirmed'),
                ('start_datetime', '>=', current_time),
                ('start_datetime', '<=', today_end)
            ], limit=3, order='start_datetime')
            
            # Format current appointment
            now_data = None
            if current_apt:
                services_names = ', '.join(current_apt.service_ids.mapped('name'))
                end_time = current_apt.end_datetime or (
                    current_apt.start_datetime + timedelta(minutes=current_apt.duration_minutes)
                )
                remaining_seconds = (end_time - current_time).total_seconds()
                remaining_min = max(0, int(remaining_seconds / 60))
                
                now_data = {
                    'apt': current_apt.name,
                    'partner': current_apt.partner_id.name if current_apt.partner_id else 'Walk-in',
                    'services': services_names,
                    'start': current_apt.start_datetime.isoformat() + 'Z',
                    'end': end_time.isoformat() + 'Z',
                    'remaining_min': remaining_min
                }
            
            # Format next appointments
            next_data = []
            for apt in next_apts:
                services_names = ', '.join(apt.service_ids.mapped('name'))
                eta_seconds = (apt.start_datetime - current_time).total_seconds()
                eta_min = max(0, int(eta_seconds / 60))
                
                next_data.append({
                    'apt': apt.name,
                    'partner': apt.partner_id.name if apt.partner_id else 'Walk-in',
                    'services': services_names,
                    'start': apt.start_datetime.isoformat() + 'Z',
                    'eta_min': eta_min
                })
            
            # Get chair information
            chair_name = ''
            if barber.chair_ids:
                chair_name = barber.chair_ids[0].name
            
            result_barbers.append({
                'id': barber.id,
                'name': barber.name,
                'color': barber.color or 1,
                'chair': chair_name,
                'now': now_data,
                'next': next_data
            })
        
        return {
            'server_time': current_time.isoformat() + 'Z',
            'barbers': result_barbers
        }