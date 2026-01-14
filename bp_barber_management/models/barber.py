# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Barber(models.Model):
    _name = 'bp.barber.barber'
    _description = 'Barber'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Name', required=True, tracking=True)
    barber_code = fields.Char(
        string='Barber Code', 
        required=True, 
        help='Short code for quick assignment'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        ondelete='set null',
        help="Contact card of the barber"
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        ondelete='set null',
        help="System user if applicable"
    )
    phone = fields.Char(
        string='Phone',
        # related='partner_id.phone',  # DISABLED to prevent _unknown object errors
        store=True,
        readonly=False
    )
    email = fields.Char(
        string='Email',
        # related='partner_id.email',  # DISABLED to prevent _unknown object errors
        store=True,
        readonly=False
    )
    skill_level = fields.Selection([
        ('junior', 'Junior'),
        ('mid', 'Mid'),
        ('senior', 'Senior')
    ], string='Skill Level', default='mid', tracking=True)
    
    chair_id = fields.Many2one(
        'bp.barber.chair',
        string='Chair',
        ondelete='set null',
        domain="[('active', '=', True)]",
        tracking=True,
        required=False
    )
    color = fields.Integer(string='Color')
    active = fields.Boolean(string='Active', default=True, tracking=True)
    note = fields.Html(string='Notes')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        index=True
    )
    
    # Schedule relationship
    schedule_ids = fields.One2many(
        'bp.barber.schedule',
        'barber_id',
        string='Working Hours'
    )

    _sql_constraints = [
        ('unique_barber_code_company', 'unique (barber_code, company_id)',
         'Barber code must be unique per company!')
    ]

    @api.constrains('barber_code', 'company_id')
    def _check_unique_barber_code_company(self):
        for record in self:
            if record.barber_code and record.company_id:
                existing = self.search([
                    ('barber_code', '=', record.barber_code),
                    ('company_id', '=', record.company_id.id),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_('Barber code "%s" already exists in company "%s"') % (record.barber_code, record.company_id.name))

    # Temporarily disabled to fix _unknown object error
    # @api.onchange('partner_id')
    # def _onchange_partner_id(self):
    #     try:
    #         if self.partner_id and self.partner_id.name and not self._origin.name:
    #             self.name = self.partner_id.name
    #     except:
    #         # If there's any error accessing partner data, do nothing
    #         pass
    pass

    @api.model
    def _fix_invalid_references(self):
        """Fix barbers with invalid chair_id or company_id references"""
        # Fix chair references
        all_barbers = self.search([])
        for barber in all_barbers:
            try:
                # Try to access the chair to see if it exists
                if barber.chair_id:
                    _ = barber.chair_id.name
            except:
                # If accessing chair fails, set to None
                barber.chair_id = False
                
            try:
                # Try to access the company to see if it exists
                if barber.company_id:
                    _ = barber.company_id.name
            except:
                # If accessing company fails, set to default company
                barber.company_id = self.env.company.id

    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.barber_code}] {record.name}"
            result.append((record.id, name))
        return result

    # Commission fields removed
    
    # Consumable fields (Stage 11)
    usage_log_count = fields.Integer(
        string='Usage Logs',
        compute='_compute_consumable_counts'
    )
    
    # Service tracking fields for POS statistics
    pos_orders_count = fields.Integer(
        string='POS Orders',
        compute='_compute_service_statistics'
    )
    
    services_today_count = fields.Integer(
        string='Services Today',
        compute='_compute_service_statistics'
    )
    
    services_week_count = fields.Integer(
        string='Services This Week',
        compute='_compute_service_statistics'
    )
    
    services_month_count = fields.Integer(
        string='Services This Month',
        compute='_compute_service_statistics'
    )
    
    revenue_today = fields.Monetary(
        string='Revenue Today',
        compute='_compute_service_statistics',
        currency_field='company_currency_id'
    )
    
    revenue_week = fields.Monetary(
        string='Revenue This Week',
        compute='_compute_service_statistics',
        currency_field='company_currency_id'
    )
    
    revenue_month = fields.Monetary(
        string='Revenue This Month',
        compute='_compute_service_statistics',
        currency_field='company_currency_id'
    )
    
    company_currency_id = fields.Many2one(
        'res.currency',
        # related='company_id.currency_id',  # DISABLED to prevent _unknown object errors
        readonly=True
    )
    
    def _compute_consumable_counts(self):
        """Compute consumable-related counts"""
        for barber in self:
            barber.usage_log_count = self.env['bp.barber.consumable.usage'].search_count([
                ('barber_id', '=', barber.id)
            ])
    
    # Commission computation removed
    
    def _compute_service_statistics(self):
        """Compute service statistics from POS orders - DISABLED to prevent _unknown object errors"""
        for barber in self:
            barber.pos_orders_count = 0
            barber.services_today_count = 0
            barber.revenue_today = 0
            barber.services_week_count = 0
            barber.revenue_week = 0
            barber.services_month_count = 0
            barber.revenue_month = 0

    # Commission action methods removed
    
    def action_view_usage_logs(self):
        """Smart button action to view usage logs"""
        return {
            'name': _('Consumable Usage Logs'),
            'type': 'ir.actions.act_window',
            'res_model': 'bp.barber.consumable.usage',
            'view_mode': 'tree,form',
            'domain': [('barber_id', '=', self.id)],
            'context': {'default_barber_id': self.id},
        }
    
    def action_issue_consumables(self):
        """Smart button action to open issue wizard"""
        return {
            'name': _('Issue Consumables'),
            'type': 'ir.actions.act_window',
            'res_model': 'bp.barber.consumable.issue.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_barber_id': self.id},
        }
    
    def action_view_pos_orders(self):
        """View POS orders with this barber's services"""
        return {
            'name': _('POS Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.order',
            'view_mode': 'tree,form',
            'domain': [
                ('lines.barber_id', '=', self.id),
                ('state', 'in', ['paid', 'done', 'invoiced'])
            ],
            'context': {'default_barber_id': self.id},
        }
    
    def action_view_services_today(self):
        """View today's service lines for this barber"""
        from datetime import datetime, date
        today = date.today()
        
        return {
            'name': _('Services Today'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.order.line',
            'view_mode': 'tree,form',
            'domain': [
                ('barber_id', '=', self.id),
                ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
                ('order_id.date_order', '>=', datetime.combine(today, datetime.min.time())),
                ('order_id.date_order', '<', datetime.combine(today, datetime.max.time()))
            ],
            'context': {'default_barber_id': self.id},
        }
    
    def action_view_service_report(self):
        """Open detailed service performance - placeholder for future implementation"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Service Report'),
                'message': _('Detailed reporting features coming soon. Check the Performance tab for current statistics.'),
                'type': 'info',
            }
        }