from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AppraisalTemplate(models.Model):
    _name = "bp.appraisal.template"
    _description = "Appraisal Template"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
    description = fields.Text()
    question_ids = fields.One2many(
        "bp.appraisal.question", "template_id", string="Questions"
    )
    reviewer_ids = fields.Many2many(
        "res.users",
        "bp_appraisal_template_user_rel",
        "template_id",
        "user_id",
        string="Default Reviewers",
    )

    @api.constrains("name", "company_id")
    def _check_unique_name(self):
        for rec in self:
            exists = self.search(
                [
                    ("name", "=", rec.name),
                    ("company_id", "=", rec.company_id.id),
                    ("id", "!=", rec.id),
                ],
                limit=1,
            )
            if exists:
                raise ValidationError(_("Template name must be unique per company."))


class AppraisalQuestion(models.Model):
    _name = "bp.appraisal.question"
    _description = "Appraisal Question"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    question_type = fields.Selection(
        [
            ("text", "Open Text"),
            ("rating", "Rating 1-5"),
            ("yesno", "Yes / No"),
        ],
        default="text",
        required=True,
    )
    weight = fields.Float(
        default=1.0, help="Relative weight for scoring if ratings are aggregated."
    )
    template_id = fields.Many2one(
        "bp.appraisal.template", required=True, ondelete="cascade"
    )
    help_text = fields.Char(string="Helper Text")
