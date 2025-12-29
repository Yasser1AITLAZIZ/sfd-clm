"""Script to generate complex test data for forms"""
import json
import random
from typing import List, Dict, Any


def generate_field(
    index: int,
    field_type: str,
    label: str,
    required: bool = False,
    possible_values: List[str] = None,
    api_name: str = None
) -> Dict[str, Any]:
    """Generate a single field definition"""
    field = {
        "label": label,
        "apiName": api_name or f"field_{index}",
        "type": field_type,
        "required": required,
        "possibleValues": possible_values or [],
        "defaultValue": None
    }
    return field


def generate_simple_fields() -> List[Dict[str, Any]]:
    """Generate simple form with 10 fields"""
    fields = [
        generate_field(1, "text", "Nom", required=True),
        generate_field(2, "text", "Prénom", required=True),
        generate_field(3, "text", "Email", required=True),
        generate_field(4, "text", "Téléphone", required=False),
        generate_field(5, "text", "Adresse", required=False),
        generate_field(6, "date", "Date de naissance", required=False),
        generate_field(7, "picklist", "Type de sinistre", required=True, 
                      possible_values=["Accident", "Bris de glace", "Incendie", "Vol"]),
        generate_field(8, "number", "Montant du sinistre", required=False),
        generate_field(9, "textarea", "Commentaire", required=False),
        generate_field(10, "picklist", "Statut", required=False,
                      possible_values=["En cours", "Traité", "Refusé"])
    ]
    return fields


def generate_medium_fields() -> List[Dict[str, Any]]:
    """Generate medium form with 50 fields"""
    fields = []
    
    # Personal information (10 fields)
    personal_fields = [
        ("Nom", "text", True),
        ("Prénom", "text", True),
        ("Date de naissance", "date", False),
        ("Lieu de naissance", "text", False),
        ("Nationalité", "picklist", False, ["Française", "Autre"]),
        ("Numéro de téléphone", "text", True),
        ("Email", "text", True),
        ("Adresse", "text", True),
        ("Code postal", "text", True),
        ("Ville", "text", True),
    ]
    
    for i, (label, field_type, required, *rest) in enumerate(personal_fields, 1):
        possible_values = rest[0] if rest else []
        fields.append(generate_field(i, field_type, label, required, possible_values))
    
    # Incident information (15 fields)
    incident_fields = [
        ("Date de l'incident", "date", True),
        ("Heure de l'incident", "text", False),
        ("Lieu de l'incident", "text", True),
        ("Type d'incident", "picklist", True, ["Accident", "Bris de glace", "Incendie", "Vol", "Dégât des eaux"]),
        ("Description de l'incident", "textarea", True),
        ("Nombre de véhicules impliqués", "number", False),
        ("Véhicule 1 - Immatriculation", "text", False),
        ("Véhicule 1 - Marque", "text", False),
        ("Véhicule 1 - Modèle", "text", False),
        ("Véhicule 2 - Immatriculation", "text", False),
        ("Véhicule 2 - Marque", "text", False),
        ("Véhicule 2 - Modèle", "text", False),
        ("Témoins présents", "picklist", False, ["Oui", "Non"]),
        ("Nombre de témoins", "number", False),
        ("Police appelée", "picklist", False, ["Oui", "Non"]),
    ]
    
    for i, (label, field_type, required, *rest) in enumerate(incident_fields, len(fields) + 1):
        possible_values = rest[0] if rest else []
        fields.append(generate_field(i, field_type, label, required, possible_values))
    
    # Damage information (10 fields)
    damage_fields = [
        ("Dommages constatés", "picklist", True, ["Oui", "Non"]),
        ("Type de dommage", "picklist", False, ["Partiel", "Total"]),
        ("Montant estimé des dommages", "number", False),
        ("Dommages corporels", "picklist", False, ["Oui", "Non"]),
        ("Dommages matériels", "picklist", False, ["Oui", "Non"]),
        ("Photos disponibles", "picklist", False, ["Oui", "Non"]),
        ("Nombre de photos", "number", False),
        ("Expertise nécessaire", "picklist", False, ["Oui", "Non"]),
        ("Date d'expertise", "date", False),
        ("Commentaire sur les dommages", "textarea", False),
    ]
    
    for i, (label, field_type, required, *rest) in enumerate(damage_fields, len(fields) + 1):
        possible_values = rest[0] if rest else []
        fields.append(generate_field(i, field_type, label, required, possible_values))
    
    # Insurance information (10 fields)
    insurance_fields = [
        ("Numéro de police", "text", True),
        ("Date de souscription", "date", False),
        ("Type de garantie", "picklist", True, ["Tous risques", "Tiers", "Tiers plus"]),
        ("Franchise", "number", False),
        ("Valeur du véhicule", "number", False),
        ("Kilométrage", "number", False),
        ("Date du dernier contrôle technique", "date", False),
        ("Assurance précédente", "text", False),
        ("Historique des sinistres", "textarea", False),
        ("Statut de la demande", "picklist", False, ["En attente", "En cours", "Traité", "Refusé"]),
    ]
    
    for i, (label, field_type, required, *rest) in enumerate(insurance_fields, len(fields) + 1):
        possible_values = rest[0] if rest else []
        fields.append(generate_field(i, field_type, label, required, possible_values))
    
    # Additional information (5 fields)
    additional_fields = [
        ("Commentaire général", "textarea", False),
        ("Pièces jointes", "picklist", False, ["Oui", "Non"]),
        ("Nombre de pièces jointes", "number", False),
        ("Date de déclaration", "date", True),
        ("Référence du sinistre", "text", False),
    ]
    
    for i, (label, field_type, required, *rest) in enumerate(additional_fields, len(fields) + 1):
        possible_values = rest[0] if rest else []
        fields.append(generate_field(i, field_type, label, required, possible_values))
    
    return fields


