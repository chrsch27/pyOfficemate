import logging
import requests
import os
import re
from datetime import datetime
import csv
from io import StringIO
from integrations.erp_sharepoint import ERPsharepointIntegration

collmex_login = os.getenv("COLLMEX_LOGIN")
collmex_password = os.getenv("COLLMEX_PASSWORD")
collmex_api_url = os.getenv("COLLMEX_API_URL", "https://www.collmex.de/c.cmx?170095,0,data_exchange")

# Define field indices for different document types
DOCUMENT_TYPE_CONFIG = {
    "Quote": {
        "record_type": "CMXQTN",
        "command": "QUOTATION_GET",
        "response_type": "Quote",  # Response type remains the same
        "fields": {
            "part_code": 69,
            "description": 70,
            "unit_of_measure": 71,
            "quantity": 72,
            "unit_price": 73,
            "discount_percentage": 75,
            "terms_and_conditions": 37,
            "total_discount_percentage": 34,
            "freight_cost": 49  # Added freight cost index
        }
    },
    "PurchaseOrder": {
        "record_type": "CMXORD-2",
        "command": "SALES_ORDER_GET",
        "response_type": "PurchaseOrderConfirmation",  # Response becomes PurchaseOrderConfirmation
        "fields": {
            "part_code": 72,
            "description": 73,
            "unit_of_measure": 74,
            "quantity": 75,
            "unit_price": 76,
            "discount_percentage": 769,
            "terms_and_conditions": 35,
            "total_discount_percentage": 38,
            "freight_cost": 52  # Added freight cost index
        }
    },
    "RequestForQuote": {
        "record_type": "CMXQTN",
        "command": "QUOTATION_GET",
        "response_type": "Quote",  # Response becomes Quote
        "fields": {
            "part_code": 69,
            "description": 70,
            "unit_of_measure": 71,
            "quantity": 72,
            "unit_price": 73,
            "discount_percentage": 75,
            "terms_and_conditions": 37,
            "total_discount_percentage": 34,
            "freight_cost": 49  # Added freight cost index
        }
    }
}

