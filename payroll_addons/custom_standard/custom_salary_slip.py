from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from dateutil.relativedelta import relativedelta
from frappe.utils import cint,cstr, flt, nowdate, add_days, getdate, fmt_money, add_to_date, DATE_FORMAT, date_diff
from frappe import _
from erpnext.accounts.utils import get_fiscal_year
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
import json 
from erpnext.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry
from erpnext.payroll.doctype.salary_slip.salary_slip import SalarySlip
from datetime import datetime
from erpnext.payroll.doctype.additional_salary.additional_salary import get_additional_salaries
from erpnext.payroll.doctype.payroll_period.payroll_period import get_period_factor, get_payroll_period
from erpnext.payroll.doctype.employee_benefit_application.employee_benefit_application import get_benefit_component_amount
from erpnext.payroll.doctype.employee_benefit_claim.employee_benefit_claim import get_benefit_claim_amount, get_last_payroll_period_benefits
from erpnext.loan_management.doctype.loan_repayment.loan_repayment import calculate_amounts, create_repayment_entry
import math
import re
from frappe.model.naming import make_autoname
from calendar import monthrange

@frappe.whitelist()
def autoname_ss(self, method):
	if self.employee:
		self.name = make_autoname("Sal Slip/{0}/.#####".format(self.employee))
	else:
		self.name = make_autoname("Sal Slip/.#####".format(self.employee))
@frappe.whitelist()
def update_umk(self, method):
	frappe.db.sql("""update tabEmployee set umk={} where branch="{}" """.format(self.umk,self.name))

@frappe.whitelist()
def debug():
	sal_slip = frappe.get_doc("Salary Slip","Sal Slip/203050007/00006")
	custom_calculate_net_pay(sal_slip)

@frappe.whitelist()
def cancel_payroll():
	frappe.db.sql(""" UPDATE `tabSalary Structure Assignment` SET workflow_state = "Cancelled" WHERE docstatus = 2 """)

def custom_validate(self):
	self.status = self.get_status()
	self.validate_dates()
	self.check_existing()
	if not self.salary_slip_based_on_timesheet:
		self.get_date_details()

	if not (len(self.get("earnings")) or len(self.get("deductions"))):
		# get details from salary structure
		self.get_emp_and_working_day_details()
	else:
		custom_get_working_days_details(self = self,lwp = self.leave_without_pay)

	custom_calculate_net_pay(self)
	self.compute_year_to_date()
	self.compute_month_to_date()
	self.compute_component_wise_year_to_date()
	self.add_leave_balances()

	if frappe.db.get_single_value("Payroll Settings", "max_working_hours_against_timesheet"):
		max_working_hours = frappe.db.get_single_value("Payroll Settings", "max_working_hours_against_timesheet")
		if self.salary_slip_based_on_timesheet and (self.total_working_hours > int(max_working_hours)):
			frappe.msgprint(_("Total working hours should not be greater than max working hours {0}").
							format(max_working_hours), alert=True)
SalarySlip.validate = custom_validate

def custom_process_salary_structure(self, for_preview=0):
	'''Calculate salary after salary structure details have been updated'''
	if not self.salary_slip_based_on_timesheet:
		self.get_date_details()
	self.pull_emp_details()
	custom_get_working_days_details(self = self,for_preview=for_preview)
	custom_calculate_net_pay(self)
SalarySlip.process_salary_structure = custom_process_salary_structure

def custom_calculate_net_pay(self):
	if self.salary_structure:
		custom_calculate_component_amounts(self,"earnings")
	self.gross_pay = self.get_component_totals("earnings", depends_on_payment_days=1)
	self.base_gross_pay = flt(flt(self.gross_pay) * flt(self.exchange_rate), self.precision('base_gross_pay'))

	if self.salary_structure:
		custom_calculate_component_amounts(self,"deductions")

	self.set_loan_repayment()
	self.set_component_amounts_based_on_payment_days()
	self.set_net_pay()

