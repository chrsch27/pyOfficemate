import azure.functions as func
import logging
import os
import requests
import json
from utils import transform_response  # Importiere die Funktion
import uuid
from datetime import datetime
import dispatcher
from dispatcher import register_erp_integration
from integrations.erp_collmex import ERPcollmexIntegration
from integrations.erp_pds import ERPpdsIntegration
from integrations.erp_sharepoint import ERPsharepointIntegration
from integrations.erp_odoo import ERPodooIntegration
from portals.shipserv.client import ShipServPortal
#from portals.cfm.downloadExcel import CloudFleetExcelExporter
import urllib.parse
import base64

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
shipserv_url= os.getenv("SHIPSERV_URL")
funcode_shipserv_getDocument = os.getenv("FUNCODE_SHIPSERV_GETDOCUMENT")

def load_schema():
    schema_path = os.path.join(os.path.dirname(__file__), "shipservschema.json")
    with open(schema_path, "r") as schema_file:
        return json.load(schema_file)
    
def initialize_erp_integrations():
    """
    Dynamically register all ERP integrations.
    """
    register_erp_integration("collmex", ERPcollmexIntegration)
    register_erp_integration("sharepoint", ERPsharepointIntegration)
    register_erp_integration("pds", ERPpdsIntegration)
    register_erp_integration("odoo", ERPodooIntegration)

# Initialisierung aufrufen
initialize_erp_integrations()
    
