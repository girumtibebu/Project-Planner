"""View filters: an allow-list of work item attributes turned into frappe.get_list filters.

A filter is [attribute, operator, value]. Views are user data, so nothing here
is put into SQL except through frappe's own filter builder.
"""

import frappe
from frappe import _

ME = "@me"
OPERATORS = {"=", "!=", "in", "not in", "like", "not like", "is", ">", "<", ">=", "<=", "between"}

# attribute -> Task field
ATTRIBUTES = {
	"state": "ep_state",
	"status": "status",
	"priority": "priority",
	"type": "type",
	"group": "ep_action_category",
	"parent": "parent_task",
	"start_date": "exp_start_date",
	"due_date": "exp_end_date",
	"milestone": "is_milestone",
	"is_group": "is_group",
	"progress": "progress",
	"estimate": "expected_time",
	"created_by": "owner",
	"created_on": "creation",
	"updated_on": "modified",
	"subject": "subject",
}
# attributes that need their own translation
SPECIAL = {"assignee", "label", "state_group"}
GROUPABLE = {"state", "state_group", "priority", "type", "group", "assignee", "milestone", "parent", "created_by", "day", "none"}
ORDERABLE = {"sequence": "ep_sequence", "subject": "subject", "priority": "priority", "start_date": "exp_start_date", "due_date": "exp_end_date", "created_on": "creation", "updated_on": "modified", "manual": "ep_sort_order"}
PRIORITY_ORDER = "field(`tabTask`.priority, 'Urgent', 'High', 'Medium', 'Low')"


def property_fields():
	return set(frappe.get_all("Planner Property", pluck="fieldname"))


def check_attribute(attribute, properties=None):
	if attribute in ATTRIBUTES or attribute in SPECIAL:
		return
	if attribute in (properties if properties is not None else property_fields()):
		return
	frappe.throw(_("Unknown filter attribute {0}").format(frappe.bold(attribute)))


def validate_filters(filters):
	if not isinstance(filters, list):
		frappe.throw(_("Filters must be a list"))
	properties = property_fields()
	for row in filters:
		if not (isinstance(row, list | tuple) and len(row) == 3):
			frappe.throw(_("Each filter is [attribute, operator, value]"))
		attribute, operator, _value = row
		check_attribute(attribute, properties)
		if operator not in OPERATORS:
			frappe.throw(_("Unknown filter operator {0}").format(frappe.bold(operator)))


def validate_group_by(group_by):
	if group_by and group_by not in GROUPABLE and group_by not in property_fields():
		frappe.throw(_("Cannot group by {0}").format(frappe.bold(group_by)))


def validate_order_by(order_by):
	if not order_by:
		return
	field, _sep, direction = order_by.partition(" ")
	if field not in ORDERABLE or direction not in ("", "asc", "desc"):
		frappe.throw(_("Cannot sort by {0}").format(frappe.bold(order_by)))


def date_token(value):
	"""Relative dates a saved view can use, so "due before end of week" stays true next week."""
	from frappe.utils import add_days, get_first_day, get_last_day, getdate, today

	if not (isinstance(value, str) and value.startswith("@")):
		return value
	day = getdate(today())
	starts = {
		"@today": day,
		"@tomorrow": add_days(day, 1),
		"@week_start": add_days(day, -day.weekday()),
		"@month_start": get_first_day(day),
	}
	ends = {"@week_end": add_days(day, 6 - day.weekday()), "@month_end": get_last_day(day)}
	if value in starts:
		return f"{starts[value]} 00:00:00"
	if value in ends:
		return f"{ends[value]} 23:59:59"
	return value


def resolve(value, user):
	if value == ME:
		return user
	if isinstance(value, list):
		return [user if v == ME else date_token(v) for v in value]
	return date_token(value)


def to_list_filters(project, filters, states_by_group):
	"""(filters, or_filters) for frappe.get_list on Task, always limited to the project."""
	validate_filters(filters)
	user = frappe.session.user
	out = [["Task", "project", "=", project]]
	for attribute, operator, value in filters:
		value = resolve(value, user)
		if attribute == "assignee":
			out.append(assignee_filter(operator, value))
		elif attribute == "label":
			out.append(["Task", "_user_tags", "not like" if operator in ("!=", "not in", "not like") else "like", f"%{value if not isinstance(value, list) else value[0]}%"])
		elif attribute == "state_group":
			groups = value if isinstance(value, list) else [value]
			names = [name for group in groups for name in states_by_group.get(group, [])] or ["-"]
			out.append(["Task", "ep_state", "not in" if operator in ("!=", "not in") else "in", names])
		else:
			out.append(["Task", ATTRIBUTES.get(attribute, attribute), operator, value])
	return out


def assignee_filter(operator, value):
	if operator == "is":
		# _assign is "[]" after the last assignee is removed, so test for a quoted user
		return ["Task", "_assign", "like" if value == "set" else "not like", '%"%']
	negate = operator in ("!=", "not in", "not like")
	user = value[0] if isinstance(value, list) else value
	return ["Task", "_assign", "not like" if negate else "like", f'%"{user}"%']


def to_order_by(order_by):
	field, _sep, direction = (order_by or "sequence asc").partition(" ")
	direction = direction or "asc"
	if field == "priority":
		return f"{PRIORITY_ORDER} {direction}"
	return f"`tabTask`.`{ORDERABLE[field]}` {direction}"