def custom_calculate_component_amounts(self, component_type):
	if not getattr(self, '_salary_structure_doc', None):
		self._salary_structure_doc = frappe.get_doc('Salary Structure', self.salary_structure)
	payroll_period = get_payroll_period(self.start_date, self.end_date, self.company)

	custom_add_structure_components(self,component_type)
	self.add_additional_salary_components(component_type)
	if component_type == "earnings":
		self.add_employee_benefits(payroll_period)
	else:
		custom_add_tax_components(self,payroll_period)

def custom_add_tax_components(self, payroll_period):
	# Calculate variable_based_on_taxable_salary after all components updated in salary slip
	tax_components, other_deduction_components = [], []
	for d in self._salary_structure_doc.get("deductions"):
		if d.variable_based_on_taxable_salary == 1 and not d.formula and not flt(d.amount):
			tax_components.append(d.salary_component)
		else:
			other_deduction_components.append(d.salary_component)
	if not tax_components:
		tax_components = [d.name for d in frappe.get_all("Salary Component", filters={"variable_based_on_taxable_salary": 1})
			if d.name not in other_deduction_components]
	for d in tax_components:
		tax_amount = custom_calculate_variable_based_on_taxable_salary(self, d, payroll_period)
		tax_row = get_salary_component_data(d)

		# custom chandra
		#if tax_amount < 0:
		#	tax_amount = flt(tax_amount) * -1
		#	self.update_component_row("Adjustment", tax_amount, "earnings")
		#else:
		#disable pph
		if self.salary_structure!="Saldo Awal Oktober":
			self.update_component_row(tax_row, tax_amount, "deductions")

def custom_calculate_variable_based_on_taxable_salary(self, tax_component, payroll_period):
	if not payroll_period:
		frappe.msgprint(_("Start and end dates not in a valid Payroll Period, cannot calculate {0}.")
			.format(tax_component))
		return

	# Deduct taxes forcefully for unsubmitted tax exemption proof and unclaimed benefits in the last period
	if payroll_period.end_date <= getdate(self.end_date):
		self.deduct_tax_for_unsubmitted_tax_exemption_proof = 1
		self.deduct_tax_for_unclaimed_employee_benefits = 1

	return custom_calculate_variable_tax(self,payroll_period, tax_component)

