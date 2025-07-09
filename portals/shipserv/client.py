# portals/shipserv/client.py
import os
import logging
import requests
import json
import base64
from typing import Dict, List, Optional, Any, Tuple, Union
from portals.base_portal import BasePortal
import time

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


    def download_attachments(self, portal_data: Dict[str, Any], include_binary: bool = True) -> List[Dict[str, Any]]:
        """
        Downloads attachments from portal data using ShipServ API.
        
        Args:
            portal_data: Dictionary containing portal data with possible attachments
            include_binary: Whether to include binary content (default True) or just metadata
            
        Returns:
            List of dictionaries containing file information and content
        """
        # Initialize correlation ID for request tracing
        correlation_id = f"attach-dl-{portal_data.get('id', 'unknown')}"
        logging.info(f"Processing attachments for document | Correlation ID: {correlation_id}")
        
        # Extract attachments from portal data
        attachments = portal_data.get("attachments", [])
        if not attachments:
            logging.info(f"No attachments found in portal data | Correlation ID: {correlation_id}")
            return []
            
        # Get authentication token
        token = self._token or self._get_token()
        if not token:
            logging.error(f"Failed to obtain authentication token | Correlation ID: {correlation_id}")
            return []
            
        # Prepare results list
        attachment_results = []
        
        # Process each attachment
        for attachment in attachments:
            attachment_id = attachment.get("id")
            if not attachment_id:
                logging.warning(f"Attachment missing ID, skipping | Correlation ID: {correlation_id}")
                continue
                
            try:
                # Create attachment result with metadata
                result = {
                    "name": attachment.get("name", f"unknown-{attachment_id}"),
                    "type": attachment.get("type", ""),
                    "size": attachment.get("size", 0),
                    "classification": attachment.get("classification", ""),
                    "id": attachment_id,
                    "content": None,  # Will be populated if include_binary is True
                    "success": False
                }
                
                # Only download content if requested
                if include_binary:
                    # Prepare API request
                    api_url = f"https://api-stg.shipservlabs.com/attachments/{attachment_id}/bytes"
                    headers = {
                        "Authorization": f"Bearer {token}",
                        "Accept": "*/*",
                        "x-correlation-id": correlation_id
                    }
                    
                    # Make request with proper error handling
                    logging.info(f"Downloading attachment: {result['name']} | Correlation ID: {correlation_id}")
                    
                    # Use stream=True for better memory management with large files
                    response = requests.get(api_url, headers=headers, stream=True, timeout=60)
                    response.raise_for_status()
                    
                    # Read content and encode as Base64 for safe transport
                    content = response.content
                    result["content"] = base64.b64encode(content).decode('utf-8')
                    result["content_encoding"] = "base64"
                    result["success"] = True
                    
                    # Log success with file size for monitoring
                    content_size_kb = len(content) / 1024
                    logging.info(f"Successfully downloaded {result['name']} ({content_size_kb:.2f} KB) | Correlation ID: {correlation_id}")
                else:
                    # Just mark as successful if we're only collecting metadata
                    result["success"] = True
                    
                attachment_results.append(result)
                    
            except requests.exceptions.RequestException as e:
                logging.error(f"Failed to download attachment {attachment_id}: {str(e)} | Correlation ID: {correlation_id}")
                # Add failed attachment with error information
                attachment_results.append({
                    "name": attachment.get("name", f"unknown-{attachment_id}"),
                    "id": attachment_id,
                    "error": str(e),
                    "success": False
                })
            except Exception as e:
                logging.exception(f"Unexpected error processing attachment {attachment_id}: {str(e)} | Correlation ID: {correlation_id}")
                # Add failed attachment with error information
                attachment_results.append({
                    "name": attachment.get("name", f"unknown-{attachment_id}"),
                    "id": attachment_id,
                    "error": f"Unexpected error: {str(e)}",
                    "success": False
                })
        
        # Return the results
        logging.info(f"Processed {len(attachment_results)} attachments | Success: {sum(1 for a in attachment_results if a.get('success'))} | Correlation ID: {correlation_id}")
        return attachment_results

    def save_attachments_to_storage(attachments: List[Dict[str, Any]], container_name: str) -> List[Dict[str, Any]]:
        """
        Saves downloaded attachments to Azure Blob Storage.
        
        Args:
            attachments: List of attachment dictionaries from download_attachments
            container_name: Azure Blob Storage container name
            
        Returns:
            Updated list of dictionaries with storage information
        """
        # This method would be implemented to save attachments to Azure Blob Storage
        # Following Azure Functions best practices for blob storage operations
        # For now, this is a placeholder
        
        # Return the attachments with added storage URLs
        return attachments

    def upload_attachment(self, file_path_or_name: str, tnid: str, file_content=None) -> Dict[str, Any]:
        """
        Upload an attachment to ShipServ API.
        
        Args:
            file_path_or_name: Path to the file or just the filename to use
            tnid: The tenant ID parameter for ShipServ API
            file_content: Optional file content as bytes. If None, file_path will be read
            
        Returns:
            Dict with operation status, response data and attachment ID
        """
        # Add correlation ID for distributed tracing
        correlation_id = f"upload-{os.path.basename(file_path_or_name)}-{tnid}"
        logging.info(f"Starting attachment upload | File: {file_path_or_name} | TNID: {tnid} | Correlation ID: {correlation_id}")
        
        # Get authentication token with retry logic
        retry_count = 0
        max_retries = 3
        token = None
        
        while retry_count < max_retries and not token:
            token = self._token or self._get_token()
            if not token:
                retry_count += 1
                if retry_count < max_retries:
                    logging.warning(f"Token acquisition failed, retrying ({retry_count}/{max_retries}) | Correlation ID: {correlation_id}")
                    time.sleep(1)  # Wait before retry
        
        if not token:
            logging.error(f"Failed to authenticate with ShipServ API after {max_retries} attempts | Correlation ID: {correlation_id}")
            return {"status": "error", "message": "Authentication failed", "correlation_id": correlation_id}
        
        # Prepare request URL and headers
        api_url = f"{self.api_url}/attachments?tnid={tnid}"
        headers = {
            'Authorization': f"Bearer {token}",
            'x-correlation-id': correlation_id
        }
        
        try:
            # Determine if we need to read the file or use provided content
            if file_content is None:
                # Check if file exists before attempting to read
                if not os.path.isfile(file_path_or_name):
                    logging.error(f"File not found: {file_path_or_name} | Correlation ID: {correlation_id}")
                    return {
                        "status": "error", 
                        "message": f"File not found: {file_path_or_name}",
                        "correlation_id": correlation_id
                    }
                    
                with open(file_path_or_name, 'rb') as f:
                    file_content = f.read()
                    logging.info(f"Read {len(file_content)} bytes from {file_path_or_name} | Correlation ID: {correlation_id}")
            
            # Get just the filename if a full path was provided
            filename = os.path.basename(file_path_or_name)
            
            # Create the multipart form data
            files = {
                'file': (filename, file_content, self._get_mime_type(filename))
            }
            
            # Set up timeout and send request
            logging.info(f"Uploading file to {api_url} | Size: {len(file_content)} bytes | Correlation ID: {correlation_id}")
            response = requests.post(api_url, headers=headers, files=files, timeout=120)  # Longer timeout for large files
            
            # Log response code immediately
            logging.info(f"Upload response status: {response.status_code} | Correlation ID: {correlation_id}")
            
            # Handle response
            response.raise_for_status()
            
            # Parse response data
            response_data = {}
            if response.content:
                try:
                    response_data = response.json()
                    logging.info(f"Upload successful, received attachment ID: {response_data.get('id')} | Correlation ID: {correlation_id}")
                except json.JSONDecodeError:
                    logging.warning(f"Response wasn't valid JSON: {response.text[:100]} | Correlation ID: {correlation_id}")
            
            return {
                "status": "success",
                "statusCode": response.status_code,
                "attachmentId": response_data.get("id"),
                "response": response_data,
                "correlation_id": correlation_id
            }
            
        except requests.exceptions.RequestException as e:
            # Enhanced error handling with status code extraction
            status_code = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            error_detail = getattr(e.response, 'text', 'No response text available') if hasattr(e, 'response') else str(e)
            
            logging.error(f"Request error uploading attachment: {str(e)} | Status: {status_code} | Correlation ID: {correlation_id}")
            logging.error(f"Error details: {error_detail[:500]} | Correlation ID: {correlation_id}")
            
            return {
                "status": "error",
                "message": f"Request failed: {str(e)}",
                "statusCode": status_code,
                "detail": error_detail,
                "correlation_id": correlation_id
            }
        except Exception as e:
            logging.exception(f"Unexpected error uploading attachment: {str(e)} | Correlation ID: {correlation_id}")
            return {
                "status": "error", 
                "message": f"Unexpected error: {str(e)}",
                "correlation_id": correlation_id
            }

    def _get_mime_type(self, filename: str) -> str:
        """
        Determine MIME type from filename extension.
        
        Args:
            filename: The filename to analyze
            
        Returns:
            MIME type string
        """
        import mimetypes
        # Ensure mimetypes are initialized
        mimetypes.init()
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or 'application/octet-stream'  # Default to binary if type can't be determined