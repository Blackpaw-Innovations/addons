# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class BarberConsumableSuggestion(models.TransientModel):
    _name = 'bp.barber.consumable.suggestion'
    _description = 'Barber Consumable Replenishment Suggestion'
    _order = 'barber_id, product_id'

    barber_id = fields.Many2one(
        'bp.barber.barber',
        string='Barber',
        required=True
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )
    
    on_hand = fields.Float(
        string='On Hand',
        digits='Product Unit of Measure',
        help="Current stock/balance for this barber"
    )
    
    min_qty = fields.Float(
        string='Min Quantity',
        digits='Product Unit of Measure'
    )
    
    target_qty = fields.Float(
        string='Target Quantity',
        digits='Product Unit of Measure'
    )
    
    suggest_qty = fields.Float(
        string='Suggested Qty',
        digits='Product Unit of Measure',
        help="Suggested quantity to issue"
    )
    
    avg_daily_usage = fields.Float(
        string='Avg Daily Usage',
        digits='Product Unit of Measure'
    )
    
    days_to_empty = fields.Float(
        string='Days to Empty',
        digits=(16, 1),
        help="Days until stock runs out at current usage rate"
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('dismissed', 'Dismissed')
    ], string='State', default='draft')
    
    # Related fields for display
    barber_name = fields.Char(
        string='Barber Name',
        # related='barber_id.name',  # DISABLED to prevent _unknown object errors
        readonly=True
    )
    
    product_name = fields.Char(
        string='Product Name',
        # related='product_id.name',  # DISABLED to prevent _unknown object errors
        readonly=True
    )
    
    uom_name = fields.Char(
        string='UoM',
        # related='product_id.uom_id.name',  # DISABLED to prevent _unknown object errors
        readonly=True
    )
    
    # Status indicators
    is_below_min = fields.Boolean(
        string='Below Minimum',
        compute='_compute_status_indicators'
    )
    
    is_urgent = fields.Boolean(
        string='Urgent',
        compute='_compute_status_indicators',
        help="Less than 3 days of stock remaining"
    )
    
    # @api.depends('on_hand', 'min_qty', 'days_to_empty')
    def _compute_status_indicators(self):
        """DISABLED to prevent _unknown object errors"""
        for record in self:
            record.is_below_min = False
            record.is_urgent = False
    
    def action_issue_suggested(self):
        """Open issue wizard with suggested quantities"""
        self.ensure_one()
        
        if self.suggest_qty <= 0:
            raise UserError(_('No quantity to issue for %s') % self.product_name)
        
        # Create issue wizard with this suggestion
        wizard = self.env['bp.barber.consumable.issue.wizard'].create({
            'barber_id': self.barber_id.id,
            'note': f"Replenishment suggestion for {self.product_name}",
            'line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'qty': self.suggest_qty,
                'uom_id': self.product_id.uom_id.id,
            })]
        })
        
        # Mark as issued
        self.state = 'issued'
        
        return {
            'name': _('Issue Consumables'),
            'type': 'ir.actions.act_window',
            'res_model': 'bp.barber.consumable.issue.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }
    
    def action_dismiss(self):
        """Dismiss this suggestion"""
        self.state = 'dismissed'
    
    @classmethod
    def generate_suggestions(cls, env, barber_ids=None):
        """Generate replenishment suggestions"""
        domain = [('company_id', '=', env.company.id)]
        if barber_ids:
            domain.append(('barber_id', 'in', barber_ids))
        
        # Get all supply profiles
        supply_profiles = env['bp.barber.barber.supply'].search(domain)
        
        suggestions = []
        
        for profile in supply_profiles:
            # Get current balance
            current_balance = profile.get_current_balance()
            
            # Calculate average daily usage
            avg_daily_usage = cls._calculate_avg_daily_usage(
                env, profile.barber_id, profile.product_id
            )
            
            # Calculate days to empty
            if avg_daily_usage > 0:
                days_to_empty = current_balance / avg_daily_usage
            else:
                days_to_empty = 999.0
            
            # Calculate suggested quantity
            suggest_qty = max(0, profile.target_qty - current_balance)
            
            # Only suggest if below minimum or low on days
            if (current_balance < profile.min_qty or 
                (days_to_empty <= 7.0 and suggest_qty > 0)):
                
                suggestion = {
                    'barber_id': profile.barber_id.id,
                    'product_id': profile.product_id.id,
                    'on_hand': current_balance,
                    'min_qty': profile.min_qty,
                    'target_qty': profile.target_qty,
                    'suggest_qty': suggest_qty,
                    'avg_daily_usage': avg_daily_usage,
                    'days_to_empty': days_to_empty,
                }
                
                suggestions.append(suggestion)
        
        return suggestions
    
    @classmethod
    def _calculate_avg_daily_usage(cls, env, barber, product):
        """Calculate average daily usage over last 30 days"""
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        usage_lines = env['bp.barber.consumable.usage.line'].search([
            ('usage_id.barber_id', '=', barber.id),
            ('product_id', '=', product.id),
            ('usage_id.date', '>=', thirty_days_ago),
            ('usage_id.state', '=', 'done')
        ])
        
        total_consumed = sum(line.qty for line in usage_lines)
        return total_consumed / 30.0


class BarberConsumableReplenishmentWizard(models.TransientModel):
    _name = 'bp.barber.consumable.replenishment.wizard'
    _description = 'Generate Replenishment Suggestions'

    barber_ids = fields.Many2many(
        'bp.barber.barber',
        string='Barbers',
        help="Leave empty to include all barbers"
    )
    
    include_all_products = fields.Boolean(
        string='Include All Products',
        default=False,
        help="Include products without supply profiles but with recent usage"
    )
    
    days_threshold = fields.Integer(
        string='Days Threshold',
        default=7,
        help="Include items with less than X days of stock"
    )
    
    def action_generate_suggestions(self):
        """Generate and show replenishment suggestions"""
        # Clear existing suggestions for this user
        self.env['bp.barber.consumable.suggestion'].search([
            ('create_uid', '=', self.env.uid)
        ]).unlink()
        
        # Generate new suggestions
        barber_ids = self.barber_ids.ids if self.barber_ids else None
        suggestions_data = self.env['bp.barber.consumable.suggestion'].generate_suggestions(
            self.env, barber_ids
        )
        
        # Create suggestion records
        suggestions = []
        for data in suggestions_data:
            if data['days_to_empty'] <= self.days_threshold or data['on_hand'] < data['min_qty']:
                suggestion = self.env['bp.barber.consumable.suggestion'].create(data)
                suggestions.append(suggestion.id)
        
        if not suggestions:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Suggestions'),
                    'message': _('No replenishment suggestions were generated based on current criteria.'),
                    'type': 'info',
                }
            }
        
        # Return action to show suggestions
        return {
            'name': _('Replenishment Suggestions'),
            'type': 'ir.actions.act_window',
            'res_model': 'bp.barber.consumable.suggestion',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', suggestions)],
            'context': {'search_default_group_barber': 1},
        }