def custom_calculate_variable_tax(self, payroll_period, tax_component):
	# get Tax slab from salary structure assignment for the employee and payroll period
	tax_slab = self.get_income_tax_slabs(payroll_period)

	# get remaining numbers of sub-period (period for which one salary is processed)
	remaining_sub_periods = round(get_period_factor(self.employee,
		self.start_date, self.end_date, self.payroll_frequency, payroll_period,1)[1])
	if remaining_sub_periods>12:
		remaining_sub_periods=12
	# get taxable_earnings, paid_taxes for previous period
	previous_taxable_earnings = self.get_taxable_earnings_for_prev_period(payroll_period.start_date,
		self.start_date, tax_slab.allow_tax_exemption)
	
	previous_total_paid_taxes = self.get_tax_paid_in_period(payroll_period.start_date, self.start_date, tax_component)
	
	# get taxable_earnings for current period (all days)
	current_taxable_earnings = custom_get_taxable_earnings(self,tax_slab.allow_tax_exemption)
	self.notes="SISA PERIOD : {}".format(remaining_sub_periods)
	print("SISA PERIOD : {0}".format(remaining_sub_periods))
	future_structured_taxable_earnings = current_taxable_earnings.taxable_earnings * (math.ceil(remaining_sub_periods) - 1)

	# get taxable_earnings, addition_earnings for current actual payment days
	current_taxable_earnings_for_payment_days = custom_get_taxable_earnings(self,tax_slab.allow_tax_exemption, based_on_payment_days=1)
	current_structured_taxable_earnings = current_taxable_earnings_for_payment_days.taxable_earnings
	current_additional_earnings = current_taxable_earnings_for_payment_days.additional_income
	current_additional_earnings_with_full_tax = current_taxable_earnings_for_payment_days.additional_income_with_full_tax

	# Get taxable unclaimed benefits
	unclaimed_taxable_benefits = 0
	if self.deduct_tax_for_unclaimed_employee_benefits:
		unclaimed_taxable_benefits = self.calculate_unclaimed_taxable_benefits(payroll_period)
		unclaimed_taxable_benefits += current_taxable_earnings_for_payment_days.flexi_benefits

	# Total exemption amount based on tax exemption declaration
	# bobby never used just skipped it
	#total_exemption_amount = self.get_total_exemption_amount(payroll_period, tax_slab)
	total_exemption_amount=0
	#Employee Other Incomes
	other_incomes = self.get_income_form_other_sources(payroll_period) or 0.0

	print("PREV TAXABLE EARNINGS : {0}".format(previous_taxable_earnings))
	print("CURRENT STRUCTURED TAXABLE EARNINGS : {0}".format(current_structured_taxable_earnings))
	print("FUTURE STRUCTURED TAXABLE EARNINGS : {0}".format(future_structured_taxable_earnings))
	print("CURRENT ADDITIONAL EARNINGS : {0}".format(current_additional_earnings))
	print("OTHER INCOMES : {0}".format(other_incomes))
	print("UNCLAIMED TAXABLE BENEFITS : {0}".format(unclaimed_taxable_benefits))
	print("TOTAL EXEMPTION AMOUNT : {0}".format(total_exemption_amount))
	self.notes="{}\nPREV TAXABLE EARNINGS : {}".format(self.notes,previous_taxable_earnings)
	self.notes="{}\nCURRENT STRUCTURED TAXABLE EARNINGS : {}".format(self.notes,current_structured_taxable_earnings)
	self.notes="{}\nFUTURE STRUCTURED TAXABLE EARNINGS : {}".format(self.notes,future_structured_taxable_earnings)
	self.notes="{}\nCURRENT ADDITIONAL EARNINGS : {}".format(self.notes,current_additional_earnings)
	self.notes="{}\nOTHER INCOMES : {}".format(self.notes,other_incomes)
	self.notes="{}\nUNCLAIMED TAXABLE BENEFITS : {}".format(self.notes,unclaimed_taxable_benefits)
	self.notes="{}\nTOTAL EXEMPTION AMOUNT : {}".format(self.notes,total_exemption_amount)
	self.notes="{}\nCurrent Additional Earning With Full Tax : {}".format(self.notes,current_additional_earnings_with_full_tax)
	# Total taxable earnings including additional and other incomes
	total_taxable_earnings = previous_taxable_earnings + current_structured_taxable_earnings + future_structured_taxable_earnings \
		+ current_additional_earnings + other_incomes + unclaimed_taxable_benefits - total_exemption_amount

	print("TOTAL TAXABLE EARNINGS : {0}".format(total_taxable_earnings))

	# Total taxable earnings without additional earnings with full tax
	total_taxable_earnings_without_full_tax_addl_components = total_taxable_earnings - current_additional_earnings_with_full_tax

	print("TOTAL TAXABLE EARNINGS WITHOUT FULL TAX: {0}".format(total_taxable_earnings_without_full_tax_addl_components))
	# Structured tax amount
	total_structured_tax_amount = self.calculate_tax_by_tax_slab(
		total_taxable_earnings_without_full_tax_addl_components, tax_slab)
	current_structured_tax_amount = (total_structured_tax_amount - previous_total_paid_taxes) / remaining_sub_periods

	print("TOTAL STRUCTURED TAX AMOUNT: {0}".format(total_structured_tax_amount))
	print("PREV TOTAL PAID TAXES : {0}".format(previous_total_paid_taxes))
	print("SISA PERIOD : {0}".format(remaining_sub_periods))
	print("(TOTAL STRUCTURED TAX AMOUNT - PREV TOTAL PAID TAXES) / SISA PERIOD : {0}".format(current_structured_tax_amount))
	# Total taxable earnings with additional earnings with full tax
	full_tax_on_additional_earnings = 0.0
	if current_additional_earnings_with_full_tax:
		total_tax_amount = self.calculate_tax_by_tax_slab(total_taxable_earnings, tax_slab)
		print("TOTAL TAX AMOUNT FROM ADD EARNING WITH FULL TAX : {0}".format(total_tax_amount))
		full_tax_on_additional_earnings = total_tax_amount - total_structured_tax_amount

	print("FULL TAX ON ADDITIONAL EARNINGS : {0}".format(full_tax_on_additional_earnings))
	current_tax_amount = current_structured_tax_amount + full_tax_on_additional_earnings

	print("CURRENT TAX AMOUNT : {0}".format(current_tax_amount))

	self.notes="{}\nTOTAL TAXABLE EARNINGS : {}".format(self.notes,total_taxable_earnings)
	self.notes="{}\nTOTAL TAXABLE EARNINGS WITHOUT FULL TAX: {}".format(self.notes,total_taxable_earnings_without_full_tax_addl_components)
	self.notes="{}\nTOTAL STRUCTURED TAX AMOUNT: {}".format(self.notes,total_structured_tax_amount)
	self.notes="{}\nPREV TOTAL PAID TAXES : {}".format(self.notes,previous_total_paid_taxes)
	self.notes="{}\nSISA PERIOD : {}".format(self.notes,remaining_sub_periods)
	self.notes="{}\n(TOTAL STRUCTURED TAX AMOUNT - PREV TOTAL PAID TAXES) / SISA PERIOD : {}".format(self.notes,current_structured_tax_amount)
	self.notes="{}\nFULL TAX ON ADDITIONAL EARNINGS : {}".format(self.notes,full_tax_on_additional_earnings)
	self.notes="{}\nCURRENT TAX AMOUNT : {}".format(self.notes,current_tax_amount)
	# custom chandra
	# if flt(current_tax_amount) < 0:
	# 	current_tax_amount = 0

	return math.floor(current_tax_amount/1000)*1000

