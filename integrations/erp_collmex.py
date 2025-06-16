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

class ERPcollmexIntegration:
    @staticmethod
    def send_to_erp(data):
        """
        Send data to the Collmex ERP system.
        :param data: The data to send (formatted as required by Collmex).
        :return: The response from the Collmex API.
        """
        logging.info("Sending document to ERP Collmex...")

        # Collmex API URL
        api_url = collmex_api_url

        # Headers for the request
        headers = {
            "Content-Type": "text/csv",  # Collmex expects plain text
        }

        try:
            # Send the POST request to Collmex
            mydata = transformDataToCollmex(data)
            logging.info(f"Data to send: {mydata}")
            response = requests.post(api_url, data=mydata, headers=headers)
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
                elif line.startswith("MESSAGE"):
                    # Extract record count (last part of the message)
                    match = re.search(r"Es wurden (\d+) Datensätze verarbeitet", line)
                    if match:
                        record_count = int(match.group(1))

            # Return the extracted values
            return {
                "ERPNummer": erp_number,
                "Recordcount": record_count
            }
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending document to ERP Collmex: {e}")
            return None

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
        login_line = f"LOGIN;{collmex_login};{collmex_password}"
        document_id = data.get("Belegnr", "-10000")
        firma = "1 Hamburg Factorship GmbH"
        id_kunde = "10033"
        payment_terms = "0 30 Tage ohne Abzug"
        currency = "EUR"
        delivery_terms = "0 Standard"
        preis_gruppe = "0 Standard"
        offer_text = "We herewith offer according to Orgalime S2012-conditions."
        end_text = "Time of delivery: \n Terms of delivery: ex works \n Validity: 2 months after offer"

        csv_content = [login_line]
        logging.info(f"Data: {data}")

        # Create the document header (CMXQTN)
        document_line = (
            f"CMXQTN;{document_id};;0;{firma};{id_kunde};;;;;;;;;;;;;;;;;;;;;;0;20250329;;{payment_terms};{currency};{preis_gruppe}"
            f";0;0,00;;\"{offer_text}\";\"{end_text}\";;0;;1;0;0;0,00;;0 Neu;;0;0,00;0,00;;;;;;;;;;;;;;;;;;0"
        )

        # Add line items for the document
        for item in data.get("lineItems", []):
            # Beschreibung mit Zeilenumbrüchen durch Pipe-Zeichen ersetzen
            raw_description = item.get('description', '')
            description = raw_description.replace('\r\n', '|').replace('\n', '|').replace('\r', '|') if raw_description else ""
            
            # Equipment-Section in die Beschreibung integrieren, falls vorhanden
            if 'equipmentSection' in item:
                equip = item['equipmentSection']
                equip_details = []
                
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
            
            number = item.get('number', '')
            unit_of_measure = item.get('unitOfMeasure', 'PCE')
            quantity = item.get('quantity', 0)
            unit_price = item.get('unitPrice', 0)
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