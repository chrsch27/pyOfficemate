import xmlrpc.client
import logging
import requests
import os
import re
from datetime import datetime
import csv
from io import StringIO
import json

# Logging setup (only once, at the beginning)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_env_config():
    """Get environment configuration and validate it"""
    config = {
        "USER": os.getenv("ODOO_LOGIN"),
        "PASS": os.getenv("ODOO_PASSWORD"),
        "URL": os.getenv("ODOO_URL", "https://factorship-ltd1.odoo.com"),
        "DB": os.getenv("ODOO_DB")
    }
    
    # Log configuration (masking password)
    masked_config = {**config}
    if masked_config["PASS"]:
        masked_config["PASS"] = "********"
    logging.info(f"Odoo configuration: {masked_config}")
    
    # Check for missing values
    missing = [k for k, v in config.items() if not v]
    if missing:
        logging.error(f"Missing environment variables: {', '.join(missing)}")
    
    return config

def authenticate_odoo_xml():
    """Authenticate to Odoo using XML-RPC."""
    config = get_env_config()
    
    # Ensure URL has proper protocol
    base_url = config["URL"]
    if not base_url.startswith(('http://', 'https://')):
        base_url = f"https://{base_url}"
    
    xml_rpc_url = f"{base_url}/xmlrpc/2/common"
    logging.info(f"Authenticating to Odoo using XML-RPC: {xml_rpc_url}")
    
    try:
        common = xmlrpc.client.ServerProxy(xml_rpc_url)
        version_info = common.version()
        logging.info(f"Connected to Odoo server version: {version_info}")
        
        uid = common.authenticate(config["DB"], config["USER"], config["PASS"], {})
        if uid:
            logging.info(f"Authentication successful, user ID: {uid}")
            return uid
        else:
            logging.error("Authentication failed. Check credentials.")
            return None
    except Exception as e:
        logging.error(f"Authentication error: {str(e)}")
        return None

def authenticate_odoo():
    config = get_env_config()
    
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "id": 1,
        "params": {
            "service": "common",
            "method": "login",
            "args": (config["DB"], config["USER"], config["PASS"])
        },

    }

    response = requests.post(f"{config['URL']}/jsonrpc", json=payload)
    logging.info("Login request sent to Odoo.")
    logging.info(f"Payload: {response.json()['result']}")
    return response.json()['result']

def list_databases():
    """
    List all databases available in the Odoo instance.
    :return: A list of database names.
    """
    config = get_env_config()
    
    logging.info("want to see Database list.")
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "id": 1,
        "params": {
            "service": "db",
            "method": "list",
            "args": []
        },
    }

    response = requests.post(f"{config['URL']}/jsonrpc", json=payload)
    logging.info("Database list request sent to Odoo.")
    logging.info(response.json())
    return response.json()

def create_offer(data, customer=None):
    uid = authenticate_odoo_xml()
    if not uid:
        logging.error("Authentication failed. Cannot create offer.")
        return None
     
    config = get_env_config()
    models = xmlrpc.client.ServerProxy(f"{config['URL']}/xmlrpc/2/object")
    if not customer:
        if data:
            customer = data.get('company')
            if not customer:
                logging.error("No customer name provided in data.")
                return None
        else:
            logging.error("No customer name provided.")
            return None

    customer_ids = models.execute_kw(config["DB"], uid, config["PASS"], 'res.partner', 'search', [[('name', 'like', customer)]])
    if not customer_ids:    
        customer_id = models.execute_kw(config["DB"], uid, config["PASS"], 'res.partner', 'create', [{'name': customer}])
        logging.info(f"Customer '{customer}' created with ID: {customer_id}")   
    else:
        customer_id = customer_ids[0]
        logging.info(f"Customer '{customer}' already exists with ID: {customer_id}")

    vals = {
    'partner_id': customer_id,
    'order_line': []
    }
    
    # Add optional fields if provided in data
    if data:
        if 'documentDate' in data:
            vals['date_order'] = data['documentDate']
        if 'note' in data:
            vals['note'] = data['note']
        if 'documentNo' in data:
            vals['client_order_ref'] = data['documentNo']
            
        # Add products from the data
        if 'items' in data and isinstance(data['items'], list):
            for product in data['items']:
                line = (0, 0, {
                    'product_id': 3,
                    'product_uom_qty': product.get('Quantity', 1),
                    'name': f"{product.get('ItemNumber', '')} {product.get('Description', '')}",
                    'price_unit': product.get('UnitPrice', 0)
                })
                vals['order_line'].append(line)

    offer_id = models.execute_kw(config["DB"], uid, config["PASS"], 'sale.order', 'create', [vals])
    logging.info(f"Offer created with ID: {offer_id}")
    return offer_id

def send_to_erp(data):
    """
    Send data to the Odoo ERP system.
    :param data: The data to send (formatted as required by Odoo).
    :return: The response from the Odoo API.
    """
    logging.info("Sending document to ERP Odoo...")
    uid = authenticate_odoo()
    if not uid:
        logging.error("Authentication failed. Cannot send data to Odoo.")
        return None
    
    config = get_env_config()

    order_data = {
        "partner_id": 20,  # ID des Kunden
        "order_line": [
            (0, 0, {"product_id": 28, "product_uom_qty": 2}),   # Produkt 1
            (0, 0, {"product_id": 27, "product_uom_qty": 2})    # Produkt 2
        ],
        # weitere Felder wie 'pricelist_id', 'date_order', etc. können ergänzt werden
    }

    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [
                config["DB"],
                uid,
                config["PASS"],
                "sale.order",
                "create",
                [order_data]
            ]
        },
        "id": 2,
    }
    response = requests.post(f"{config['URL']}/jsonrpc", json=payload)
    sale_order_id = response.json()["result"]
    print("Angebot erstellt mit ID:", sale_order_id)

def main():
    """Main function to demonstrate Odoo integration"""
    logging.info("Starting Odoo integration test")
    
    # Debug environment variables
    config = get_env_config()
    if not all([config["USER"], config["PASS"], config["URL"], config["DB"]]):
        logging.error("Cannot proceed without all required environment variables")
        return
    
    # Parse test data
    with open("test_data.json", "r") as f:
        data = json.load(f)
    
    # Uncomment to use hardcoded test data instead
    # data = json.loads("""{"company": "ANGLOTECH S.R.L.",...}""") 
    
    # Create offer
    offer_id = create_offer(data=data)
    if offer_id:
        logging.info(f"Successfully created offer with ID: {offer_id}")
    else:
        logging.error("Failed to create offer")

if __name__ == "__main__":
    main()
