app_name = "education_k12"

website_route_rules = [
    {"from_route": "/portal/<path:app_path>", "to_route": "portal"},
]
app_title = "Education K12"
app_publisher = "Asif Mohtesham"
app_description = "K-12 extensions for Frappe Education"
app_email = "asifmohtesham@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "education_k12",
# 		"logo": "/assets/education_k12/logo.png",
# 		"title": "Education K12",
# 		"route": "/education_k12",
# 		"has_permission": "education_k12.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/education_k12/css/education_k12.css"
# app_include_js = "/assets/education_k12/js/education_k12.js"

# include js, css files in header of web template
# web_include_css = "/assets/education_k12/css/education_k12.css"
# web_include_js = "/assets/education_k12/js/education_k12.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "education_k12/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "education_k12/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "education_k12.utils.jinja_methods",
# 	"filters": "education_k12.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "education_k12.install.before_install"
# after_install = "education_k12.install.after_install"

after_install = ["education_k12.setup.install.ensure_customizations"]
after_migrate = ["education_k12.setup.install.ensure_customizations"]

# Uninstallation
# ------------

# before_uninstall = "education_k12.uninstall.before_uninstall"
# after_uninstall = "education_k12.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "education_k12.utils.before_app_install"
# after_app_install = "education_k12.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "education_k12.utils.before_app_uninstall"
# after_app_uninstall = "education_k12.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "education_k12.notifications.get_notification_config"

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

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

doc_events = {
    "Student": {
        "validate": "education_k12.k12_sis.siblings.validate_siblings",
        "on_update": "education_k12.k12_sis.siblings.sync_reciprocal_siblings",
    },
    "Student Group": {
        "validate": "education_k12.k12_sis.homeroom.validate_homeroom",
    },
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"education_k12.tasks.all"
# 	],
# 	"daily": [
# 		"education_k12.tasks.daily"
# 	],
# 	"hourly": [
# 		"education_k12.tasks.hourly"
# 	],
# 	"weekly": [
# 		"education_k12.tasks.weekly"
# 	],
# 	"monthly": [
# 		"education_k12.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "education_k12.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "education_k12.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "education_k12.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["education_k12.utils.before_request"]
# after_request = ["education_k12.utils.after_request"]

# Job Events
# ----------
# before_job = ["education_k12.utils.before_job"]
# after_job = ["education_k12.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"education_k12.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

