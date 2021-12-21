// Copyright (c) 2016, w and contributors
// For license information, please see license.txt
/* eslint-disable */

/*frappe.query_reports["Custom Salary Slip"] = {
	"filters": [
		{
			"fieldname":"month",
			"label": __("Month"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1,
			"width": "60px"
		},
		{
			"fieldname":"year",
			"label": __("Year"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1,
			"width": "60px"
		}
	]
};*/

var bulan = function(){
	var b = ''
	var tanggal = frappe.datetime.get_today()
	var pisah = tanggal.split('-');
	// frappe.msgprint(pisah[1])
	if(pisah[1] == '01'){
		b = 'Januari'
	}
	if(pisah[1] == '02'){
		b = 'Februari'
	}
	if(pisah[1] == '03'){
		b = 'Maret'
	}
	if(pisah[1] == '04'){
		b = 'April'
	}
	if(pisah[1] == '05'){
		b = 'Mei'
	}
	if(pisah[1] == '06'){
		b = 'Juni'
	}
	if(pisah[1] == '07'){
		b = 'Juli'
	}
	if(pisah[1] == '08'){
		b = 'Agustus'
	}
	if(pisah[1] == '09'){
		b = 'September'
	}
	if(pisah[1] == '10'){
		b = 'Oktober'
	}
	if(pisah[1] == '11'){
		b = 'November'
	}
	if(pisah[1] == '12'){
		b = 'Desember'
	}
	return b
}

frappe.query_reports["Rekap Transfer Gaji"] = {
	"filters": [
		{
		   "fieldname": "month",
		   "fieldtype": "Select",
		   "label": "Month",
		   "mandatory": 0,
		   "options": "Januari\nFebruari\nMaret\nApril\nMei\nJuni\nJuli\nAgustus\nSeptember\nOktober\nNovember\nDesember",
		   "default": bulan(),
		   "reqd": 1,
		   "wildcard_filter": 0
		},
		  {
		   "fieldname": "year",
		   "fieldtype": "Data",
		   "label": "Year",
		   "default": frappe.defaults.get_user_default("fiscal_year"),
		   "reqd": 1,
		   "wildcard_filter": 0
		}
	]
};
