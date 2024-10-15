// Copyright (c) 2021, Peter Maged and contributors
// For license information, please see license.txt

frappe.ui.form.on("Permission Application", {
  refresh: function (frm) {
    // frm.events.set_total_minutes(frm);
  },

  from_time: function (frm) {
    frm.events.set_total_minutes(frm);
  },

  to_time: function (frm) {
    frm.events.set_total_minutes(frm);
  },

  set_total_minutes(frm) {
    if (frm.doc.from_time && frm.doc.to_time) {
      frappe.call({
        doc: frm.doc,
        method: "set_total_minutes",
        callback: function (r) {
          frm.refresh_field("total_minutes");
          frm.refresh_field("to_time");
          frm.refresh_field("from_time");
        },
      });
    }
  },
});
