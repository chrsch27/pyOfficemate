from integrations.erp_collmex import ERPcollmexIntegration
from integrations.erp_pds import ERPpdsIntegration
from integrations.erp_sharepoint import ERPsharepointIntegration
import logging
from typing import Dict, Any, List, Callable, Optional, Union

# Registrierung der ERP-Integrationen
_erp_integrations = {}

# Neues Dictionary für Document Type Handler
_document_type_handlers = {}

def register_erp_integration(name, integration_class):
    """Registriert eine ERP-Integration unter dem angegebenen Namen."""
    _erp_integrations[name] = integration_class
    logging.info(f"Registered ERP integration: {name}")
    
def register_document_type_handler(doc_type: str, handler_func: Callable):
    """
    Registriert einen Handler für einen bestimmten Document Type.
    
    Args:
        doc_type: Document Type (RequestForQuote, Quote, PurchaseOrder, etc.)
        handler_func: Funktion, die den Dispatch für diesen Document Type übernimmt
    """
    _document_type_handlers[doc_type] = handler_func
    logging.info(f"Registered document type handler: {doc_type}")

def dispatch_to_erps(document_data: Dict[str, Any], erp_targets: List[str]) -> Dict[str, Any]:
    """
    Hauptmethode zum Dispatching von Dokumenten zu ERPs basierend auf dem Dokumenttyp.
    
    Args:
        document_data: Die Dokumentdaten für die Verarbeitung
        erp_targets: Liste der Ziel-ERP-Systeme
        
    Returns:
        Dictionary mit den Ergebnissen pro ERP-System
    """
    if not document_data:
        logging.error("No document data provided for dispatch")
        return {"error": "No document data provided"}
    
    # Dokumenttyp ermitteln
    doc_type = document_data.get("type", "Unknown")
    logging.info(f"Dispatching document of type: {doc_type}")
    
    # Spezifischen Handler für den Dokumenttyp aufrufen
    handler = _document_type_handlers.get(doc_type)
    
    if handler:
        return handler(document_data, erp_targets)
    else:
        logging.warning(f"No handler registered for document type: {doc_type}")
        # Fallback auf den bisherigen RequestForQuote-Handler
        return dispatch_to_erps_RequestForQuote(document_data, erp_targets)

def dispatch_to_erps_RequestForQuote(document_data: Dict[str, Any], erp_targets: List[str]) -> Dict[str, Any]:
    """
    Verarbeitet ein RequestForQuote-Dokument und sendet es an die angegebenen ERP-Systeme.
    (Enthält die bestehende Implementierung von dispatch_to_erps)
    """
    results = {}
    
    for erp_name in erp_targets:
        if erp_name not in _erp_integrations:
            results[erp_name] = {"success": False, "error": f"ERP integration '{erp_name}' not found"}
            continue
            
        erp_class = _erp_integrations[erp_name]
        try:
            erp_result = erp_class.send_to_erp(document_data)
            results[erp_name] = {"success": True, "result": erp_result}
        except Exception as e:
            logging.error(f"Error dispatching to {erp_name}: {str(e)}")
            results[erp_name] = {"success": False, "error": str(e)}
    
    return results

def dispatch_to_erps_Quote(document_data: Dict[str, Any], erp_targets: List[str]) -> Dict[str, Any]:
    """
    Verarbeitet ein Quote-Dokument und sendet es an die angegebenen ERP-Systeme.
    """
    results = {}
    
    for erp_name in erp_targets:
        if erp_name not in _erp_integrations:
            results[erp_name] = {"success": False, "error": f"ERP integration '{erp_name}' not found"}
            continue
            
        erp_class = _erp_integrations[erp_name]
        try:
            # Spezielle Methode für Quote, falls vorhanden
            if hasattr(erp_class, 'send_quote_to_erp'):
                erp_result = erp_class.send_quote_to_erp(document_data)
            # Fallback auf die generische Methode
   
            
            results[erp_name] = {"success": True, "result": erp_result}
        except Exception as e:
            logging.error(f"Error dispatching Quote to {erp_name}: {str(e)}")
            results[erp_name] = {"success": False, "error": str(e)}
    
    return results

def dispatch_to_erps_PurchaseOrder(document_data: Dict[str, Any], erp_targets: List[str]) -> Dict[str, Any]:
    """
    Verarbeitet ein PurchaseOrder-Dokument und sendet es an die angegebenen ERP-Systeme.
    """
    results = {}
    
    for erp_name in erp_targets:
        if erp_name not in _erp_integrations:
            results[erp_name] = {"success": False, "error": f"ERP integration '{erp_name}' not found"}
            continue
            
        erp_class = _erp_integrations[erp_name]
        try:
            # Spezielle Methode für PurchaseOrder, falls vorhanden
            if hasattr(erp_class, 'send_purchase_order_to_erp'):
                erp_result = erp_class.send_purchase_order_to_erp(document_data)
            # Fallback auf die generische Methode
            
            results[erp_name] = {"success": True, "result": erp_result}
        except Exception as e:
            logging.error(f"Error dispatching PurchaseOrder to {erp_name}: {str(e)}")
            results[erp_name] = {"success": False, "error": str(e)}
    
    return results

