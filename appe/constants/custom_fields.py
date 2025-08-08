import frappe

custom_Fields = {
    "DocField": [
        {
            "fieldname": "appe_autocomplete_api",
            "label": "Appe Autocomplete Api",
            "fieldtype": "Small Text",
            "insert_after": "options",
            "depends_on": "eval: doc.fieldtype =='Autocomplete'",
            "description": "Appe Autocomplete API End Point For Mobile App. This will be used to fetch the autocomplete suggestions for this field.",
        },
        {
            "fieldname": "appe_validate_field_api",
            "label": "Appe Validate Field Api",
            "fieldtype": "Small Text",
            "insert_after": "appe_autocomplete_api",
            "description": "Appe Validate Field API End Point For Mobile App. This will be used to validate the data for this field.",
        },
        {
            "fieldname": "appe_location_required",
            "label": "Appe Location Required",
            "fieldtype": "Small Text",
            "insert_after": "options",
            "description": "Appe Location Required For Mobile App. if this field is set to true, then the mobile app will ask for location permission and send the location data to the server.",
        },
        {
            "fieldname": "show_in_mobile",
            "label": "Show in Mobile",
            "fieldtype": "Check",
            "insert_after": "disabled",
        },
    ]
}