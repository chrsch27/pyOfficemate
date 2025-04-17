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
            #"requestedDeliveryDate": data["requestedDeliveryDate"],  # Angefragtes Lieferdatum
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
                "Langtext": langtext,  # Langtext
                "AnfrageID": int(header_item_id)
            }
            logging.info(f"Creating line item with data: {json.dumps(line_item_data, indent=2)}")
            create_list_item(access_token, site_id, line_items_list_id, line_item_data)

        return {"status": "success", "message": "Data sent to SharePoint successfully."}

    @staticmethod
    def fetch_document(document_id, document_type):
        """
        Fetch a document from the PDS ERP system.
        :param document_id: The unique document ID.
        :param document_type: The type of the document.
        :return: The document data.
        """
        logging.info(f"Fetching document {document_id} of type {document_type} from ERP PDS...")
        api_url = f"https://erp-pds.example.com/api/{document_type}/{document_id}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('ERP_PDS_TOKEN')}"
        }
        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching document from ERP PDS: {e}")
            return None

    @staticmethod
    def fetch_portal_data_by_erp_number(document_id):
        """
        Sucht in der SharePoint-Liste 'Anfragen' den Eintrag mit ERPNr = document_id
        und gibt das Feld 'PortalDataJson' zurück (als dict).
        """
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
            f"?expand=fields&$filter=fields/ERPNr eq '{document_id}'"
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
            portal_data_json = fields.get("PortalDataJson")
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