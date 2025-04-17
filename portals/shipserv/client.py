# portals/shipserv/client.py
from portals.base_portal import BasePortal

class ShipServPortal(BasePortal):
    def __init__(self, api_key, api_url):
        self.api_key = api_key
        self.api_url = api_url
        
    def fetch_documents(self, **filters):
        # Implementation für ShipServ
        pass
        
    def send_document(self, document):
        # Implementation für ShipServ
        pass