def custom_add_structure_components(self, component_type):
	data = self.get_data_for_eval()
	# extra_ontime_present
	# extra_late_present
	# extra_early_exit_present
	# extra_late_early_present

	date_object_awal = frappe.utils.add_months(frappe.utils.getdate(self.start_date),-1)
	date_object_akhir =frappe.utils.getdate(self.start_date)
	
	# tanggal_awal = str(frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE field = "tanggal_awal_tunjangan" """)[0][0])
	# date_awal = "{}-{}-{}".format(str(date_object_awal).split("-")[0],str(date_object_awal).split("-")[1],tanggal_awal)

	# tanggal_akhir = str(frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE field = "tanggal_akhir_tunjangan" """)[0][0])
	# date_akhir = "{}-{}-{}".format(str(date_object_akhir).split("-")[0],str(date_object_akhir).split("-")[1],tanggal_akhir)
	
	date_awal = self.start_date
	date_akhir = self.end_date

	ontime_present_query = frappe.db.sql(""" SELECT count(name) FROM `tabAttendance` 
					WHERE 
					(status = "Present" or status = "Half Day" or status = "Work From Home" )
					AND late_entry = 0 AND early_exit = 0
					and employee = "{}"  and docstatus=1
					and attendance_date >= "{}"
					and attendance_date <= "{}" 
					""".format(self.employee, date_awal, date_akhir))
	ontime_present = 0
	if len(ontime_present_query) > 0:
		ontime_present = ontime_present_query[0][0]

	late_present_query = frappe.db.sql(""" SELECT count(name) FROM `tabAttendance` 
			WHERE 
			(status = "Present" or status = "Half Day" or status = "Work From Home" )
			AND late_entry = 1 AND early_exit = 0 and docstatus=1
			and employee = "{}"
			and attendance_date >= "{}"
			and attendance_date <= "{}" 
			""".format(self.employee, date_awal, date_akhir))

	late_present = 0
	if len(late_present_query) > 0:
		late_present = late_present_query[0][0]

	early_exit_present_query = frappe.db.sql(""" SELECT count(name) FROM `tabAttendance` 
			WHERE 
			(status = "Present" or status = "Half Day" or status = "Work From Home" )
			AND late_entry = 0 AND early_exit = 1 and docstatus=1
			and employee = "{}"
			and attendance_date >= "{}"
			and attendance_date <= "{}" 
			""".format(self.employee, date_awal, date_akhir))

	early_exit_present = 0
	if len(early_exit_present_query) > 0:
		early_exit_present = early_exit_present_query[0][0]

	late_early_present_query = frappe.db.sql(""" SELECT count(name) FROM `tabAttendance` 
		WHERE 
		(status = "Present" or status = "Half Day" or status = "Work From Home" )
		AND late_entry = 1 AND early_exit = 1 and docstatus=1
		and employee = "{}"
		and attendance_date >= "{}"
		and attendance_date <= "{}" 
		""".format(self.employee, date_awal, date_akhir))

	late_early_present = 0
	if len(late_early_present_query) > 0:
		late_early_present = late_early_present_query[0][0]

	query_leave_type = frappe.db.sql(""" 
		SELECT NAME,
		REPLACE(LOWER(NAME)," ","_") 
		FROM `tabLeave Type` """)

	for row in query_leave_type:
		nama_variable = "extra_{}_days".format(re.sub('[^A-Za-z0-9_]', '', row[1]))
		nama_variable2 = "{}_days".format(re.sub('[^A-Za-z0-9_]', '', row[1]))

		tunjangan_att = frappe.db.sql(""" SELECT count(name) FROM `tabAttendance` 
			WHERE 
			(status = "On Leave")
			and leave_type = "{}" and docstatus=1
			and employee = "{}"
			and attendance_date >= "{}"
			and attendance_date <= "{}" 
		""".format(row[0],self.employee, date_awal, date_akhir))

		non_tunjangan_att = frappe.db.sql(""" SELECT count(name) FROM `tabAttendance` 
			WHERE 
			(status = "On Leave")
			and leave_type = "{}" and docstatus=1
			and employee = "{}"
			and attendance_date >= "{}"
			and attendance_date <= "{}" 
		""".format(row[0],self.employee, self.start_date, self.end_date))

		angka_variable = 0
		angka_variable2 = 0

		if len(tunjangan_att) > 0:
			angka_variable = tunjangan_att[0][0]

		if len(non_tunjangan_att) > 0:
			angka_variable2 = non_tunjangan_att[0][0]

		# data.update({'{}'.format(nama_variable): angka_variable})
		data.update({'{}'.format(nama_variable2): angka_variable2})

	# data.update({'extra_ontime_present': ontime_present})
	# data.update({'extra_late_present': late_present})
	# data.update({'extra_early_exit_present': early_exit_present})
	# data.update({'extra_late_early_present': late_early_present})

	payroll_period = get_payroll_period(self.start_date, self.end_date, self.company)
	remaining_sub_periods = get_period_factor(self.employee,
		self.start_date, self.end_date, self.payroll_frequency, payroll_period)[1]

	total_prev_biaya_jabatan_query = frappe.db.sql(""" 
		
		SELECT SUM(td.`amount`) as amount
		FROM `tabSalary Component` tc
		JOIN `tabSalary Detail` td ON td.`parentfield` = "earnings" 
		AND td.`parenttype` = "Salary Slip"
		AND td.`salary_component` = tc.`name`
		AND td.`docstatus` = 1
		JOIN `tabSalary Slip` tss ON tss.name = td.parent
		WHERE tc.biaya_jabatan = 1
		AND tss.`employee` = "{}"
		AND tss.`start_date` < "{}"
		AND tss.`start_date` >= "{}"

	""".format(self.employee, self.start_date, payroll_period.start_date),as_dict=1)

	total_biaya_jabatan = 0

	if len(total_prev_biaya_jabatan_query) > 0:
		for row in total_prev_biaya_jabatan_query:
			total_biaya_jabatan = row.amount

	#get_total_bulan lalu
	slip_data=frappe.db.sql("""select c.golongan_a1,sum(sd.amount) as "total"
			from `tabSalary Detail` sd left join `tabSalary Component` c on sd.salary_component = c.name left join `tabSalary Slip` sl on sl.name=sd.parent
			where sd.parenttype="Salary Slip" and sd.docstatus=1 and c.golongan_a1 is not NULL and sl.end_date >= "{0}" and sl.employee="{1}"
			group by sl.employee,c.golongan_a1
			""".format(payroll_period.start_date,self.employee),as_dict=1)

	amount_detail={}
	amount_detail["1"]=0
	amount_detail["3"]=0
	amount_detail["5"]=0
	amount_detail["7"]=0
	amount_detail["17"]=0
	amount_detail["9"]=0
	amount_detail["10"]=0
	for row in slip_data:
		amount_detail[cstr(row.golongan_a1)]=flt(row.total)

	data.update({'jumlah_1':amount_detail["1"]})
	data.update({'jumlah_3':amount_detail["3"]})
	data.update({'jumlah_5':amount_detail["5"]})
	data.update({'jumlah_7':amount_detail["7"]})
	data.update({'jumlah_17':amount_detail["17"]})
	data.update({'jumlah_9':amount_detail["9"]})
	data.update({'jumlah_10':amount_detail["10"]})
	data.update({'total_prev_biaya_jabatan': total_biaya_jabatan or 0})
	data.update({'remaining_sub_periods': remaining_sub_periods or 0 })
	data.update({'ontime_present': ontime_present})
	data.update({'late_present': late_present})
	data.update({'early_exit_present': early_exit_present})
	data.update({'late_early_present': late_early_present})

	
	#jumlah_cal_days = monthrange(getdate(self.start_date).year,getdate(self.start_date).month)
	#data.update({'calendar_days_periode_gaji': flt(jumlah_cal_days[1])})
	#self.calendar_days_periode_gaji = flt(jumlah_cal_days[1])
	self.calendar_days_periode_gaji=flt(date_diff(self.end_date,self.start_date))+1
	data.update({'calendar_days_periode_gaji': self.calendar_days_periode_gaji})

	bedanya = 0
	employee_doc = frappe.get_doc("Employee",self.employee)
	if getdate(employee_doc.date_of_joining) > getdate(self.start_date):
		bedanya = flt(date_diff(employee_doc.date_of_joining, self.start_date))

	if employee_doc.relieving_date:
		bedanya = bedanya + (date_diff(self.end_date , employee_doc.relieving_date))
	self.calendar_days_efektif_days = flt(self.calendar_days_periode_gaji) - flt(bedanya)
	data.update({'calendar_days_efektif_days': self.calendar_days_efektif_days})

	for struct_row in self._salary_structure_doc.get(component_type):
		amount = custom_eval_condition_and_formula(self,struct_row, data)
		if amount and struct_row.statistical_component == 0:
			self.update_component_row(struct_row, amount, component_type)

	# frappe.throw(str(data))
	# add component baru