class ERPcollmexIntegration:
    @staticmethod
    def send_to_erp(data):
        """Legacy-Methode für RequestForQuote, bleibt für Kompatibilität erhalten"""
        return ERPcollmexIntegration.send_request_for_quote_to_erp(data)
    
    @staticmethod
    def send_request_for_quote_to_erp(data):
        """Verarbeitet ein RequestForQuote und sendet es an Collmex"""
        logging.info("Processing RequestForQuote document for Collmex")
        return ERPcollmexIntegration.send_docType_to_erp(data, docType="RequestForQuote")

    
    @staticmethod
    def send_quote_to_erp(data):
        """Verarbeitet ein Quote und sendet es an Collmex"""
        logging.info("Processing Quote document for Collmex")
        return {"type": "Quote"}
    
    @staticmethod
    def send_purchase_order_to_erp(data):
        """Verarbeitet ein PurchaseOrder und sendet es an Collmex"""
        logging.info("Processing PurchaseOrder document for Collmex")
        # Hier würde die eigentliche Verarbeitung stattfinden
        return ERPcollmexIntegration.send_docType_to_erp(data, docType="PurchaseOrder")
    
    @staticmethod
    def send_requisition_to_erp(data):
        """Verarbeitet ein Requisition und sendet es an Collmex"""
        logging.info("Processing Requisition document for Collmex")
        # Hier würde die eigentliche Verarbeitung stattfinden
        return {"type": "Requisition"}
    
    @staticmethod
    def send_purchase_order_confirmation_to_erp(data):
        """Verarbeitet ein PurchaseOrderConfirmation und sendet es an Collmex"""
        logging.info("Processing PurchaseOrderConfirmation document for Collmex")
        # Hier würde die eigentliche Verarbeitung stattfinden
        return {"type": "PurchaseOrderConfirmation"}
    
    # Fetch-Methoden
    
    @staticmethod
    def fetch_request_for_quote(document_id):
        """Holt ein RequestForQuote-Dokument aus Collmex"""
        logging.info(f"Fetching RequestForQuote document {document_id} from Collmex")
        # Hier würde die eigentliche Abfrage stattfinden
        fetch_document = ERPcollmexIntegration.fetch_document(document_id, "RequestForQuote")
        return fetch_document
    
    @staticmethod
    def fetch_quote(document_id):
        """Holt ein Quote-Dokument aus Collmex"""
        logging.info(f"Fetching Quote document {document_id} from Collmex")
        # Hier würde die eigentliche Abfrage stattfinden
        return {"id": document_id, "type": "Quote"}
    
    @staticmethod
    def fetch_purchase_order(document_id):
        """Holt ein PurchaseOrder-Dokument aus Collmex"""
        logging.info(f"Fetching PurchaseOrder document {document_id} from Collmex")
        fetch_document = ERPcollmexIntegration.fetch_document(document_id, "PurchaseOrder")
        # Hier würde die eigentliche Abfrage stattfinden
        return fetch_document
    
    @staticmethod
    def fetch_requisition(document_id):
        """Holt ein Requisition-Dokument aus Collmex"""
        logging.info(f"Fetching Requisition document {document_id} from Collmex")
        # Hier würde die eigentliche Abfrage stattfinden
        return {"id": document_id, "type": "Requisition"}
    
    @staticmethod
    def fetch_purchase_order_confirmation(document_id):
        """Holt ein PurchaseOrderConfirmation-Dokument aus Collmex"""
        logging.info(f"Fetching PurchaseOrderConfirmation document {document_id} from Collmex")
        # Hier würde die eigentliche Abfrage stattfinden
        return {"id": document_id, "type": "PurchaseOrderConfirmation"}
    
    @staticmethod
    def fetch_document1(document_id, document_type):
        """Generische Methode zum Abrufen von Dokumenten aus Collmex"""
        logging.info(f"Fetching generic document {document_id} of type {document_type} from Collmex")
        # Je nach document_type die spezifische Methode aufrufen
        if document_type == "RequestForQuote":
            return ERPcollmexIntegration.fetch_request_for_quote(document_id)
        elif document_type == "Quote":
            return ERPcollmexIntegration.fetch_quote(document_id)
        elif document_type == "PurchaseOrder":
            return ERPcollmexIntegration.fetch_purchase_order(document_id)
        elif document_type == "Requisition":
            return ERPcollmexIntegration.fetch_requisition(document_id)
        elif document_type == "PurchaseOrderConfirmation":
            return ERPcollmexIntegration.fetch_purchase_order_confirmation(document_id)
        else:
            # Unbekannter Dokumenttyp
            logging.warning(f"Unknown document type: {document_type}")
            return {"id": document_id, "type": "Unknown"}

    @staticmethod
    def send_docType_to_erp(data, docType="RequestForQuote"):
        """
        Send data to the Collmex ERP system.
        :param data: The data to send (formatted as required by Collmex).
        :param docType: The type of document being sent.
        :return: The response from the Collmex API with processed line items.
        """
        logging.info(f"Sending {docType} document to ERP Collmex...")

        # Collmex API URL
        api_url = collmex_api_url

        # Headers for the request
        headers = {
            "Content-Type": "text/csv",  # Collmex expects plain text
        }

        try:
            # Transform data to Collmex format and get processed items
            csv_data, processed_data = transformDataToCollmex(data, docType=docType)
            logging.info(f"Data to send: {csv_data}")
            
            # Send the POST request to Collmex
            response = requests.post(api_url, data=csv_data, headers=headers)
            response.raise_for_status()  # Raise an exception for HTTP errors

            # Log and return the response
            logging.info(f"Document sent to ERP Collmex successfully: {response.status_code}")
            logging.info(f"Response got from ERP Collmex: {response.text}")
            erp_number = None
            record_count = None

            # Parse the response text
            for line in response.text.splitlines():
                if line.startswith("NEW_OBJECT_ID"):
                    # Extract ERP number (second field)
                    erp_number = line.split(";")[1]
                    logging.info(f"Extracted ERP number: {erp_number}")
                elif line.startswith("MESSAGE"):
                    # Extract record count (last part of the message)
                    match = re.search(r"Es wurden (\d+) Datensätze verarbeitet", line)
                    if match:
                        record_count = int(match.group(1))

            # Attach the ERP number to the original data object
            if erp_number:
                # Use a new dictionary to avoid modifying the original if it's immutable
                if isinstance(data, dict):
                    data["ERPNummer"] = erp_number
                    logging.info(f"Added ERPNummer {erp_number} to data object")
                else:
                    logging.warning(f"Could not add ERPNummer to data - not a dictionary")

            # Return the extracted values and processed data
            return {
                "ERPNummer": erp_number,
                "Recordcount": record_count,
                "processedData": processed_data
            }
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending document to ERP Collmex: {e}")
            return None

    @staticmethod
    def fetch_document(document_id, document_type):
        """
        Fetch an existing document from Collmex ERP using configurable field indices.
        
        Args:
            document_id: The ID of the document to fetch
            document_type: Type of document (RequestForQuote, Quote, PurchaseOrder, etc.)
            
        Returns:
            Dictionary containing document data, line items, and custom fields
        """
        logging.info(f"Fetching document {document_id} of type {document_type} from ERP Collmex...")
        
        # Get configuration for this document type
        config = DOCUMENT_TYPE_CONFIG.get(document_type)
        if not config:
            logging.error(f"No configuration found for document type: {document_type}")
            return {"error": f"Unsupported document type: {document_type}"}
        
        # Get the response_type from config (if present) or default to document_type
        response_type = config.get("response_type", document_type)
        logging.info(f"Using response_type '{response_type}' for document_type '{document_type}'")
        
        # PortalData from SharePoint (for freightCost, termsAndConditions, etc.)
        portalData = ERPsharepointIntegration.fetch_portal_data_by_erp_number(document_id, document_type)
        
        # Add response_type to portalData if it exists
        if portalData is None:
            portalData = {}
        
        # Set the type in portalData to the response_type from config
        portalData["type"] = response_type
        logging.info(f"Set portalData['type'] to '{response_type}'")
        
        logging.info(f"PortalData fetched and enriched with type: {portalData}")

        api_url = "https://www.collmex.de/c.cmx?170095,0,data_exchange"
        request_body = f"LOGIN;{collmex_login};{collmex_password}\n{config['command']};{document_id}"
        headers = {"Content-Type": "text/csv"}

        try:
            # Robust error handling following Azure Functions best practices
            response = requests.post(
                api_url,
                data=request_body,
                headers=headers,
                timeout=30  # Explicit timeout for network resilience
            )
            response.raise_for_status()
            logging.info(f"Fetched document from Collmex: {response.status_code}")
            
            # Use a context manager for better resource handling
            csv_buffer = StringIO(response.text)
            csv_reader = csv.reader(csv_buffer, delimiter=';', quotechar='"')

            line_items = []
            item_number = 1  # Start numbering at 1
            discount_proz_ges = 0.0  # Initialize total discount percentage
            terms_and_conditions = ""
            
            fields = config["fields"]  # Get field indices for this document type
            
            for row in csv_reader:
                if len(row) < max(fields.values()) + 1:  # Ensure row has enough fields
                    continue
                    
                if row[0] != config["record_type"]:  # Check for correct record type
                    continue

                # Extract values using the field indices from configuration
                try:
                    # Parse quantity and unit price, handling comma as decimal separator
                    quantity = float(row[fields["quantity"]].replace(',', '.')) 
                    unit_price = float(row[fields["unit_price"]].replace(',', '.'))
                except (ValueError, IndexError):
                    quantity, unit_price = 0.0, 0.0
                    
                try:
                    discount_percentage = float(row[fields["discount_percentage"]].replace(',', '.'))
                except (ValueError, IndexError):
                    discount_percentage = 0.0
                    
                itemDeclined =  quantity <= 0 or unit_price <= 0  
                # Calculate discount cost with proper rounding to 2 decimal places
                discount_cost = round(unit_price * (discount_percentage / 100.0), 2)
                total_cost = quantity * (unit_price - discount_cost)
                itemDeclinedReasontext = "Not available" if itemDeclined else ""
                line_items.append({
                    "number": item_number,
                    "partCode": row[fields["part_code"]],
                    "description": row[fields["description"]],
                    "unitOfMeasure": row[fields["unit_of_measure"]],
                    "quantity": quantity,
                    "unitPrice": unit_price,
                    "discountPercentage": discount_percentage,
                    "discountCost": discount_cost,
                    "totalCost": total_cost,
                    "declined": itemDeclined,
                    "declinedReasonText": itemDeclinedReasontext

                })
                
                # Increment item number for next item
                item_number += 1
                
                # Get total discount percentage and terms & conditions
                try:
                    discount_proz_ges = float(row[fields["total_discount_percentage"]].replace(',', '.'))
                    terms_and_conditions = row[fields["terms_and_conditions"]]
                except (ValueError, IndexError):
                    pass

            logging.info(f"Line items fetched: {len(line_items)}")
            
            # Calculate totals
            sub_cost = 0.0
            for item in line_items:
                try:
                    q = item["quantity"]
                    up = item["unitPrice"]
                    disc = item["discountCost"]
                except (KeyError, ValueError):
                    q, up, disc = 0.0, 0.0, 0.0
                sub_cost += q * up - disc 
                logging.info(f"Item: {item['number']}, Subtotal: {q * up - disc}")

            # Get freight cost from portal data or default to 0
            freight_cost = float(row[fields["freight_cost"]].replace(',', '.'))
            
            # Calculate final discount cost with proper rounding
            discount_cost = round(sub_cost * discount_proz_ges / 100.0, 2)
            
            # Total cost calculation
            cost = sub_cost - discount_cost + freight_cost

            custom_fields = {
                "type": config["response_type"],
                "fetchedOn": datetime.utcnow().isoformat() + "Z",
                "collmexDocumentId": document_id,
                "discountPercentage": discount_proz_ges,
                "discountCost": discount_cost,
                "subCost": sub_cost,
                "cost": cost,
                "termsAndConditions": terms_and_conditions if terms_and_conditions else "",
                "paymentTerms": portalData.get("paymentTerms", "") if portalData else "",
                "freightCost": freight_cost
            }

            return {
                "portalData": portalData,
                "lineItems": line_items,
                "customFields": custom_fields
            }
            
        except requests.exceptions.RequestException as e:
            # Enhanced error handling with context
            logging.error(f"Error fetching document {document_id} from Collmex: {str(e)}")
            return {
                "error": f"Failed to fetch document: {str(e)}",
                "documentId": document_id,
                "documentType": document_type
            }
        except Exception as e:
            # Catch-all for unexpected errors
            logging.exception(f"Unexpected error processing document {document_id}: {str(e)}")
            return {
                "error": f"Document processing failed: {str(e)}",
                "documentId": document_id,
                "documentType": document_type
            }

