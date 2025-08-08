import frappe
from frappe.utils import nowdate
from erpnext.stock.get_item_details import get_item_details
import json

@frappe.whitelist()
def search_item_details():
    try:
        # Request Parameters
        search = frappe.form_dict.get("search", "")
        customer = frappe.form_dict.get("customer", "")
        limit = int(frappe.form_dict.get("limit", 100))
        offset = int(frappe.form_dict.get("offset", 0))
        item_code = frappe.form_dict.get("item_code", "")
        qty = frappe.form_dict.get("qty") or ''
        uom = frappe.form_dict.get("uom") or ''
        user = frappe.session.user

        # customer = get_customer_from_user(user)
        if not customer:
            frappe.throw("No Customer linked to this user.")

        filters = get_item_filters(search, item_code)
        items = frappe.get_all(
            "Item",
            filters=filters,
            fields=["name", "item_name", "stock_uom", "description", "image", "item_group", "brand"],
            limit_page_length=limit,
            limit_start=offset,
            order_by="modified desc"
        )

        today = nowdate()
        company = frappe.defaults.get_user_default("company") or "Default Company"
        currency, price_list, price_list_currency = get_currency_and_price_list(customer, company)

        results = []
        for item in items:
            item_code = item["name"]
            item_args = {
                "item_code": item_code,
                "customer": customer,
                "currency": currency,
                "conversion_rate": 1,
                "price_list": price_list,
                "price_list_currency": price_list_currency,
                "plc_conversion_rate": 1,
                "company": company,
                "order_type": "Sales",
                "ignore_pricing_rule": 0,
                "doctype": "Sales Order",
                "qty": qty,
                "uom": uom
            }

            item_detail = get_item_details(item_args)
            videos = get_files(item_code, "/videos/%")
            images = get_files(item_code, "%.jpg")
            uom_prices = get_uom_prices(item_code, item["stock_uom"], price_list)
            promotions = get_promotions(item_detail)

            results.append(format_item_response(item, item_detail, uom_prices, videos, images, promotions))

        frappe.response.message = {
            "status": True,
            "data": results
        }

    except Exception as e:
        frappe.log_error("Get Customer Items Error", str(e))
        frappe.response.message = {
            "status": False,
            "data": str(e)
        }

# ----------------------------
# 🔧 Helper Functions Below
# ----------------------------

def get_customer_from_user(user):
    return frappe.db.get_value("Customer", [["Portal User", "user", "=", user]], "name")

def get_item_filters(search, item_code):
    filters = [["disabled", "=", 0]]
    if item_code:
        filters.append(["name", "=", item_code])
    elif search:
        filters.append(["item_name", "like", f"%{search}%"])
    return filters

def get_currency_and_price_list(customer, company):
    customer_currency = frappe.db.get_value("Customer", customer, "default_currency")
    company_currency = frappe.db.get_value("Company", company, "default_currency") or "INR"
    price_list = frappe.db.get_value("Customer", customer, "default_price_list") or "Standard Selling"
    price_list_currency = frappe.db.get_value("Price List", price_list, "currency") or "INR"
    return customer_currency or company_currency, price_list, price_list_currency

def get_files(item_code, file_filter):
    return frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": "Item",
            "attached_to_name": item_code,
            "file_url": ["like", file_filter]
        },
        fields=["file_url"]
    )

def get_uom_prices(item_code, stock_uom, price_list):
    uoms = frappe.get_all(
        "UOM Conversion Detail",
        filters={"parent": item_code},
        fields=["uom", "conversion_factor"]
    )
    uoms.insert(0, {"uom": stock_uom, "conversion_factor": 1.0})

    uom_prices = []
    for uom_entry in uoms:
        uom_name = uom_entry["uom"]
        price = frappe.db.get_value("Item Price", {
            "item_code": item_code,
            "price_list": price_list,
            "uom": uom_name
        }, "price_list_rate")
        uom_prices.append({
            "uom": uom_name,
            "conversion_factor": uom_entry["conversion_factor"],
            "price": price or 0.0
        })

    return uom_prices

def get_promotions(item_detail):
    promotions = []
    pricing_rules = parse_json_if_string(item_detail.get("pricing_rules", "[]"))
    for rule in pricing_rules:
        doc = frappe.get_doc("Pricing Rule", rule)
        promotions.append(doc.as_dict())
    return promotions

def parse_json_if_string(data):
    if isinstance(data, str):
        try:
            return json.loads(data)
        except:
            return []
    return data or []

def format_item_response(item, item_detail, uom_prices, videos, images, promotions):
    return {
        "item_code": item["name"],
        "item_name": item["item_name"],
        "description": item["description"],
        "item_group": item["item_group"],
        "brand": item["brand"],
        "uom": item["stock_uom"],
        "image": item["image"],
        "price": item_detail.get("price_list_rate", 0.0),
        "discount_percentage": item_detail.get("discount_percentage", 0.0),
        "rate": item_detail.get("rate", 0.0),
        "net_rate": item_detail.get("net_rate", 0.0),
        "amount": item_detail.get("amount", 0.0),
        "taxes": item_detail.get("item_tax_rate", {}),
        "margin_type": item_detail.get("margin_type"),
        "margin_rate_or_amount": item_detail.get("margin_rate_or_amount"),
        "uom_prices": uom_prices,
        "videos": [v["file_url"] for v in videos],
        "images": [img["file_url"] for img in images],
        "promotions": promotions,
        "free_items": item_detail.get("free_item_data", [])
    }
