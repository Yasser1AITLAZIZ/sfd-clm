"""Generate fake test data for pipeline testing"""
from typing import Dict, Any, List
import random
from datetime import datetime, timedelta


class TestDataGenerator:
    """Generator for fake test data"""
    
    # Sample record IDs
    RECORD_IDS = [
        "001XXXX",
        "001YYYY",
        "001ZZZZ",
        "001AAAA",
        "001BBBB"
    ]
    
    # Sample user requests
    USER_REQUESTS = [
        "Remplis tous les champs manquants",
        "Quel est le montant sur la facture ?",
        "Corrige la date, elle semble incorrecte",
        "Extraire les informations du bénéficiaire",
        "Remplis automatiquement tous les champs vides",
        "Quelle est la date de la facture ?",
        "Extrais le montant total de la facture",
        "Remplis les champs montant_total et date_facture",
        "Peux-tu vérifier et corriger les informations du document ?",
        "Extrais toutes les données de la facture PDF"
    ]
    
    # Document types
    DOCUMENT_TYPES = [
        "application/pdf",
        "image/jpeg",
        "image/png"
    ]
    
    # Field types
    FIELD_TYPES = [
        "currency",
        "date",
        "text",
        "number",
        "email",
        "phone"
    ]
    
    @staticmethod
    def generate_record_id() -> str:
        """Generate a random record ID"""
        return random.choice(TestDataGenerator.RECORD_IDS)
    
    @staticmethod
    def generate_user_request() -> str:
        """Generate a random user request"""
        return random.choice(TestDataGenerator.USER_REQUESTS)
    
    @staticmethod
    def generate_documents(count: int = 3) -> List[Dict[str, Any]]:
        """Generate fake documents"""
        documents = []
        doc_names = [
            "facture.pdf",
            "justificatif.pdf",
            "photo_justificatif.jpg",
            "document_scan.pdf",
            "attestation.pdf"
        ]
        
        for i in range(count):
            doc_name = doc_names[i] if i < len(doc_names) else f"document_{i+1}.pdf"
            doc_type = random.choice(TestDataGenerator.DOCUMENT_TYPES)
            
            documents.append({
                "document_id": f"doc_{i+1}",
                "name": doc_name,
                "url": f"https://example.com/documents/{doc_name}",
                "type": doc_type,
                "indexed": True
            })
        
        return documents
    
    @staticmethod
    def generate_fields_to_fill(count: int = 5) -> List[Dict[str, Any]]:
        """Generate fake fields to fill"""
        fields = []
        
        field_templates = [
            {
                "field_name": "montant_total",
                "field_type": "currency",
                "label": "Montant total",
                "required": True
            },
            {
                "field_name": "date_facture",
                "field_type": "date",
                "label": "Date de facture",
                "required": True
            },
            {
                "field_name": "beneficiaire_nom",
                "field_type": "text",
                "label": "Nom du bénéficiaire",
                "required": True
            },
            {
                "field_name": "beneficiaire_email",
                "field_type": "email",
                "label": "Email du bénéficiaire",
                "required": False
            },
            {
                "field_name": "numero_facture",
                "field_type": "text",
                "label": "Numéro de facture",
                "required": True
            },
            {
                "field_name": "montant_ht",
                "field_type": "currency",
                "label": "Montant HT",
                "required": False
            },
            {
                "field_name": "montant_tva",
                "field_type": "currency",
                "label": "Montant TVA",
                "required": False
            },
            {
                "field_name": "date_echeance",
                "field_type": "date",
                "label": "Date d'échéance",
                "required": False
            }
        ]
        
        for i in range(min(count, len(field_templates))):
            field = field_templates[i].copy()
            # Randomly set some fields as prefilled
            if random.random() < 0.3:  # 30% chance of being prefilled
                if field["field_type"] == "currency":
                    field["value"] = f"{random.uniform(100, 5000):.2f}"
                elif field["field_type"] == "date":
                    date = datetime.now() - timedelta(days=random.randint(1, 365))
                    field["value"] = date.strftime("%Y-%m-%d")
                elif field["field_type"] == "text":
                    field["value"] = f"Sample {field['label']}"
                else:
                    field["value"] = "sample_value"
            else:
                field["value"] = None
            
            fields.append(field)
        
        return fields
    
    @staticmethod
    def generate_salesforce_data_response(record_id: str = None) -> Dict[str, Any]:
        """Generate complete Salesforce data response"""
        if not record_id:
            record_id = TestDataGenerator.generate_record_id()
        
        return {
            "record_id": record_id,
            "record_type": "Claim",
            "documents": TestDataGenerator.generate_documents(random.randint(2, 4)),
            "fields_to_fill": TestDataGenerator.generate_fields_to_fill(random.randint(5, 8))
        }
    
    @staticmethod
    def generate_apex_request(record_id: str = None, session_id: str = None) -> Dict[str, Any]:
        """Generate Apex request"""
        if not record_id:
            record_id = TestDataGenerator.generate_record_id()
        
        return {
            "record_id": record_id,
            "session_id": session_id,  # None for new session
            "user_request": TestDataGenerator.generate_user_request()
        }
    
    @staticmethod
    def generate_mcp_request(record_id: str = None, session_id: str = None) -> Dict[str, Any]:
        """Generate MCP receive request"""
        if not record_id:
            record_id = TestDataGenerator.generate_record_id()
        
        return {
            "record_id": record_id,
            "session_id": session_id,  # None for new session
            "user_message": TestDataGenerator.generate_user_request()
        }


if __name__ == "__main__":
    # Example usage
    generator = TestDataGenerator()
    
    print("Sample Salesforce Data Response:")
    print(generator.generate_salesforce_data_response())
    print()
    
    print("Sample Apex Request (New Session):")
    print(generator.generate_apex_request())
    print()
    
    print("Sample Apex Request (Continuation):")
    print(generator.generate_apex_request(session_id="session_12345"))
    print()
    
    print("Sample MCP Request:")
    print(generator.generate_mcp_request())

