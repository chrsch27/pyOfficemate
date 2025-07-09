import logging
import requests
import os
import json
from io import StringIO
import csv
from datetime import datetime

def get_sharepoint_access_token():
    """
    Fetch the SharePoint access token using OAuth 2.0.
    :return: The access token as a string.
    """
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    resource =  "https://factorship.sharepoint.com" # Resource for Microsoft Graph API

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": f"{resource}/.default"
    }

    try:
        response = requests.post(token_url, data=payload)
        response.raise_for_status()
        token_data = response.json()
        return token_data.get("access_token")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching SharePoint access token: {e}")
        return None

def get_graph_access_token():
    """
    Fetch the Microsoft Graph access token using OAuth 2.0.
    :return: The access token as a string.
    """
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    resource = "https://graph.microsoft.com"

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": f"{resource}/.default"
    }

    try:
        response = requests.post(token_url, data=payload)
        response.raise_for_status()
        token_data = response.json()
        return token_data.get("access_token")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching Microsoft Graph access token: {e}")
        return None

def get_site_id(access_token, hostname, site_name):
    """
    Fetch the site ID for a given SharePoint site.
    :param access_token: The Microsoft Graph access token.
    :param hostname: The hostname of the SharePoint site (e.g., factorship.sharepoint.com).
    :param site_name: The name of the site (e.g., AngeboteundAuftrge).
    :return: The site ID as a string.
    """
    url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:/sites/{site_name}"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        site_data = response.json()
        return site_data.get("id")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching site ID: {e}")
        return None

def get_list_id(access_token, site_id, list_name):
    """
    Fetch the list ID for a given list on a SharePoint site.
    :param access_token: The Microsoft Graph access token.
    :param site_id: The ID of the SharePoint site.
    :param list_name: The name of the list (e.g., Anfragen).
    :return: The list ID as a string.
    """
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        lists = response.json().get("value", [])
        for lst in lists:
            if lst.get("name") == list_name:
                return lst.get("id")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching list ID: {e}")
        return None

def create_list_item(access_token, site_id, list_id, item_data):
    """
    Create a new item in a SharePoint list.
    :param access_token: The Microsoft Graph access token.
    :param site_id: The ID of the SharePoint site.
    :param list_id: The ID of the SharePoint list.
    :param item_data: The data for the new list item.
    :return: The response from the API.
    """
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "fields": item_data
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        # Hier bekommst du den Text der Fehlermeldung
        logging.error(
            f"HTTPError creating list item: {http_err}, "
            f"Status code: {response.status_code}, "
            f"Response content: {response.text}"
        )
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"RequestException creating list item: {e}")
        return None
    
