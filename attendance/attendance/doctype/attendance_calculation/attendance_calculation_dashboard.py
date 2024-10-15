from __future__ import unicode_literals
from frappe import _


def get_data(data=''):
    return {
        'fieldname': 'attendance_calculation',
        'non_standard_fieldnames': {
            'Leave Ledger Entry': 'reference_name',
        },
        'transactions': [
            {
                'label': '',
                'items': ['Attendance']
            },
            {
                'label': '',
                'items': ['Additional Salary']
            },
            {
                'label': '',
                'items': ['Leave Ledger Entry']
            },
            {
                'label': '',
                'items': ['Employee Penalty']
            }
        ],
        'reports': [
            {
                'label': _('Reports'),
                'items': ['Employee Attendance Details', 'Employee Attendance Summary']
            }
        ]
    }
