
from frappe import _


def get_data():
	return {
		'fieldname': 'leave_return_request',
          "internal_links": {"Leave Policy Assignment": "leave_policy_assignment"},

		'transactions': [
			{
				'items': ['Leave Policy Assignment']
			}
		],
    }
