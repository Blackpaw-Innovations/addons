# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import AccessError
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class OpticalTest(models.Model):
    _name = "optical.test"
    _description = "Optical Test"
    _order = "test_date desc, id desc"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Identification & relations
    name = fields.Char(
        string="Test Number",
        required=True,
        readonly=True,
        default="New",
        copy=False
    )
    is_medical_user = fields.Boolean(compute="_compute_is_medical_user")

    @api.depends_context('uid')
    def _compute_is_medical_user(self):
        for record in self:
            user = self.env.user
            # Check if user is linked to an optician or is a manager
            is_optician = self.env['optical.optician'].search_count([('user_id', '=', user.id)]) > 0
            is_manager = user.has_group('BP_Optical_solution.group_optical_manager')
            record.is_medical_user = is_optician or is_manager

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence number and set default stage."""
        if not self.env.user.has_group('BP_Optical_solution.group_optical_manager'):
            is_optician = self.env['optical.optician'].search_count([('user_id', '=', self.env.user.id)]) > 0
            if not is_optician:
                raise AccessError(_("You are not allowed to create Optical Tests. Only Opticians and Optometrists can create tests."))

        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                sequence_date = vals.get('test_date') or fields.Datetime.now()
                sequence_date = fields.Datetime.to_datetime(sequence_date)
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'optical.test',
                    sequence_date=sequence_date,
                ) or 'New'
            
            # Set default stage to Test Room stage if not provided
            if not vals.get('stage_id'):
                test_room_stage = self.env['optical.prescription.stage'].search(
                    [('name', '=', 'Test Room')], limit=1
                )
                if test_room_stage:
                    vals['stage_id'] = test_room_stage.id
        
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.user.has_group('BP_Optical_solution.group_optical_manager'):
            is_optician = self.env['optical.optician'].search_count([('user_id', '=', self.env.user.id)]) > 0
            if not is_optician:
                # Allow writing only to stage_id and tracking fields
                allowed_fields = ['stage_id', 'message_follower_ids', 'activity_ids', 'message_ids']
                if any(field not in allowed_fields for field in vals):
                    raise AccessError(_("You are not allowed to edit Optical Test details. You can only move the test to a different stage."))
        return super().write(vals)

    patient_id = fields.Many2one(
        comodel_name="res.partner",
        string="Patient",
        required=True,
        ondelete="restrict",
        tracking=True
    )
    phone_number = fields.Char(
        string="Phone Number",
        related="patient_id.phone",
        readonly=True,
        store=False
    )
    age = fields.Integer(
        string="Age",
        compute="_compute_age",
        store=False
    )
    validity_until = fields.Date(
        string="Valid Until",
        compute="_compute_validity_until",
        store=True,
        help="Prescription is valid for 2 years from test date"
    )
    optometrist_id = fields.Many2one(
        comodel_name="res.users",
        string="Optometrist",
        tracking=True
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company
    )
    test_date = fields.Datetime(
        string="Test Date",
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )

    def _get_default_branch(self):
        """Get default branch from the current user's linked optician record."""
        if self.env.user:
            optician = self.env['optical.optician'].search([('user_id', '=', self.env.user.id)], limit=1)
            if optician and optician.branch_id:
                return optician.branch_id
        return False

    # Relational fields to config models
    branch_id = fields.Many2one(
        comodel_name="optical.branch",
        string="Branch",
        tracking=True,
        default=_get_default_branch
    )
    stage_id = fields.Many2one(
        comodel_name="optical.prescription.stage",
        string="Stage",
        help="Clinical or workflow stage of this prescription.",
        tracking=True,
        group_expand="_expand_stages"
    )
    is_test_room_stage = fields.Boolean(compute="_compute_stage_state")
    is_fitting_stage = fields.Boolean(compute="_compute_stage_state")
    is_completed_stage = fields.Boolean(compute="_compute_stage_state")
    is_cancelled_stage = fields.Boolean(compute="_compute_stage_state")
    
    @api.depends('stage_id')
    def _compute_stage_state(self):
        for record in self:
            record.is_test_room_stage = record.stage_id.name == 'Test Room'
            record.is_fitting_stage = record.stage_id.name == 'Fitting'
            record.is_completed_stage = record.stage_id.name in ['Completed', 'Collected']
            record.is_cancelled_stage = record.stage_id.name == 'Cancelled'

    is_readonly = fields.Boolean(
        string="Is Readonly",
        compute="_compute_is_readonly",
        store=False
    )
    
    def _get_default_optician(self):
        """Get the optician record linked to the current user."""
        if self.env.user:
            optician = self.env['optical.optician'].search([('user_id', '=', self.env.user.id)], limit=1)
            return optician if optician else False
        return False
    
    optician_id = fields.Many2one(
        comodel_name="optical.optician",
        string="Optician",
        default=_get_default_optician
    )
    workshop_order_number = fields.Char(string="Workshop Order Number")
    needs_new_lens = fields.Boolean(string="Needs New Lens?", default=False)
    needs_new_frame = fields.Boolean(string="Needs new frame?", default=False)
    insurance_company_id = fields.Many2one(
        comodel_name="optical.insurance.company",
        string="Insurance Company",
        help="Insurance provider associated with this test (for billing in POS or external systems)."
    )
    insurance_id = fields.Many2one(
        comodel_name="optical.patient.insurance",
        string="Patient Insurance",
        help="Link this test to a specific patient insurance policy.",
        domain="[('patient_id', '=', patient_id), ('active', '=', True)]"
    )
    patient_insurance_ids = fields.One2many(
        comodel_name="optical.patient.insurance",
        inverse_name="patient_id",
        string="Patient Insurances",
        related="patient_id.insurance_ids",
        readonly=True
    )
    symptom_ids = fields.Many2many(
        comodel_name="optical.symptom",
        relation="optical_test_symptom_rel",
        column1="test_id",
        column2="symptom_id",
        string="Symptoms"
    )
    prescription_template_id = fields.Many2one(
        comodel_name="optical.prescription.template",
        string="Prescription Template"
    )
    pd_record_id = fields.Many2one(
        comodel_name="optical.pd_record",
        string="PD Record"
    )
    height_record_id = fields.Many2one(
        comodel_name="optical.height_record",
        string="Height Record"
    )

    # Follow-up fields
    follow_up_required = fields.Boolean(
        string="Follow-up Required",
        default=False
    )
    follow_up_date = fields.Date(
        string="Follow-up Date"
    )

    # Right Eye (OD) fields
    sphere_od = fields.Float(string="Sphere OD", digits=(4, 2))
    cylinder_od = fields.Float(string="Cylinder OD", digits=(4, 2))
    axis_od = fields.Integer(string="Axis OD")
    prism_od = fields.Float(string="Prism OD", digits=(4, 2))
    add_od = fields.Float(string="Add OD", digits=(4, 2))
    va_od = fields.Char(string="VA OD")
    pd_od = fields.Float(string="PD OD", digits=(4, 1))
    height_od = fields.Float(string="Height OD", digits=(4, 1))

    # Left Eye (OS) fields
    sphere_os = fields.Float(string="Sphere OS", digits=(4, 2))
    cylinder_os = fields.Float(string="Cylinder OS", digits=(4, 2))
    axis_os = fields.Integer(string="Axis OS")
    prism_os = fields.Float(string="Prism OS", digits=(4, 2))
    add_os = fields.Float(string="Add OS", digits=(4, 2))
    va_os = fields.Char(string="VA OS")
    pd_os = fields.Float(string="PD OS", digits=(4, 1))
    height_os = fields.Float(string="Height OS", digits=(4, 1))

    # Previous RX - Right Eye (OD) fields
    prev_sphere_od = fields.Float(string="Previous Sphere OD", digits=(4, 2))
    prev_cylinder_od = fields.Float(string="Previous Cylinder OD", digits=(4, 2))
    prev_axis_od = fields.Integer(string="Previous Axis OD")
    prev_prism_od = fields.Float(string="Previous Prism OD", digits=(4, 2))
    prev_add_od = fields.Float(string="Previous Add OD", digits=(4, 2))
    prev_va_od = fields.Char(string="Previous VA OD")
    prev_pd_od = fields.Float(string="Previous PD OD", digits=(4, 1))
    prev_height_od = fields.Float(string="Previous Height OD", digits=(4, 1))

    # Previous RX - Left Eye (OS) fields
    prev_sphere_os = fields.Float(string="Previous Sphere OS", digits=(4, 2))
    prev_cylinder_os = fields.Float(string="Previous Cylinder OS", digits=(4, 2))
    prev_axis_os = fields.Integer(string="Previous Axis OS")
    prev_prism_os = fields.Float(string="Previous Prism OS", digits=(4, 2))
    prev_add_os = fields.Float(string="Previous Add OS", digits=(4, 2))
    prev_va_os = fields.Char(string="Previous VA OS")
    prev_pd_os = fields.Float(string="Previous PD OS", digits=(4, 1))
    prev_height_os = fields.Float(string="Previous Height OS", digits=(4, 1))

    # Lens and Frame Info
    lens_type_id = fields.Many2one(
        comodel_name="optical.lens.type",
        string="Lens Type"
    )
    coating_id = fields.Many2one(
        comodel_name="optical.coating",
        string="Coating"
    )
    index_id = fields.Many2one(
        comodel_name="optical.index",
        string="Index"
    )
    material_id = fields.Many2one(
        comodel_name="optical.material",
        string="Material"
    )
    frame_id = fields.Many2one(
        comodel_name="product.product",
        string="Frame",
        domain="[('categ_id.name', '=', 'Frame')]"
    )

    # Other
    notes = fields.Text(string="Clinical Notes")

    @api.depends('test_date')
    def _compute_validity_until(self):
        """Compute validity date as 2 years from test date."""
        for record in self:
            if record.test_date:
                record.validity_until = record.test_date + relativedelta(years=2)
            else:
                record.validity_until = False

    @api.depends('patient_id.date_of_birth', 'test_date')
    def _compute_age(self):
        """Calculate age based on patient's date of birth and test date."""
        for record in self:
            if record.patient_id.date_of_birth and record.test_date:
                test_date = record.test_date.date() if isinstance(record.test_date, datetime) else record.test_date
                dob = record.patient_id.date_of_birth
                age_delta = relativedelta(test_date, dob)
                record.age = age_delta.years
            else:
                record.age = 0

    @api.onchange('patient_id')
    def _onchange_patient_id(self):
        """Auto-fill branch from patient when patient is selected."""
        if self.patient_id:
            # Find the optical.patient record linked to this res.partner
            optical_patient = self.env['optical.patient'].search([
                ('partner_id', '=', self.patient_id.id)
            ], limit=1)
            
            if optical_patient and optical_patient.branch_id:
                self.branch_id = optical_patient.branch_id

    def _get_default_valid_until(self, test_date):
        """Calculate default valid_until based on settings."""
        try:
            validity_months = int(self.env['ir.config_parameter'].sudo().get_param(
                'BP_Optical_solution.prescription_validity_months', '12'
            ))
            if validity_months > 0 and test_date:
                if isinstance(test_date, str):
                    test_date = fields.Date.from_string(test_date)
                return test_date + relativedelta(months=validity_months)
        except (ValueError, TypeError):
            pass
        return False

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence number and set default stage."""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('optical.test') or 'New'
            
            # Set default stage to first stage by sequence if not provided
            if not vals.get('stage_id'):
                first_stage = self.env['optical.prescription.stage'].search(
                    [], limit=1, order='sequence asc'
                )
                if first_stage:
                    vals['stage_id'] = first_stage.id
        
        return super().create(vals_list)

    @api.model
    def _expand_stages(self, stages, domain, order):
        """Expand stages for kanban view grouping."""
        return stages.search([], order=order)

    @api.depends('stage_id')
    def _compute_is_readonly(self):
        """Make form read-only after leaving first stage."""
        for record in self:
            if record.stage_id:
                # Get the first stage by sequence
                first_stage = self.env['optical.prescription.stage'].search(
                    [], limit=1, order='sequence asc'
                )
                # If current stage is not the first stage, make it readonly
                if first_stage and record.stage_id.id != first_stage.id:
                    record.is_readonly = True
                else:
                    record.is_readonly = False
            else:
                record.is_readonly = False

    def action_move_to_test_room(self):
        """Move test to Test Room stage."""
        test_room_stage = self.env['optical.prescription.stage'].search(
            [('name', '=', 'Test Room')], limit=1
        )
        if test_room_stage:
            self.write({'stage_id': test_room_stage.id})

    def action_move_to_fitting(self):
        """Move test to Fitting stage."""
        fitting_stage = self.env['optical.prescription.stage'].search(
            [('name', '=', 'Fitting')], limit=1
        )
        if fitting_stage:
            self.write({'stage_id': fitting_stage.id})

    def action_move_to_ready(self):
        """Move test to Ready For collection stage."""
        ready_stage = self.env['optical.prescription.stage'].search(
            [('name', '=', 'Ready For collection')], limit=1
        )
        if ready_stage:
            self.write({'stage_id': ready_stage.id})

    def action_move_to_completed(self):
        """Move test to Completed stage."""
        completed_stage = self.env['optical.prescription.stage'].search(
            [('name', '=', 'Completed')], limit=1
        )
        if completed_stage:
            self.write({'stage_id': completed_stage.id})

    def action_move_to_next_stage(self):
        """Move test to the next stage in sequence."""
        self.ensure_one()
        if not self.stage_id:
            return
        
        # Get the next stage by sequence
        next_stage = self.env['optical.prescription.stage'].search(
            [('sequence', '>', self.stage_id.sequence)],
            order='sequence asc',
            limit=1
        )
        
        if next_stage:
            self.write({'stage_id': next_stage.id})

    def action_done_testing(self):
        """Move test to Fitting stage (Done Testing button)."""
        fitting_stage = self.env['optical.prescription.stage'].search(
            [('name', '=', 'Fitting')], limit=1
        )
        if fitting_stage:
            self.write({'stage_id': fitting_stage.id})

    def action_file(self):
        """Move test to final stage (File button)."""
        final_stage = self.env['optical.prescription.stage'].search(
            [('is_final', '=', True)], limit=1, order='sequence asc'
        )
        if final_stage:
            self.write({'stage_id': final_stage.id})

    @api.model
    def optical_follow_up_reminder_cron(self):
        """Cron job to create follow-up reminders for optical tests."""
        try:
            # Check if follow-up reminders are enabled
            enabled = self.env['ir.config_parameter'].sudo().get_param(
                'BP_Optical_solution.enable_follow_up_reminders', 'False'
            )
            if enabled != 'True':
                return

            # Get notification group
            group_id = self.env['ir.config_parameter'].sudo().get_param(
                'BP_Optical_solution.notification_group_id', False
            )

            # Find tests requiring follow-up in the next 7 days
            today = date.today()
            date_limit = today + timedelta(days=7)
            
            tests = self.sudo().search([
                ('follow_up_required', '=', True),
                ('follow_up_date', '!=', False),
                ('follow_up_date', '<=', date_limit),
                ('follow_up_date', '>=', today)
            ])

            # Get activity type (To Do)
            activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            
            for test in tests:
                # Check if activity already exists for this test
                existing_activity = self.env['mail.activity'].sudo().search([
                    ('res_model', '=', 'optical.test'),
                    ('res_id', '=', test.id),
                    ('summary', 'ilike', 'Optical Follow-up Due')
                ], limit=1)
                
                if existing_activity:
                    continue

                # Determine who should receive the activity
                user_ids = []
                if test.optometrist_id:
                    user_ids.append(test.optometrist_id.id)
                elif group_id:
                    group = self.env['res.groups'].sudo().browse(int(group_id))
                    user_ids = group.users.ids

                # Create activity for each user
                for user_id in user_ids:
                    self.env['mail.activity'].sudo().create({
                        'activity_type_id': activity_type.id if activity_type else False,
                        'res_model_id': self.env['ir.model']._get_id('optical.test'),
                        'res_id': test.id,
                        'user_id': user_id,
                        'summary': 'Optical Follow-up Due',
                        'note': f'Follow-up required for patient {test.patient_id.name} - Test: {test.name}',
                        'date_deadline': test.follow_up_date,
                    })
        except Exception as e:
            # Log error but don't crash
            _logger.error(f"Error in optical follow-up reminder cron: {str(e)}")

    @api.model
    def optical_expiry_reminder_cron(self):
        """Cron job to create expiry reminders for optical prescriptions."""
        try:
            # Check if expiry reminders are enabled
            enabled = self.env['ir.config_parameter'].sudo().get_param(
                'BP_Optical_solution.enable_expiry_reminders', 'False'
            )
            if enabled != 'True':
                return

            # Get notification group
            group_id = self.env['ir.config_parameter'].sudo().get_param(
                'BP_Optical_solution.notification_group_id', False
            )

            # Find tests expiring in the next 7 days
            today = date.today()
            date_limit = today + timedelta(days=7)
            
            tests = self.sudo().search([
                ('validity_until', '!=', False),
                ('validity_until', '<=', date_limit),
                ('validity_until', '>=', today)
            ])

            # Get activity type (To Do)
            activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            
            for test in tests:
                # Check if activity already exists for this test
                existing_activity = self.env['mail.activity'].sudo().search([
                    ('res_model', '=', 'optical.test'),
                    ('res_id', '=', test.id),
                    ('summary', 'ilike', 'Prescription Expiry')
                ], limit=1)
                
                if existing_activity:
                    continue

                # Determine who should receive the activity
                user_ids = []
                if test.optometrist_id:
                    user_ids.append(test.optometrist_id.id)
                elif group_id:
                    group = self.env['res.groups'].sudo().browse(int(group_id))
                    user_ids = group.users.ids

                # Create activity for each user
                for user_id in user_ids:
                    self.env['mail.activity'].sudo().create({
                        'activity_type_id': activity_type.id if activity_type else False,
                        'res_model_id': self.env['ir.model']._get_id('optical.test'),
                        'res_id': test.id,
                        'user_id': user_id,
                        'summary': 'Prescription Expiry Approaching',
                        'note': f'Prescription expiring on {test.validity_until} for patient {test.patient_id.name} - Test: {test.name}',
                        'date_deadline': test.validity_until,
                    })
        except Exception as e:
            # Log error but don't crash
            _logger.error(f"Error in optical expiry reminder cron: {str(e)}")
