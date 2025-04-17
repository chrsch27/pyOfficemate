import logging
import requests
import os
class ERPpdsIntegration:
    @staticmethod
    def send_to_erp(data):
        logging.info("Sending document to ERP PDS...")
        return data
        api_url = "https://erp-a.example.com/api/documents"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('ERP_A_TOKEN')}"
        }
        try:
            response = requests.post(api_url, json=data, headers=headers)
            response.raise_for_status()
            logging.info(f"Document sent to ERP Collmex successfully: {response.status_code}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending document to ERP A: {e}")
            return None
    
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