from __future__ import unicode_literals


def get_data(data=''):
    return {
        'fieldname': 'penalty_type',
        'non_standard_fieldnames': {
            'Leave Ledger Entry': 'reference_name',
        },
        "internal_links": {"Additional Salary": "salary_slip"},

        'transactions': [

            {
                'label': '',
                'items': ['Employee Penalty']
            }
        ]
    }