class BarberConsumableReportWizard(models.TransientModel):
    _name = 'bp.barber.consumable.report.wizard'
    _description = 'Consumable Usage Report'

    date_from = fields.Date(
        string='Date From',
        default=lambda self: fields.Date.today().replace(day=1),
        required=True
    )
    
    date_to = fields.Date(
        string='Date To',
        default=fields.Date.today,
        required=True
    )
    
    barber_ids = fields.Many2many(
        'bp.barber.barber',
        string='Barbers'
    )
    
    product_ids = fields.Many2many(
        'product.product',
        string='Products',
        domain=[('type', 'in', ['consu', 'product'])]
    )
    
    report_type = fields.Selection([
        ('summary', 'Summary'),
        ('detailed', 'Detailed')
    ], string='Report Type', default='summary', required=True)
    
    def action_generate_report(self):
        """Generate consumption report"""
        domain = [
            ('usage_id.date', '>=', self.date_from),
            ('usage_id.date', '<=', self.date_to),
            ('usage_id.state', '=', 'done')
        ]
        
        if self.barber_ids:
            domain.append(('usage_id.barber_id', 'in', self.barber_ids.ids))
        
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        
        usage_lines = self.env['bp.barber.consumable.usage.line'].search(domain)
        
        return {
            'name': _('Consumable Usage Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'bp.barber.consumable.usage.line',
            'view_mode': 'tree,pivot,graph',
            'domain': [('id', 'in', usage_lines.ids)],
            'context': {
                'search_default_group_barber': 1,
                'search_default_group_product': 1,
            }
        }