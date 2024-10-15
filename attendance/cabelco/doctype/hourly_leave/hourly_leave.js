// Copyright (c) 2021, KCSC and contributors
// For license information, please see license.txt

// frappe.ui.form.on('Hourly Leave', {
// 	 after_save: function(frm) {
//         $.each(frm.doc.employees, function(i, d) {
//           show_alert("Siam")
// 	        frappe.call({
//             method:"masar_hr.masar_hr.doctype.hourly_leave.hourly_leave.defAddAdditionalSalary",
//             args:{
//               employee_no: d.employee_no,
//               salary_component: "Salary Deduction",
//               amount: 20,
//               payroll_date: d.leave_date
//             },
//             callback: function(r){
//             }
//           })
//         })
// 	      }
//       });

frappe.ui.form.on("Hourly Leave", "refresh", function (frm) {
  if (frm.doc.docstatus == 1) {
    frm.add_custom_button(__("Cancel Leave Entry"), function () {
      frappe.call({
        method: "cancel_leave_leadger_entry",
        doc: frm.doc,
        callback: function (r) {
          frm.refresh();
        },
      });
    });
  }
});
frappe.ui.form.on("Hourly Leave", "to_time", function (frm, cdt, cdn) {
  var z = locals[cdt][cdn];

  if (z.from_time && z.to_time) {
    var start = moment(z.from_time, "HH:mm");
    var end = moment(z.to_time, "HH:mm");
    var minutes = end.diff(start, "minutes");
    var hours = minutes / 60;
    frappe.model.set_value(cdt, cdn, "duration", hours);
  }
});

frappe.ui.form.on("Hourly Leave", "from_time", function (frm, cdt, cdn) {
  var z = locals[cdt][cdn];

  if (z.from_time && z.to_time) {
    var start = moment(z.from_time, "HH:mm");
    var end = moment(z.to_time, "HH:mm");
    var minutes = end.diff(start, "minutes");
    var hours = minutes / 60;
    frappe.model.set_value(cdt, cdn, "duration", hours);
  }
});

frappe.ui.form.on(
  "Hourly Leave Employee",
  "employees_add",
  function (frm, cdt, cdn) {
    var d = locals[cdt][cdn];
    if (frm.doc.transaction_date) {
      d.leave_date = frm.doc.transaction_date;
    }
  }
);
