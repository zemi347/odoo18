# -*- coding: utf-8 -*-


from odoo import fields, models,tools,api

class pos_config(models.Model):
    _inherit = 'pos.config' 
    
    allow_pos_fake_report = fields.Boolean("Allow Pos Fake Report")
    pos_fake_report_percentage = fields.Float("Understated Percentage")
    pos_fake_report_days = fields.Selection([('Monday', 'Monday'),
                                             ('Tuesday', 'Tuesday'),
                                             ('Wednesday', 'Wednesday'),
                                             ('Thursday', 'Thursday'),
                                             ('Friday', 'Friday'),
                                             ('Saturday', 'Saturday'),
                                             ('Sunday', 'Sunday')], string='Fake Report Days')

class PosFakeReportDay(models.Model):
    _name = "pos.fake.report.day"
    _order = "value"
    _description = "POS Understated Days"

    name = fields.Selection([('Monday', 'Monday'),
                             ('Tuesday', 'Tuesday'),
                             ('Wednesday', 'Wednesday'),
                             ('Thursday', 'Thursday'),
                             ('Friday', 'Friday'),
                             ('Saturday', 'Saturday'),
                             ('Sunday', 'Sunday')], required=True, string='Day')
    value = fields.Float("Under-stated Value", required=True)
    active = fields.Boolean("Active", default=True, help="If the active field is set to false, it will ignore the record and pick the global under-state value.")

    @api.model
    def name_create(self, name):
        result = super().create({"name": name, "value": float(name)})
        return result.name_get()[0]

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    allow_pos_fake_report = fields.Boolean("Allow Pos Fake Report")
    pos_fake_report_percentage = fields.Float("Global Under-stated Value (%)")
    # default_understated_days_ids = fields.Many2many('pos.fake.report.day', string="Under-stated days")

    @api.model
    def get_values(self):
        """get values from the fields"""
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo().get_param
        allow_pos_fake_report = params('pos_fake_report.allow_pos_fake_report')
        pos_fake_report_percentage = params('pos_fake_report.pos_fake_report_percentage')
        # default_understated_days_ids = params('pos_fake_report.default_understated_days_ids')
        res.update(
            allow_pos_fake_report=allow_pos_fake_report,
            pos_fake_report_percentage=pos_fake_report_percentage
        )
        return res

    def set_values(self):
        """Set values in the fields"""
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('pos_fake_report.allow_pos_fake_report', self.allow_pos_fake_report)
        self.env['ir.config_parameter'].sudo().set_param('pos_fake_report.pos_fake_report_percentage', self.pos_fake_report_percentage)
        # self.env['ir.config_parameter'].with_context({'default_model': self._name}).sudo().set_param('pos_fake_report.default_understated_days_ids', self.default_understated_days_ids)

    