def transformDataToCollmex(data, docType="RequestForQuote"):
    """
    Transform JSON data into Collmex CSV format (semicolon-separated) and return processed line items.
    
    Args:
        data: The JSON data to transform.
        docType: Type of document (RequestForQuote, PurchaseOrder)
        
    Returns:
        tuple: (csv_string, processed_data)
            - csv_string: A string in Collmex CSV format
            - processed_data: Dictionary with document and line items information
    """
    try:
        # Start with the LOGIN line
        login_line = f"LOGIN;{collmex_login};{collmex_password}"
        document_id = data.get("Belegnr", "-10000")
        firma = "1 Hamburg Factorship GmbH"
        id_kunde = "99998"
        payment_terms = "0 30 Tage ohne Abzug"
        currency = "EUR"
        delivery_terms = "0 Standard"
        preis_gruppe = "0 Standard"
        offer_text = "We herewith offer according to Orgalime S2012-conditions."
        order_text ="We herewith acknowledge your order, based on Orgalime-conditions S2012."
        end_text = "Time of delivery: \n Terms of delivery: ex works \n Validity: 2 months after offer"
        customerRef = data.get("referenceNumber", "")
        documentDate = format_document_date(data.get("submittedDate"))
        
        # Convert decimal values from portal data (with period) to Collmex format (with comma)
        discount_proz = data.get("discountPercentage", 0.0)
        discount_proz_str = format_decimal_for_collmex(discount_proz)
        
        freight_cost = data.get("freightCost", 0.0)
        freight_cost_str = format_decimal_for_collmex(freight_cost)

        # Initialize processed data dictionary
        processed_data = {
            "documentInfo": {
                "documentId": document_id,
                "documentType": docType,
                "customerRef": customerRef,
                "documentDate": documentDate,
                "currency": currency
            },
            "lineItems": []
        }

        csv_content = [login_line]
        logging.info(f"Data: {data}")

        # Create the document header
        if docType == "RequestForQuote":
            document_line = (
                f"CMXQTN;{document_id};;0;{firma};{id_kunde};;;;;;;;;;;;;;;;;;;;;;0;{documentDate};;{payment_terms};{currency};{preis_gruppe}"
                f";0;0,00;;\"{offer_text}\";\"{end_text}\";;0;;1;0;0;0,00;;0 Neu;;0;0,00;0,00;;;;;;;;;;;;;;;;;;0"
            )
        elif docType == "PurchaseOrder":
            document_line = (
                f"CMXORD-2;{document_id};;0;{firma};{id_kunde};;;;;;;;;;;;;;;;;;;;;;0;{customerRef};{documentDate};;{payment_terms};{currency};{preis_gruppe}"
                f";0;{discount_proz_str};;\"{order_text}\";\"{end_text}\";;1;1;0;0 Neu;1;0;0;;0,00;;;;0;{freight_cost_str};0,00;;;;;;;;;;;;;;;;;0"
            )
        logging.info(f"Document line: {document_line}")
        
        # Add line items for the document
        line_items = data.get("lineItems", [])
        if not line_items:
            logging.warning("No line items found in data")
            
        for item in line_items:
            try:
                # Process item description and details
                logging.info(f"Processing item: {item}")
                raw_description = item.get('description', '')
                
                # Convert decimal values from portal data format to Collmex format
                discount_item_prozent = item.get('discountPercentage', 0.0)
                discount_item_prozent_str = format_decimal_for_collmex(discount_item_prozent)
                
                quantity = item.get('quantity', 0)
                quantity_str = format_decimal_for_collmex(quantity)
                
                unit_price = item.get('unitPrice', 0)
                unit_price_str = format_decimal_for_collmex(unit_price)
                
                description = raw_description.replace('\r\n', '|').replace('\n', '|').replace('\r', '|') if raw_description else ""
                
                # Part Identification in die Beschreibung integrieren, falls vorhanden
                part_ids = item.get('partIdentification', [])
                part_details = []
                if part_ids and isinstance(part_ids, list):
                    for part_id in part_ids:
                        if not isinstance(part_id, dict):
                            continue
                        
                        part_type = part_id.get('partType', '')
                        part_code = part_id.get('partCode', '')
                        
                        if part_type and part_code:
                            part_details.append(f"{part_type}: {part_code}")
                        elif part_code:
                            part_details.append(f"Part: {part_code}")
                    
                    if part_details:
                        part_text = " | ".join(part_details)
                        # Zur Beschreibung hinzufügen
                        description = f"{description} | {part_text}" if description else part_text
                        logging.info(f"Added part identification: {part_text}")
                
                # Equipment-Section in die Beschreibung integrieren, falls vorhanden
                equip_details = []
                if 'equipmentSection' in item and item['equipmentSection'] is not None:
                    equip = item['equipmentSection']
                    
                    # Equipment-Details sammeln
                    if equip.get('name'):
                        equip_details.append(f"Equipment: {equip.get('name')}")
                    if equip.get('accountNumber'):
                        equip_details.append(f"Account: {equip.get('accountNumber')}")
                    if equip.get('serialNumber'):
                        equip_details.append(f"Serial: {equip.get('serialNumber')}")
                    if equip.get('manufacturer'):
                        equip_details.append(f"Manufacturer: {equip.get('manufacturer')}")
                    if equip.get('modelNumber'):
                        equip_details.append(f"Model: {equip.get('modelNumber')}")
                    if equip.get('departmentType'):
                        equip_details.append(f"Department: {equip.get('departmentType')}")
                    
                    # Equipment-Details zur Beschreibung hinzufügen (mit Pipe als Trennzeichen)
                    if equip_details:
                        equipment_text = " | ".join(equip_details)
                        # Zeilenumbrüche in Equipment-Details ersetzen
                        equipment_text = equipment_text.replace('\r\n', '|').replace('\n', '|').replace('\r', '|')
                        
                        # Zur Beschreibung hinzufügen
                        description = f"{description} | {equipment_text}" if description else equipment_text
                
                # Add comment to description if available
                comment = item.get('comment')
                comment_text = ""
                if comment:
                    comment_text = comment.replace('\r\n', '|').replace('\n', '|').replace('\r', '|')
                    description = f"{description} | Comment: {comment_text}" if description else f"Comment: {comment_text}"
                
                number = item.get('number', '')
                logging.info(f"Item number: {number}, Description: {description}")
                unit_of_measure = item.get('unitOfMeasure', 'PCE')
                logging.info(f"Unit of measure: {unit_of_measure}")
                logging.info(f"Quantity: {quantity_str} (original: {quantity})")
                logging.info(f"Unit price: {unit_price_str} (original: {unit_price})")   

                # Add to processed_data dictionary
                processed_item = {
                    "itemId": item.get('id', f"item-{number}"),
                    "number": number,
                    "description": raw_description,
                    "formattedDescription": description,
                    "unitOfMeasure": unit_of_measure,
                    "quantity": quantity,  # Store original value in processed data
                    "unitPrice": unit_price,  # Store original value in processed data
                    "partDetails": part_details,
                    "equipmentDetails": equip_details,
                    "comment": comment_text
                }
                processed_data["lineItems"].append(processed_item)

                # Format document lines with comma decimal separator
                if docType == "RequestForQuote":                
                    item_line = (
                        f"{document_line};;{number} {description};"
                        f"{unit_of_measure};{quantity_str};{unit_price_str};1;0,00;;0;0;0;0;;;;;;"
                    )
                elif docType == "PurchaseOrder":
                    item_line = (
                        f"{document_line};;{number} {description};"
                        f"{unit_of_measure};{quantity_str};{unit_price_str};;1;{discount_item_prozent_str};;0;0;0;0;0;0;;;;;;0;0;;;;;"
                    )
                csv_content.append(item_line)
            except Exception as item_error:
                logging.error(f"Error processing item {item.get('id', 'unknown')}: {item_error}")
                continue

        # Return joined CSV and processed data
        return "\n".join(csv_content), processed_data
    except KeyError as e:
        logging.error(f"Missing key in data: {e}")
        raise ValueError(f"Invalid data format: Missing key {e}")
    except Exception as e:
        logging.error(f"Error transforming data to Collmex format: {e}")
        raise

