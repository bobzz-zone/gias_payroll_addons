# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from dateutil.relativedelta import relativedelta
from frappe.utils import cint, flt, nowdate, add_days, getdate, fmt_money, add_to_date, DATE_FORMAT, date_diff
from frappe import _
from erpnext.accounts.utils import get_fiscal_year
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
import json 
from erpnext.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry
from datetime import datetime

@frappe.whitelist()
def patch_payroll_entry_grade():
	list_payroll = frappe.db.sql(""" SELECT name FROM `tabPayroll Entry` """)
	for baris in list_payroll:
		doc = frappe.get_doc("Payroll Entry", baris[0])
		for row in doc.employees:
			if row.employee:
				
				row.employee_grade = frappe.get_doc("Employee",row.employee).grade
				row.db_update()

def create_salary_slips_custom(self):
	"""
		Creates salary slip for selected employees if already not created
	"""
	self.check_permission('write')
	self.created = 1
	employees = [emp.employee for emp in self.employees]
	if employees:
		args = frappe._dict({
			"salary_slip_based_on_timesheet": self.salary_slip_based_on_timesheet,
			"payroll_frequency": self.payroll_frequency,
			"start_date": self.start_date,
			"end_date": self.end_date,
			"company": self.company,
			"posting_date": self.posting_date,
			"deduct_tax_for_unclaimed_employee_benefits": self.deduct_tax_for_unclaimed_employee_benefits,
			"deduct_tax_for_unsubmitted_tax_exemption_proof": self.deduct_tax_for_unsubmitted_tax_exemption_proof,
			"payroll_entry": self.name,
			"exchange_rate": self.exchange_rate,
			"currency": self.currency
		})
		if len(employees) > 30:
			frappe.enqueue(create_salary_slips_for_employees, timeout=600, employees=employees, args=args)
		else:
			create_salary_slips_for_employees_custom(employees, args, publish_progress=False)
			# since this method is called via frm.call this doc needs to be updated manually
			self.reload()

def create_salary_slips_for_employees_custom(employees, args, publish_progress=True):
	salary_slips_exists_for = get_existing_salary_slips(employees, args)
	count=0
	for emp in employees:
		if emp not in salary_slips_exists_for:
			args.update({
				"doctype": "Salary Slip",
				"employee": emp
			})
			ss = frappe.get_doc(args)
			date_object_awal = frappe.utils.add_months(frappe.utils.getdate(ss.start_date),-1)
			date_object_akhir =frappe.utils.getdate(ss.start_date)
			
			tanggal_awal = str(frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE field = "tanggal_awal_tunjangan" """)[0][0])
			date_awal = "{}-{}-{}".format(str(date_object_awal).split("-")[0],str(date_object_awal).split("-")[1],tanggal_awal)

			tanggal_akhir = str(frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE field = "tanggal_awal_tunjangan" """)[0][0])
			date_akhir = "{}-{}-{}".format(str(date_object_akhir).split("-")[0],str(date_object_akhir).split("-")[1],tanggal_akhir)
			
			ss.tunjangan_start_date = date_awal
			ss.tunjangan_end_date = date_akhir

			list_status_attendance = frappe.db.sql(""" SELECT status,is_late_included,early_exit_included FROM `tabStatus Attendance` """)
			jumlah_tanggal = 0
			for row_status in list_status_attendance:
				status = row_status[0]
				is_late = row_status[1]
				early_exit = row_status[2]
				query_late = ""
				query_early = ""

				if is_late == 0:
					query_late = " AND late_entry = 0"

				if early_exit == 0:
					query_early = " AND early_exit = 0"
				
				list_count = frappe.db.sql(""" SELECT count(name) FROM `tabAttendance` 
					WHERE status = "{}" {} {} and employee = "{}"
					and attendance_date >= "{}" and attendance_date <= "{}"
				""".format(status,query_late,query_early,ss.employee, date_awal, date_akhir))

				for row_list in list_count:
					jumlah_tanggal = jumlah_tanggal + row_list[0]			

			# get_attendance = frappe.db.sql(""" SELECT work_period, forget_to_checkout, paid_leave, late_count 
			# 	FROM `tabPayroll Employee Detail` WHERE parent = "{}" and employee = "{}" """.format(args.payroll_entry,args.employee))
			
			# if len(get_attendance) > 0:
			# 	ss.work_period = get_attendance[0][0]
			# 	ss.forget_to_checkout = get_attendance[0][1]
			# 	ss.paid_leave = get_attendance[0][2]
			# 	ss.late_count = get_attendance[0][3]
			ss.tunjangan_days = jumlah_tanggal
			
			ss.insert()
			count+=1
			if publish_progress:
				frappe.publish_progress(count*100/len(set(employees) - set(salary_slips_exists_for)),
					title = _("Creating Salary Slips..."))

	payroll_entry = frappe.get_doc("Payroll Entry", args.payroll_entry)
	payroll_entry.db_set("salary_slips_created", 1)
	payroll_entry.notify_update()

