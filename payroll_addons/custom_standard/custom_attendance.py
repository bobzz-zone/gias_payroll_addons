from __future__ import unicode_literals
import frappe, math, datetime
from frappe.utils import cstr, flt, getdate, comma_and, cint, nowdate, add_days
from frappe import msgprint, _
from frappe.model.document import Document
from frappe.utils import flt,now



@frappe.whitelist()
def set_time(self, method):
	if self.in_time:
		self.in_time_detail = str(self.in_time).split(" ")[1].split(".")[0]
	else:
		self.in_time_detail = ""
	if self.out_time:
		self.out_time_detail = str(self.out_time).split(" ")[1].split(".")[0]
	else:
		self.out_time_detail = ""

@frappe.whitelist()
def debug_set_time():
	list_att = frappe.db.sql(""" SELECT name, in_time, out_time FROM `tabAttendance` """)
	for row in list_att:
		self = frappe.get_doc("Attendance", row[0])
		print(str(row[0]))
		if self.in_time:
			self.in_time_detail = str(self.in_time).split(" ")[1].split(".")[0]
			print(str(self.in_time))
			print(str(self.in_time_detail))
		else:
			self.in_time_detail = ""
		if self.out_time:
			self.out_time_detail = str(self.out_time).split(" ")[1].split(".")[0]
			print(str(self.out_time))
			print(str(self.out_time_detail))
		else:
			self.out_time_detail = ""

		self.db_update()
		frappe.db.commit()


@frappe.whitelist()
def get_all_non_attendance():
	# get_time = frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE field = "type_out" """)
	
	time = ""
	get_time = frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE field = "check_attendance_time" """)
	if len(get_time) > 0:
		time = get_time[0][0]
	if time:
		time_now = now().split(" ")[1].split(":")[0]
		if(time.split(":")[0] == now().split(" ")[1].split(":")[0]):
			print(str(time_now))
			get_all_dont_have_attendance = frappe.db.sql(""" 
				SELECT
				tem.name as employee_id, 
				tem.`user_id` as user_email, 
				tem.employee_name, 
				DATE(NOW()) as date_now, 
				tat.name as attendance, 
				GROUP_CONCAT(thl.`holiday_date`) AS holiday_list
				FROM `tabEmployee` tem
				JOIN `tabHoliday List` th ON tem.`holiday_list` = th.name
				JOIN `tabHoliday` thl ON thl.parent = th.name

				LEFT JOIN `tabAttendance` tat ON tat.`employee` = tem.`employee`
				AND DATE(tat.`attendance_date`) = DATE(NOW())
				WHERE tem.user_id IS NOT NULL

				AND tem.`status` = "Active"

				GROUP BY tem.name
				HAVING holiday_list NOT LIKE CONCAT("%",DATE(NOW()),"%")
				AND tat.name IS NULL

			""",as_dict =1)

			for row in get_all_dont_have_attendance:
				new_doc = frappe.new_doc("Attendance Reminder")
				new_doc.owner = row.user_email
				new_doc.erp_user = row.user_email
				new_doc.employee = row.employee_id
				new_doc.employee_name = row.employee_name
				new_doc.date = row.date_now
				new_doc.notified = 0 
				new_doc.save()
				print(str(new_doc.erp_user))

