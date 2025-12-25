"""Mock datasets for different record IDs"""
from typing import Dict, Any
from app.models.schemas import (
    GetRecordDataResponse, 
    DocumentSchema, 
    FieldToFillSchema,
    SalesforceFormFieldSchema
)


# Mock datasets mapping record_id to data
# Using new format with "fields" instead of "fields_to_fill"
MOCK_RECORDS: Dict[str, GetRecordDataResponse] = {
    "001XX000001": GetRecordDataResponse(
        record_id="001XX000001",
        record_type="Claim",
        documents=[
            DocumentSchema(
                document_id="doc_1",
                name="facture_001.pdf",
                url="https://example.com/documents/facture_001.pdf",
                type="application/pdf",
                indexed=True
            ),
            DocumentSchema(
                document_id="doc_2",
                name="photo_dommages_001.jpg",
                url="https://example.com/documents/photo_dommages_001.jpg",
                type="image/jpeg",
                indexed=True
            )
        ],
        fields=[
            SalesforceFormFieldSchema(
                label="Montant total",
                apiName="montant_total",
                type="number",
                required=True,
                possibleValues=[],
                defaultValue=None
            ),
            SalesforceFormFieldSchema(
                label="Date de facture",
                apiName="date_facture",
                type="text",
                required=True,
                possibleValues=[],
                defaultValue=None
            ),
            SalesforceFormFieldSchema(
                label="Numéro de facture",
                apiName="numero_facture",
                type="text",
                required=True,
                possibleValues=[],
                defaultValue=None
            ),
            SalesforceFormFieldSchema(
                label="Nom du bénéficiaire",
                apiName="beneficiaire_nom",
                type="text",
                required=True,
                possibleValues=[],
                defaultValue=None
            )
        ]
    ),
    "001XX000002": GetRecordDataResponse(
        record_id="001XX000002",
        record_type="Claim",
        documents=[
            DocumentSchema(
                document_id="doc_3",
                name="devis_002.pdf",
                url="https://example.com/documents/devis_002.pdf",
                type="application/pdf",
                indexed=True
            )
        ],
        fields=[
            SalesforceFormFieldSchema(
                label="Montant total",
                apiName="montant_total",
                type="number",
                required=True,
                possibleValues=[],
                defaultValue=None
            ),
            SalesforceFormFieldSchema(
                label="Date du devis",
                apiName="date_devis",
                type="text",
                required=True,
                possibleValues=[],
                defaultValue=None
            ),
            SalesforceFormFieldSchema(
                label="Description du sinistre",
                apiName="description_sinistre",
                type="textarea",
                required=False,
                possibleValues=[],
                defaultValue=None
            )
        ]
    ),
    "001XX000003": GetRecordDataResponse(
        record_id="001XX000003",
        record_type="Claim",
        documents=[
            DocumentSchema(
                document_id="doc_4",
                name="rapport_expert_003.pdf",
                url="https://example.com/documents/rapport_expert_003.pdf",
                type="application/pdf",
                indexed=True
            ),
            DocumentSchema(
                document_id="doc_5",
                name="photos_003.zip",
                url="https://example.com/documents/photos_003.zip",
                type="application/zip",
                indexed=True
            )
        ],
        fields=[
            SalesforceFormFieldSchema(
                label="Montant d'indemnisation",
                apiName="montant_indemnisation",
                type="number",
                required=True,
                possibleValues=[],
                defaultValue=None
            ),
            SalesforceFormFieldSchema(
                label="Date du sinistre",
                apiName="date_sinistre",
                type="text",
                required=True,
                possibleValues=[],
                defaultValue=None
            ),
            SalesforceFormFieldSchema(
                label="Lieu du sinistre",
                apiName="lieu_sinistre",
                type="text",
                required=True,
                possibleValues=[],
                defaultValue=None
            ),
            SalesforceFormFieldSchema(
                label="Nom de l'expert",
                apiName="expert_nom",
                type="text",
                required=False,
                possibleValues=[],
                defaultValue=None
            )
        ]
    ),
    "001XX000004": GetRecordDataResponse(
        record_id="001XX000004",
        record_type="Claim",
        documents=[
            DocumentSchema(
                document_id="doc_6",
                name="contrat_004.pdf",
                url="https://example.com/documents/contrat_004.pdf",
                type="application/pdf",
                indexed=True
            )
        ],
        fields=[
            SalesforceFormFieldSchema(
                label="Numéro de contrat",
                apiName="numero_contrat",
                type="text",
                required=True,
                possibleValues=[],
                defaultValue=None
            ),
            SalesforceFormFieldSchema(
                label="Date d'effet",
                apiName="date_effet",
                type="text",
                required=True,
                possibleValues=[],
                defaultValue=None
            ),
            SalesforceFormFieldSchema(
                label="Prime annuelle",
                apiName="prime_annuelle",
                type="number",
                required=True,
                possibleValues=[],
                defaultValue=None
            )
        ]
    ),
    "001XX000005": GetRecordDataResponse(
        record_id="001XX000005",
        record_type="Claim",
        documents=[
            DocumentSchema(
                document_id="doc_7",
                name="reclamation_005.pdf",
                url="https://example.com/documents/reclamation_005.pdf",
                type="application/pdf",
                indexed=True
            ),
            DocumentSchema(
                document_id="doc_8",
                name="justificatifs_005.pdf",
                url="https://example.com/documents/justificatifs_005.pdf",
                type="application/pdf",
                indexed=True
            )
        ],
        fields=[
            SalesforceFormFieldSchema(
                label="Montant réclamé",
                apiName="montant_reclame",
                type="number",
                required=True,
                possibleValues=[],
                defaultValue=None
            ),
            SalesforceFormFieldSchema(
                label="Date de réclamation",
                apiName="date_reclamation",
                type="text",
                required=True,
                possibleValues=[],
                defaultValue=None
            ),
            SalesforceFormFieldSchema(
                label="Motif de réclamation",
                apiName="motif_reclamation",
                type="textarea",
                required=True,
                possibleValues=[],
                defaultValue=None
            )
        ]
    ),
    # Example based on final_form_fields_page_infor_des_circons.json format
    "001XX000006": GetRecordDataResponse(
        record_id="001XX000006",
        record_type="Claim",
        documents=[
            DocumentSchema(
                document_id="doc_9",
                name="constat_amiable_006.pdf",
                url="https://example.com/documents/constat_amiable_006.pdf",
                type="application/pdf",
                indexed=True
            )
        ],
        fields=[
            SalesforceFormFieldSchema(
                label="Evènement déclencheur de sinistre",
                apiName=None,
                type="picklist",
                required=True,
                possibleValues=[
                    "Accident",
                    "Assistance",
                    "Bris de glace",
                    "Incendie",
                    "Évènement Catastrophe/ climatique & naturel"
                ],
                defaultValue="Accident"
            ),
            SalesforceFormFieldSchema(
                label="Est-ce qu'il y a un dommage ?",
                apiName=None,
                type="picklist",
                required=False,
                possibleValues=["Non", "Oui"],
                defaultValue="Oui"
            ),
            SalesforceFormFieldSchema(
                label="Type de dommage",
                apiName=None,
                type="picklist",
                required=False,
                possibleValues=[
                    "Dommages à l'adversaire",
                    "Dommages à l'adversaire et à l'assuré",
                    "Dommages à l'assuré"
                ],
                defaultValue="Dommages à l'adversaire et à l'assuré"
            ),
            SalesforceFormFieldSchema(
                label="Causes de sinistre",
                apiName=None,
                type="picklist",
                required=True,
                possibleValues=[
                    "Carambolage",
                    "Choc / Collision",
                    "Circonstance indéterminée",
                    "Renversement"
                ],
                defaultValue="Choc / Collision"
            ),
            SalesforceFormFieldSchema(
                label="Nombre de véhicules impliqués",
                apiName=None,
                type="number",
                required=False,
                possibleValues=[],
                defaultValue=None
            ),
            SalesforceFormFieldSchema(
                label="Nature de dommage",
                apiName=None,
                type="picklist",
                required=True,
                possibleValues=["Partiel", "Total"],
                defaultValue="Total"
            ),
            SalesforceFormFieldSchema(
                label="Sens de circulation",
                apiName=None,
                type="radio",
                required=True,
                possibleValues=[
                    "Cas Spéciaux",
                    "Exceptions",
                    "Véhicule Provenant de deux chaussée différentes. Leurs directions devant se couper ou se rejoindre",
                    "Véhicule en Circulation dans le même sens et sur la même chaussée",
                    "Véhicule en Circulation en Sens Inverse",
                    "Véhicules en Stationnement"
                ],
                defaultValue=None
            ),
            SalesforceFormFieldSchema(
                label="Taux de responsabilité applicable",
                apiName=None,
                type="number",
                required=False,
                possibleValues=[],
                defaultValue=None
            ),
            SalesforceFormFieldSchema(
                label="Commentaire",
                apiName=None,
                type="textarea",
                required=False,
                possibleValues=[],
                defaultValue=None
            )
        ]
    )
}


def get_mock_record(record_id: str) -> GetRecordDataResponse:
    """Get mock record data by record_id"""
    if not record_id:
        raise ValueError("record_id cannot be None or empty")
    
    record_id = record_id.strip()
    
    if record_id not in MOCK_RECORDS:
        raise KeyError(f"Record {record_id} not found in mock data")
    
    return MOCK_RECORDS[record_id]

