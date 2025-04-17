# portals/base_portal.py
from abc import ABC, abstractmethod

class BasePortal(ABC):
    """Abstrakte Basisklasse für alle Portal-Integrationen."""
    
    @abstractmethod
    def fetch_documents(self, **filters):
        """Dokumente vom Portal abrufen."""
        pass
    
    @abstractmethod
    def send_document(self, document):
        """Dokument an das Portal senden."""
        pass