def generate_complex_fields() -> List[Dict[str, Any]]:
    """Generate complex form with 100+ fields"""
    fields = []
    
    # Start with medium fields
    fields.extend(generate_medium_fields())
    
    # Add more sections to reach 100+ fields
    
    # Vehicle details (20 fields)
    for vehicle_num in range(1, 4):
        vehicle_fields = [
            (f"Véhicule {vehicle_num} - Immatriculation", "text", False),
            (f"Véhicule {vehicle_num} - Marque", "text", False),
            (f"Véhicule {vehicle_num} - Modèle", "text", False),
            (f"Véhicule {vehicle_num} - Année", "number", False),
            (f"Véhicule {vehicle_num} - Puissance", "number", False),
            (f"Véhicule {vehicle_num} - Carburant", "picklist", False, ["Essence", "Diesel", "Électrique", "Hybride"]),
            (f"Véhicule {vehicle_num} - Kilométrage", "number", False),
        ]
        for i, (label, field_type, required, *rest) in enumerate(vehicle_fields, len(fields) + 1):
            possible_values = rest[0] if rest else []
            fields.append(generate_field(i, field_type, label, required, possible_values))
    
    # Third party information (15 fields)
    third_party_fields = [
        ("Tiers - Nom", "text", False),
        ("Tiers - Prénom", "text", False),
        ("Tiers - Adresse", "text", False),
        ("Tiers - Téléphone", "text", False),
        ("Tiers - Email", "text", False),
        ("Tiers - Assurance", "text", False),
        ("Tiers - Numéro de police", "text", False),
        ("Tiers - Responsabilité", "picklist", False, ["Responsable", "Non responsable", "Partagée"]),
        ("Taux de responsabilité", "number", False),
        ("Tiers - Véhicule - Immatriculation", "text", False),
        ("Tiers - Véhicule - Marque", "text", False),
        ("Tiers - Véhicule - Modèle", "text", False),
        ("Tiers - Dommages constatés", "picklist", False, ["Oui", "Non"]),
        ("Tiers - Montant des dommages", "number", False),
        ("Tiers - Commentaire", "textarea", False),
    ]
    
    for i, (label, field_type, required, *rest) in enumerate(third_party_fields, len(fields) + 1):
        possible_values = rest[0] if rest else []
        fields.append(generate_field(i, field_type, label, required, possible_values))
    
    # Additional details (15 fields)
    detail_fields = [
        ("Météo au moment de l'incident", "picklist", False, ["Beau temps", "Pluie", "Neige", "Brouillard"]),
        ("Visibilité", "picklist", False, ["Bonne", "Moyenne", "Faible"]),
        ("État de la route", "picklist", False, ["Sèche", "Mouillée", "Enneigée", "Verglacée"]),
        ("Limitation de vitesse", "number", False),
        ("Vitesse estimée", "number", False),
        ("Feux allumés", "picklist", False, ["Oui", "Non"]),
        ("Ceinture de sécurité", "picklist", False, ["Oui", "Non"]),
        ("Airbag déployé", "picklist", False, ["Oui", "Non"]),
        ("Alcoolémie", "picklist", False, ["Négative", "Positive"]),
        ("Taux d'alcoolémie", "number", False),
        ("Téléphone au volant", "picklist", False, ["Oui", "Non"]),
        ("Autre infraction", "picklist", False, ["Oui", "Non"]),
        ("Description de l'infraction", "textarea", False),
        ("Amende reçue", "picklist", False, ["Oui", "Non"]),
        ("Montant de l'amende", "number", False),
    ]
    
    for i, (label, field_type, required, *rest) in enumerate(detail_fields, len(fields) + 1):
        possible_values = rest[0] if rest else []
        fields.append(generate_field(i, field_type, label, required, possible_values))
    
    return fields


