from integrations.erp_collmex import ERPcollmexIntegration
from integrations.erp_pds import ERPpdsIntegration
from integrations.erp_sharepoint import ERPsharepointIntegration
import logging

ERP_INTEGRATIONS = {}

def register_erp_integration(name, integration_class):
    """
    Register an ERP integration class with a specific name.
    :param name: The name of the ERP system (e.g., "ERP_A").
    :param integration_class: The class that handles the ERP integration.
    """
    ERP_INTEGRATIONS[name] = integration_class

    

def dispatch_to_erps(data, erp_targets):
    """
    Dispatch data to multiple ERP systems and update data with ERPNummer if available.
    :param data: The data to send.
    :param erp_targets: A list of ERP systems to send the data to.
    :return: A dictionary with the results for each ERP system.
    """
    results = {}
    for erp in erp_targets:
        integration_class = ERP_INTEGRATIONS.get(erp)
        if not integration_class:
            logging.warning(f"Unknown ERP target: {erp}")
            results[erp] = None
            continue

        try:
            # Send data to the ERP system
            response = integration_class.send_to_erp(data)
            results[erp] = response

            # Update or add ERPNummer in data if it exists in the response
            if response and "ERPNummer" in response:
                erp_number = response["ERPNummer"]
                if erp_number:
                    data["ERPNummer"] = erp_number  # Update or add ERPNummer
                    logging.info(f"ERPNummer updated in data: {erp_number}")

        except Exception as e:
            logging.error(f"Error sending data to {erp}: {e}")
            results[erp] = None

    return results


def fetch_data_from_erp(erp_name, document_id, document_type):
    """
    Fetch data from the specified ERP system based on document ID and type.
    :param erp_name: The name of the ERP system (e.g., "ERP_A").
    :param document_id: The unique document ID.
    :param document_type: The type of the document (e.g., "Quote").
    :return: The data fetched from the ERP system.
    """
    integration_class = ERP_INTEGRATIONS.get(erp_name)
    if not integration_class:
        raise ValueError(f"Unknown ERP system: {erp_name}")

    try:
        return integration_class.fetch_document(document_id, document_type)
    except Exception as e:
        logging.error(f"Error fetching data from {erp_name}: {e}")
        raise