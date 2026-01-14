# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date


class ResPartnerOptical(models.Model):
    _inherit = "res.partner"

    # Optical patient marker
    is_optical_patient = fields.Boolean(
        string="Optical Patient",
        default=False,
        help="Tick if this contact is an optical patient.",
        copy=False,
        store=True,
        index=True
    )
    date_of_birth = fields.Date(
        string="Date of Birth",
        help="Date of birth used to calculate age in optical tests"
    )

    # Computed statistics fields
    x_last_test_date = fields.Date(
        string="Last Optical Test",
        compute="_compute_optical_stats",
        store=False
    )
    x_test_count = fields.Integer(
        string="Number of Optical Tests",
        compute="_compute_optical_stats",
        store=False
    )
    x_last_optometrist_id = fields.Many2one(
        comodel_name="res.users",
        string="Last Optometrist",
        compute="_compute_optical_stats",
        store=False
    )
    x_active_prescription = fields.Boolean(
        string="Active Prescription",
        compute="_compute_optical_stats",
        store=False
    )
    x_prescription_valid_until = fields.Date(
        string="Prescription Valid Until",
        compute="_compute_optical_stats",
        store=False
    )
    x_follow_up_next_date = fields.Date(
        string="Next Optical Follow-up",
        compute="_compute_optical_stats",
        store=False
    )
    x_insurance_count = fields.Integer(
        string="Number of Insurance Policies",
        compute="_compute_insurance_count",
        store=False
    )
    insurance_ids = fields.One2many(
        comodel_name="optical.patient.insurance",
        inverse_name="patient_id",
        string="Insurance Policies"
    )

    # Clinical notes
    x_optical_notes = fields.Text(string="Optical Notes", copy=False)

    # Gender field
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string="Gender")

    def _compute_optical_stats(self):
        """Compute optical statistics from related optical.test records."""
        for partner in self:
            # Search for optical tests for this patient
            tests = self.env['optical.test'].search(
                [('patient_id', '=', partner.id)],
                order='test_date desc, id desc'
            )

            partner.x_test_count = len(tests)

            if tests:
                latest_test = tests[0]
                partner.x_last_test_date = latest_test.test_date.date() if latest_test.test_date else False
                partner.x_last_optometrist_id = latest_test.optometrist_id.id if latest_test.optometrist_id else False
                partner.x_prescription_valid_until = latest_test.validity_until

                # Check if prescription is active (validity_until is in the future or not set)
                if latest_test.validity_until:
                    partner.x_active_prescription = latest_test.validity_until >= date.today()
                else:
                    # If no expiry date, consider it active
                    partner.x_active_prescription = True

                # Set next follow-up date to the prescription expiry date
                partner.x_follow_up_next_date = latest_test.validity_until
            else:
                # No tests found - reset all fields
                partner.x_last_test_date = False
                partner.x_last_optometrist_id = False
                partner.x_prescription_valid_until = False
                partner.x_active_prescription = False
                partner.x_follow_up_next_date = False

    def _compute_insurance_count(self):
        """Compute number of insurance policies for this patient."""
        for partner in self:
            partner.x_insurance_count = self.env['optical.patient.insurance'].search_count(
                [('patient_id', '=', partner.id)]
            )

    def action_open_optical_tests(self):
        """Open optical tests for this patient."""
        self.ensure_one()
        return {
            'name': 'Optical Tests',
            'type': 'ir.actions.act_window',
            'res_model': 'optical.test',
            'view_mode': 'tree,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {
                'default_patient_id': self.id,
                'search_default_patient_id': self.id,
            },
            'target': 'current',
        }

    def action_open_insurances(self):
        """Open insurance policies for this patient."""
        self.ensure_one()
        return {
            'name': 'Insurance Policies',
            'type': 'ir.actions.act_window',
            'res_model': 'optical.patient.insurance',
            'view_mode': 'tree,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {
                'default_patient_id': self.id,
            },
            'target': 'current',
        }
