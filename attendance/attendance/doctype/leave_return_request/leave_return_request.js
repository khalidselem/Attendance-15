// Copyright (c) 2024, Peter Maged and contributors
// For license information, please see license.txt

frappe.ui.form.on('Leave Return Request', {
	// refresh: function(frm) {

	// } ,
	setup : function(frm) {
		frm.set_query("employee" , function(doc){
			return {
				filters : {
					"is_foreign" : 1 ,
					"status" : "Inactive"
				}
			}
		})
	}
});
