import xmlrpc.client
import logging
from const_odoo import DB,URL,USER,PASS
import requests

url=f"{URL}/xmlrpc/2/common"
api_url=f"{URL}/jsonrpc"  # Replace with your actual endpoint
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



def authenticate_odoo_xml():
    common=xmlrpc.client.ServerProxy(url)
    logging.basicConfig(level=logging.DEBUG)
    logging.debug("Connecting to Odoo...")
    logging.info(common.version())



    #uid=common.authenticate("factorship-ltd", "Christoph Schmalisch", "hueODO##2025", {})
    #logging.info(f"Authenticated to Odoo with user ID: {uid}")
    """
    Authenticate to Odoo using XML-RPC.
    :return: The user ID if authentication is successful, None otherwise.
    """
    logging.info("Authenticating to Odoo...")
    try:
        uid = common.authenticate(DB, USER, PASS, {})
        if uid:
            logging.info(f"Authenticated to Odoo with user ID: {uid}")
            return uid
        else:
            logging.error("Failed to authenticate to Odoo. Check your credentials.")
            return None
    except Exception as e:
        logging.error(f"Error during authentication: {e}")
        return None
    
def authenticate_odoo():
    
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "id": 1,
        "params": {
            "service": "common",
            "method": "login",
            "args": (DB,USER,PASS)
        },

    }

    response = requests.post(api_url, json=payload)
    logging.info("Login request sent to Odoo.")
    logging.info(f"Payload: {response.json()['result']}")
    return response.json()['result']

def list_databases():
    """
    List all databases available in the Odoo instance.
    :return: A list of database names.
    """

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

    response = requests.post(api_url, json=payload)
    logging.info("Database list request sent to Odoo.")
    logging.info(response.json())
    return response.json()

def create_offer(customer):
    uid=authenticate_odoo_xml()
    if not uid:
        logging.error("Authentication failed. Cannot create offer.")
        return None 
    models=xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")
    customer_ids=models.execute_kw(DB, uid, PASS, 'res.partner', 'search', [[('name', 'like', customer)]])
    if not customer_ids:    
        customer_id=models.execute_kw(DB, uid, PASS, 'res.partner', 'create', [{'name': customer}])
        logging.info(f"Customer '{customer}' created with ID: {customer_id}")   
    else:
        customer_id=customer_ids[0]
        logging.info(f"Customer '{customer}' already exists with ID: {customer_id}")

    vals = {
        'partner_id': customer_id,  # ID des Kunden
        'order_line': [
            (0, 0, {'product_id': 3, 'product_uom_qty': 5, 'name':"produkt12", "price_unit":0}),   # Produkt 1
            (0, 0, {'product_id': 3, 'product_uom_qty': 2, 'name': 'Produkt222',"price_unit":0})    # Produkt 2
        ],
        # weitere Felder wie 'pricelist_id', 'date_order', etc. können ergänzt werden
    }
    offer_id=models.execute_kw(DB, uid, PASS, 'sale.order', 'create', [vals])
    logging.info(f"Offer created with ID: {offer_id}")

    models=xmlrpc.client.ServerProxy("https://factorship-ltd1.odoo.com/xmlrpc/2/object")



def send_to_erp(data):
    """
    Send data to the Odoo ERP system.
    :param data: The data to send (formatted as required by Odoo).
    :return: The response from the Odoo API.
    """
    logging.info("Sending document to ERP Odoo...")
    uid=authenticate_odoo()
    if not uid:
        logging.error("Authentication failed. Cannot send data to Odoo.")
        return None
   

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
                DB,
                uid,
                PASS,
                "sale.order",
                "create",
                [order_data]
            ]
        },
        "id": 2,
    }
    response = requests.post(url, json=payload)
    sale_order_id = response.json()["result"]
    print("Angebot erstellt mit ID:", sale_order_id)

def main():
    create_offer("Maximo Marine")

if __name__ == "__main__":
    main()