def custom_eval_condition_and_formula(self, d, data):

	try:
		condition = d.condition.strip().replace("\n", " ") if d.condition else None
		if condition:
			if not frappe.safe_eval(condition, self.whitelisted_globals, data):
				return None
		amount = d.amount
		if d.amount_based_on_formula:
			formula = d.formula.strip().replace("\n", " ") if d.formula else None
			if formula:
				amount = flt(frappe.safe_eval(formula, self.whitelisted_globals, data), d.precision("amount"))
		if amount:
			data[d.abbr] = amount

		return amount

	except NameError as err:
		frappe.throw(_("{0} <br> This error can be due to missing or deleted field.").format(err),
			title=_("Name error"))
	except SyntaxError as err:
		frappe.throw(_("Syntax error in formula or condition: {0} in {1}").format(err,d.salary_component))
	except Exception as e:
		frappe.throw(_("Error in formula or condition: {0}").format(e))
		raise


def get_salary_component_data(component):
	return frappe.get_value(
		"Salary Component",
		component,
		[
			"name as salary_component",
			"depends_on_payment_days",
			"salary_component_abbr as abbr",
			"do_not_include_in_total",
			"is_tax_applicable",
			"is_flexible_benefit",
			"variable_based_on_taxable_salary",
		],
		as_dict=1,
	)


