"""Intelligent mock data generator with field relationship detection"""
import random
from typing import Dict, Any, List, Set, Optional
from datetime import datetime, timedelta
import re


class MockDataGenerator:
    """Intelligent mock data generator with field relationship detection"""
    
    def __init__(self):
        """Initialize mock data generator"""
        self.generated_values = {}  # Track generated values for consistency
        self.field_relationships = {}  # Track detected relationships
        
        # French city/postal code mappings for realistic data
        self.city_postal_codes = {
            "Paris": "75001",
            "Lyon": "69001",
            "Marseille": "13001",
            "Toulouse": "31000",
            "Nice": "06000",
            "Nantes": "44000",
            "Strasbourg": "67000",
            "Montpellier": "34000",
            "Bordeaux": "33000",
            "Lille": "59000"
        }
        
        # Sample names for realistic generation
        self.first_names = ["Jean", "Marie", "Pierre", "Sophie", "Paul", "Julie", "Michel", "Claire"]
        self.last_names = ["Dupont", "Martin", "Bernard", "Thomas", "Petit", "Robert", "Richard", "Durand"]
    
    def detect_field_relationships(self, fields_dictionary: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Detect relationships between fields based on names and labels.
        
        Args:
            fields_dictionary: Dictionary of field definitions
            
        Returns:
            Dictionary mapping field names to list of related field names
        """
        relationships = {}
        field_names = list(fields_dictionary.keys())
        field_labels = {name: fields_dictionary[name].get("label", "").lower() 
                       for name in field_names}
        
        # Common relationship patterns
        relationship_patterns = {
            "city": ["postal_code", "code_postal", "zip", "country", "pays"],
            "postal_code": ["city", "ville", "address", "adresse"],
            "first_name": ["last_name", "nom", "name"],
            "last_name": ["first_name", "prénom", "name"],
            "incident_date": ["claim_date", "date_sinistre", "date_declaration"],
            "has_damage": ["damage_type", "type_dommage", "damage_amount", "montant_dommage"],
            "vehicle_count": ["vehicle_1", "vehicle_2", "vehicule"],
            "number_vehicles": ["vehicle_details", "vehicule_details"]
        }
        
        for field_name, field_label in field_labels.items():
            related = []
            
            # Check against patterns
            for pattern, related_keywords in relationship_patterns.items():
                if pattern in field_label or any(kw in field_label for kw in pattern.split("_")):
                    # Find related fields
                    for other_name, other_label in field_labels.items():
                        if other_name != field_name:
                            for keyword in related_keywords:
                                if keyword in other_label:
                                    related.append(other_name)
            
            # Detect conditional dependencies (e.g., "has_damage" -> damage fields)
            if "has" in field_label or "est_ce" in field_label or "y_a" in field_label:
                # This might be a boolean/conditional field
                for other_name, other_label in field_labels.items():
                    if other_name != field_name:
                        # Check if other field is related to this conditional
                        conditional_keywords = ["dommage", "damage", "vehicule", "vehicle", 
                                               "tiers", "third", "adversaire", "adverse"]
                        if any(kw in other_label for kw in conditional_keywords):
                            if field_name not in relationships:
                                relationships[field_name] = []
                            relationships[field_name].append(other_name)
            
            if related:
                relationships[field_name] = list(set(related))  # Remove duplicates
        
        self.field_relationships = relationships
        return relationships
    
    def generate_coherent_value(
        self,
        field_name: str,
        field_config: Dict[str, Any],
        fields_dictionary: Dict[str, Any]
    ) -> Any:
        """
        Generate a coherent value for a field, considering relationships.
        
        Args:
            field_name: Name of the field
            field_config: Field configuration
            fields_dictionary: All fields dictionary for context
            
        Returns:
            Generated value
        """
        field_type = field_config.get("type", "text").lower()
        field_label = field_config.get("label", "").lower()
        is_required = field_config.get("required", False)
        possible_values = field_config.get("possibleValues", [])
        default_value = field_config.get("defaultValue")
        
        # Skip optional fields 30% of the time
        if not is_required and random.random() < 0.3:
            return None
        
        # Check for relationships and use existing values
        if field_name in self.field_relationships:
            related_fields = self.field_relationships[field_name]
            for related_field in related_fields:
                if related_field in self.generated_values:
                    related_value = self.generated_values[related_field]
                    # Generate coherent value based on relationship
                    if "city" in field_label and "postal" in related_field.lower():
                        # If we have a city, generate matching postal code
                        city = related_value
                        if city in self.city_postal_codes:
                            return self.city_postal_codes[city]
                    elif "postal" in field_label and "city" in related_field.lower():
                        # If we have postal code, generate matching city
                        postal = related_value
                        for city, code in self.city_postal_codes.items():
                            if code == postal:
                                return city
        
        # Generate based on type
        if field_type in ["picklist", "radio"]:
            if possible_values:
                value = random.choice(possible_values)
            elif default_value:
                value = default_value
            else:
                value = "Valeur par défaut"
        
        elif field_type == "number":
            value = self._generate_number(field_label, field_name)
        
        elif field_type == "textarea":
            value = self._generate_textarea(field_label)
        
        elif field_type == "date":
            value = self._generate_date(field_label, fields_dictionary)
        
        else:  # text or other
            value = self._generate_text(field_name, field_label, fields_dictionary)
        
        # Store generated value for consistency
        self.generated_values[field_name] = value
        return value
    
    def _generate_number(self, field_label: str, field_name: str) -> float:
        """Generate a number value based on field context"""
        label_lower = field_label.lower()
        
        if "taux" in label_lower or "pourcentage" in label_lower or "percentage" in label_lower:
            return round(random.uniform(0, 100), 2)
        elif "montant" in label_lower or "amount" in label_lower or "prix" in label_lower:
            return round(random.uniform(100, 50000), 2)
        elif "nombre" in label_lower or "count" in label_lower or "number" in label_lower:
            if "vehicule" in label_lower or "vehicle" in label_lower:
                return random.randint(1, 3)
            else:
                return random.randint(1, 10)
        elif "age" in label_lower:
            return random.randint(18, 80)
        else:
            return random.randint(0, 10000)
    
    def _generate_textarea(self, field_label: str) -> str:
        """Generate textarea value"""
        if "commentaire" in field_label.lower() or "comment" in field_label.lower():
            return "Ceci est un commentaire de test généré automatiquement pour simuler l'extraction de données depuis un document.\nIl peut contenir plusieurs lignes de texte."
        else:
            return "Texte multi-lignes généré automatiquement.\nLigne 2 du texte.\nLigne 3 du texte avec plus de détails."
    
    def _generate_date(self, field_label: str, fields_dictionary: Dict[str, Any]) -> str:
        """Generate a date value, ensuring logical ordering"""
        label_lower = field_label.lower()
        base_date = datetime.now() - timedelta(days=random.randint(1, 365))
        
        # Ensure incident date is before claim date
        if "incident" in label_lower or "sinistre" in label_lower or "accident" in label_lower:
            # Incident date should be in the past
            date = base_date - timedelta(days=random.randint(1, 30))
        elif "claim" in label_lower or "declaration" in label_lower or "déclaration" in label_lower:
            # Claim date should be after incident date if it exists
            incident_dates = [v for k, v in self.generated_values.items() 
                            if "incident" in k.lower() or "sinistre" in k.lower()]
            if incident_dates:
                # Parse the incident date and ensure claim is after
                try:
                    incident_date = datetime.strptime(incident_dates[0], "%Y-%m-%d")
                    date = incident_date + timedelta(days=random.randint(1, 7))
                except:
                    date = base_date
            else:
                date = base_date
        else:
            date = base_date
        
        return date.strftime("%Y-%m-%d")
    
    def _generate_text(self, field_name: str, field_label: str, fields_dictionary: Dict[str, Any]) -> str:
        """Generate text value based on field context"""
        label_lower = field_label.lower()
        
        # Name fields
        if "nom" in label_lower and "prénom" not in label_lower:
            return random.choice(self.last_names)
        elif "prénom" in label_lower or "first" in label_lower:
            first = random.choice(self.first_names)
            self.generated_values[field_name] = first
            return first
        elif "name" in label_lower and "first" not in label_lower and "last" not in label_lower:
            return f"{random.choice(self.first_names)} {random.choice(self.last_names)}"
        
        # Address fields
        elif "adresse" in label_lower or "address" in label_lower:
            city = random.choice(list(self.city_postal_codes.keys()))
            postal = self.city_postal_codes[city]
            return f"{random.randint(1, 200)} Rue de la Paix, {postal} {city}"
        elif "ville" in label_lower or "city" in label_lower:
            city = random.choice(list(self.city_postal_codes.keys()))
            self.generated_values[field_name] = city
            return city
        elif "postal" in label_lower or "code_postal" in label_lower or "zip" in label_lower:
            # Check if we have a city already
            for k, v in self.generated_values.items():
                if "ville" in k.lower() or "city" in k.lower():
                    if v in self.city_postal_codes:
                        return self.city_postal_codes[v]
            # Otherwise random
            return random.choice(list(self.city_postal_codes.values()))
        
        # Contact fields
        elif "téléphone" in label_lower or "phone" in label_lower or "tel" in label_lower:
            return f"+33 {random.randint(1, 9)} {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)}"
        elif "email" in label_lower or "e-mail" in label_lower:
            first = self.generated_values.get("first_name", random.choice(self.first_names))
            last = self.generated_values.get("last_name", random.choice(self.last_names))
            return f"{first.lower()}.{last.lower()}@example.com"
        
        # Vehicle fields
        elif "immatriculation" in label_lower or "license" in label_lower or "plate" in label_lower:
            return f"{random.choice(['AB', 'CD', 'EF', 'GH'])}-{random.randint(100, 999)}-{random.choice(['AB', 'CD', 'EF', 'GH'])}"
        
        # Default text generation
        elif "numéro" in label_lower or "n°" in label_lower or "number" in label_lower:
            return f"{random.randint(1000, 9999)}"
        elif "date" in label_lower:
            return self._generate_date(label_lower, fields_dictionary)
        else:
            # Use label as base
            return f"Valeur pour {field_label if field_label else field_name}"
    
    def generate_extracted_data(self, fields_dictionary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate intelligent mock extracted data with relationships.
        
        Args:
            fields_dictionary: Dictionary of field definitions
            
        Returns:
            Dictionary of extracted field values
        """
        # Reset state
        self.generated_values = {}
        
        # Detect relationships
        relationships = self.detect_field_relationships(fields_dictionary)
        
        # Sort fields: required first, then by relationships
        required_fields = []
        optional_fields = []
        
        for field_name, field_config in fields_dictionary.items():
            if isinstance(field_config, dict) and field_config.get("required", False):
                required_fields.append((field_name, field_config))
            else:
                optional_fields.append((field_name, field_config))
        
        # Process required fields first
        all_fields = required_fields + optional_fields
        
        extracted_data = {}
        for field_name, field_config in all_fields:
            value = self.generate_coherent_value(field_name, field_config, fields_dictionary)
            extracted_data[field_name] = value
        
        return extracted_data
    
    def validate_data_consistency(self, extracted_data: Dict[str, Any], fields_dictionary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and fix data consistency issues.
        
        Args:
            extracted_data: Generated extracted data
            fields_dictionary: Field definitions
            
        Returns:
            Validated extracted data
        """
        validated = extracted_data.copy()
        
        # Validate date ordering
        incident_dates = {}
        claim_dates = {}
        
        for field_name, value in validated.items():
            if value is None:
                continue
            field_config = fields_dictionary.get(field_name, {})
            field_label = field_config.get("label", "").lower()
            
            if "incident" in field_label or "sinistre" in field_label:
                try:
                    incident_dates[field_name] = datetime.strptime(str(value), "%Y-%m-%d")
                except:
                    pass
            elif "claim" in field_label or "declaration" in field_label:
                try:
                    claim_dates[field_name] = datetime.strptime(str(value), "%Y-%m-%d")
                except:
                    pass
        
        # Ensure claim dates are after incident dates
        for claim_field, claim_date in claim_dates.items():
            for incident_field, incident_date in incident_dates.items():
                if claim_date < incident_date:
                    # Adjust claim date to be after incident
                    validated[claim_field] = (incident_date + timedelta(days=random.randint(1, 7))).strftime("%Y-%m-%d")
        
        # Validate city/postal code consistency
        cities = {}
        postal_codes = {}
        
        for field_name, value in validated.items():
            if value is None:
                continue
            field_config = fields_dictionary.get(field_name, {})
            field_label = field_config.get("label", "").lower()
            
            if "ville" in field_label or "city" in field_label:
                cities[field_name] = str(value)
            elif "postal" in field_label or "code_postal" in field_label:
                postal_codes[field_name] = str(value)
        
        # Ensure postal codes match cities
        for city_field, city in cities.items():
            if city in self.city_postal_codes:
                # Find related postal code field
                for postal_field in postal_codes.keys():
                    if postal_field in self.field_relationships.get(city_field, []):
                        validated[postal_field] = self.city_postal_codes[city]
        
        return validated

