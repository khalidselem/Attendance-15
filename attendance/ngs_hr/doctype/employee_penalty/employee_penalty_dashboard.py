from __future__ import unicode_literals


def get_data(data=''):
    return {
        'fieldname': 'employee_penalty',
        'non_standard_fieldnames': {
            'Additional Salary Slip': 'ref_docname',
        },
        "internal_links": {"Additional Salary": "salary_slip"},

        'transactions': [

            {
                'label': '',
                'items': ['Additional Salary']
            }
        ]
    }