def generate_conditional_fields() -> List[Dict[str, Any]]:
    """Generate form with conditional dependencies"""
    fields = [
        # Conditional trigger
        generate_field(1, "picklist", "Y a-t-il un dommage ?", required=True,
                      possible_values=["Oui", "Non"]),
        
        # Conditional fields (should only be filled if "Oui")
        generate_field(2, "picklist", "Type de dommage", required=False,
                      possible_values=["Dommages à l'adversaire", "Dommages à l'assuré", "Les deux"]),
        generate_field(3, "number", "Montant du dommage", required=False),
        generate_field(4, "textarea", "Description du dommage", required=False),
        
        # Another conditional
        generate_field(5, "picklist", "Y a-t-il un tiers impliqué ?", required=True,
                      possible_values=["Oui", "Non"]),
        
        # Conditional fields for third party
        generate_field(6, "text", "Tiers - Nom", required=False),
        generate_field(7, "text", "Tiers - Prénom", required=False),
        generate_field(8, "text", "Tiers - Téléphone", required=False),
        generate_field(9, "text", "Tiers - Assurance", required=False),
        
        # Date dependencies
        generate_field(10, "date", "Date de l'incident", required=True),
        generate_field(11, "date", "Date de déclaration", required=True),  # Should be after incident
        
        # Location dependencies
        generate_field(12, "text", "Ville", required=False),
        generate_field(13, "text", "Code postal", required=False),  # Should match city
    ]
    
    return fields


def main():
    """Generate all test data files"""
    print("Generating test data files...")
    
    # Simple form (10 fields)
    simple_fields = generate_simple_fields()
    with open("test-data/fields/fields_simple.json", "w", encoding="utf-8") as f:
        json.dump({"fields": simple_fields}, f, indent=2, ensure_ascii=False)
    print(f"✓ Generated fields_simple.json with {len(simple_fields)} fields")
    
    # Medium form (50 fields)
    medium_fields = generate_medium_fields()
    with open("test-data/fields/fields_medium.json", "w", encoding="utf-8") as f:
        json.dump({"fields": medium_fields}, f, indent=2, ensure_ascii=False)
    print(f"✓ Generated fields_medium.json with {len(medium_fields)} fields")
    
    # Complex form (100+ fields)
    complex_fields = generate_complex_fields()
    with open("test-data/fields/fields_complex.json", "w", encoding="utf-8") as f:
        json.dump({"fields": complex_fields}, f, indent=2, ensure_ascii=False)
    print(f"✓ Generated fields_complex.json with {len(complex_fields)} fields")
    
    # Conditional form
    conditional_fields = generate_conditional_fields()
    with open("test-data/fields/fields_conditional.json", "w", encoding="utf-8") as f:
        json.dump({"fields": conditional_fields}, f, indent=2, ensure_ascii=False)
    print(f"✓ Generated fields_conditional.json with {len(conditional_fields)} fields")
    
    print("\nAll test data files generated successfully!")


if __name__ == "__main__":
    main()


