import logging
import requests
import os
import re
from datetime import datetime
import csv
from io import StringIO
from integrations.erp_sharepoint import ERPsharepointIntegration
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
    def send_request_for_quote_to_erp(data):
        """
        Verarbeitet ein RequestForQuote und sendet es an Odoo.
        Diese Methode nutzt die bestehende send_to_erp Implementierung.
        """
        logging.info("Processing RequestForQuote document for Odoo")
        # Nutze die vorhandene Implementierung
        result = ERPodooIntegration.send_to_erp(data)
        return {"type": "RequestForQuote", "result": result}
    
    @staticmethod
    def send_quote_to_erp(data):
        """Verarbeitet ein Quote und sendet es an Odoo"""
        logging.info("Processing Quote document for Odoo")
        # Nutze auch hier die vorhandene Implementierung mit spezifischen Anpassungen
        #result = ERPodooIntegration.send_to_erp(data)
        result = "no process"
        return {"type": "Quote", "result": result}
    
    @staticmethod
    def send_purchase_order_to_erp(data):
        """Verarbeitet ein PurchaseOrder und sendet es an Odoo"""
        logging.info("Processing PurchaseOrder document for Odoo")
        # Eigene Implementierung für PurchaseOrder könnte hier folgen
        #result = ERPodooIntegration.send_to_erp(data)
        result = "no process"
        return {"type": "PurchaseOrder", "result": result}
    
    @staticmethod
    def send_requisition_to_erp(data):
        """Verarbeitet ein Requisition und sendet es an Odoo"""
        logging.info("Processing Requisition document for Odoo")
        # Eigene Implementierung für Requisition könnte hier folgen
        #result = ERPodooIntegration.send_to_erp(data)
        result = "no process"
        return {"type": "Requisition", "result": result}
    
    @staticmethod
    def send_purchase_order_confirmation_to_erp(data):
        """Verarbeitet ein PurchaseOrderConfirmation und sendet es an Odoo"""
        logging.info("Processing PurchaseOrderConfirmation document for Odoo")
        # Eigene Implementierung für PurchaseOrderConfirmation könnte hier folgen
        # result = ERPodooIntegration.send_to_erp(data)
        result = "no process"
        return {"type": "PurchaseOrderConfirmation", "result": result}

    @staticmethod
    def send_to_erp(data, customer=None):
        """
        Create or update an offer in Odoo.
        
        Args:
            data: Dictionary containing offer data
            customer: Optional customer name override
                
        Returns:
            Tuple of (offer_id, record_count) or None if error occurs
        """
        # Validate that data is a dictionary
        if data is None:
            logging.error("No data provided to send_to_erp")
            return 0, 0
            
        if not isinstance(data, dict):
            logging.error(f"Expected dictionary for data, got {type(data).__name__}: {data}")
            return 0, 0
        
        uid = authenticate_odoo_xml()
        if not uid:
            logging.error("Authentication failed. Cannot create offer.")
            return 0, 0
        
        config = get_env_config()
        # Create XML-RPC client with allow_none=True
        models = xmlrpc.client.ServerProxy(
            f"{config['URL']}/xmlrpc/2/object",
            allow_none=True  # Enable None values in XML-RPC calls
        )
        
        # Extract key information (with safe defaults)
        document_type = data.get('documentType', '')
        reference_no = data.get('referencNo', '')
        
        # Check if this is a quotation with a reference to an existing offer
        existing_offer_id = None
        if document_type == 'Quotation' and reference_no:
            logging.info(f"Processing quotation with reference: {reference_no}")
            
            # Try to extract an offer number from the reference
            # Common patterns: "Ref: SO0001", "Quote #SO0001", "Your Ref: SO0001", etc.
            potential_refs = []
            
            # Look for Odoo sale order references (typically start with SO)
            # Get patterns from configuration to avoid hardcoding
            reference_patterns = os.getenv("OFFER_REFERENCE_PATTERNS", "(SO\\d+|CY-S\\d+)").split('|')
            combined_pattern = f"({'|'.join(reference_patterns)})"
            so_matches = re.findall(combined_pattern, reference_no)
            potential_refs.extend(so_matches)
            
            # Look for numeric references with common prefixes
            num_pattern = r'(?:ref|reference|quote|quotation|offer|#)[:\s]*(\d+)'
            num_matches = re.findall(num_pattern, reference_no, re.IGNORECASE)
            potential_refs.extend(num_matches)
            
            # If we found potential references, try to find the corresponding offer
            for ref in potential_refs:
                logging.info(f"Checking for existing offer with reference: {ref}")
                offer = ERPodooIntegration.find_offer_by_number(ref)
                if offer:
                    existing_offer_id = offer['id']
                    logging.info(f"Found existing offer: {existing_offer_id}")
                    break
        
        # If we found an existing offer, update it instead of creating a new one
        if existing_offer_id:
            return ERPodooIntegration.update_existing_offer(existing_offer_id, data)
        
        # Continue with regular offer creation process if no existing offer found
        if not customer:
            if data:
                customer = data.get('company')
                customername = customer['name']
                if not customer:
                    logging.error("No customer name provided in data.")
                    return None
            else:
                logging.error("No customer name provided.")
                return None
        
        # Find or create customer
        customer_ids = models.execute_kw(config["DB"], uid, config["PASS"], 
                                         'res.partner', 'search', 
                                         [[('name', 'like', customername)]])
        if not customer_ids:    
            customer_id = models.execute_kw(config["DB"], uid, config["PASS"], 
                                            'res.partner', 'create', [{'name': customername, 'email':customer['email'], 'contact_address': customer.get('street', '') + ', ' + customer.get('city', '') + ' ' + customer.get('postalcode', '')+ ' ' + customer.get('country', '')}])
            logging.info(f"Customer '{customer}' created with ID: {customer_id}")   
        else:
            customer_id = customer_ids[0]
            logging.info(f"Customer '{customer}' already exists with ID: {customer_id}")

        # Prepare sale order values with defaults for None values
        vals = {
            'partner_id': customer_id,
            'x_studio_vessel': data.get('vesselName', ''),
            'x_studio_imo': data.get('imoNumber', ''),
            'client_order_ref': data.get('documentNo', ''),
            'order_line': []
        }

        # Handle specifications data safely
        if data and 'specifications' in data:
            specs = data['specifications']
            if not isinstance(specs, list):
                logging.warning(f"Expected list for specifications, got {type(specs).__name__}")
                vals['x_studio_specification'] = ""
            else:
                # Format specifications as a readable string
                spec_details = []
                for spec in specs:
                    if not isinstance(spec, dict):
                        logging.warning(f"Expected dictionary for specification, got {type(spec).__name__}")
                        continue
                        
                    if spec.get('Manufacturer'):
                        spec_details.append(f"Manufacturer: {spec['Manufacturer']}")
                    if spec.get('PartType'):
                        spec_details.append(f"Part Type: {spec['PartType']}")
                    if spec.get('PartTypeNumber'):
                        spec_details.append(f"Part Number: {spec['PartTypeNumber']}")
                
                # Join all specifications with line breaks
                vals['x_studio_specification'] = "\n".join(spec_details)
                logging.info(f"Specifications set: {vals['x_studio_specification']}")
        else:
            vals['x_studio_specification'] = ""

        record_count = 0
        # Add optional fields if provided in data
        if data:
            if 'documentDate' in data:
                vals['date_order'] = data['documentDate'] or datetime.now().strftime('%Y-%m-%d')
            if 'note' in data:
                vals['note'] = data['note'] or ''
            if 'documentNo' in data:
                vals['client_order_ref'] = data['documentNo'] or ''
            if 'vesselName' in data:
                vals['note'] = vals.get('note', '') + f"\nVessel: {data['vesselName']}"
                
            # Add products from the data with defaults for None values
            if 'items' in data and isinstance(data['items'], list):
                for product in data['items']:
                    # Handle null values with defaults
                    quantity = product.get('Quantity') or 1.0
                    unit_price = product.get('UnitPrice') or 0.0
                    description = product.get('Description', '')
                    item_number = product.get('ItemNumber', '')
                    
                    # Get specification data if available
                    spec_info = ""
                    if product.get('specification'):
                        specItem = product['specification']
                        if specItem.get('Manufacturer') and specItem.get('Manufacturer') != specs[0].get('Manufacturer'):
                            spec_info += f"Manufacturer: {specItem['Manufacturer']}\n"
                        if specItem.get('PartType') and specItem.get('PartType') != specs[0].get('PartType'):
                            spec_info += f"Part Type: {specItem['PartType']}\n"
                        if specItem.get('PartTypeNumber') and specItem.get('PartTypeNumber') != specs[0].get('PartTypeNumber'):
                            spec_info += f"Part Number: {specItem['PartTypeNumber']}\n"
                    
                    # Create complete description
                    full_description = f"{item_number} {description}"
                    if spec_info:
                        full_description += f"\n\n{spec_info}"
                    
                    line = (0, 0, {
                        'product_id': 3,  # Default product ID
                        'product_uom_qty': float(quantity) if quantity else 1.0,
                        'name': full_description,
                        'price_unit': float(unit_price) if unit_price else 0.0
                    })
                    vals['order_line'].append(line)
                    record_count += 1

        try:
            # Create the sales order
            offer_id = models.execute_kw(config["DB"], uid, config["PASS"], 
                                         'sale.order', 'create', [vals])
            logging.info(f"Offer created with ID: {offer_id}")
            # Fetch the new offer to get its number (name)
            offer_data = models.execute_kw(config["DB"], uid, config["PASS"], 
                                           'sale.order', 'read', 
                                           [offer_id], 
                                           {'fields': ['name']})
            offer_number = offer_data[0]['name'] if offer_data and 'name' in offer_data[0] else ""
            return offer_id, record_count, offer_number
           
        except Exception as e:
            logging.error(f"Error creating offer in Odoo: {str(e)}")
            # Return explicit tuple to avoid None value issues
            return 0, 0

    @staticmethod
    def update_existing_offer(offer_id, data):
        """
        Update an existing offer with new price information.
        
        Args:
            offer_id: The ID of the existing offer to update
            data: The new quotation data with prices
                
        Returns:
            Tuple of (offer_id, updated_count) or None if error occurs
        """
        uid = authenticate_odoo_xml()
        if not uid:
            logging.error("Authentication failed. Cannot update offer.")
            return None
        
        config = get_env_config()
        models = xmlrpc.client.ServerProxy(
            f"{config['URL']}/xmlrpc/2/object",
            allow_none=True
        )
        offer_data = models.execute_kw(config["DB"], uid, config["PASS"], 
                                           'sale.order', 'read', 
                                           [offer_id], 
                                           {'fields': ['name']})
        offer_number = offer_data[0]['name'] if offer_data and 'name' in offer_data[0] else ""
        try:
            # Get existing offer lines
            line_ids = models.execute_kw(config["DB"], uid, config["PASS"],
                'sale.order.line', 'search',
                [[('order_id', '=', int(offer_id))]]
            )
            
            existing_lines = models.execute_kw(config["DB"], uid, config["PASS"],
                'sale.order.line', 'read',
                [line_ids],
                {'fields': ['product_id', 'name', 'product_uom_qty', 'price_unit', 'sequence']}
            )
            
            # Create a mapping of names to line IDs for easier matching
            line_map = {line['name'].strip(): line['id'] for line in existing_lines}
            line_sequence_map = {line['sequence']: line['id'] for line in existing_lines if 'sequence' in line}
            
            # Track how many lines we update
            updated_count = 0
            
            # Process new items from the quotation
            if 'items' in data and isinstance(data['items'], list):
                for item in data['items']:
                    item_number = item.get('ItemNumber', '')
                    description = item.get('Description', '')
                    position = item.get('Position', 0)
                    unit_price = item.get('UnitPrice')
                    
                    if unit_price is None:
                        logging.warning(f"Skipping item {item_number} - no price provided")
                        continue
                    
                    # Try to match by various criteria
                    matched_line_id = None
                    
                    # 1. Match by full name (ItemNumber + Description)
                    full_name = f"{item_number} {description}".strip()
                    if full_name in line_map:
                        matched_line_id = line_map[full_name]
                    
                    # 2. Match by position/sequence
                    elif position and position in line_sequence_map:
                        matched_line_id = line_sequence_map[position]
                    
                    # 3. Match by description only
                    elif description in line_map:
                        matched_line_id = line_map[description]
                    
                    # 4. Match by item number only
                    elif item_number and any(item_number in key for key in line_map):
                        matching_keys = [key for key in line_map if item_number in key]
                        if matching_keys:
                            matched_line_id = line_map[matching_keys[0]]
                    
                    # If we found a matching line, update its price
                    if matched_line_id:
                        models.execute_kw(config["DB"], uid, config["PASS"],
                            'sale.order.line', 'write',
                            [[matched_line_id], {'price_unit': float(unit_price)}]
                        )
                        updated_count += 1
                        logging.info(f"Updated price for item {item_number} {description} to {unit_price}")
                    else:
                        logging.info(f"No matching line found for {item_number} {description}. Adding as new line.")
                        
                        # Create specification info if available
                        spec_info = ""
                        if item.get('specification'):
                            spec = item['specification']
                            if spec.get('Manufacturer'):
                                spec_info += f"Manufacturer: {spec['Manufacturer']}\n"
                            if spec.get('PartType'):
                                spec_info += f"Part Type: {spec['PartType']}\n"
                            if spec.get('PartTypeNumber'):
                                spec_info += f"Part Number: {spec['PartTypeNumber']}\n"
                        
                        # Create complete description
                        full_description = f"{item_number} {description}"
                        if spec_info:
                            full_description += f"\n\n{spec_info}"
                        
                        # Add the new line to the existing offer
                        # Format: (0, 0, vals) for create operation in one2many fields
                        new_line = {
                            'order_id': int(offer_id),
                            'product_id': 3,  # Default product ID
                            'product_uom_qty': float(item.get('Quantity') or 1.0),
                            'name': full_description,
                            'price_unit': float(unit_price)
                        }
                        
                        try:
                            new_line_id = models.execute_kw(config["DB"], uid, config["PASS"],
                                'sale.order.line', 'create', [new_line]
                            )
                            updated_count += 1
                            logging.info(f"Added new line with ID {new_line_id} for item {item_number} {description}")
                        except Exception as line_err:
                            logging.error(f"Failed to add new line for {item_number}: {str(line_err)}")
            
            # Update the offer status if we made changes
            if updated_count > 0:
                # Add a note about the price update
                existing_note = models.execute_kw(config["DB"], uid, config["PASS"],
                    'sale.order', 'read',
                    [int(offer_id)],
                    {'fields': ['note']}
                )[0].get('note', '')
                
                update_note = f"{existing_note}\n\nPrices updated on {datetime.now().strftime('%Y-%m-%d')} from quotation reference: {data.get('documentNo', 'Unknown')}"
                
                models.execute_kw(config["DB"], uid, config["PASS"],
                    'sale.order', 'write',
                    [[int(offer_id)], {'note': update_note}]
                )
                # models.execute_kw(config["DB"], uid, config["PASS"],
                #     'sale.order', 'action_confirm',
                #     [[int(offer_id)]]
                #     )
                
                logging.info(f"Updated {updated_count} items in offer {offer_id}")
            else:
                logging.warning(f"No items were updated in offer {offer_id}")
            
            return int(offer_id), updated_count, offer_number
        
        except Exception as e:
            logging.error(f"Error updating existing offer: {str(e)}")
            return 0, 0

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
        request_body = f""
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

    @staticmethod
    def get_offer(offer_id):
        """
        Ruft ein Angebot (sale.order) von Odoo anhand der ID ab.
        
        Args:
            offer_id: ID des Angebots in Odoo
            
        Returns:
            Ein Dictionary mit den Angebotsdaten oder None bei Fehlern
        """
        uid = authenticate_odoo_xml()
        if not uid:
            logging.error("Authentication failed. Cannot fetch offer.")
            return None
        
        config = get_env_config()
        models = xmlrpc.client.ServerProxy(f"{config['URL']}/xmlrpc/2/object")
        
        try:
            # Angebotsdaten abrufen
            offer_data = models.execute_kw(config["DB"], uid, config["PASS"], 
                'sale.order', 'read', 
                [int(offer_id)], 
                {'fields': ['name', 'date_order', 'partner_id', 'client_order_ref', 'note', 'amount_total', 'state']}
            )
            
            if not offer_data:
                logging.error(f"No offer found with ID: {offer_id}")
                return None
                
            offer = offer_data[0]
            
            # Angebotszeilen abrufen
            line_ids = models.execute_kw(config["DB"], uid, config["PASS"],
                'sale.order.line', 'search',
                [[('order_id', '=', int(offer_id))]]
            )
            
            offer_lines = models.execute_kw(config["DB"], uid, config["PASS"],
                'sale.order.line', 'read',
                [line_ids],
                {'fields': ['product_id', 'name', 'product_uom_qty', 'price_unit', 'price_subtotal']}
            )
            
            # Kundendaten abrufen
            customer_id = offer['partner_id'][0]
            customer_data = models.execute_kw(config["DB"], uid, config["PASS"],
                'res.partner', 'read',
                [customer_id],
                {'fields': ['name', 'street', 'city', 'zip', 'email', 'phone']}
            )
            
            # Strukturiertes Ergebnis zusammenstellen
            result = {
                "id": offer_id,
                "reference": offer['name'],
                "status": offer['state'],
                "documentDate": offer['date_order'],
                "documentNo": offer.get('client_order_ref', ''),
                "note": offer.get('note', ''),
                "totalAmount": offer['amount_total'],
                "company": customer_data[0]['name'],
                "customerDetails": {
                    "name": customer_data[0]['name'],
                    "street": customer_data[0].get('street', ''),
                    "city": customer_data[0].get('city', ''),
                    "zip": customer_data[0].get('zip', ''),
                    "email": customer_data[0].get('email', ''),
                    "phone": customer_data[0].get('phone', '')
                },
                "items": []
            }
            
            # Produktzeilen hinzufügen
            for line in offer_lines:
                result["items"].append({
                    "ItemNumber": line['product_id'][0],
                    "Description": line['name'],
                    "Quantity": line['product_uom_qty'],
                    "UnitPrice": line['price_unit'],
                    "TotalPrice": line['price_subtotal']
                })
                
            logging.info(f"Successfully retrieved offer {offer_id} with {len(result['items'])} line items")
            return result
            
        except Exception as e:
            logging.error(f"Error fetching offer from Odoo: {str(e)}")
            return None

    @staticmethod
    def find_offer_by_number(offer_number):
        """
        Sucht und ruft ein Angebot (sale.order) von Odoo anhand der Angebotsnummer (name) ab.
        
        Args:
            offer_number: Angebotsnummer (im Feld 'name') in Odoo
                
        Returns:
            Ein Dictionary mit den Angebotsdaten oder None bei Fehlern/nicht gefunden
        """
        uid = authenticate_odoo_xml()
        if not uid:
            logging.error("Authentication failed. Cannot search for offer.")
            return None
        
        config = get_env_config()
        models = xmlrpc.client.ServerProxy(f"{config['URL']}/xmlrpc/2/object")
        
        try:
            # Nach Angebot mit der angegebenen Nummer suchen
            offer_ids = models.execute_kw(config["DB"], uid, config["PASS"], 
                'sale.order', 'search', 
                [[('name', '=', offer_number)]], 
                {'limit': 1}
            )
            
            if not offer_ids:
                logging.info(f"No offer found with number: {offer_number}")
                return None
                
            # Den ersten gefundenen Datensatz verwenden
            offer_id = offer_ids[0]
            logging.info(f"Found offer with ID: {offer_id} for number: {offer_number}")
            
            # Die vorhandene get_offer-Funktion verwenden, um die Daten abzurufen
            return ERPodooIntegration.get_offer(offer_id)
            
        except Exception as e:
            logging.error(f"Error searching for offer by number in Odoo: {str(e)}")
            return None

