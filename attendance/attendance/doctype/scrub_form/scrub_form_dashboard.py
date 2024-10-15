from __future__ import unicode_literals


def get_data(data=''):
	return {
		'fieldname': 'scrub_form',
		'non_standard_fieldnames': {
			'Additional Salary': 'ref_docname',
		},
		'transactions': [
   			{
				'label': '',
				'items': ['Additional Salary']
			},
   			{
				'label': '',
				'items': ['Stock Entry']
			}
		]
	}
