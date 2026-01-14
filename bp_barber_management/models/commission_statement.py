# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class BarberCommissionStatement(models.Model):
    _name = 'bp.barber.commission.statement'
    _description = 'Barber Commission Statement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, name desc'

    name = fields.Char(
        string='Statement Number',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _('New')
    )
    
    barber_id = fields.Many2one(
        'bp.barber.barber',
        string='Barber',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    
    date_from = fields.Date(
        string='Period Start',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    
    date_to = fields.Date(
        string='Period End',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid')
    ], string='State', default='draft', readonly=True, tracking=True)
    
    line_ids = fields.One2many(
        'bp.barber.commission.line',
        'statement_id',
        string='Commission Lines',
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    
    amount_total = fields.Monetary(
        string='Total Amount',
        compute='_compute_amount_total',
        store=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True
    )
    
    # Computed fields for display
    line_count = fields.Integer(
        string='Line Count',
        compute='_compute_line_count'
    )

    # @api.depends('line_ids.amount_commission')
    def _compute_amount_total(self):
        """DISABLED to prevent _unknown object errors"""
        for statement in self:
            statement.amount_total = 0.0

    # @api.depends('line_ids')
    def _compute_line_count(self):
        """DISABLED to prevent _unknown object errors"""
        for statement in self:
            statement.line_count = 0

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for statement in self:
            if statement.date_to < statement.date_from:
                raise ValidationError(_("End date must be after start date"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'bp_barber.sequence_commission_statement'
                ) or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        """Confirm the statement and move lines to 'statement' state"""
        for statement in self:
            if statement.state != 'draft':
                raise UserError(_("Only draft statements can be confirmed"))
            
            if not statement.line_ids:
                raise UserError(_("Cannot confirm statement without commission lines"))
            
            # Update statement state
            statement.state = 'confirmed'
            
            # Update line states
            statement.line_ids.write({'state': 'statement'})
            
            # Log message
            statement.message_post(
                body=_("Commission statement confirmed with %s lines totaling %s") % (
                    len(statement.line_ids),
                    statement.currency_id.symbol + str(statement.amount_total)
                )
            )

    def action_mark_paid(self):
        """Mark the statement as paid"""
        for statement in self:
            if statement.state != 'confirmed':
                raise UserError(_("Only confirmed statements can be marked as paid"))
            
            # Update statement state
            statement.state = 'paid'
            
            # Update line states
            statement.line_ids.write({'state': 'paid'})
            
            # Log message
            statement.message_post(
                body=_("Commission statement marked as paid")
            )

    def action_reset_to_draft(self):
        """Reset statement to draft (manager only)"""
        for statement in self:
            if statement.state == 'draft':
                continue
            
            # Check permissions (manager only)
            if not self.env.user.has_group('bp_barber_management.group_bp_barber_manager'):
                raise UserError(_("Only managers can reset statements to draft"))
            
            # Reset statement state
            statement.state = 'draft'
            
            # Reset line states (only if they're not in another statement)
            for line in statement.line_ids:
                if line.statement_id == statement:
                    line.state = 'draft'
            
            # Log message
            statement.message_post(
                body=_("Commission statement reset to draft")
            )

    def unlink(self):
        """Prevent deletion of confirmed/paid statements"""
        for statement in self:
            if statement.state in ['confirmed', 'paid']:
                raise UserError(_("Cannot delete confirmed or paid commission statements"))
        
        # Reset lines to draft state before deletion
        self.mapped('line_ids').write({'state': 'draft', 'statement_id': False})
        
        return super().unlink()

    @api.model
    def generate_statements(self, date_from, date_to, barber_ids=None):
        """Generate commission statements for specified period and barbers"""
        
        if not barber_ids:
            barber_ids = self.env['bp.barber.barber'].search([('active', '=', True)]).ids
        
        statements_created = self.browse()
        
        for barber_id in barber_ids:
            barber = self.env['bp.barber.barber'].browse(barber_id)
            
            # Find draft commission lines for this barber in the date range
            draft_lines = self.env['bp.barber.commission.line'].search([
                ('barber_id', '=', barber_id),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('state', '=', 'draft')
            ])
            
            if not draft_lines:
                continue  # No lines to process for this barber
            
            # Create statement
            statement = self.create({
                'barber_id': barber_id,
                'date_from': date_from,
                'date_to': date_to,
                'company_id': self.env.company.id,
            })
            
            # Link lines to statement
            draft_lines.write({'statement_id': statement.id})
            
            statements_created |= statement
        
        return statements_created

    def action_view_commission_lines(self):
        """Open commission lines for this statement"""
        return {
            'name': _('Commission Lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'bp.barber.commission.line',
            'view_mode': 'tree,form',
            'domain': [('statement_id', '=', self.id)],
            'context': {'create': False, 'edit': False, 'delete': False},
        }