import logging
import base64
import os
import json
import tempfile
import io
import requests
import mimetypes
import azure.functions as func
from typing import Optional, Dict, Any, Union

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
    
    @staticmethod
    def upload_document_to_offer(
        base64_string: str, 
        bearer_token: str, 
        angebot_uuid: str, 
        dokumenten_typ_uuid: str,
        file_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Uploads a document to a PDS offer.
        
        Args:
            base64_string: The file content as a base64 encoded string
            bearer_token: The authentication token for PDS API
            angebot_uuid: The UUID of the offer to attach the document to
            dokumenten_typ_uuid: The UUID of the document type
            file_name: Optional file name, if not provided will use a default name
            
        Returns:
            Dict containing the response from the PDS API or error information
        """
        logging.info(f"Uploading document to PDS offer {angebot_uuid}")
        
        # Validate inputs
        if not base64_string:
            error_msg = "No file content provided (base64_string is empty)"
            logging.error(error_msg)
            return {"success": False, "error": error_msg}
            
        if not bearer_token:
            error_msg = "No authentication token provided"
            logging.error(error_msg)
            return {"success": False, "error": error_msg}
            
        if not angebot_uuid:
            error_msg = "No offer UUID provided"
            logging.error(error_msg)
            return {"success": False, "error": error_msg}
            
        if not dokumenten_typ_uuid:
            error_msg = "No document type UUID provided"
            logging.error(error_msg)
            return {"success": False, "error": error_msg}
        
        # Get API base URL from environment variable
        api_url = os.getenv("PDS_API_URL", "https://10536-01.pdscloud.de/pds/rest/api")
        logging.info(f"Using PDS API URL: {api_url}")
        upload_endpoint = f"{api_url}/dokument/uploaddokument"
        
        try:
            # Decode base64 string to binary
            try:
                # If the base64 string contains metadata (like data:application/pdf;base64,)
                if ',' in base64_string:
                    base64_string = base64_string.split(',')[1]
                
                file_data = base64.b64decode(base64_string)
            except Exception as e:
                logging.error(f"Failed to decode base64 string: {e}")
                return {"success": False, "error": f"Invalid base64 content: {str(e)}"}
            
            # Determine file name and content type
            if not file_name:
                file_name = f"document_{angebot_uuid}.pdf"  # Default file name
            
            # Guess mime type from file name
            content_type, _ = mimetypes.guess_type(file_name)
            if not content_type:
                content_type = 'application/octet-stream'  # Default content type
            
            # Prepare the multipart/form-data request
            files = {
                'file': (file_name, file_data, content_type)
            }
            
            data = {
                'dokumententypUUID': dokumenten_typ_uuid,
                'referenzVorgangUUIDOpt': angebot_uuid,
                'referenzVorgangtypOpt': 'ANGEBOT'  # As per the API docs, for offers
            }
            
            headers = {
                'Authorization': f'{bearer_token}'
            }
            
            # Log request details
            logging.info(f"Request URL: {upload_endpoint}")
            logging.info(f"Request Headers: {headers}")
            logging.info(f"Request Data Keys: {list(data.keys())}")
            logging.info(f"File name: {file_name}, Content-Type: {content_type}")
            
            # Send the request
            logging.info(f"Sending document upload request to PDS API: {upload_endpoint}")
            response = requests.post(
                upload_endpoint,
                headers=headers,
                data=data,
                files=files
            )
            
            # Check response
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            logging.info(f"Document uploaded successfully. Document UUID: {result.get('uuid', 'unknown')}")
            
            
            return {
                "success": True,
                "document_uuid": result.get('uuid'),
                "file_name": result.get('fileName'),
                "document_type": result.get('dokumententyp', {}).get('bezeichnung'),
                "response": result
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error uploading document to PDS API: {str(e)}"
            logging.error(error_msg)
            status_code = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            response_text = getattr(e.response, 'text', None) if hasattr(e, 'response') else None
            
            return {
                "success": False,
                "error": error_msg,
                "status_code": status_code,
                "response_text": response_text
            }
        except Exception as e:
            error_msg = f"Unexpected error uploading document: {str(e)}"
            logging.error(error_msg)
            return {"success": False, "error": error_msg}