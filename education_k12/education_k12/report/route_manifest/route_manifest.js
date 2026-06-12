frappe.query_reports["Route Manifest"] = {
	filters: [
		{
			fieldname: "route",
			label: __("Route"),
			fieldtype: "Link",
			options: "K12 Transport Route",
			reqd: 1,
		},
		{
			fieldname: "academic_year",
			label: __("Academic Year"),
			fieldtype: "Link",
			options: "Academic Year",
			reqd: 1,
		},
	],
};