def link_documents_in_sharepoint(data, source_document_type, target_document_type, 
                                source_id_field, target_id_field, filter_field, update_field):
    """
    Generic function to link documents in SharePoint by updating fields.
    
    Args:
        data: The document data
        source_document_type: Type of the source document (e.g., 'Quote', 'PurchaseOrder')
        target_document_type: Type of the target document to link to (e.g., 'RequestForQuote')
        source_id_field: Field name in 'data' containing the source document ID (e.g., 'id')
        target_id_field: Field name in 'data' containing the target document ID to link to (e.g., 'requestForQuoteId')
        filter_field: Field name in SharePoint to filter by (e.g., 'RFQID')
        update_field: Field name in SharePoint to update (e.g., 'QuoteID')
        
    Returns:
        Dictionary with result and status information
    """
    logging.info(f"Processing {source_document_type} document for SharePoint")
    
    # 1. Standard processing using existing send_to_erp function
    result = "" # Uncomment when needed: ERPsharepointIntegration.send_to_erp(data)
    
    # 2. Link documents if possible
    try:
        # Extract the necessary IDs from the data
        target_document_id = data.get(target_id_field)
        logging.info(f"Target document ID ({target_id_field}): {target_document_id}")
        source_document_id = data.get(source_id_field)
        logging.info(f"Source document ID ({source_id_field}): {source_document_id}")   
        
        if not target_document_id or not source_document_id:
            logging.warning(f"Missing {target_id_field} or {source_id_field} in {source_document_type} data. Cannot link documents.")
            return {"type": source_document_type, "result": result, "linkStatus": "missing_ids"}
        
        logging.info(f"Linking {source_document_type} {source_document_id} to {target_document_type} {target_document_id}")
        
        # Get Graph API access token
        access_token = get_graph_access_token()
        if not access_token:
            logging.error("Failed to fetch Microsoft Graph access token")
            return {"type": source_document_type, "result": result, "linkStatus": "token_error"}
        
        # Get site and list information
        hostname = "factorship.sharepoint.com"
        site_name = "AngeboteundAuftrge"
        
        site_id = get_site_id(access_token, hostname, site_name)
        if not site_id:
            logging.error("Failed to fetch site ID")
            return {"type": source_document_type, "result": result, "linkStatus": "site_error"}
        
        anfragen_list_id = get_list_id(access_token, site_id, "Anfragen")
        if not anfragen_list_id:
            logging.error("Failed to fetch list ID for 'Anfragen'")
            return {"type": source_document_type, "result": result, "linkStatus": "list_error"}
        
        # Search for the target item in the SharePoint list
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Prefer": "HonorNonIndexedQueriesWarningMayFailRandomly"
        }
        
        filter_url = (
            f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{anfragen_list_id}/items"
            f"?expand=fields&$filter=fields/{filter_field} eq '{target_document_id}'"
        )
        
        response = requests.get(filter_url, headers=headers)
        response.raise_for_status()
        
        items = response.json().get("value", [])
        
        if not items:
            logging.warning(f"No {target_document_type} found with {filter_field}={target_document_id}")
            return {"type": source_document_type, "result": result, "linkStatus": f"{target_document_type.lower()}_not_found"}
        
        # Get the first matching item
        target_item = items[0]
        target_item_id = target_item["id"]
        
        # Extract the ERPNr from the found SharePoint item
        erp_number = target_item.get("fields", {}).get("ERPNr", "UNKNOWN")
        logging.info(f"Found ERPNr '{erp_number}' for {target_document_type} {target_document_id}")
        
        # Update the target item with the source document ID
        update_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{anfragen_list_id}/items/{target_item_id}/fields"
        
        # Create update data dictionary with the standard field update
        update_data = {
            update_field: source_document_id
        }
        
        # Add ERP number to appropriate fields based on document type
        if target_document_type == "RequestForQuote":
            update_data["ERPNummer"] = erp_number
            logging.info(f"Adding ERPNr '{erp_number}' to field 'ERPNummer' for RequestForQuote")
        elif target_document_type == "PurchaseOrder":
            update_data["requestedDeliveryDate"] = data.get("requestedDeliveryDate", "")
            update_data["ERPOrderNummer"] = erp_number
            update_data["PortalDataJsonOrder"] = json.dumps(data)
            update_data["POID"] = source_document_id
            logging.info(f"Adding ERPNr '{erp_number}' to field 'ERPOrderNummer' for PurchaseOrder")
        
        update_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Log the update data for troubleshooting
        logging.info(f"Updating SharePoint item {target_item_id} with data: {json.dumps(update_data)}")
        
        update_response = requests.patch(update_url, headers=update_headers, json=update_data)
        update_response.raise_for_status()
        
        logging.info(f"Successfully linked {source_document_type} {source_document_id} to {target_document_type} {target_document_id}")
        return {
            "type": source_document_type, 
            "result": result, 
            "linkStatus": "success",
            "targetItemId": target_item_id,
            "ERPNummer": erp_number
        }
        
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error linking {source_document_type} to {target_document_type}: {http_err}, " 
                        f"Response: {http_err.response.text if hasattr(http_err, 'response') else 'No response'}")
        return {"type": source_document_type, "result": result, "linkStatus": "http_error", "error": str(http_err)}
    except Exception as e:
        logging.error(f"Error linking {source_document_type} to {target_document_type}: {str(e)}")
        return {"type": source_document_type, "result": result, "linkStatus": "error", "error": str(e)}

