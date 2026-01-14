# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OpticalPatient(models.Model):
    _name = "optical.patient"
    _description = "Optical Patient"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "name"

    # Basic Information
    name = fields.Char(string="Name", required=True, tracking=True)
    phone = fields.Char(string="Phone", required=True, tracking=True)
    mobile = fields.Char(string="Mobile", tracking=True)
    email = fields.Char(string="Email", tracking=True)
    date_of_birth = fields.Date(string="Date of Birth", tracking=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string="Gender", tracking=True)
    active = fields.Boolean(string="Active", default=True)
    
    def _get_default_branch(self):
        """Get default branch from the current user's linked optician record."""
        if self.env.user:
            optician = self.env['optical.optician'].search([('user_id', '=', self.env.user.id)], limit=1)
            if optician and optician.branch_id:
                return optician.branch_id
        return False
    
    branch_id = fields.Many2one(
        comodel_name="optical.branch",
        string="Branch",
        required=True,
        tracking=True,
        default=_get_default_branch
    )
    has_insurance = fields.Boolean(string="Has Insurance?", default=False, tracking=True)
    
    # Timeline filter
    timeline_period = fields.Selection([
        ('today', 'Today'),
        ('week', 'This Week'),
        ('month', 'This Month'),
        ('year', 'This Year'),
    ], string="Timeline", compute="_compute_timeline_period", store=False, search="_search_timeline_period")

    # Link to res.partner
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Related Contact",
        readonly=True,
        ondelete="cascade"
    )

    # Optical Information (from res.partner)
    is_optical_patient = fields.Boolean(related="partner_id.is_optical_patient", store=True)
    x_last_test_date = fields.Date(related="partner_id.x_last_test_date", string="Last Test Date")
    x_test_count = fields.Integer(related="partner_id.x_test_count", string="Total Tests")
    x_last_optometrist_id = fields.Many2one(related="partner_id.x_last_optometrist_id", string="Last Optometrist")
    x_active_prescription = fields.Boolean(related="partner_id.x_active_prescription", string="Active Prescription")
    x_prescription_valid_until = fields.Date(related="partner_id.x_prescription_valid_until", string="Prescription Valid Until")
    x_follow_up_next_date = fields.Date(related="partner_id.x_follow_up_next_date", string="Next Follow-up")
    x_optical_notes = fields.Text(related="partner_id.x_optical_notes", string="Optical Notes", readonly=False)

    # Insurance
    insurance_ids = fields.One2many(related="partner_id.insurance_ids", string="Insurance Records", readonly=False)
    x_insurance_count = fields.Integer(related="partner_id.x_insurance_count", string="Insurance Count")
    insurance_company_ids = fields.Many2many(
        comodel_name="optical.insurance.company",
        string="Insurance Companies",
        compute="_compute_insurance_companies",
        store=True
    )

    # Smart buttons count
    test_count = fields.Integer(compute="_compute_test_count", string="Tests")
    meeting_count = fields.Integer(compute="_compute_meeting_count", string="Meetings")
    sale_order_count = fields.Integer(compute="_compute_sale_order_count", string="Sales")
    purchase_order_count = fields.Integer(compute="_compute_purchase_order_count", string="Purchases")

    @api.depends('partner_id')
    def _compute_test_count(self):
        for patient in self:
            if patient.partner_id:
                patient.test_count = self.env['optical.test'].search_count([
                    ('patient_id', '=', patient.partner_id.id)
                ])
            else:
                patient.test_count = 0

    @api.depends('insurance_ids', 'insurance_ids.insurance_company_id')
    def _compute_insurance_companies(self):
        for patient in self:
            if patient.insurance_ids:
                patient.insurance_company_ids = patient.insurance_ids.mapped('insurance_company_id')
            else:
                patient.insurance_company_ids = False

    def _compute_timeline_period(self):
        """Dummy compute method - timeline is only used for search"""
        for patient in self:
            patient.timeline_period = False

    def _search_timeline_period(self, operator, value):
        """Search method for timeline filter based on creation date"""
        from datetime import datetime, timedelta
        
        today = fields.Date.context_today(self)
        
        if value == 'today':
            domain = [('create_date', '>=', today)]
        elif value == 'week':
            week_start = today - timedelta(days=today.weekday())
            domain = [('create_date', '>=', week_start)]
        elif value == 'month':
            month_start = today.replace(day=1)
            domain = [('create_date', '>=', month_start)]
        elif value == 'year':
            year_start = today.replace(month=1, day=1)
            domain = [('create_date', '>=', year_start)]
        else:
            domain = []
        
        return domain

    @api.depends('partner_id')
    def _compute_meeting_count(self):
        for patient in self:
            if patient.partner_id:
                patient.meeting_count = self.env['calendar.event'].search_count([
                    ('partner_ids', 'in', patient.partner_id.id)
                ])
            else:
                patient.meeting_count = 0

    @api.depends('partner_id')
    def _compute_sale_order_count(self):
        for patient in self:
            if patient.partner_id:
                patient.sale_order_count = self.env['sale.order'].search_count([
                    ('partner_id', '=', patient.partner_id.id)
                ])
            else:
                patient.sale_order_count = 0

    @api.depends('partner_id')
    def _compute_purchase_order_count(self):
        for patient in self:
            if patient.partner_id:
                patient.purchase_order_count = self.env['purchase.order'].search_count([
                    ('partner_id', '=', patient.partner_id.id)
                ])
            else:
                patient.purchase_order_count = 0

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to sync with res.partner."""
        patients = super().create(vals_list)
        for patient in patients:
            # Create or update partner
            partner_vals = patient._prepare_partner_vals()
            if not patient.partner_id:
                partner = self.env['res.partner'].create(partner_vals)
                patient.partner_id = partner.id
            else:
                patient.partner_id.write(partner_vals)
        return patients

    def write(self, vals):
        """Override write to sync with res.partner."""
        res = super().write(vals)
        # Check if any synced fields were updated
        sync_fields = ['name', 'phone', 'mobile', 'email', 'date_of_birth', 'gender', 'active']
        if any(field in vals for field in sync_fields):
            for patient in self:
                if patient.partner_id:
                    partner_vals = patient._prepare_partner_vals()
                    patient.partner_id.write(partner_vals)
        return res

    def _prepare_partner_vals(self):
        """Prepare values to sync with res.partner."""
        return {
            'name': self.name,
            'phone': self.phone,
            'mobile': self.mobile,
            'email': self.email,
            'date_of_birth': self.date_of_birth,
            'gender': self.gender,
            'is_optical_patient': True,
            'active': self.active,
        }

    def action_open_optical_tests(self):
        """Open optical tests for this patient."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Optical Tests',
            'res_model': 'optical.test',
            'view_mode': 'tree,form',
            'domain': [('patient_id', '=', self.partner_id.id)],
            'context': {'default_patient_id': self.partner_id.id}
        }

    def action_open_insurances(self):
        """Open insurance records for this patient."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Insurance Records',
            'res_model': 'optical.patient.insurance',
            'view_mode': 'tree,form',
            'domain': [('patient_id', '=', self.partner_id.id)],
            'context': {'default_patient_id': self.partner_id.id}
        }

    def action_open_meetings(self):
        """Open meetings for this patient."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Meetings',
            'res_model': 'calendar.event',
            'view_mode': 'tree,form',
            'domain': [('partner_ids', 'in', self.partner_id.id)],
            'context': {'default_partner_ids': [self.partner_id.id]}
        }

    def action_open_sales(self):
        """Open sales orders for this patient."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Orders',
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.partner_id.id)],
            'context': {'default_partner_id': self.partner_id.id}
        }

    def action_open_purchases(self):
        """Open purchase orders for this patient."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Orders',
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.partner_id.id)],
            'context': {'default_partner_id': self.partner_id.id}
        }
