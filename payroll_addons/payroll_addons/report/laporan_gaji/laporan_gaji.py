# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, cstr, flt, fmt_money
from frappe import _, _dict
import datetime
from datetime import date



def execute(filters=None):

	if not filters: filters = {}

	#columns, data = get_column(), get_item(filters)
	columns = get_column()
	data = frappe.db.sql("""select d.salary_component,sum(d.amount) from `tabSalary Detail` d 
			join `tabSalary Slip` s on s.name = d.parent 
			where d.parenttype="Salary Slip" and s.start_date>="{}" and end_date<="{}" and branch="{}" and s.docstatus=1 group by salary_component 
		""".format(filters.get('from_date'),filters.get('to_date'),filters.get('cabang')))
	return columns, data

def get_conditions(filters):
	conditions = []
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	branch = filters.get("cabang")

	return filters

def get_item(filters):
	allItem = []
	allItemData = []
	data = []
	salary_slip = frappe.db.get_all('Salary Slip', {
					'start_date': ['>=', filters["from_date"] ],
					'end_date': ['<=', filters["to_date"]],
					'branch': filters['cabang'],
					"docstatus": 1
				}, ["*"])
	all_salary_component = frappe.db.get_all('Salary Component',{}, ["name"])
	all_salary_component_data = []

	for h in all_salary_component:
		all_salary_component_data.append({
			"name": h['name'],
			"total": 0
		})

	total_gross_pay = 0
	total_loan_payment = 0
	total_deductive = 0
	total_net_pay = 0

	for i in salary_slip: 

		salary_detail = frappe.db.get_all('Salary Detail', { "parent": i['name']}, ["*"])

		total_gross_pay = total_gross_pay + i['gross_pay']
		total_loan_payment = total_loan_payment + i['total_loan_repayment']
		total_deductive = total_deductive + i['total_deduction']
		total_net_pay = total_net_pay + i['net_pay']

		for j in salary_detail:
			for f in all_salary_component_data:
				if j['salary_component'] == f['name']:
					f['total'] = f['total'] + j['amount']

	for p in all_salary_component_data:
		data.append({
			'salary_component' : p['name'],
			'total_amount': p['total']
		})
	data.append({'salary_component':"Gross Pay", 'total_amount':total_gross_pay})
	data.append({'salary_component':"Loan Payment", 'total_amount':total_loan_payment})
	data.append({'salary_component':"Total Deductive", 'total_amount':total_deductive})
	data.append({'salary_component':"Net Pay", 'total_amount':total_net_pay})
	return data

def get_column():
	columns = [
		{
			"fieldname": "salary_component",
			"label": "Salary Component",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "total_amount",
			"label": "Total Amount",
			"fieldtype": "Currency",
			"width": 200
			}
		]
	return columns