@frappe.whitelist()
def add_extra_component(self, method):
	SalarySlip.validate = custom_validate

@frappe.whitelist()
def override_calculate_net_pay(self, method):
	SalarySlip.calculate_net_pay = custom_calculate_net_pay

def custom_get_taxable_earnings(self, allow_tax_exemption=False, based_on_payment_days=0):
		joining_date, relieving_date = frappe.get_cached_value("Employee", self.employee,
			["date_of_joining", "relieving_date"])

		if not relieving_date:
			relieving_date = getdate(self.end_date)

		if not joining_date:
			frappe.throw(_("Please set the Date Of Joining for employee {0}").format(frappe.bold(self.employee_name)))

		taxable_earnings = 0
		additional_income = 0
		additional_income_with_full_tax = 0
		flexi_benefits = 0

		for earning in self.earnings:
			if based_on_payment_days:
				amount, additional_amount = self.get_amount_based_on_payment_days(earning, joining_date, relieving_date)
			else:
				amount, additional_amount = earning.amount, earning.additional_amount

			if earning.is_tax_applicable:
				if additional_amount:
					if not earning.is_recurring_additional_salary:
						taxable_earnings += (amount - additional_amount)
						additional_income += additional_amount
					else:
						to_date = frappe.db.get_value("Additional Salary", earning.additional_salary, 'to_date')
						period = (getdate(to_date).month - getdate(self.start_date).month) + 1
						if period > 0:
							taxable_earnings += (amount - additional_amount) * period
							additional_income += additional_amount * period

					if earning.deduct_full_tax_on_selected_payroll_date:
						additional_income_with_full_tax += additional_amount
					continue

				if earning.is_flexible_benefit:
					flexi_benefits += amount
				else:
					#if(based_on_payment_days == 1):
					taxable_earnings += amount
					#print("current_komponen {} : {} => {}".format(earning.salary_component,amount,taxable_earnings))
					#taxable_earnings += amount

		if allow_tax_exemption:
			print("GG")
			for ded in self.deductions:
				if ded.exempted_from_income_tax:
					amount = ded.amount
					if based_on_payment_days:
						amount = self.get_amount_based_on_payment_days(ded, joining_date, relieving_date)[0]
					taxable_earnings -= flt(amount)

		return frappe._dict({
			"taxable_earnings": taxable_earnings,
			"additional_income": additional_income,
			"additional_income_with_full_tax": additional_income_with_full_tax,
			"flexi_benefits": flexi_benefits
		})

