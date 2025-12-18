"""Mock user request examples for testing"""
from typing import List, Dict, Any

# Examples of realistic user requests
MOCK_USER_REQUESTS: List[str] = [
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


def get_random_user_request() -> str:
    """Get a random user request from the mock list"""
    import random
    return random.choice(MOCK_USER_REQUESTS)


def get_user_request_by_index(index: int) -> str:
    """Get a specific user request by index"""
    if 0 <= index < len(MOCK_USER_REQUESTS):
        return MOCK_USER_REQUESTS[index]
    return MOCK_USER_REQUESTS[0]

