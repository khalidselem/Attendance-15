// Copyright (c) 2022, Peter Maged and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Penalty', {
	refresh: function (frm) {

	},
	factor: function (frm) {
		frm.events.set_penalty_amount(frm);
	},
	penalty_amount: function (frm) {
		frm.events.set_penalty_amount(frm);
	},
	penalty_type: function (frm) {
		frm.events.set_penalty_amount(frm);
	},
	employee: function (frm) {
		frm.events.set_penalty_amount(frm);
	},
	penalty_date: function (frm) {
		frm.events.set_penalty_amount(frm);
	},
	payroll_effect_date: function (frm) {
		frm.events.set_penalty_amount(frm);
	},
	set_penalty_amount(frm) {
		frm.call({
			method: "set_penalty_details",
			doc: frm.doc,
			callback: function (r) {
				frm.refresh_fields(["factor", "penalty_amount", "current_time", "previous_times", "penalty_type", "employee"])
			}
		})
	}
});
