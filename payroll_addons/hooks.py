from . import __version__ as app_version

app_name = "payroll_addons"
app_title = "Payroll Addons"
app_publisher = "das"
app_description = "addons untuk payroll"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "das@gmail.com"
app_license = "MIT"

# Includes in <head>
# ------------------

fixtures = [
    {"dt": "Custom Field", "filters": [
        [
            "dt", "in", [
                "Salary Slip", "Attendance"
            ]
        ]
    ]},
     {"dt": "DocType", "filters": [
        [
            "module", "in", [
                "Payroll Addons"
            ]
        ]
    ]}
]

# include js, css files in header of desk.html
# app_include_css = "/assets/payroll_addons/css/payroll_addons.css"
# app_include_js = "/assets/payroll_addons/js/payroll_addons.js"

# include js, css files in header of web template
# web_include_css = "/assets/payroll_addons/css/payroll_addons.css"
# web_include_js = "/assets/payroll_addons/js/payroll_addons.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "payroll_addons/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Salary Slip" : "public/js/custom_salary_slip.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "payroll_addons.install.before_install"
# after_install = "payroll_addons.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "payroll_addons.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Payroll Entry":{
		"validate" : "payroll_addons.custom_standard.custom_salary_slip.add_extra_component"
	},
	"Salary Slip":{
		"validate" : "payroll_addons.custom_standard.custom_salary_slip.add_extra_component",
		"autoname": "payroll_addons.custom_standard.custom_salary_slip.autoname_ss"
	},
	"Attendance":{
		"validate" : "payroll_addons.custom_standard.custom_attendance.set_time"
	},
	"Branch":{
		"validate": "payroll_addons.custom_standard.custom_salary_slip.update_umk"
	}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	# "all": [
	# 	"payroll_addons.tasks.all"
	# ],
	# "daily": [
	# 	"payroll_addons.tasks.daily"
	# ],
	"hourly": [
		"payroll_addons.custom_standard.custom_attendance.get_all_non_attendance"
	],
	# "weekly": [
	# 	"payroll_addons.tasks.weekly"
	# ]
	# "monthly": [
	# 	"payroll_addons.tasks.monthly"
	# ]
}

# Testing
# -------

# before_tests = "payroll_addons.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "payroll_addons.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "payroll_addons.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

user_data_fields = [
	{
		"doctype": "{doctype_1}",
		"filter_by": "{filter_by}",
		"redact_fields": ["{field_1}", "{field_2}"],
		"partial": 1,
	},
	{
		"doctype": "{doctype_2}",
		"filter_by": "{filter_by}",
		"partial": 1,
	},
	{
		"doctype": "{doctype_3}",
		"strict": False,
	},
	{
		"doctype": "{doctype_4}"
	}
]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"payroll_addons.auth.validate"
# ]

