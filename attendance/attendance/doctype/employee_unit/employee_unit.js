// Copyright (c) 2023, Peter Maged and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Unit', {
  // refresh: function(frm) {

  // }
  setup(frm) {
    frm.set_query('department', function () {
      return {
        filters: {
          is_group: 0,
        },
      };
    });
  },
});
