# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OpticalLensType(models.Model):
    _name = "optical.lens.type"
    _description = "Optical Lens Type"

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code")
    active = fields.Boolean(string="Active", default=True)
    note = fields.Text(string="Note")


class OpticalCoating(models.Model):
    _name = "optical.coating"
    _description = "Optical Coating"

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code")
    active = fields.Boolean(string="Active", default=True)
    note = fields.Text(string="Note")


class OpticalIndex(models.Model):
    _name = "optical.index"
    _description = "Optical Index"

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code")
    active = fields.Boolean(string="Active", default=True)
    note = fields.Text(string="Note")


class OpticalMaterial(models.Model):
    _name = "optical.material"
    _description = "Optical Material"

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code")
    active = fields.Boolean(string="Active", default=True)
    note = fields.Text(string="Note")


class OpticalOptician(models.Model):
    _name = "optical.optician"
    _description = "Optician / Optometrist"

    name = fields.Char(string="Name", required=True)
    user_id = fields.Many2one(comodel_name="res.users", string="Related User")
    branch_id = fields.Many2one(comodel_name="optical.branch", string="Default Branch")
    allowed_branch_ids = fields.Many2many(
        "optical.branch",
        "optical_branch_optician_rel",
        "optician_id",
        "branch_id",
        string="Allowed Branches",
        help="Branches this optician is allowed to access."
    )
    active = fields.Boolean(string="Active", default=True)
    note = fields.Text(string="Note")


class OpticalPrescriptionStage(models.Model):
    _name = "optical.prescription.stage"
    _description = "Optical Prescription Stage"
    _order = "sequence, id"

    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(string="Sequence", default=10)
    fold = fields.Boolean(string="Folded in Kanban", default=False)
    is_final = fields.Boolean(string="Is Final Stage", default=False)


class OpticalBranch(models.Model):
    _name = "optical.branch"
    _description = "Optical Branch"

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code")
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        help="Analytic account used for financial reporting for this branch."
    )
    optician_ids = fields.Many2many(
        "optical.optician",
        "optical_branch_optician_rel",
        "branch_id",
        "optician_id",
        string="Assigned Opticians",
        help="Opticians who are allowed to access and create data for this branch."
    )
    user_ids = fields.Many2many(
        "res.users",
        "optical_branch_user_rel",
        "branch_id",
        "user_id",
        string="Assigned Users",
        help="Users who are allowed to access data for this branch (Patients, Tests, etc.)."
    )
    manager_id = fields.Many2one(
        "res.users",
        string="Branch Manager",
        domain="[('share', '=', False)]",
        help="Manager responsible for this branch. Has full access to branch data."
    )
    active = fields.Boolean(string="Active", default=True)
    note = fields.Text(string="Note")


class OpticalInsuranceCompany(models.Model):
    _name = "optical.insurance.company"
    _description = "Optical Insurance Company"

    name = fields.Char(string="Name", required=True)
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        help="Linked contact for accounting and communication."
    )
    code = fields.Char(string="Code")
    active = fields.Boolean(string="Active", default=True)
    note = fields.Text(string="Note")

    @api.model
    def _ensure_partner(self, insurance_company_id):
        """
        Ensure the insurance company has a partner record.
        Auto-creates one if it doesn't exist.
        Returns the partner record.
        """
        insurance_company = self.browse(insurance_company_id)
        if not insurance_company.partner_id:
            # Create partner for insurance company
            partner_vals = {
                'name': insurance_company.name,
                'company_type': 'company',
                'is_company': True,
                'customer_rank': 0,
                'supplier_rank': 0,
                'comment': 'Auto-created partner for optical insurance company',
            }
            partner = self.env['res.partner'].create(partner_vals)
            insurance_company.write({'partner_id': partner.id})
        
        return insurance_company.partner_id


class OpticalAddRecord(models.Model):
    _name = "optical.add_record"
    _description = "ADD Record"
    _order = "sequence, id"

    name = fields.Char(string="Name", required=True)
    value = fields.Float(string="ADD Value", digits=(4, 2))
    sequence = fields.Integer(string="Sequence", default=10)


class OpticalSphCylRecord(models.Model):
    _name = "optical.sph_cyl_record"
    _description = "Sphere/Cylinder Record"
    _order = "sphere_value, cylinder_value, id"

    name = fields.Char(string="Name", required=True)
    sphere_value = fields.Float(string="Sphere", digits=(4, 2))
    cylinder_value = fields.Float(string="Cylinder", digits=(4, 2))
    is_sphere_only = fields.Boolean(string="Sphere Only", default=False)
    sequence = fields.Integer(string="Sequence", default=10)


class OpticalAxisRecord(models.Model):
    _name = "optical.axis_record"
    _description = "Axis Record"
    _order = "axis_value, id"

    name = fields.Char(string="Name", required=True)
    axis_value = fields.Integer(string="Axis", help="0 to 180")
    sequence = fields.Integer(string="Sequence", default=10)


class OpticalSymptom(models.Model):
    _name = "optical.symptom"
    _description = "Optical Symptom"

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code")
    description = fields.Text(string="Description")


class OpticalPrescriptionTemplate(models.Model):
    _name = "optical.prescription.template"
    _description = "Optical Prescription Template"

    name = fields.Char(string="Name", required=True)
    description = fields.Text(string="Description")
    sphere_od = fields.Float(string="Sphere OD", digits=(4, 2))
    cylinder_od = fields.Float(string="Cylinder OD", digits=(4, 2))
    axis_od = fields.Float(string="Axis OD")
    add_od = fields.Float(string="Add OD", digits=(4, 2))
    sphere_os = fields.Float(string="Sphere OS", digits=(4, 2))
    cylinder_os = fields.Float(string="Cylinder OS", digits=(4, 2))
    axis_os = fields.Float(string="Axis OS")
    add_os = fields.Float(string="Add OS", digits=(4, 2))


class OpticalHeightRecord(models.Model):
    _name = "optical.height_record"
    _description = "Height Record"
    _order = "value, id"

    name = fields.Char(string="Name", required=True)
    value = fields.Float(string="Height", digits=(6, 2))
    sequence = fields.Integer(string="Sequence", default=10)


class OpticalPdRecord(models.Model):
    _name = "optical.pd_record"
    _description = "PD Record"

    name = fields.Char(string="Name", required=True)
    pd_binocular = fields.Float(string="PD Binocular", digits=(4, 1))
    pd_od = fields.Float(string="PD OD", digits=(4, 1))
    pd_os = fields.Float(string="PD OS", digits=(4, 1))
