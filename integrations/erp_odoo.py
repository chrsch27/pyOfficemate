import logging
import requests
import os
import re
from datetime import datetime
import csv
from io import StringIO
#from integrations.erp_sharepoint import ERPsharepointIntegration
import xmlrpc.client



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

class ERPodooIntegration:
    @staticmethod
    def send_to_erp(data,customer=None):
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
        recordCount = 0
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
                    recordCount += 1

        offer_id = models.execute_kw(config["DB"], uid, config["PASS"], 'sale.order', 'create', [vals])
        logging.info(f"Offer created with ID: {offer_id}")
        return offer_id, recordCount

    @staticmethod
    def fetch_document(document_id, document_type):
        """
        Fetch an existing document (e.g. QUOTATION) from Collmex ERP via QUOTATION_GET
        and parse the response into lineItems and customFields, handling
        possible embedded line breaks in fields.
        """
        logging.info(f"Fetching document {document_id} of type {document_type} from ERP Collmex...")

        # PortalData aus SharePoint holen (z.B. für freightCost, termsAndConditions etc.)
        portalData = ERPsharepointIntegration.fetch_portal_data_by_erp_number(document_id)
        logging.info(f"PortalData fetched: {portalData}")

        api_url = "https://www.collmex.de/c.cmx?170095,0,data_exchange"
        request_body = f"LOGIN;{collmex_login};{collmex_password}\nQUOTATION_GET;{document_id}"
        headers = {"Content-Type": "text/csv"}

        try:
            response = requests.post(api_url, data=request_body, headers=headers)
            response.raise_for_status()
            logging.info(f"Fetched document from Collmex: {response.status_code}")
            logging.info(f"Response text:\n{response.text}")

            csv_buffer = StringIO(response.text)
            csv_reader = csv.reader(csv_buffer, delimiter=';', quotechar='"')

            line_items = []
            item_number = 1  # Fortlaufende Nummerierung beginnt bei 1

            for fields in csv_reader:
                if len(fields) < 75:
                    continue
                if fields[0] != "CMXQTN":
                    continue

                # Für jedes Item Quantity und UnitPrice extrahieren und in float konvertieren
                # Collmex verwendet Komma als Dezimaltrenner, daher ersetzen wir es durch Punkt
                try:
                    quantity = float(fields[72].replace(',', '.'))
                    unit_price = float(fields[73].replace(',', '.'))
                except ValueError:
                    quantity, unit_price = 0.0, 0.0
                discount_cost = 0.0
                # TotalCost berechnen
                total_cost = quantity * unit_price - discount_cost

                line_items.append({
                    "number": item_number,  # Fortlaufende Nummer hinzufügen
                    "partCode": fields[69],
                    "description": fields[70],
                    "unitOfMeasure": fields[71],
                    "quantity": quantity,
                    "unitPrice": unit_price,
                    "discountCost": discount_cost,
                    "totalCost": total_cost
                })
                
                # Nummer für nächstes Item erhöhen
                item_number += 1

            logging.info(f"Line items fetched: {line_items}")
            # discountCost wird fest auf 0 gesetzt
            discount_cost = 0.0

            # subCost ermitteln (Summe aus quantity * unitPrice aller Positionen)
            sub_cost = 0.0
            for item in line_items:
                try:
                    # Auch hier Komma durch Punkt ersetzen
                    q = item["quantity"]
                    up = item["unitPrice"]
                except ValueError:
                    q, up = 0.0, 0.0
                sub_cost += q * up
                logging.info(f"Item: {item}, Quantity: {q}, UnitPrice: {up}, SubCost: {sub_cost}")

            # freightCost (optional aus portalData, sonst 0)
            freight_cost = float(portalData.get("freightCost", 0)) if portalData else 0.0

            # cost = subCost - discountCost + freightCost
            cost = sub_cost - discount_cost + freight_cost

            custom_fields = {
                "type": "Quote",
                "fetchedOn": datetime.utcnow().isoformat() + "Z",
                "collmexDocumentId": document_id,
                "discountCost": discount_cost,
                "subCost": sub_cost,
                "cost": cost,
                "termsAndConditions": (
                    portalData.get("termsAndConditions", "") if portalData else ""
                ),
                "paymentTerms": (
                    portalData.get("paymentTerms", "") if portalData else ""
                ),
                "freightCost": freight_cost  # optional zum Debugging
            }

            return {
                "portalData": portalData,
                "lineItems": line_items,
                "customFields": custom_fields
            }
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching document from Collmex: {e}")
            return None

def transformDataToCollmex(data):
    """
    Transform JSON data into Collmex CSV format (semicolon-separated).
    :param data: The JSON data to transform.
    :return: A string in Collmex CSV format.
    """
    try:
        # Start with the LOGIN line
        #login_line = f"LOGIN;{collmex_login};{collmex_password}"
        document_id = data.get("Belegnr", "-10000")
        firma = "1 Hamburg Factorship GmbH"
        id_kunde = "10033"
        payment_terms = "0 30 Tage ohne Abzug"
        currency = "EUR"
        delivery_terms = "0 Standard"
        preis_gruppe = "0 Standard"
        offer_text = "We herewith offer according to Orgalime S2012-conditions."
        end_text = "Time of delivery: \n Terms of delivery: ex works \n Validity: 2 months after offer"

        #csv_content = [login_line]
        logging.info(f"Data: {data}")

        # Create the document header (CMXQTN)
        document_line = (
            f"CMXQTN;{document_id};;0;{firma};{id_kunde};;;;;;;;;;;;;;;;;;;;;;0;20250329;;{payment_terms};{currency};{preis_gruppe}"
            f";0;0,00;;\"{offer_text}\";\"{end_text}\";;0;;1;0;0;0,00;;0 Neu;;0;0,00;0,00;;;;;;;;;;;;;;;;;;0"
        )

        # Add line items for the document
        for item in data.get("lineItems", []):
            description = item['description']
            number = item['number']
            unit_of_measure = item.get('unitOfMeasure', 'PCE')
            quantity = item['quantity']
            unit_price = item['unitPrice']
            item_line = (
                f"{document_line};;{number} {description};"
                f"{unit_of_measure};{quantity};{unit_price};1;0,00;;0;0;0;0;;;;;;"
            )
            csv_content.append(item_line)

        # Return joined CSV
        return "\n".join(csv_content)
    except KeyError as e:
        logging.error(f"Missing key in data: {e}")
        raise ValueError(f"Invalid data format: Missing key {e}")
    except Exception as e:
        logging.error(f"Error transforming data to Collmex format: {e}")
        raise