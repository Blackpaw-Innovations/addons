from odoo import models, fields

class MigrationDataType(models.Model):
    _name = 'migration.data.type'
    _description = 'Migration Data Type'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    color = fields.Integer(string='Color')

class StaffTracking(models.Model):
    _name = 'migration.staff.tracking'
    _description = 'Staff Tracking'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    color = fields.Integer(string='Color')


class Inefficiency(models.Model):
    _name = 'migration.inefficiency'
    _description = 'Inefficiency'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    color = fields.Integer(string='Color')


class DataFormat(models.Model):
    _name = 'migration.data.format'
    _description = 'Data Format'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    color = fields.Integer(string='Color')

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    migration_data_type_ids = fields.Many2many(
        'migration.data.type',
        'crm_lead_migration_data_type_rel',
        'lead_id',
        'type_id',
        string='Migration Data Types'
    )

    staff_tracking_ids = fields.Many2many(
        'migration.staff.tracking',
        'crm_lead_staff_tracking_rel',
        'lead_id',
        'tracking_id',
        string='Staff Tracking'
    )

    inefficiency_ids = fields.Many2many(
        'migration.inefficiency',
        'crm_lead_inefficiency_rel',
        'lead_id',
        'inefficiency_id',
        string='Inefficiencies'
    )

    data_format_ids = fields.Many2many(
        'migration.data.format',
        'crm_lead_data_format_rel',
        'lead_id',
        'format_id',
        string='Data Formats'
    )
