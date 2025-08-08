import frappe
import json
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from frappe import _

@frappe.whitelist(allow_guest=True)  # Remove allow_guest=True if authentication needed
def get_post_offices():
    try:
        # Validate input
        if not frappe.form_dict.get('text'):
            frappe.response.message = {
                'status': False,
                'message': 'Pincode is required'
            }
            return

        text = frappe.form_dict.text
        # Validate pincode (6 digits)
        if not re.match(r'^\d{6}$', text):
            frappe.response.message = {
                'status': False,
                'message': 'Invalid pincode. Must be 6 digits'
            }
            return

        # Set up retry strategy
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retries))

        # Make API request with timeout and headers
        response = session.get(
            f'https://api.postalpincode.in/pincode/{text}',
            timeout=10,  # 10 seconds timeout
            headers={
                'User-Agent': 'Frappe/1.0',  # Add User-Agent to avoid blocking
                'Accept': 'application/json'
            }
        )

        # Raise exception for bad status codes
        response.raise_for_status()

        # Parse response
        data = response.json()
        
        # Log response for debugging
        frappe.log_error('autocomplete api response', json.dumps(data, indent=2))

        # Check API status
        if not data or not isinstance(data, list) or not data[0].get('Status'):
            frappe.response.message = {
                'status': False,
                'message': 'Invalid response from external API'
            }
            return

        if data[0]['Status'] != 'Success':
            frappe.response.message = {
                'status': False,
                'message': data[0].get('Message', 'No post offices found')
            }
            return

        # Extract post office names
        post_offices = [{'name': item['Name'], 'description': f"{item['Name']}, {item['District']}, {item['State']}", 'label': item['State']} for item in data[0]['PostOffice']]

        # Set response
        frappe.response.message = {
            'status': True,
            'message': 'Success',
            'data': post_offices
        }
        return

    except requests.exceptions.RequestException as e:
        # Handle network or API errors
        frappe.log_error('autocomplete api error', str(e))
        frappe.response.message = {
            'status': False,
            'message': f'Failed to fetch post offices: {str(e)}'
        }
    except Exception as e:
        # Handle other unexpected errors
        frappe.log_error('autocomplete api unexpected error', str(e))
        frappe.response.message = {
            'status': False,
            'message': f'Internal server error: {str(e)}'
        }