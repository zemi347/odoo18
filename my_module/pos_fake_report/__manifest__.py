# -*- coding: utf-8 -*-
{
    "name" : "POS Report Fake",
    "version" : "15.0.0.8",
    "category" : "Point of Sale",
    'summary': '',
    "description": """""",
    "author": "Hammad Hussain",
    "website" : "https://www.bazaartech.com",
    "currency": 'EUR',
    "depends" : ['base', 'point_of_sale'],
    "data": [
        'security/ir.model.access.csv',
        'wizard/pos_details.xml',
        'views/point_of_sale_report.xml',
        'views/res_config_settings_views.xml',
        'views/pos_fake_report_days_views.xml'
    ],
    'qweb': [],
    "auto_install": False,
    'license': 'OPL-1',
    "installable": True,
    "live_test_url":'',
    "images":[""],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
