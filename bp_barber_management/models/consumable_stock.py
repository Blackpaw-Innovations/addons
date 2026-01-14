# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BarberBarber(models.Model):
    _inherit = 'bp.barber.barber'

    stock_location_id = fields.Many2one(
        'stock.location',
        string='Stock Location',
        domain="[('usage', '=', 'internal'), ('company_id', 'in', [False, company_id])]",
        help="Per-barber location for consumables (created automatically if stock module installed)"
    )
    
    def _get_or_create_stock_location(self):
        """Get or create stock location for this barber"""
        self.ensure_one()
        
        # Check if stock module is installed
        if 'stock' not in self.env.registry._init_modules:
            return None
        
        if self.stock_location_id:
            return self.stock_location_id
        
        # Find or create parent location (main internal location)
        parent_location = self._get_main_internal_location()
        
        # Create barber-specific location
        location_vals = {
            'name': f"BARBER/{self.barber_code or self.name}",
            'usage': 'internal',
            'location_id': parent_location.id,
            'company_id': self.company_id.id,
        }
        
        location = self.env['stock.location'].create(location_vals)
        self.stock_location_id = location.id
        
        return location
    
    def _get_main_internal_location(self):
        """Get the main internal location for the company"""
        # Try to find the main warehouse internal location
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        
        if warehouse:
            return warehouse.lot_stock_id
        
        # Fallback: find any internal location
        internal_location = self.env['stock.location'].search([
            ('usage', '=', 'internal'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        
        if not internal_location:
            raise UserError(_('No internal location found for company %s') % self.company_id.name)
        
        return internal_location


class BarberConsumableUsage(models.Model):
    _inherit = 'bp.barber.consumable.usage'

    def _get_consumption_location(self):
        """Get or create the consumption location"""
        # Check if stock module is installed
        if 'stock' not in self.env.registry._init_modules:
            return None
        
        # Look for existing consumption location
        consumption_location = self.env['stock.location'].search([
            ('name', '=', 'Barber Consumption'),
            ('usage', '=', 'inventory'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        
        if consumption_location:
            return consumption_location
        
        # Create consumption location
        location_vals = {
            'name': 'Barber Consumption',
            'code': 'BARBER-CONS',
            'usage': 'inventory',
            'company_id': self.company_id.id,
        }
        
        return self.env['stock.location'].create(location_vals)


class BarberConsumableIssueWizard(models.TransientModel):
    _name = 'bp.barber.consumable.issue.wizard'
    _description = 'Issue Consumables to Barber'

    barber_id = fields.Many2one(
        'bp.barber.barber',
        string='Barber',
        required=True
    )
    
    line_ids = fields.One2many(
        'bp.barber.consumable.issue.wizard.line',
        'wizard_id',
        string='Products to Issue'
    )
    
    note = fields.Text(
        string='Note',
        help="Additional information about this issuance"
    )
    
    def action_issue(self):
        """Issue products to barber"""
        if not self.line_ids:
            raise UserError(_('Please add at least one product to issue.'))
        
        # Check if stock module is installed
        stock_installed = 'stock' in self.env.registry._init_modules
        
        if stock_installed:
            self._create_stock_transfers()
        else:
            self._create_ledger_issues()
        
        # Post message on barber record
        message = f"Issued consumables:\n"
        for line in self.line_ids:
            message += f"• {line.product_id.name}: {line.qty} {line.uom_id.name}\n"
        
        self.barber_id.message_post(
            body=message,
            subject="Consumables Issued",
            message_type='comment'
        )
        
        return {'type': 'ir.actions.act_window_close'}
    
    def _create_stock_transfers(self):
        """Create stock transfers for issuance"""
        # Ensure barber has stock location
        barber_location = self.barber_id._get_or_create_stock_location()
        
        # Find source location (main internal)
        source_location = self.barber_id._get_main_internal_location()
        
        # Create picking for the transfer
        picking_vals = {
            'picking_type_id': self._get_internal_picking_type().id,
            'location_id': source_location.id,
            'location_dest_id': barber_location.id,
            'origin': f"Issue to {self.barber_id.name}",
        }
        
        picking = self.env['stock.picking'].create(picking_vals)
        
        # Create moves for each line
        for line in self.line_ids:
            if line.qty > 0:
                move_vals = {
                    'name': f"Issue: {line.product_id.name}",
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.qty,
                    'product_uom': line.uom_id.id,
                    'location_id': source_location.id,
                    'location_dest_id': barber_location.id,
                    'picking_id': picking.id,
                    'company_id': self.barber_id.company_id.id,
                }
                
                self.env['stock.move'].create(move_vals)
        
        # Confirm and process the picking
        picking.action_confirm()
        picking.action_assign()
        
        # Set quantities on move lines and validate
        for move in picking.move_ids:
            for move_line in move.move_line_ids:
                move_line.qty_done = move_line.product_uom_qty
        
        picking._action_done()
    
    def _create_ledger_issues(self):
        """Create ledger entries for issuance (fallback)"""
        for line in self.line_ids:
            if line.qty > 0:
                self.env['bp.barber.consumable.ledger'].create({
                    'barber_id': self.barber_id.id,
                    'product_id': line.product_id.id,
                    'move_type': 'issue',
                    'qty': line.qty,
                    'uom_id': line.uom_id.id,
                    'date': fields.Datetime.now(),
                    'origin_note': f"Manual issue: {self.note or 'No note'}",
                    'company_id': self.barber_id.company_id.id,
                })
    
    def _get_internal_picking_type(self):
        """Get internal picking type for transfers"""
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('company_id', '=', self.barber_id.company_id.id)
        ], limit=1)
        
        if not picking_type:
            # Create a basic internal picking type
            picking_type = self.env['stock.picking.type'].create({
                'name': 'Internal Transfers',
                'code': 'internal',
                'sequence_code': 'INT',
                'company_id': self.barber_id.company_id.id,
            })
        
        return picking_type
    
    @api.model
    def default_get(self, fields_list):
        """Set default values"""
        res = super().default_get(fields_list)
        
        # If called from barber context, set the barber
        if self.env.context.get('active_model') == 'bp.barber.barber':
            barber_id = self.env.context.get('active_id')
            if barber_id:
                res['barber_id'] = barber_id
        
        return res


class BarberConsumableIssueWizardLine(models.TransientModel):
    _name = 'bp.barber.consumable.issue.wizard.line'
    _description = 'Issue Wizard Line'

    wizard_id = fields.Many2one(
        'bp.barber.consumable.issue.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain=[('type', 'in', ['consu', 'product'])]
    )
    
    qty = fields.Float(
        string='Quantity',
        required=True,
        default=1.0,
        digits='Product Unit of Measure'
    )
    
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True
    )
    
    # Temporarily disabled to fix _unknown object error
    # @api.onchange('product_id')
    # def _onchange_product_id(self):
    #     """Set default UOM from product"""
    #     try:
    #         if self.product_id and self.product_id.uom_id:
    #             self.uom_id = self.product_id.uom_id
    #         else:
    #             self.uom_id = False
    #     except:
    #         # If there's any error accessing product data, clear UOM
    #         self.uom_id = False