// Copyright (c) 2023, Peter Maged and contributors
// For license information, please see license.txt

frappe.ui.form.on("Scrub Form", {
  onload: function (frm) {
    if (frm.is_new()) {
      frm.events.get_default_settings(frm);
    }
  },
  refresh: function (frm) {
    if (frm.doc.docstatus == 1) {
      if (frm.doc.status == "New") {
        frm.events.create_stock_entry(frm);
      }
      if (frm.doc.status == "Delivered") {
        frm.events.return_additional_salary(frm);
      }

    }
  },
  get_default_settings: function (frm) {
    frappe.call({
      method: "get_default_settings",
      doc: frm.doc,
      callback: function (r) {
        frm.refresh();
      },
    });
  },
  create_stock_entry: function (frm) {
    frm
      .add_custom_button(
        __("Stock Entry"),
        function () {
          frappe.model.open_mapped_doc({
            method:
              "attendance.attendance.doctype.scrub_form.scrub_form.create_stock_entry",
            frm: frm,
          });
        },
        __("Create")
      )
      .addClass("btn-primary");
  },
  return_additional_salary: function (frm) {
    frm
      .add_custom_button(
        __("Return"),
        function () {
          frappe.model.open_mapped_doc({
            method:
              "attendance.attendance.doctype.scrub_form.scrub_form.return_additional_salary",
            frm: frm,
          });
        },
        __("Create")
      )
      .addClass("btn-primary");
  },
  due_date: function (frm) {
    frm.events.set_return_date(frm);
  },
  months: function (frm) {
    frm.events.set_return_date(frm);
  },
  set_return_date: function (frm) {
    frappe.call({
      method: "set_return_date",
      doc: frm.doc,
      callback: function (r) {
        frm.refresh();
      },
    });
  },
  set_totals: function (frm) {
    frappe.call({
      method: "set_totals",
      doc: frm.doc,
      callback: function (r) {
        frm.refresh_fields(["items", "total_amount"]);
        frm.refresh();
      },
    });
  },
  // refresh: function(frm) {

  // }
});

frappe.ui.form.on("Scrub Form Item", {
  item_code: function (frm, cdt, cdn) {
    frm.events.set_totals(frm);
  },
  qty: function (frm, cdt, cdn) {
    frm.events.set_totals(frm);
  },
  rate: function (frm, cdt, cdn) {
    frm.events.set_totals(frm);
  },
});