def format_document_date(date_value):
    """
    Formats a date string or datetime object into the YYYYMMDD format required by Collmex.
    Can handle various date formats.
    
    Args:
        date_value: A string date in various formats or a datetime object
        
    Returns:
        String formatted date in YYYYMMDD format or today's date if parsing fails
    """
    # If None is passed, use current datetime
    if date_value is None:
        logging.info("No date value provided, using current UTC time")
        return datetime.utcnow().strftime("%Y%m%d")
    
    # If already a datetime object, just format it
    if isinstance(date_value, datetime):
        return date_value.strftime("%Y%m%d")
    
    # Handle string dates with various formats
    if isinstance(date_value, str):
        # Try common date formats
        date_formats = [
            # ISO formats
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ", 
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            # Date only formats
            "%Y-%m-%d",
            "%d.%m.%Y",
            "%m/%d/%Y",
            "%d/%m/%Y",
            # Already in target format
            "%Y%m%d"
        ]
        
        # Special handling for ISO format with timezone offset
        if 'Z' in date_value:
            try:
                # Replace Z with UTC timezone indicator
                date_obj = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                return date_obj.strftime("%Y%m%d")
            except ValueError:
                pass
                
        # Try each format until one works
        for fmt in date_formats:
            try:
                date_obj = datetime.strptime(date_value, fmt)
                return date_obj.strftime("%Y%m%d")
            except ValueError:
                continue
    
    # If we couldn't parse the date, log a warning and use current date
    logging.warning(f"Could not parse date: {date_value}, using current UTC time")
    return datetime.utcnow().strftime("%Y%m%d")

