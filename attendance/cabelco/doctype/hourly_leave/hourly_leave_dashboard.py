from __future__ import unicode_literals


def get_data(data=''):
	return {
		'fieldname': 'ref_docname',
		'non_standard_fieldnames': {
			'Additional Salary': 'ref_docname',
			'Leave Ledger Entry': 'reference_name',
		},
		'transactions': [
   			{
				'label': '',
				'items': ['Additional Salary']
			},
   			{
				'label': '',
				'items': ['Leave Ledger Entry']
			},
		]
	}
