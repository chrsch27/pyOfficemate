# portals/shipserv/client.py
import os
import logging
import requests
import json
from typing import Dict, List, Optional, Any, Tuple, Union
from portals.base_portal import BasePortal

class ShipServPortal(BasePortal):
    """
    Portal implementation for interacting with the ShipServ API.
    Extends the BasePortal interface for standard document operations.
    """
    
    def __init__(self, api_url=None, client_id=None, client_secret=None):
        """
        Initialize the ShipServ portal with configuration.
        
        Args:
            api_url: Base URL for the ShipServ API. If None, read from environment variable.
            client_id: OAuth client ID. If None, read from environment variable.
            client_secret: OAuth client secret. If None, read from environment variable.
        """
        self.api_url = api_url or os.getenv("SHIPSERV_URL")
        self.client_id = client_id or os.getenv("SHIPSERV_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("SHIPSERV_CLIENT_SECRET")
        
        if not all([self.api_url, self.client_id, self.client_secret]):
            logging.warning("ShipServ portal configuration incomplete. Some API calls may fail.")
        
        # Cache the token to avoid unnecessary token requests
        self._token = None
        
    def _get_token(self) -> Optional[str]:
        """
        Get an OAuth token for authenticating with the ShipServ API.
        
        Returns:
            str: The access token, or None if authentication failed.
        """
        if not all([self.api_url, self.client_id, self.client_secret]):
            logging.error("Cannot get token: Missing ShipServ configuration")
            return None
            
        token_url = f"{self.api_url}/authentication/oauth2/token"
        
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(token_url, json=payload, headers=headers)
            response.raise_for_status()
            token_data = response.json()
            self._token = token_data.get("access_token")
            return self._token
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching ShipServ token: {e}")
            return None
    
    def fetch_documents(self, **filters):
        """
        Fetch documents from ShipServ API based on filters.
        
        Args:
            **filters: Filter parameters, doc_type is required
            
        Returns:
            List of document objects or empty list if request failed
        """
        doc_type = filters.get('doc_type')
        submittedDate = filters.get('submittedDate')
        urlParam = ""
        if doc_type:
            urlParam="?type=" + doc_type
        if submittedDate:
            if urlParam == "":
                urlParam = "?submittedDate=" + submittedDate
            else:
                urlParam=urlParam + "&submittedDate=" + submittedDate

        token = self._token or self._get_token()
        if not token:
            logging.error("Failed to authenticate with ShipServ API")
            return []
        
        api_url = f"{self.api_url}/order-management/documents{urlParam}"
        logging.info(f"Fetching documents from ShipServ API: {api_url}")
        headers = {
            'Accept': 'application/json',
            'Authorization': f"Bearer {token}"
        }
        
        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            documents = response.json()
            return documents.get('content', [])
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching documents from ShipServ API: {e}")
            return []
    
    def get_document(self, document_id: str) -> Optional[Dict]:
        """
        Get a specific document from ShipServ API by ID.
        
        Args:
            document_id: The ID of the document to retrieve.
            
        Returns:
            Document data dict or None if request failed
        """
        token = self._token or self._get_token()
        if not token:
            logging.error("Failed to authenticate with ShipServ API")
            return None
        
        api_url = f"{self.api_url}/order-management/documents/{document_id}"
        headers = {
            'Accept': 'application/json',
            'Authorization': f"Bearer {token}"
        }
        
        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching document {document_id} from ShipServ API: {e}")
            return None

    def send_document(self, document):
        """
        Send a document to ShipServ.
        
        Args:
            document: Document data to send
            
        Returns:
            Dict with operation status and details
        """
        # This would be implemented based on ShipServ's document submission API
        # Currently ShipServ doesn't expose a document submission endpoint in this context
        logging.warning("Document submission to ShipServ not implemented")
        return {"status": "error", "message": "Operation not supported by ShipServ API"}

    def mark_document_as_exported(self, doc_id: str) -> Dict:
        """
        Marks a document as exported via the ShipServ API.
        
        Args:
            doc_id: The ID of the document to mark as exported.
            
        Returns:
            Dict with operation status and details
        """
        token = self._token or self._get_token()
        if not token:
            return {
                "status": "error", 
                "message": "Failed to authenticate with ShipServ API"
            }
        
        url = f"{self.api_url}/order-management/documents/{doc_id}/mark-as-exported"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, headers=headers)
            response.raise_for_status()
            return {"status": "success", "response": response.json()}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}