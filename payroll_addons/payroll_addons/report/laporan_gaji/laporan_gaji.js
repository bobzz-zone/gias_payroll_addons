// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Laporan Gaji"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("In Date From"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "cabang",
			"label": __("Cabang"),
			"fieldtype": "Link",
			"options": "Branch",
			"reqd": 1
		}
	]
};