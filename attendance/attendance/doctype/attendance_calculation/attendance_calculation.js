// Copyright (c) 2021, Peter Maged and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance Calculation", {
  refresh: function (frm) {
    frappe.realtime.on("attendance_calculation_progress", function (data) {
      frappe.hide_msgprint(true);
      frappe.show_progress(data.title, data.count, data.total, data.message);
    });
  },
  calculate(frm) {
    frappe.call({
      method: "calculate_attendance",
      doc: frm.doc,
      freeze:1,
      callback: function () {
        frm.refresh();
        frappe.hide_progress();
        frappe.hide_msgprint(false);
        frappe.msgprint({
          message: __("Done"),
          title: __("Calculation is Done"),
          indicator: "green"
        });
      },
    });
  },

  post_attendance(frm) {
    frappe.call({
      method: "post_attendance",
      doc: frm.doc,
      freeze:1,
      callback: function () {
        frm.refresh();
        frappe.hide_progress();
        frappe.msgprint({
          message: __("Done"),
          title: __("Calculation is Done"),
          indicator: "green"
        });
      },
    });
  },
});
