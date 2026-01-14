# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BarberChair(models.Model):
    _name = 'bp.barber.chair'
    _description = 'Barber Chair'
    _order = 'name'

    name = fields.Char(string='Chair Name', required=True)
    code = fields.Char(string='Chair Code', required=True, help='Short code for quick identification')
    active = fields.Boolean(string='Active', default=True)
    is_available = fields.Boolean(
        string='Available',
        default=True,
        help="If unchecked, the chair is temporarily out of service."
    )
    note = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        index=True,
        ondelete='set null',
        required=False
    )

    _sql_constraints = [
        ('unique_code_company', 'unique (code, company_id)',
         'Chair code must be unique per company!')
    ]

    @api.constrains('code', 'company_id')
    def _check_unique_code_company(self):
        for record in self:
            if record.code and record.company_id:
                existing = self.search([
                    ('code', '=', record.code),
                    ('company_id', '=', record.company_id.id),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_('Chair code "%s" already exists in company "%s"') % (record.code, record.company_id.name))

    @api.model
    def _fix_invalid_references(self):
        """Fix chairs with invalid company_id references"""
        # Find chairs with invalid company references
        chairs_without_company = self.search([('company_id', '=', False)])
        if chairs_without_company:
            # Set default company for chairs without company
            chairs_without_company.write({
                'company_id': self.env.company.id
            })
        
        # Check for chairs with non-existent company references
        all_chairs = self.search([])
        for chair in all_chairs:
            try:
                # Try to access the company to see if it exists
                if chair.company_id:
                    _ = chair.company_id.name
            except:
                # If accessing company fails, set to default company
                chair.company_id = self.env.company.id
    
    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.code}] {record.name}"
            result.append((record.id, name))
        return result