def get_existing_salary_slips(employees, args):
	return frappe.db.sql_list("""
		select distinct employee from `tabSalary Slip`
		where docstatus!= 2 and company = %s
			and start_date >= %s and end_date <= %s
			and employee in (%s)
	""" % ('%s', '%s', '%s', ', '.join(['%s']*len(employees))),
		[args.company, args.start_date, args.end_date] + employees)

@frappe.whitelist()
def override_create_slip(doc,method):
	PayrollEntry.create_salary_slips = create_salary_slips_custom

@frappe.whitelist()
def fill_employee_details(self):
	self = frappe.get_doc(json.loads(self))
	self.set('employees', [])
	employees = get_emp_list_custom(self)
	if not employees:
		frappe.throw(_("No employees for the mentioned criteria"))

	for d in employees:
		if d.employee:
			self.append('employees', d)

	self.number_of_employees = len(employees)
	
	if not self.employees:
		frappe.throw(_("No employees for the mentioned criteria"))

	self.save()
	self.reload()

	if self.validate_attendance:
		return self.validate_employee_attendance()

@frappe.whitelist()
def get_emp_list_custom(self):
	"""
		Returns list of active employees based on selected criteria
		and for which salary structure exists
	"""
	condition = ''

	cond = get_filter_condition_custom(self)
	cond += get_joining_relieving_condition_custom(self)

	
	if self.payroll_frequency:
		condition = """and payroll_frequency = '%(payroll_frequency)s'"""% {"payroll_frequency": self.payroll_frequency}

	sal_struct = frappe.db.sql_list("""
			select
				name from `tabSalary Structure`
			where
				docstatus = 1 and
				is_active = 'Yes'
				and company = %(company)s and
				ifnull(salary_slip_based_on_timesheet,0) = %(salary_slip_based_on_timesheet)s
				{condition}""".format(condition=condition),
			{"company": self.company, "salary_slip_based_on_timesheet":self.salary_slip_based_on_timesheet})

	if sal_struct:
		start_date = self.start_date
		end_date = self.end_date
		
		cond += " "
		cond += ""

		emp_list = frappe.db.sql("""
			SELECT DISTINCT t1.name AS employee, t1.employee_name, t1.department, t1.designation, 
				DATEDIFF("{0}",t1.date_of_joining) AS work_period, 
				COUNT(DISTINCT ta1.name) AS late_count, 
				COUNT(DISTINCT ta2.name) AS forget_to_checkout,
				COUNT(DISTINCT ta3.name) AS paid_leave 

				FROM `tabEmployee` t1 LEFT JOIN `tabAttendance` ta1 ON ta1.`employee` = t1.`name` 
				AND ta1.`late_entry` = 1 AND ta1.`status` = "Present" 
				AND ta1.attendance_date >= "{1}" 
				AND ta1.attendance_date <= "{0}"
				 AND ta1.docstatus = 1 
				 LEFT JOIN `tabAttendance` ta2 ON ta2.`employee` = t1.`name` AND ta2.`forgot_to_checkout` = 1 AND ta2.`status` = "Present" 
				 AND ta2.attendance_date >= "{1}" AND ta2.attendance_date <= "{0}" AND ta2.docstatus = 1 
				 AND ta2.docstatus=1
				 LEFT JOIN `tabAttendance` ta3 ON ta3.`employee` = t1.`name` 
				 AND ta3.`status` = "On Leave" AND ta3.attendance_date >= "{1}" 
				 AND ta3.attendance_date <= "{0}" AND ta3.docstatus = 1 
				 AND ta3.leave_type IN (SELECT NAME FROM `tabLeave Type` WHERE is_lwp = 0)
				 AND ta3.docstatus=1
				 ,
				 `tabSalary Structure Assignment` t2 WHERE t1.name = t2.employee AND t2.docstatus = 1 
				AND t2.salary_structure IN {2}
				 AND "{0}" >= t2.from_date 

				 {3}
				 GROUP BY t1.name
				 ORDER BY t2.from_date DESC

		""".format(end_date, start_date, str(sal_struct).replace("[","(").replace("]",")"), cond), as_dict=True)

		return emp_list

def get_filter_condition_custom(self):
	check_mandatory_custom(self)

	cond = ''
	for f in ['company', 'branch', 'department', 'designation']:
		if self.get(f):
			cond += " and t1." + f + " = '" + self.get(f).replace("'", "\'") + "'"

	return cond

def get_joining_relieving_condition_custom(self):
	cond = """
		and ifnull(t1.date_of_joining, '0000-00-00') <= '%(end_date)s'
		and ifnull(t1.relieving_date, '2199-12-31') >= '%(start_date)s'
	""" % {"start_date": self.start_date, "end_date": self.end_date}
	return cond

def check_mandatory_custom(self):
	for fieldname in ['company', 'start_date', 'end_date']:
		if not self.get(fieldname):
			frappe.throw(_("Please set {0}").format(self.meta.get_label(fieldname)))
