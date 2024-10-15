// Copyright (c) 2022, Peter Maged and contributors
// For license information, please see license.txt

frappe.ui.form.on("Functional sanctions", {
  // refresh: function(frm) {

  // }
  calculate_period: function (frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    if (row.from_date && row.to_date) {
	if (row.from_date > row.to_date) {
		row.to_date = row.from_date 
	}
      var from_date = new Date(row.from_date);
      var to_date = new Date(row.to_date);
      var period = parseInt((to_date - from_date) / (1000 * 60 * 60 * 24), 10);
      //   var from_date = moment(row.from_date, "M/D/YYYY");
      //   var to_date = moment(row.to_date, "M/D/YYYY");
      //   var period = from_date.diff(to_date, "days");
	  if (period >= 0) {
		period ++ ;
	  }
    //   alert(period);

      row.period = period;
      frm.refresh_field("functional_sanctions");
    }
  },
});

frappe.ui.form.on("Functional sanctions_CH", {
  // refresh: function(frm) {

  // }
  from_date: function (frm, cdt, cdn) {
    frm.events.calculate_period(frm, cdt, cdn);
  },
  to_date: function (frm, cdt, cdn) {
    frm.events.calculate_period(frm, cdt, cdn);
  },
});
