# Copyright (c) 2013, das and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, cstr, flt, fmt_money
from frappe import _, _dict
import datetime
from datetime import date

def execute(filters=None):
	columns, data = [], []
	columns = [
		{
			"fieldname": "employee_id",
			"label": "Employee ID",
			"fieldtype": "Link/Employee",
			"width": 150
		},
		{
			"fieldname": "employee_name",
			"label": "Employee Name",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "gross_pay",
			"label": "Gross Pay",
			"fieldtype": "Currency",
			"width": 200
		},
		{
			"fieldname": "regular",
			"label": "Regular",
			"fieldtype": "Currency",
			"width": 200
		},
		{
			"fieldname": "pph21",
			"label": "PPH21",
			"fieldtype": "Currency",
			"width": 200
		}
	]
	columns=["Employee ID:Link/Employee:150","Employee Name:Data:200","Nomor NPWP:Data:200","Gross Pay:Currency:200","Regular:Currency:200","PPH21:Currency:200"]
	raw_data = frappe.db.sql(""" 
		SELECT 
		ts.employee,ts.`employee_name`,te.nomor_npwp, te.`branch`,
		tsd.`is_tax_applicable`, tsd.`salary_component`, tsd.`statistical_component`,
		tsd.`amount`, tsd.`parentfield`

		FROM `tabSalary Slip` ts
		JOIN `tabEmployee` te ON te.name = ts.`employee`
		JOIN `tabSalary Detail` tsd ON tsd.parent = ts.name
		WHERE
		ts.posting_date >= "{}"
		AND
		ts.posting_date <= "{}"

		AND 
		te.`branch` = "{}"
		AND
		ts.`docstatus` = 1

		ORDER BY ts.`employee` """.format(filters.get("from_date"),filters.get("to_date"),filters.get("cabang")),as_dict=1)

	forbidden_component = ["Potongan Perhitungan Pajak BIJAB","BPJS Di Potongkan Di Akui Pajak"]
	regular_forbidden_component = ["Black Bonus","Komisi","Lembur"]
	temp_employee = []
	for row in raw_data:
		if row.employee not in temp_employee:
			temp_employee.append(row.employee)

	for row in temp_employee:
		employee_id = row
		gross_pay = 0
		regular = 0
		pph21 = 0
		employee_name=""
		no_npwp=""
		for row_raw in raw_data:
			if row_raw.employee == employee_id:
				no_npwp=row_raw.nomor_npwp
				employee_name=row_raw.employee_name
				if row_raw.salary_component == "PPH21":
					pph21 += flt(row_raw.amount)

				elif row_raw.salary_component not in forbidden_component and row_raw.parentfield == "earnings" and str(row_raw.statistical_component) == "0"  and str(row_raw.is_tax_applicable) == "1":
					gross_pay += flt(row_raw.amount)
					if row_raw.salary_component not in regular_forbidden_component:
						regular += flt(row_raw.amount)
				
		data.append([employee_id, employee_name,no_npwp, gross_pay, regular, pph21])


	return columns, data
