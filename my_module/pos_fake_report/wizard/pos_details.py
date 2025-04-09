# -*- coding: utf-8 -*-
from itertools import groupby
from operator import itemgetter

from odoo import api, fields, models, _
from odoo.osv.expression import AND
import pytz
from datetime import timedelta
from collections import defaultdict

days_map = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6}

class PosDetails(models.TransientModel):
    _name = 'pos.details.wizard.fake'
    _description = 'Point of Sale Details Report Fake'

    def _default_start_date(self):
        """ Find the earliest start_date of the latests sessions """
        # restrict to configs available to the user
        config_ids = self.env['pos.config'].search([]).ids
        # exclude configs has not been opened for 2 days
        self.env.cr.execute("""
            SELECT
            max(start_at) as start,
            config_id
            FROM pos_session
            WHERE config_id = ANY(%s)
            AND start_at > (NOW() - INTERVAL '2 DAYS')
            GROUP BY config_id
        """, (config_ids,))
        latest_start_dates = [res['start'] for res in self.env.cr.dictfetchall()]
        # earliest of the latest sessions
        return latest_start_dates and min(latest_start_dates) or fields.Datetime.now()

    start_date = fields.Datetime(required=True, default=_default_start_date)
    end_date = fields.Datetime(required=True, default=fields.Datetime.now)
    pos_config_ids = fields.Many2many('pos.config', 'pos_detail_fake_configs',
        default=lambda s: s.env['pos.config'].search([]))

    @api.onchange('start_date')
    def _onchange_start_date(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            self.end_date = self.start_date

    @api.onchange('end_date')
    def _onchange_end_date(self):
        if self.end_date and self.end_date < self.start_date:
            self.start_date = self.end_date

    def generate_report(self):
        data = {'date_start': self.start_date, 'date_stop': self.end_date, 'config_ids': self.pos_config_ids.ids}
        return self.env.ref('pos_fake_report.sale_details_report_fake').report_action([], data=data)

class ReportSaleDetails(models.AbstractModel):

    _inherit = 'report.point_of_sale.report_saledetails'
    _description = 'Point of Sale Details Fake'


    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False):
        """ Serialise the orders of the requested time period, configs and sessions.

        :param date_start: The dateTime to start, default today 00:00:00.
        :type date_start: str.
        :param date_stop: The dateTime to stop, default date_start + 23:59:59.
        :type date_stop: str.
        :param config_ids: Pos Config id's to include.
        :type config_ids: list of numbers.
        :param session_ids: Pos Config id's to include.
        :type session_ids: list of numbers.

        :returns: dict -- Serialised sales.
        """

        if self.env.context['active_model'] != 'pos.details.wizard.fake':
            return super(ReportSaleDetails, self).get_sale_details(date_start, date_stop, config_ids, session_ids)

        domain = [('state', 'in', ['paid','invoiced','done'])]
        fake_report = self.env['ir.config_parameter'].sudo().get_param('pos_fake_report.allow_pos_fake_report')

        if (session_ids):
            domain = AND([domain, [('session_id', 'in', session_ids)]])
        else:
            if date_start:
                date_start = fields.Datetime.from_string(date_start)
            else:
                # start by default today 00:00:00
                user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
                today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
                date_start = today.astimezone(pytz.timezone('UTC'))

            if date_stop:
                date_stop = fields.Datetime.from_string(date_stop)
                # avoid a date_stop smaller than date_start
                if (date_stop < date_start):
                    date_stop = date_start + timedelta(days=1, seconds=-1)
            else:
                # stop by default today 23:59:59
                date_stop = date_start + timedelta(days=1, seconds=-1)

            domain = AND([domain,
                [('date_order', '>=', fields.Datetime.to_string(date_start)),
                ('date_order', '<=', fields.Datetime.to_string(date_stop))]
            ])

            if config_ids:
                domain = AND([domain, [('config_id', 'in', config_ids)]])

        orders = self.env['pos.order'].search(domain)

        user_currency = self.env.company.currency_id

        total = 0.0
        products_sold = {}
        taxes = {}
        for order in orders:
            if user_currency != order.pricelist_id.currency_id:
                total += order.pricelist_id.currency_id._convert(
                    order.amount_total, user_currency, order.company_id, order.date_order or fields.Date.today())
            else:
                total += not fake_report and order.amount_total or self.understate_amount(order.date_order, order.amount_total)
            currency = order.session_id.currency_id

            for line in order.lines:
                key = (
                    line.product_id,
                    not fake_report and line.price_unit or self.understate_amount(order.date_order, line.price_unit),
                    not fake_report and line.discount or self.understate_amount(order.date_order, line.discount)
                )
                products_sold.setdefault(key, 0.0)
                products_sold[key] += line.qty

                if line.tax_ids_after_fiscal_position:
                    line_taxes = line.tax_ids_after_fiscal_position.sudo().compute_all(line.price_unit * (1-(line.discount or 0.0)/100.0), currency, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)
                    for tax in line_taxes['taxes']:
                        taxes.setdefault(tax['id'], {'name': tax['name'], 'tax_amount':0.0, 'base_amount':0.0})
                        taxes[tax['id']]['tax_amount'] += not fake_report and tax['amount'] or self.understate_amount(order.date_order, tax['amount'])
                        taxes[tax['id']]['base_amount'] += not fake_report and tax['base'] or self.understate_amount(order.date_order, tax['base'])
                else:
                    taxes.setdefault(0, {'name': _('No Taxes'), 'tax_amount':0.0, 'base_amount':0.0})
                    taxes[0]['base_amount'] += not fake_report and line.price_subtotal_incl or self.understate_amount(order.date_order, line.price_subtotal_incl)

        payment_ids = self.env["pos.payment"].search([('pos_order_id', 'in', orders.ids)]).ids
        if payment_ids:
            self.env.cr.execute("""
                SELECT method.name, o.date_order, sum(amount) total
                FROM pos_payment AS payment,
                     pos_payment_method AS method,
                     pos_order AS o
                WHERE payment.payment_method_id = method.id
                    AND o.id = payment.pos_order_id
                    AND payment.id IN %s
                GROUP BY method.name, o.date_order
            """, (tuple(payment_ids),))
            payments = self.env.cr.dictfetchall()
        else:
            payments = []

        if fake_report and payments:
            payments.sort(key=itemgetter('name'))
            payments = [{'name': key, 'total': sum(self.understate_amount(item['date_order'], item['total']) for item in group)}
                                for key, group in groupby(payments, key=itemgetter('name'))]

        return {
            'currency_precision': user_currency.decimal_places,
            'total_paid': user_currency.round(total),
            'payments': payments,
            'company_name': self.env.company.name,
            'taxes': list(taxes.values()),
            'products': sorted([{
                'product_id': product.id,
                'product_name': product.name,
                'code': product.default_code,
                'quantity': qty,
                'price_unit': price_unit,
                'discount': discount,
                'uom': product.uom_id.name
            } for (product, price_unit, discount), qty in products_sold.items()], key=lambda l: l['product_name'])
        }

    def understate_amount(self, order_date, amount):

        default_value = self.env['ir.config_parameter'].sudo().get_param('pos_fake_report.pos_fake_report_percentage')
        days = self.env['pos.fake.report.day'].sudo().search_read([('active', '=', True)])
        values_map = defaultdict(lambda: 0)

        if not days:
            return float(default_value) != 0 and amount - amount * float(default_value) or amount

        for day in days:
            values_map[days_map[day['name']]] = day['value']
        return amount - amount * values_map[order_date.weekday()]

