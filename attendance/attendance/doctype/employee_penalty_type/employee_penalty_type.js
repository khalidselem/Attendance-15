// Copyright (c) 2021, Peter Maged and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Penalty Type', {
	// refresh: function(frm) {

	// }
	setup: function (frm) {
		frm.set_query("salary_component", function () {
			return {
				filters: {
					type: "deduction"
				}
			}
		});
	}
});