class ERPsharepointIntegration:
    @staticmethod
    def send_to_erp(data):
        access_token = get_graph_access_token()
        if not access_token:
            return {"status": "error", "message": "Failed to fetch Microsoft Graph access token."}

        hostname = "factorship.sharepoint.com"
        site_name = "AngeboteundAuftrge"

        ERPNumber = data.get("ERPNummer", "NNNNNNN")

        # Get site ID
        site_id = get_site_id(access_token, hostname, site_name)
        if not site_id:
            return {"status": "error", "message": "Failed to fetch site ID."}

        # Get list IDs
        header_list_id = get_list_id(access_token, site_id, "Anfragen")
        line_items_list_id = get_list_id(access_token, site_id, "Anfragepos")
        if not header_list_id or not line_items_list_id:
            return {"status": "error", "message": "Failed to fetch list IDs."}

        # Create header item
        header_data = {
            "Title": data["referenceNumber"],  # Titel des Angebots
            "DokumentDatum": data["createdDate"][:10],  # Erstellungsdatum
            "Dokumentnr": data["referenceNumber"],  # Dokumentnummer
            "Referenznr": data["subject"],  # Referenznummer
            "Kunde": data["buyer"]["name"],  # Name des Lieferanten
            "Dokumenttyp": data["type"],  # Dokumenttyp (z. B. quotation)
            "Spezifikation": data.get("subject", ""),  # Spezifikation
            #"DatumOfferLieferant": data["submittedDate"],  # Angebotsdatum des Lieferanten
            "LieferantDokumentNr": "",  # Dokumentnummer des Lieferanten
            "NachrichtenID": data.get("id", ""),  # Nachrichten-ID
            "Customer": data["buyer"]["name"],  # Kunde
            "CustomerID": data["buyer"]["tnId"],  # Kunden-ID
            #"comment": data["comment"],  # Kommentar
            #"deliveryPortCode": data["deliveryPortCode"],  # Code des Lieferhafens
            #"deliveryPortCountryCode": data["deliveryPortCountryCode"],  # Land des Lieferhafens
            #"deliveryPortName": data["deliveryPortName"],  # Name des Lieferhafens
            "vesselName": data["vessel"]["name"],  # Name des Schiffs
            "vesselID": data["vessel"]["imoNumber"],  # ID des Schiffs
            "RFQID": data["id"],  # RFQ-ID
            "currency": data["currency"]["code"],  # Währung
            "requestedDeliveryDate": data["requestedDeliveryDate"],  # Großschreibung am Anfang
            "subject": data["subject"],  # Betreff
            #"termsAndConditions": data["termsAndConditions"],  # Bedingungen
            #"buyerContact": data["buyerContact"],  # Kontakt des Käufers
            #"portal": "shipserv",
            "PortalDataJson": json.dumps(data),  # JSON-Daten des Portals
            "ERPNr": ERPNumber  # ERP-Nummer
        }

        logging.info(f"Creating header item with data: {header_data}")
        header_response = create_list_item(access_token, site_id, header_list_id, header_data)
        if not header_response:
            return {"status": "error", "message": "Failed to create header item."}

        # Get the ID of the created header item
        header_item_id = header_response.get("id")

        # Create line items
        for item in data.get("lineItems", []):
            equipment_section = item.get("equipmentSection", {})
    
            # Berechnung der Langtext-Felder nur, wenn equipmentSection vorhanden ist
            langtext = f"{item.get('comment', '')}"
            if equipment_section:
                langtext += f" {equipment_section.get('accountNumber', '')} {equipment_section.get('description', '')} {equipment_section.get('manufacturer', '')} {equipment_section.get('modelNumber', '')} {equipment_section.get('serialNumber', '')} {equipment_section.get('drawingNumber', '')}"

            line_item_data = {
                "Title": f"{ERPNumber}-{header_item_id}-{item.get('number','999')}",  # Titel des Angebots
                "Position": item["number"],  # Position der Anfrage
                "Artikelnr": item.get("partIdentification", [{}])[0].get("partCode", ""),  # Artikelnummer
                "Artikeltext": item["description"],  # Beschreibung des Artikels
                "Menge": item["quantity"],  # Menge
                "UnitPrice": item["unitPrice"],  # Einzelpreis
                "Discount": item.get("discountCost", 0),  # Rabatt
                "Langtext": langtext,  # Langtext
                "AnfrageID": int(header_item_id)
            }
            logging.info(f"Creating line item with data: {json.dumps(line_item_data, indent=2)}")
            create_list_item(access_token, site_id, line_items_list_id, line_item_data)

        return {"status": "success", "message": "Data sent to SharePoint successfully."}


    # Existing send_to_erp method is preserved exactly as is
    
    @staticmethod
    def send_request_for_quote_to_erp(data):
        """
        Verarbeitet ein RequestForQuote und speichert es in SharePoint.
        Verwendet die bestehende send_to_erp Implementierung.
        """
        logging.info("Processing RequestForQuote document for SharePoint")
        result = ERPsharepointIntegration.send_to_erp(data)
        return {"type": "RequestForQuote", "result": result}
    
    @staticmethod
    def send_quote_to_erp(data):
        """
        Verarbeitet ein Quote und speichert es in SharePoint.
        Sucht auch nach dem zugehörigen RequestForQuote und verlinkt diesen.
        """
        return link_documents_in_sharepoint(
            data=data,
            source_document_type="Quote",
            target_document_type="RequestForQuote",
            source_id_field="id",
            target_id_field="requestForQuoteId",
            filter_field="RFQID",
            update_field="QuoteID"
        )

    @staticmethod
    def send_purchase_order_to_erp(data):
        """
        Verarbeitet ein PurchaseOrder und speichert es in SharePoint.
        Sucht auch nach dem zugehörigen Quote und verlinkt diesen.

        """
        ERPNumber = data.get("ERPNummer", "NNNNNNN")
        return link_documents_in_sharepoint(
            data=data,
            source_document_type="RequestForQuote",
            target_document_type="PurchaseOrder",
            source_id_field="id",
            target_id_field="requestForQuoteId",
            filter_field="RFQID",
            update_field="POID"

        )

    @staticmethod
    def send_purchase_order_confirmation_to_erp(data):
        """
        Verarbeitet ein PurchaseOrderConfirmation und speichert es in SharePoint.
        Sucht auch nach dem zugehörigen PurchaseOrder und verlinkt diesen.
        """
        return link_documents_in_sharepoint(
            data=data,
            source_document_type="PurchaseOrderConfirmation",
            target_document_type="PurchaseOrder",
            source_id_field="id",
            target_id_field="purchaseOrderId",
            filter_field="POID",
            update_field="POConfirmationID"
        )
    
    # Fetch methods
    
    @staticmethod
    def fetch_request_for_quote(document_id):
        """
        Holt ein RequestForQuote-Dokument aus SharePoint basierend auf der ERPNr.
        """
        logging.info(f"Fetching RequestForQuote document {document_id} from SharePoint")
        portal_data = ERPsharepointIntegration.fetch_portal_data_by_erp_number(document_id)
        if portal_data:
            return {"id": document_id, "type": "RequestForQuote", "data": portal_data}
        return {"id": document_id, "type": "RequestForQuote", "error": "Document not found"}
    
    @staticmethod
    def fetch_quote(document_id):
        """
        Holt ein Quote-Dokument aus SharePoint basierend auf der ERPNr.
        """
        logging.info(f"Fetching Quote document {document_id} from SharePoint")
        portal_data = ERPsharepointIntegration.fetch_portal_data_by_erp_number(document_id)
        if portal_data:
            return {"id": document_id, "type": "Quote", "data": portal_data}
        return {"id": document_id, "type": "Quote", "error": "Document not found"}
    
    @staticmethod
    def fetch_purchase_order(document_id):
        """
        Holt ein PurchaseOrder-Dokument aus SharePoint basierend auf der ERPNr.
        """
        logging.info(f"Fetching PurchaseOrder document {document_id} from SharePoint")
        portal_data = ERPsharepointIntegration.fetch_portal_data_by_erp_number(document_id)
        if portal_data:
            return {"id": document_id, "type": "PurchaseOrder", "data": portal_data}
        return {"id": document_id, "type": "PurchaseOrder", "error": "Document not found"}
    
    @staticmethod
    def fetch_requisition(document_id):
        """
        Holt ein Requisition-Dokument aus SharePoint basierend auf der ERPNr.
        """
        logging.info(f"Fetching Requisition document {document_id} from SharePoint")
        portal_data = ERPsharepointIntegration.fetch_portal_data_by_erp_number(document_id)
        if portal_data:
            return {"id": document_id, "type": "Requisition", "data": portal_data}
        return {"id": document_id, "type": "Requisition", "error": "Document not found"}
    
    @staticmethod
    def fetch_purchase_order_confirmation(document_id):
        """
        Holt ein PurchaseOrderConfirmation-Dokument aus SharePoint basierend auf der ERPNr.
        """
        logging.info(f"Fetching PurchaseOrderConfirmation document {document_id} from SharePoint")
        portal_data = ERPsharepointIntegration.fetch_portal_data_by_erp_number(document_id)
        if portal_data:
            return {"id": document_id, "type": "PurchaseOrderConfirmation", "data": portal_data}
        return {"id": document_id, "type": "PurchaseOrderConfirmation", "error": "Document not found"}
    
    @staticmethod
    def fetch_document(document_id, document_type):
        """
        Generische Methode zum Abrufen von Dokumenten aus SharePoint.
        Leitet an die spezifischen Fetch-Methoden weiter.
        """
        logging.info(f"Fetching generic document {document_id} of type {document_type} from SharePoint")
        
        # Delegate to the appropriate type-specific method
        if document_type == "RequestForQuote":
            return ERPsharepointIntegration.fetch_request_for_quote(document_id)
        elif document_type == "Quote":
            return ERPsharepointIntegration.fetch_quote(document_id)
        elif document_type == "PurchaseOrder":
            return ERPsharepointIntegration.fetch_purchase_order(document_id)
        elif document_type == "Requisition":
            return ERPsharepointIntegration.fetch_requisition(document_id)
        elif document_type == "PurchaseOrderConfirmation":
            return ERPsharepointIntegration.fetch_purchase_order_confirmation(document_id)
        else:
            # Unknown document type
            logging.warning(f"Unknown document type: {document_type}")
            return {"id": document_id, "type": "Unknown", "error": f"Unsupported document type: {document_type}"}

    @staticmethod
    def fetch_portal_data_by_erp_number(document_id,documentType):
        """
        Sucht in der SharePoint-Liste 'Anfragen' den Eintrag mit ERPNr = document_id
        und gibt das Feld 'PortalDataJson' zurück (als dict).
        """
        if documentType == "RequestForQuote":
            lookForERPnr = "ERPNr"
            portalDataSource="PortalDataJson"
        elif documentType == "PurchaseOrder":
            lookForERPnr = "ERPOrderNummer"
            portalDataSource="PortalDataJsonOrder"
        access_token = get_graph_access_token()
        if not access_token:
            logging.error("Failed to fetch Microsoft Graph access token.")
            return None

        hostname = "factorship.sharepoint.com"
        site_name = "AngeboteundAuftrge"
        site_id = get_site_id(access_token, hostname, site_name)
        if not site_id:
            logging.error("Failed to fetch site ID.")
            return None

        anfragen_list_id = get_list_id(access_token, site_id, "Anfragen")
        if not anfragen_list_id:
            logging.error("Failed to fetch list ID for 'Anfragen'.")
            return None
        logging.info(f"List ID for 'Anfragen': {anfragen_list_id} Dokumentid: {document_id}")
        # Suche Einträge in der Liste, bei denen fields/ERPNr = 'document_id'
        query_url = (
            f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{anfragen_list_id}/items"
            f"?expand=fields&$filter=fields/{lookForERPnr} eq '{document_id}'"
        )
        logging.info(f"Query URL: {query_url}")
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            response = requests.get(query_url, headers=headers)
            response.raise_for_status()
            items = response.json().get("value", [])

            if not items:
                logging.info(f"No items found with ERPNr = {document_id}.")
                return None

            # Nimm z.B. das erste gefundene Element
            fields = items[0].get("fields", {})
            portal_data_json = fields.get(portalDataSource, None)
            if not portal_data_json:
                logging.info(f"No 'PortalDataJson' found for item with ERPNr={document_id}")
                return None

            try:
                # JSON in ein Python-Dict parsen und zurückgeben
                return json.loads(portal_data_json)
            except json.JSONDecodeError:
                # Falls das Feld kein gültiges JSON enthält, gib den Roh-String zurück
                return portal_data_json

        except requests.exceptions.RequestException as e:
            logging.error(f"Error while querying SharePoint: {e}")
            return None

