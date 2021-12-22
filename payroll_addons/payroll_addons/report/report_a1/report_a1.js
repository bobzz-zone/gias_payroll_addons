// Copyright (c) 2016, das and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Report A1"] = {
	"filters": [
		{
		   "fieldname": "year",
		   "fieldtype": "Link",
		   "options":"Fiscal Year",
		   "label": "Year",
		   "reqd": 1,
		   "wildcard_filter": 0
		},
		{
		   "fieldname": "branch",
		   "fieldtype": "Link",
		   "options":"Branch",
		   "label": "Cabang",
		   "reqd": 1,
		   "wildcard_filter": 0
		}

	]
};