def custom_get_working_days_details(self, joining_date=None, relieving_date=None, lwp=None, for_preview=0):
	payroll_based_on = frappe.db.get_value("Payroll Settings", None, "payroll_based_on")
	include_holidays_in_total_working_days = frappe.db.get_single_value("Payroll Settings", "include_holidays_in_total_working_days")

	working_days = date_diff(self.end_date, self.start_date) + 1
	if for_preview:
		self.total_working_days = working_days
		self.payment_days = working_days
		return

	holidays = self.get_holidays_for_employee(self.start_date, self.end_date)

	

	if not payroll_based_on:
		frappe.throw(_("Please set Payroll based on in Payroll settings"))

	if payroll_based_on == "Attendance":
		actual_lwp, absent = self.calculate_lwp_ppl_and_absent_days_based_on_attendance(holidays)
		self.absent_days = absent
	else:
		actual_lwp = self.calculate_lwp_or_ppl_based_on_leave_application(holidays, working_days)

	# Custom chandra karena erp tidak bisa hitung leave without pay kalau working days dikurangi dulu
	if not cint(include_holidays_in_total_working_days):
		working_days -= len(holidays)
		if working_days < 0:
			frappe.throw(_("There are more holidays than working days this month."))

	if not lwp:
		lwp = actual_lwp
	elif lwp != actual_lwp:
		frappe.msgprint(_("Leave Without Pay does not match with approved {} records")
			.format(payroll_based_on))

	self.leave_without_pay = lwp
	self.total_working_days = working_days

	payment_days = self.get_payment_days(joining_date,
		relieving_date, include_holidays_in_total_working_days)

	if flt(payment_days) > flt(lwp):
		self.payment_days = flt(payment_days) - flt(lwp)

		if payroll_based_on == "Attendance":
			self.payment_days -= flt(absent)

		unmarked_days = self.get_unmarked_days()
		consider_unmarked_attendance_as = frappe.db.get_value("Payroll Settings", None, "consider_unmarked_attendance_as") or "Present"

		if payroll_based_on == "Attendance" and consider_unmarked_attendance_as =="Absent":
			self.absent_days += unmarked_days #will be treated as absent
			self.payment_days -= unmarked_days
			if include_holidays_in_total_working_days:
				for holiday in holidays:
					if not frappe.db.exists("Attendance", {"employee": self.employee, "attendance_date": holiday, "docstatus": 1 }):
						self.payment_days += 1
	else:
		self.payment_days = 0