def format_decimal_for_collmex(value):
    """
    Formats a decimal value for Collmex using comma as decimal separator.
    
    Args:
        value: A numeric value or string containing a number
        
    Returns:
        String with the value formatted using comma as decimal separator
    """
    if value is None:
        return "0,00"
        
    # Convert to float if it's a string with period as decimal separator
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            logging.warning(f"Could not parse decimal value: {value}, using 0,00")
            return "0,00"            
       # Format with 2 decimal places and comma as decimal separator
    return f"{float(value):.2f}".replace('.', ',')    
        
def transformDataToCollmex(data, docType="RequestForQuote"):
    """
    Transform JSON data into Collmex CSV format (semicolon-separated) and return processed line items.
    
    Args:
        data: The JSON data to transform.
        docType: Type of document (RequestForQuote, PurchaseOrder)
        
    Returns:
        tuple: (csv_string, processed_data)
            - csv_string: A string in Collmex CSV format
            - processed_data: Dictionary with document and line items information
    """
    try:
        # Start with the LOGIN line
        login_line = f"LOGIN;{collmex_login};{collmex_password}"
        document_id = data.get("Belegnr", "-10000")
        firma = "1 Hamburg Factorship GmbH"
        id_kunde = "99998"
        payment_terms = "0 30 Tage ohne Abzug"
        currency = "EUR"
        delivery_terms = "0 Standard"
        preis_gruppe = "0 Standard"
        offer_text = "We herewith offer according to Orgalime S2012-conditions."
        order_text ="We herewith acknowledge your order, based on Orgalime-conditions S2012."
        end_text = "Time of delivery: \n Terms of delivery: ex works \n Validity: 2 months after offer"
        customerRef = data.get("referenceNumber", "")
        documentDate = format_document_date(data.get("submittedDate"))
        
        # Convert decimal values from portal data (with period) to Collmex format (with comma)
        discount_proz = data.get("discountPercentage", 0.0)
        discount_proz_str = format_decimal_for_collmex(discount_proz)
        
        freight_cost = data.get("freightCost", 0.0)
        freight_cost_str = format_decimal_for_collmex(freight_cost)

        # Initialize processed data dictionary
        processed_data = {
            "documentInfo": {
                "documentId": document_id,
                "documentType": docType,
                "customerRef": customerRef,
                "documentDate": documentDate,
                "currency": currency
            },
            "lineItems": []
        }

        csv_content = [login_line]
        logging.info(f"Data: {data}")

        # Create the document header
        if docType == "RequestForQuote":
            document_line = (
                f"CMXQTN;{document_id};;0;{firma};{id_kunde};;;;;;;;;;;;;;;;;;;;;;0;{documentDate};;{payment_terms};{currency};{preis_gruppe}"
                f";0;0,00;;\"{offer_text}\";\"{end_text}\";;0;;1;0;0;0,00;;0 Neu;;0;0,00;0,00;;;;;;;;;;;;;;;;;;0"
            )
        elif docType == "PurchaseOrder":
            document_line = (
                f"CMXORD-2;{document_id};;0;{firma};{id_kunde};;;;;;;;;;;;;;;;;;;;;;0;{customerRef};{documentDate};;{payment_terms};{currency};{preis_gruppe}"
                f";0;{discount_proz_str};;\"{order_text}\";\"{end_text}\";;1;1;0;0 Neu;1;0;0;;0,00;;;;0;{freight_cost_str};0,00;;;;;;;;;;;;;;;;;0"
            )
        logging.info(f"Document line: {document_line}")
        
        # Add line items for the document
        line_items = data.get("lineItems", [])
        if not line_items:
            logging.warning("No line items found in data")
            
        for item in line_items:
            try:
                # Process item description and details
                logging.info(f"Processing item: {item}")
                raw_description = item.get('description', '')
                
                # Convert decimal values from portal data format to Collmex format
                discount_item_prozent = item.get('discountPercentage', 0.0)
                discount_item_prozent_str = format_decimal_for_collmex(discount_item_prozent)
                
                quantity = item.get('quantity', 0)
                quantity_str = format_decimal_for_collmex(quantity)
                
                unit_price = item.get('unitPrice', 0)
                unit_price_str = format_decimal_for_collmex(unit_price)
                
                description = raw_description.replace('\r\n', '|').replace('\n', '|').replace('\r', '|') if raw_description else ""
                
                # Part Identification in die Beschreibung integrieren, falls vorhanden
                part_ids = item.get('partIdentification', [])
                part_details = []
                if part_ids and isinstance(part_ids, list):
                    for part_id in part_ids:
                        if not isinstance(part_id, dict):
                            continue
                        
                        part_type = part_id.get('partType', '')
                        part_code = part_id.get('partCode', '')
                        
                        if part_type and part_code:
                            part_details.append(f"{part_type}: {part_code}")
                        elif part_code:
                            part_details.append(f"Part: {part_code}")
                    
                    if part_details:
                        part_text = " | ".join(part_details)
                        # Zur Beschreibung hinzufügen
                        description = f"{description} | {part_text}" if description else part_text
                        logging.info(f"Added part identification: {part_text}")
                
                # Equipment-Section in die Beschreibung integrieren, falls vorhanden
                equip_details = []
                if 'equipmentSection' in item and item['equipmentSection'] is not None:
                    equip = item['equipmentSection']
                    
                    # Equipment-Details sammeln
                    if equip.get('name'):
                        equip_details.append(f"Equipment: {equip.get('name')}")
                    if equip.get('accountNumber'):
                        equip_details.append(f"Account: {equip.get('accountNumber')}")
                    if equip.get('serialNumber'):
                        equip_details.append(f"Serial: {equip.get('serialNumber')}")
                    if equip.get('manufacturer'):
                        equip_details.append(f"Manufacturer: {equip.get('manufacturer')}")
                    if equip.get('modelNumber'):
                        equip_details.append(f"Model: {equip.get('modelNumber')}")
                    if equip.get('departmentType'):
                        equip_details.append(f"Department: {equip.get('departmentType')}")
                    
                    # Equipment-Details zur Beschreibung hinzufügen (mit Pipe als Trennzeichen)
                    if equip_details:
                        equipment_text = " | ".join(equip_details)
                        # Zeilenumbrüche in Equipment-Details ersetzen
                        equipment_text = equipment_text.replace('\r\n', '|').replace('\n', '|').replace('\r', '|')
                        
                        # Zur Beschreibung hinzufügen
                        description = f"{description} | {equipment_text}" if description else equipment_text
                
                # Add comment to description if available
                comment = item.get('comment')
                comment_text = ""
                if comment:
                    comment_text = comment.replace('\r\n', '|').replace('\n', '|').replace('\r', '|')
                    description = f"{description} | Comment: {comment_text}" if description else f"Comment: {comment_text}"
                
                number = item.get('number', '')
                logging.info(f"Item number: {number}, Description: {description}")
                unit_of_measure = item.get('unitOfMeasure', 'PCE')
                logging.info(f"Unit of measure: {unit_of_measure}")
                logging.info(f"Quantity: {quantity_str} (original: {quantity})")
                logging.info(f"Unit price: {unit_price_str} (original: {unit_price})")   

                # Add to processed_data dictionary
                processed_item = {
                    "itemId": item.get('id', f"item-{number}"),
                    "number": number,
                    "description": raw_description,
                    "formattedDescription": description,
                    "unitOfMeasure": unit_of_measure,
                    "quantity": quantity,  # Store original value in processed data
                    "unitPrice": unit_price,  # Store original value in processed data
                    "partDetails": part_details,
                    "equipmentDetails": equip_details,
                    "comment": comment_text
                }
                processed_data["lineItems"].append(processed_item)

                # Format document lines with comma decimal separator
                if docType=="RequestForQuote":                
                    item_line = (
                        f"{document_line};;{number} {description};"
                        f"{unit_of_measure};{quantity_str};{unit_price_str};1;0,00;;0;0;0;0;;;;;;"
                    )
                elif docType=="PurchaseOrder":
                    item_line = (
                        f"{document_line};;{number} {description};"
                        f"{unit_of_measure};{quantity_str};{unit_price_str};;1;{discount_item_prozent_str};;0;0;0;0;0;0;;;;;;0;0;;;;;"
                    )
                csv_content.append(item_line)
            except Exception as item_error:
                logging.error(f"Error processing item {item.get('id', 'unknown')}: {item_error}")
                continue

        # Return joined CSV and processed data
        return "\n".join(csv_content), processed_data
    except KeyError as e:
        logging.error(f"Missing key in data: {e}")
        raise ValueError(f"Invalid data format: Missing key {e}")
    except Exception as e:
        logging.error(f"Error transforming data to Collmex format: {e}")
        raise