def get_token() -> str:
    """Fetches an OAuth2 token from the authentication endpoint."""
    token_url = f"{shipserv_url}/authentication/oauth2/token"
    client_id = os.getenv("SHIPSERV_CLIENT_ID")
    client_secret = os.getenv("SHIPSERV_CLIENT_SECRET")

    if not client_id or not client_secret:
        logging.error("CLIENT_ID or CLIENT_SECRET environment variables are not set.")
        return None

    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }
    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(token_url, json=payload, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        token_data = response.json()
        logging.info(f"Token fetched successfully: {token_data}")
        return token_data.get("access_token")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching token: {e}")
        return None

@app.route(route="csitofficemate", methods=["GET"])
def csitofficemate(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )

@app.route(route="shipserv_getDocument", methods=["GET"])
def shipserv_getDocument(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function "getInquiry" processed a request.')

    # Extract the 'id' parameter from the query string
    document_id = req.params.get('id')
    erp_targets = req.params.get('erpTargets', "").split(",")  # Comma-separated list of ERP targets
    
    if not document_id:
        return func.HttpResponse(
            "Please provide a document ID in the query string (e.g., ?id=12345).",
            status_code=400
        )
    
    token = get_token()
    if not token:
        return func.HttpResponse(
            "Failed to fetch authentication token.",
            status_code=500
        )


    # Define the API endpoint and headers
    api_url = f"{shipserv_url}/order-management/documents/{document_id}"
    headers = {
        'Accept': 'application/json',
        #'Api-Version': 'v2.1',
        'Authorization': f"Bearer {token}"  # Replace with a secure method to store the token
    }

    try:
        # Perform the GET request
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        logging.info(f"Response from ShipServ API: {response.status_code} - {response.text}")
        # Transform the response
        transformed_response = transform_response(response.json())
        logging.info(f"Transformed response: {transformed_response}")
        dispatch_results = dispatcher.dispatch_document(transformed_response, erp_targets)
        logging.info(f"Dispatch results: {dispatch_results}")
        # Return the transformed JSON response
        return func.HttpResponse(
             json.dumps({
                "document": transformed_response,
                "dispatchResults": dispatch_results
            }),
            mimetype="application/json",
            status_code=response.status_code
        )
    except requests.exceptions.RequestException as e:
        logging.error(f"Error during API call: {e}")
        return func.HttpResponse(
            "Error fetching data from the ShipServ API.",
            status_code=500
        )

shipserv_portal = ShipServPortal()  # Create once at module level

@app.route(route="shipserv_getDocuments", methods=["GET"])
def shipserv_getDocuments(req: func.HttpRequest) -> func.HttpResponse:
    doc_type = req.params.get('DocType')
    submitted = req.params.get('submittedDate')
    #if not doc_type:
    #    return func.HttpResponse("Missing DocType", status_code=400)
        
    documents = shipserv_portal.fetch_documents(doc_type=doc_type, submittedDate=submitted)
    return func.HttpResponse(json.dumps({"documents": documents}), 
                            mimetype="application/json")

@app.route(route="modifyAndSendDocument", methods=["POST"])
def modifyAndSendDocument(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing and modifying document data.')

    try:
        # Parse the request body
        request_body = req.get_json()
        document_data = request_body.get("document")
        line_items = request_body.get("lineItems")
        custom_fields = request_body.get("customFields", {})

        if not document_data or not line_items:
            return func.HttpResponse(
                "Invalid input. Please provide 'document' and 'lineItems' in the request body.",
                status_code=400
            )

        # Replace the 'id' field with 'requestForQuoteId'
        document_data["requestForQuoteId"] = document_data.pop("id", None)

        # Replace the lineItems in the document data
        document_data["lineItems"] = line_items

        # Replace or add custom fields
        document_data["type"] = custom_fields.get("type", "Quote")
        document_data["discountCost"] = custom_fields.get("discountCost", 0)
        document_data["subCost"] = custom_fields.get("subCost", 45)
        document_data["cost"] = custom_fields.get("cost", 45)
        document_data["termsAndConditions"] = custom_fields.get("termsAndConditions", document_data.get("termsAndConditions", ""))
        document_data["paymentTerms"] = custom_fields.get("paymentTerms", document_data.get("paymentTerms", ""))
        document_data["createdDate"] = custom_fields.get("createdDate", datetime.utcnow().isoformat() + "Z")
        document_data["submittedDate"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        document_data["quoteExpiryDate"] = custom_fields.get("quoteExpiryDate", "2025-12-31T23:59:59")

        # Fetch the token
        token = get_token()
        if not token:
            return func.HttpResponse(
                "Failed to fetch authentication token.",
                status_code=500
            )

        # Define the API endpoint and headers
        api_url = f"{shipserv_url}/order-management/documents"
        headers = {
            "Api-Version": "v2.1",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}"
        }

        # Perform the POST request to send the modified document
        response = requests.post(api_url, json=document_data, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Return the API response
        return func.HttpResponse(
            response.text,
            mimetype="application/json",
            status_code=response.status_code
        )
    except ValueError:
        return func.HttpResponse(
            "Invalid JSON in the request body.",
            status_code=400
        )
    except requests.exceptions.RequestException as e:
        logging.error(f"Error during API call: {e}")
        return func.HttpResponse(
            "Error sending the document to the ShipServ API.",
            status_code=500
        )

@app.route(route="sendDataToPortal", methods=["POST"])
def sendDataToPortal(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Fetching data from ERP and sending it to the portal.')

    try:
        # Parse the request body
        request_body = req.get_json()
        erp_name = request_body.get("erpName")
        document_id = request_body.get("documentId")
        document_type = request_body.get("documentType")

        if not erp_name or not document_id or not document_type:
            return func.HttpResponse(
                "Please provide 'erpName', 'documentId', and 'documentType' in the request body.",
                status_code=400
            )

        # Fetch data from the ERP system using the dispatcher
        document_data = dispatcher.fetch_data_from_erp(erp_name, document_id, document_type)
        logging.info(f"Fetched document data: {document_data}") 
        if not document_data:
            return func.HttpResponse(
                f"Failed to fetch data from ERP system '{erp_name}' for document ID '{document_id}'.",
                status_code=500
            )

        # Prepare the data for modifyAndSendDocument
        #document_data["portalData"] = request_body.get("portalData", {})
        #document_data["lineItems"] = request_body.get("lineItems", [])
        #document_data["customFields"] = request_body.get("customFields", {})

        # Call modifyAndSendDocument logic
        return modify_and_send_document_logic(document_data)
    except ValueError as e:
        logging.error(f"Error: {e}")
        return func.HttpResponse(
            str(e),
            status_code=400
        )
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return func.HttpResponse(
            "An unexpected error occurred.",
            status_code=500
        )

def modify_and_send_document_logic(document_data):
    """
    Logic for modifying and sending the document.
    :param document_data: The document data to modify and send.
    :return: HttpResponse with the result.
    """
    doc_SendData=document_data.get("portalData", False)
    logging.info(f"Document data to send (doc_SendData): {doc_SendData}")
    try:
        # Replace the 'id' field with 'requestForQuoteId'
        

        # Replace or add custom fields
        doc_SendData["type"] = document_data["customFields"].get("type", "Quote")
        if doc_SendData["type"] == "Quote":
            # Replace the 'id' field with 'requestForQuoteId'
            doc_SendData["requestForQuoteId"] = doc_SendData.pop("id", None)
            # Felder entfernen, falls vorhanden
            if "requisitionId" in doc_SendData:
                doc_SendData.pop("requisitionId")
            if "quoteId" in doc_SendData:
                doc_SendData.pop("quoteId")
            if "purchaseOrderId" in doc_SendData:
                doc_SendData.pop("purchaseOrderId")
        elif doc_SendData["type"] == "PurchaseOrderConfirmation":
            # Replace the 'id' field with 'purchaseOrderId'
            doc_SendData["purchaseOrderId"] = doc_SendData.pop("id", None)

        doc_SendData["discountCost"] = document_data["customFields"].get("discountCost", 0)
        doc_SendData["subCost"] = document_data["customFields"].get("subCost", 45)
        doc_SendData["cost"] = document_data["customFields"].get("cost", 45)
        doc_SendData["termsAndConditions"] = document_data["customFields"].get(
            "termsAndConditions", document_data.get("termsAndConditions", "")
        )
        doc_SendData["paymentTerms"] = document_data["customFields"].get(
            "paymentTerms", document_data.get("paymentTerms", "")
        )
        doc_SendData["createdDate"] = document_data["customFields"].get(
            "createdDate", datetime.utcnow().isoformat() + "Z"
        )
        doc_SendData["submittedDate"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        doc_SendData["quoteExpiryDate"] = document_data["customFields"].get(
            "quoteExpiryDate", "2025-12-31T23:59:59"
        )
        doc_SendData["lineItems"] = document_data.get("lineItems", [])
        doc_SendData["exported"] = True
        json_string=json.dumps(doc_SendData, indent=4, ensure_ascii=False)
        logging.info(f"Document data to send (JSON): {json_string}")
       

        # Fetch the token
        token = get_token()
        if not token:
            return func.HttpResponse(
                "Failed to fetch authentication token.",
                status_code=500
            )

        # Define the API endpoint and headers
        api_url = f"{shipserv_url}/order-management/documents"
        headers = {
            "Api-Version": "v2.1",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}"
        }

        # Perform the POST request to send the modified document
        response = requests.post(api_url, json=doc_SendData, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Return the API response
        return func.HttpResponse(
            response.text,
            mimetype="application/json",
            status_code=response.status_code
        )
    except requests.exceptions.RequestException as e:
        logging.error(response)
        logging.error(f"Error during API call: {e}")
        return func.HttpResponse(
            "Error sending the document to the ShipServ API.",
            status_code=500
        )

def mark_document_as_exported(doc_id, token):
    """
    Marks a document as exported via the ShipServ API.
    """
    url = f"{shipserv_url}/order-management/documents/{doc_id}/mark-as-exported"
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

@app.route(route="processFirstDocument", methods=["GET"])
def process_first_document(req: func.HttpRequest) -> func.HttpResponse:
    """
    Fetches all documents (via shipserv_getDocuments), takes the first one,
    processes it with shipserv_getDocument, and finally marks it as exported
    only if the processing was successful.
    """
    try:
        # Basis-URL ohne Route ermitteln:
        url_parsed = urllib.parse.urlparse(req.url)
        base_url = f"{url_parsed.scheme}://{url_parsed.netloc}"
        #doc_type = "RequestForQuote"
        submitted = req.params.get('submittedDate')
        if submitted:
            #doc_type = f"{doc_type}?submittedDate={submitted}"
            docs_json = shipserv_portal.fetch_documents(submittedDate=submitted)
        else:
            docs_json = shipserv_portal.fetch_documents()
        #docs_url = f"{base_url}/api/shipserv_getDocuments?DocType={doc_type}"
        #logging.info(f"Fetching documents from: {docs_url}")
        #docs_response = requests.get(docs_url)
        #docs_response.raise_for_status()

        #docs_json = docs_response.json()
        logging.info(f"Fetched documents: {docs_json}") 
        if isinstance(docs_json, dict):
            content = docs_json.get("content", [])
        elif isinstance(docs_json, list):
            content = docs_json
        else:
            content = []
        if not content:
            return func.HttpResponse("No documents found.", status_code=404)

        first_doc_id = content[0]["id"]

        # 2) Dokument verarbeiten
        processed_doc_url = f"{base_url}/api/shipserv_getDocument?id={first_doc_id}&erpTargets=collmex,sharepoint"
        azureheaders = {
            "x-functions-key": f"{funcode_shipserv_getDocument}"
        }
        processed_doc_response = requests.get(processed_doc_url,headers=azureheaders)
        logging.info(f"Processed document response: {processed_doc_response.status_code} - {processed_doc_response.text}")
        # Wenn nicht erfolgreich -> abbrechen
        if processed_doc_response.status_code != 200:
            return func.HttpResponse(
                f"Document {first_doc_id} could not be processed. Not exporting.",
                status_code=processed_doc_response.status_code
            )
        
        # 3) Nur bei erfolgreichem Schritt 2 -> Dokument auf 'exportiert' setzen
        token = get_token()
        export_result = mark_document_as_exported(first_doc_id, token or "")
        #export_result = "noch nicht exportiert" 

        return func.HttpResponse(
            json.dumps({
                "fetchedDocument": first_doc_id,
                "processingResult": processed_doc_response.json(),
                "exportResult": export_result
            }),
            mimetype="application/json",
            status_code=200
        )
    except requests.exceptions.RequestException as e:
        logging.error(f"Error in process_first_document: {e}")
        return func.HttpResponse("Error occurred while processing.", status_code=500)

@app.route(route="sendDataToPortalGet", methods=["GET"])
def sendDataToPortalGet(req: func.HttpRequest) -> func.HttpResponse:
    """
    Simple GET-based wrapper to call sendDataToPortal logic.
    Usage example (query params):
        /api/sendDataToPortalGet?erpName=collmex&documentId=250782&documentType=Quote
    """
    erp_name = req.params.get("erpName")
    document_id = req.params.get("documentId")
    document_type = req.params.get("documentType")

    if not erp_name or not document_id or not document_type:
        return func.HttpResponse(
            "Please provide 'erpName', 'documentId', and 'documentType' in the query string.",
            status_code=400
        )

    # Baue ein JSON-Objekt wie im POST-Body
    request_body = {
        "erpName": erp_name,
        "documentId": document_id,
        "documentType": document_type,
        "lineItems": [],
        "customFields": {}
    }

    # Interner Aufruf der vorhandenen sendDataToPortal-Logik
    class MockRequest:
        def __init__(self, body):
            self._body = body
        def get_json(self):
            return self._body

    mock_req = MockRequest(request_body)
    return sendDataToPortal(mock_req)

@app.route(route="createOfferOdoo", methods=["POST"])
def create_oddo_offer(req: func.HttpRequest) -> func.HttpResponse:
    """
    Create an offer in Odoo.
    :param data: The data for the offer.
    :param customer: Optional customer information.
    :return: The response from the Odoo API.
    """
    try:
        request_body = req.get_json()
        data_raw = request_body.get("data")
        customer = request_body.get("customer")
        
        if not data_raw:
            return func.HttpResponse(
                "Please provide 'data' in the request body.",
                status_code=400
            )
        
        # Check if data is a string and try to parse it as JSON
        if isinstance(data_raw, str):
            try:
                data = json.loads(data_raw)
                logging.info(f"Successfully parsed string data into JSON object")
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse data string as JSON: {str(e)}")
                return func.HttpResponse(
                    f"Invalid JSON string in 'data' field: {str(e)}",
                    status_code=400
                )
        else:
            data = data_raw
            
        # Create the offer in Odoo
        result = ERPodooIntegration.send_to_erp(data, customer)
        
        # Handle None result (integration failure)
        if result is None:
            logging.error("Odoo integration returned None")
            return func.HttpResponse(
                "Failed to create offer in Odoo: Integration error",
                status_code=500
            )
            
        # Safely unpack the tuple
        offer_id, count, offer_number= result
        logging.info(f"Offer created with ID: {offer_id} with {count} items. Offer number: {offer_number}")
        
        if not offer_id:
            return func.HttpResponse(
                "Failed to create offer in Odoo: No offer ID returned",
                status_code=500
            )
            
        # Success response
        return func.HttpResponse(
            json.dumps({
                "success": True,
                "offer_id": offer_id,
                "item_count": count,
                "offer_number": offer_number
            }),
            mimetype="application/json",
            status_code=201
        )
    except ValueError as e:
        logging.error(f"JSON parsing error: {str(e)}")
        return func.HttpResponse(
            f"Invalid request format: {str(e)}",
            status_code=400
        )
    except Exception as e:
        logging.error(f"Error creating offer in Odoo: {str(e)}")
        return func.HttpResponse(
            f"Error creating offer: {str(e)}",
            status_code=500
        )

@app.route(route="getOfferOdoo", methods=["GET"])
def get_odoo_offer(req: func.HttpRequest) -> func.HttpResponse:
    """
    Ruft ein Angebot aus Odoo anhand seiner ID ab.
    
    Query-Parameter:
        id: Die ID des Angebots in Odoo
        
    Returns:
        JSON mit den Angebotsdaten oder Fehlermeldung
    """
    logging.info('Function "getOfferOdoo" wurde aufgerufen.')
    
    try:
        # Angebots-ID aus den Query-Parametern extrahieren
        offer_id = req.params.get('id')
        
        if not offer_id:
            return func.HttpResponse(
                json.dumps({"error": "Bitte geben Sie eine Angebots-ID als 'id' Parameter an"}),
                mimetype="application/json",
                status_code=400
            )
            
        # Angebot aus Odoo abrufen
        offer_data = ERPodooIntegration.get_offer(offer_id)
        
        if not offer_data:
            return func.HttpResponse(
                json.dumps({"error": f"Angebot mit ID {offer_id} wurde nicht gefunden oder Fehler bei der Abfrage"}),
                mimetype="application/json",
                status_code=404
            )
            
        # Erfolgsantwort mit Angebotsdaten
        return func.HttpResponse(
            json.dumps(offer_data, ensure_ascii=False),
            mimetype="application/json",
            status_code=200
        )
        
    except ValueError as e:
        logging.error(f"Fehler bei der Parameterverarbeitung: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Ungültiges Anfrageformat: {str(e)}"}),
            mimetype="application/json",
            status_code=400
        )
    except Exception as e:
        logging.error(f"Fehler beim Abrufen des Angebots aus Odoo: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Serverfehler: {str(e)}"}),
            mimetype="application/json", 
            status_code=500
        )

@app.route(route="uploadPdsDocument", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def upload_pds_document(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP Trigger function to upload a document to a PDS offer.
    
    Request body should contain:
        base64String: The file content as a base64 encoded string
        bearerToken: The authentication token for PDS API
        angebotUUID: The UUID of the offer to attach the document to
        dokumentenTypUUID: The UUID of the document type
        fileName: (Optional) Name of the file
        
    Returns:
        HTTP response with the result of the upload operation
    """
    logging.info("Processing request to upload document to PDS offer")
    
    # Create correlation ID for tracking this request through logs
    correlation_id = req.headers.get('x-correlation-id', f"pds-upload-{os.urandom(6).hex()}")
    logging.info(f"Request correlation ID: {correlation_id}")
    
    try:
        # Parse request body
        req_body = req.get_json()
        
        # Extract required parameters
        base64_string = req_body.get('base64String')
        bearer_token = req_body.get('bearerToken')
        angebot_uuid = req_body.get('angebotUUID')
        dokumenten_typ_uuid = req_body.get('dokumentenTypUUID')
        file_name = req_body.get('fileName')
        
        
        # Validate required parameters
        if not all([base64_string, bearer_token, angebot_uuid, dokumenten_typ_uuid]):
            missing_params = []
            if not base64_string: missing_params.append('base64String')
            if not bearer_token: missing_params.append('bearerToken')
            if not angebot_uuid: missing_params.append('angebotUUID')
            if not dokumenten_typ_uuid: missing_params.append('dokumentenTypUUID')
            
            logging.warning(f"Missing required parameters: {', '.join(missing_params)} | Correlation ID: {correlation_id}")
            return func.HttpResponse(
                json.dumps({
                    "error": f"Missing required parameters: {', '.join(missing_params)}",
                    "correlationId": correlation_id
                }),
                mimetype="application/json",
                status_code=400
            )
        
        # Log upload attempt (security best practice - not logging actual token or content)
        logging.info(f"Attempting document upload for offer {angebot_uuid} | Correlation ID: {correlation_id}")
        
        # Call the integration function
        result = ERPpdsIntegration.upload_document_to_offer(
            base64_string=base64_string,
            bearer_token=bearer_token,
            angebot_uuid=angebot_uuid,
            dokumenten_typ_uuid=dokumenten_typ_uuid,
            file_name=file_name
        )
        
        # Add correlation ID to the result
        result["correlationId"] = correlation_id
        
        # Return the result
        if result.get('success', False):
            logging.info(f"Document upload successful | Document UUID: {result.get('document_uuid')} | Correlation ID: {correlation_id}")
            return func.HttpResponse(
                json.dumps(result),
                mimetype="application/json",
                status_code=201  # Created
            )
        else:
            logging.error(f"Document upload failed | Error: {result.get('error')} | Correlation ID: {correlation_id}")
            return func.HttpResponse(
                json.dumps(result),
                mimetype="application/json",
                status_code=500
            )
            
    except ValueError as e:
        error_msg = f"Invalid request format: {str(e)}"
        logging.error(f"{error_msg} | Correlation ID: {correlation_id}")
        return func.HttpResponse(
            json.dumps({"error": error_msg, "correlationId": correlation_id}),
            mimetype="application/json",
            status_code=400
        )
    except Exception as e:
        error_msg = f"Server error: {str(e)}"
        logging.exception(f"{error_msg} | Correlation ID: {correlation_id}")
        return func.HttpResponse(
            json.dumps({"error": error_msg, "correlationId": correlation_id}),
            mimetype="application/json",
            status_code=500
        )

@app.route(route="markDocumentAsExported", methods=["POST"])
def mark_document_exported_http(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP trigger to mark a document as exported in ShipServ.
    
    Request body should contain:
        documentId: The ID of the document to mark as exported
        
    Returns:
        HTTP response with the result of the operation
    """
    # Create correlation ID for request tracing
    correlation_id = req.headers.get('x-correlation-id', f"export-mark-{uuid.uuid4()}")
    logging.info(f"Processing request to mark document as exported | Correlation ID: {correlation_id}")
    
    try:
        # Get document ID from request body
        req_body = req.get_json()
        doc_id = req_body.get('documentId')
        
        # Validate document ID
        if not doc_id:
            logging.warning(f"Missing required parameter: documentId | Correlation ID: {correlation_id}")
            return func.HttpResponse(
                json.dumps({
                    "error": "Missing required parameter: documentId",
                    "correlationId": correlation_id
                }),
                mimetype="application/json",
                status_code=400
            )
        
        # Get authentication token
        token = get_token()
        if not token:
            logging.error(f"Failed to obtain authentication token | Correlation ID: {correlation_id}")
            return func.HttpResponse(
                json.dumps({
                    "error": "Authentication failed: Could not obtain token",
                    "correlationId": correlation_id
                }),
                mimetype="application/json",
                status_code=500
            )
        
        # Call the mark_document_as_exported function
        logging.info(f"Marking document {doc_id} as exported | Correlation ID: {correlation_id}")
        result = mark_document_as_exported(doc_id, token)
        
        # Add correlation ID to response
        result["correlationId"] = correlation_id
        
        # Return appropriate response based on the result
        if result.get('status') == 'success':
            logging.info(f"Document {doc_id} successfully marked as exported | Correlation ID: {correlation_id}")
            return func.HttpResponse(
                json.dumps(result),
                mimetype="application/json",
                status_code=200
            )
        else:
            logging.error(f"Failed to mark document {doc_id} as exported: {result.get('message')} | Correlation ID: {correlation_id}")
            return func.HttpResponse(
                json.dumps(result),
                mimetype="application/json",
                status_code=500
            )
            
    except ValueError as e:
        error_msg = f"Invalid request format: {str(e)}"
        logging.error(f"{error_msg} | Correlation ID: {correlation_id}")
        return func.HttpResponse(
            json.dumps({"error": error_msg, "correlationId": correlation_id}),
            mimetype="application/json",
            status_code=400
        )
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logging.exception(f"{error_msg} | Correlation ID: {correlation_id}")
        return func.HttpResponse(
            json.dumps({"error": error_msg, "correlationId": correlation_id}),
            mimetype="application/json",
            status_code=500
        )

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    # Hier können Sie den Code für die Verarbeitung der Anfrage hinzufügen
    return func.HttpResponse(
        "This HTTP triggered function executed successfully.",
        status_code=200
    )

@app.route(route="shipserv_upload_attachment", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def shipserv_upload_attachment(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP-Trigger zum Hochladen von Dateien an die ShipServ API.
    
    Unterstützt folgende Eingabeformate:
    1. multipart/form-data mit 'file' als Dateifeld und 'tnid' als Parameter
    2. Binärdaten im Body mit 'filename' und 'tnid' als Parameter
    3. Base64-codierte Daten mit 'filename', 'content' und 'tnid' im JSON-Body
    
    Returns:
        HTTP-Antwort mit Upload-Ergebnis
    """
    logging.info("Processing attachment upload request")
    
    # Korrelations-ID für Request-Tracing
    correlation_id = req.headers.get("x-correlation-id", f"upload-{req.url}")
    
    try:
        # TNID-Parameter abrufen (erforderlich für ShipServ API)
        tnid = req.params.get("tnid")
        if not tnid:
            body_json = req.get_json() if req.get_body() else {}
            tnid = body_json.get("tnid") if isinstance(body_json, dict) else None
            
        if not tnid:
            return func.HttpResponse(
                json.dumps({"status": "error", "message": "Missing required parameter: tnid"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Drei mögliche Upload-Szenarien prüfen
        # 1. multipart/form-data (standard file upload)
        if req.files and "file" in req.files:
            file = req.files["file"]
            filename = file.filename
            file_content = file.stream.read()
            
            logging.info(f"Processing multipart upload: {filename} | {len(file_content)} bytes | Correlation ID: {correlation_id}")
            result = shipserv_portal.upload_attachment(filename, tnid, file_content)
            
        # 2. JSON mit Base64-codiertem Inhalt
        elif req.get_body() and req.headers.get("content-type", "").startswith("application/json"):
            body_json = req.get_json()
            
            if not isinstance(body_json, dict):
                return func.HttpResponse(
                    json.dumps({"status": "error", "message": "Invalid JSON body"}),
                    status_code=400,
                    mimetype="application/json"
                )
                
            filename = body_json.get("filename")
            content_base64 = body_json.get("content")
            
            if not filename or not content_base64:
                return func.HttpResponse(
                    json.dumps({"status": "error", "message": "Missing required fields: filename and content"}),
                    status_code=400,
                    mimetype="application/json"
                )
                
            try:
                file_content = base64.b64decode(content_base64)
                logging.info(f"Processing base64 upload: {filename} | {len(file_content)} bytes | Correlation ID: {correlation_id}")
                result = shipserv_portal.upload_attachment(filename, tnid, file_content)
            except Exception as decode_error:
                return func.HttpResponse(
                    json.dumps({"status": "error", "message": f"Invalid base64 content: {str(decode_error)}"}),
                    status_code=400,
                    mimetype="application/json"
                )
            
        # 3. Binärdaten mit Dateiname als Parameter
        else:
            filename = req.params.get("filename")
            if not filename:
                return func.HttpResponse(
                    json.dumps({"status": "error", "message": "Missing required parameter: filename"}),
                    status_code=400,
                    mimetype="application/json"
                )
                
            file_content = req.get_body()
            if not file_content:
                return func.HttpResponse(
                    json.dumps({"status": "error", "message": "Missing file content in request body"}),
                    status_code=400,
                    mimetype="application/json"
                )
                
            logging.info(f"Processing raw binary upload: {filename} | {len(file_content)} bytes | Correlation ID: {correlation_id}")
            result = shipserv_portal.upload_attachment(filename, tnid, file_content)
            
        # Ergebnis zurückgeben
        status_code = 200 if result.get("status") == "success" else 500
        return func.HttpResponse(
            json.dumps(result),
            status_code=status_code,
            mimetype="application/json"
        )
        
    except Exception as e:
        error_message = str(e)
        logging.exception(f"Error processing attachment upload: {error_message} | Correlation ID: {correlation_id}")
        return func.HttpResponse(
            json.dumps({
                "status": "error", 
                "message": f"Error processing request: {error_message}",
                "correlation_id": correlation_id
            }),
            status_code=500,
            mimetype="application/json"
        )