def dispatch_to_erps_Requisition(document_data: Dict[str, Any], erp_targets: List[str]) -> Dict[str, Any]:
    """
    Verarbeitet ein Requisition-Dokument und sendet es an die angegebenen ERP-Systeme.
    """
    results = {}
    
    for erp_name in erp_targets:
        if erp_name not in _erp_integrations:
            results[erp_name] = {"success": False, "error": f"ERP integration '{erp_name}' not found"}
            continue
            
        erp_class = _erp_integrations[erp_name]
        try:
            # Spezielle Methode für Requisition, falls vorhanden
            if hasattr(erp_class, 'send_requisition_to_erp'):
                erp_result = erp_class.send_requisition_to_erp(document_data)
              
            results[erp_name] = {"success": True, "result": erp_result}
        except Exception as e:
            logging.error(f"Error dispatching Requisition to {erp_name}: {str(e)}")
            results[erp_name] = {"success": False, "error": str(e)}
    
    return results

def dispatch_to_erps_PurchaseOrderConfirmation(document_data: Dict[str, Any], erp_targets: List[str]) -> Dict[str, Any]:
    """
    Verarbeitet ein PurchaseOrderConfirmation-Dokument und sendet es an die angegebenen ERP-Systeme.
    """
    results = {}
    
    for erp_name in erp_targets:
        if erp_name not in _erp_integrations:
            results[erp_name] = {"success": False, "error": f"ERP integration '{erp_name}' not found"}
            continue
            
        erp_class = _erp_integrations[erp_name]
        try:
            # Spezielle Methode für PurchaseOrderConfirmation, falls vorhanden
            if hasattr(erp_class, 'send_purchase_order_confirmation_to_erp'):
                erp_result = erp_class.send_purchase_order_confirmation_to_erp(document_data)

            
            results[erp_name] = {"success": True, "result": erp_result}
        except Exception as e:
            logging.error(f"Error dispatching PurchaseOrderConfirmation to {erp_name}: {str(e)}")
            results[erp_name] = {"success": False, "error": str(e)}
    
    return results

def fetch_data_from_erp(erp_name: str, document_id: str, document_type: str) -> Optional[Dict[str, Any]]:
    """Fetches data from an ERP system."""
    if erp_name not in _erp_integrations:
        logging.error(f"ERP integration '{erp_name}' not found")
        return None
        
    erp_class = _erp_integrations[erp_name]
    try:
        # Determine the appropriate method based on document type
        if document_type == "Quote" and hasattr(erp_class, 'fetch_quote'):
            return erp_class.fetch_quote(document_id)
        elif document_type == "PurchaseOrder" and hasattr(erp_class, 'fetch_purchase_order'):
            return erp_class.fetch_purchase_order(document_id)
        elif document_type == "Requisition" and hasattr(erp_class, 'fetch_requisition'):
            return erp_class.fetch_requisition(document_id)
        elif document_type == "RequestForQuote" and hasattr(erp_class, 'fetch_request_for_quote'):
            return erp_class.fetch_request_for_quote(document_id)
        elif document_type == "PurchaseOrderConfirmation" and hasattr(erp_class, 'fetch_purchase_order_confirmation'):
            return erp_class.fetch_purchase_order_confirmation(document_id)
        # Fallback to generic fetch method
        elif hasattr(erp_class, 'fetch_document'):
            return erp_class.fetch_document(document_id, document_type)
        else:
            logging.error(f"No appropriate fetch method found for {document_type} in {erp_name}")
            return None
    except Exception as e:
        logging.error(f"Error fetching {document_type} from {erp_name}: {str(e)}")
        return None

def dispatch_document(document_data, erp_targets):
    """
    Routes a document to the appropriate dispatch method based on its type.
    
    Args:
        document_data: The document data with a 'type' field
        erp_targets: List of ERP systems to dispatch to
        
    Returns:
        Results from dispatching to the targeted ERP systems
    """
    doc_type = document_data.get('type')
    
    if doc_type == "RequestForQuote":
        return dispatch_to_erps(document_data, erp_targets)
    elif doc_type == "PurchaseOrderConfirmation":
        return dispatch_to_erps_PurchaseOrderConfirmation(document_data, erp_targets)
    elif doc_type == "Requisition":
        return dispatch_to_erps_Requisition(document_data, erp_targets)
    elif doc_type == "Quote":
        return dispatch_to_erps_Quote(document_data, erp_targets)
    elif doc_type == "PurchaseOrder":
        return dispatch_to_erps_PurchaseOrder(document_data, erp_targets)
    else:
        logging.warning(f"Unknown document type: {doc_type}. No dispatching performed.")
        return {"status": "error", "message": f"Unknown document type: {doc_type}"}