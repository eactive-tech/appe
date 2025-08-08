import frappe
from frappe.custom.doctype.custom_field.custom_field import (
    create_custom_fields as _add_custom_fields,
)
from appe.constants.custom_fields import custom_Fields

def after_install():
    """
    Function to run after the app is installed.
    It creates custom fields defined in all_custom_fields.
    """
    print("Creating new custom fields")

    _add_custom_fields(all_custom_fields(), ignore_validate=True)
    frappe.db.commit()

def all_custom_fields():
    result = {}
    for doctypes, fields in custom_Fields.items():
        if isinstance(fields, dict):
            fields = [fields]

        result.setdefault(doctypes, []).extend(fields)
    return result


def remove_custom_fields_from_appe():
    for doctypes, fields in all_custom_fields().items():
        if isinstance(fields, dict):
            fields = [fields]

        if isinstance(doctypes, str):
            doctypes = (doctypes,)

        for doctype in doctypes:
            frappe.db.delete(
                "Custom Field",
                {
                    "fieldname": ("in", [field["fieldname"] for field in fields]),
                    "dt": doctype,
                },
            )

            frappe.clear_cache(doctype=doctype)