import uuid
from datetime import datetime

def get_nested(data, *keys, default=None):
    """Hilfsfunktion, um verschachtelte Felder sicher zu extrahieren."""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data if data is not None else default

def transform_response(response):
    """Transformiert die Antwort basierend auf dem Schema."""
    transformed = {
        "id": get_nested(response, "id", default=None),
        "type": get_nested(response, "type", default=None),
        "buyer": {
            "tnId": get_nested(response, "buyer", "tnId", default=None),
            "name": get_nested(response, "buyer", "name", default=None)
        },
        "supplier": {
            "tnId": get_nested(response, "supplier", "tnId", default=None),
            "name": get_nested(response, "supplier", "name", default=None)
        },
        "subject": get_nested(response, "subject", default=None),
        "comment": get_nested(response, "comment", default=None),
        "referenceNumber": get_nested(response, "referenceNumber", default=None),
        "requisitionId": get_nested(response, "requisitionId", default=None),
        "requestForQuoteId": get_nested(response, "requestForQuoteId", default=None),
        "quoteId": get_nested(response, "quoteId", default=None),
        "purchaseOrderId": get_nested(response, "purchaseOrderId", default=None),
        "priority": get_nested(response, "priority", default=None),
        "offeredQuality": "Genuine",
        "taxStatus": "Exempt",
        "paymentTerms": get_nested(response, "paymentTerms", default=None),
        "termsAndConditions": get_nested(response, "termsAndConditions", default=None),
        "transportMode": get_nested(response, "transportMode", default=None),
        "vessel": {
            "name": get_nested(response, "vessel", "name", default=None),
            "imoNumber": get_nested(response, "vessel", "imoNumber", default=None),
            "estimatedTimeArrival": datetime.utcnow().isoformat() + "Z",
            "estimatedTimeDeparture": datetime.utcnow().isoformat() + "Z"
        },
        "deliveryPort": {
            "code": get_nested(response, "deliveryPort", "code", default=None),
            "name": get_nested(response, "deliveryPort", "name", default=None),
            "countryCode": get_nested(response, "deliveryPort", "countryCode", default=None)
        },
        "deliveryTerms": {
            "code": get_nested(response, "deliveryTerms", "code", default=None),
            "placeOfDelivery": get_nested(response, "deliveryTerms", "placeOfDelivery", default=None)
        },
        "packagingInstructions": get_nested(response, "packagingInstructions", default=None),
        "billing": {
            "name": get_nested(response, "billing", "name", default=None),
            "identification": get_nested(response, "billing", "identification", default=None),
            "address": {
                "streetAddress1": get_nested(response, "billing", "address", "streetAddress1", default=None),
                "streetAddress2": get_nested(response, "billing", "address", "streetAddress2", default=None),
                "city": get_nested(response, "billing", "address", "city", default=None),
                "zipCode": get_nested(response, "billing", "address", "zipCode", default=None),
                "state": get_nested(response, "billing", "address", "state", default=None),
                "countryCode": get_nested(response, "billing", "address", "countryCode", default=None)
            },
            "contact": {
                "jobTitle": get_nested(response, "billing", "contact", "jobTitle", default=None),
                "name": get_nested(response, "billing", "contact", "name", default=None),
                "telephone": get_nested(response, "billing", "contact", "telephone", default=None),
                "fax": get_nested(response, "billing", "contact", "fax", default=None),
                "email": get_nested(response, "billing", "contact", "email", default=None)
            }
        },
        "buyerContact": {
            "name": get_nested(response, "buyerContact", "name", default=None),
            "identification": get_nested(response, "buyerContact", "identification", default=None),
            "address": {
                "streetAddress1": get_nested(response, "buyerContact", "address", "streetAddress1", default=None),
                "streetAddress2": get_nested(response, "buyerContact", "address", "streetAddress2", default=None),
                "city": get_nested(response, "buyerContact", "address", "city", default=None),
                "zipCode": get_nested(response, "buyerContact", "address", "zipCode", default=None),
                "state": get_nested(response, "buyerContact", "address", "state", default=None),
                "countryCode": get_nested(response, "buyerContact", "address", "countryCode", default=None)
            },
            "contact": {
                "jobTitle": get_nested(response, "buyerContact", "contact", "jobTitle", default=None),
                "name": get_nested(response, "buyerContact", "contact", "name", default=None),
                "telephone": get_nested(response, "buyerContact", "contact", "telephone", default=None),
                "fax": get_nested(response, "buyerContact", "contact", "fax", default=None),
                "email": get_nested(response, "buyerContact", "contact", "email", default=None)
            }
        },
        "supplierContact": {
            "name": get_nested(response, "supplierContact", "name", default=None),
            "identification": get_nested(response, "supplierContact", "identification", default=None),
            "address": {
                "streetAddress1": get_nested(response, "supplierContact", "address", "streetAddress1", default=None),
                "streetAddress2": get_nested(response, "supplierContact", "address", "streetAddress2", default=None),
                "city": get_nested(response, "supplierContact", "address", "city", default=None),
                "zipCode": get_nested(response, "supplierContact", "address", "zipCode", default=None),
                "state": get_nested(response, "supplierContact", "address", "state", default=None),
                "countryCode": get_nested(response, "supplierContact", "address", "countryCode", default=None)
            },
            "contact": {
                "jobTitle": get_nested(response, "supplierContact", "contact", "jobTitle", default=None),
                "name": get_nested(response, "supplierContact", "contact", "name", default=None),
                "telephone": get_nested(response, "supplierContact", "contact", "telephone", default=None),
                "fax": get_nested(response, "supplierContact", "contact", "fax", default=None),
                "email": get_nested(response, "supplierContact", "contact", "email", default=None)
            }
        },
        "lineItemCount": get_nested(response, "lineItemCount", default=None),
        "lineItems": [
            {
                "id": str(uuid.uuid4()),
                "number": get_nested(item, "number", default=None),
                "supplierPartNumber": get_nested(item, "supplierPartNumber", default=None),
                "description": get_nested(item, "description", default=None),
                "quality": "High",
                "partIdentification": get_nested(item, "partIdentification", default=None),
                "leadTimeDays": get_nested(item, "deliveryLeadTime", default=None),
                "quantity": get_nested(item, "quantity", default=None),
                "unitOfMeasure": get_nested(item, "unitOfMeasure", default=None),
                "unitPrice": get_nested(item, "unitPrice", default=None),
                "discountCost": get_nested(item, "discountCost", default=None),
                "discountPercentage": get_nested(item, "discountPercentage", default=None),
                "totalCost": get_nested(item, "totalCost", default=None),
                "comment": get_nested(item, "comment", default=None),
                "equipmentSection": get_nested(item, "equipmentSection", default=None),
                "deliveryTerms": {
                    "code": get_nested(item, "deliveryTerms", "code", default=None),
                    "placeOfDelivery": get_nested(item, "deliveryTerms", "placeOfDelivery", default=None)
                },
                "declined": get_nested(item, "declined", default=None),
                "declinedReasonText": get_nested(item, "declinedReasonText", default=None),
                "customsInfo": {
                    "code": get_nested(item, "customsInfo", "code", default=None),
                    "grossWeight": get_nested(item, "customsInfo", "grossWeight", default=None),
                    "netWeight": get_nested(item, "customsInfo", "netWeight", default=None),
                    "countryOfOrigin": get_nested(item, "customsInfo", "countryOfOrigin", default=None)
                },
                "attachments": get_nested(item, "attachments", default=None)
            }
            for item in get_nested(response, "lineItems", default=[])
        ],
        "currency": {
            "code": get_nested(response, "currency", "code", default=None)
        },
        "exported": get_nested(response, "exported", default=None),
        "exportedDate": get_nested(response, "exportedDate", default=None),
        "createdDate": get_nested(response, "createdDate", default=None),
        "submittedDate": get_nested(response, "submittedDate", default=None)
    }
    return transformed