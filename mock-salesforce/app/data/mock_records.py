"""Mock datasets for different record IDs"""
from typing import Dict, Any
from app.models.schemas import GetRecordDataResponse, DocumentSchema, FieldToFillSchema


# Mock datasets mapping record_id to data
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
        fields_to_fill=[
            FieldToFillSchema(
                field_name="montant_total",
                field_type="currency",
                value=None,
                required=True,
                label="Montant total"
            ),
            FieldToFillSchema(
                field_name="date_facture",
                field_type="date",
                value=None,
                required=True,
                label="Date de facture"
            ),
            FieldToFillSchema(
                field_name="numero_facture",
                field_type="text",
                value=None,
                required=True,
                label="Numéro de facture"
            ),
            FieldToFillSchema(
                field_name="beneficiaire_nom",
                field_type="text",
                value=None,
                required=True,
                label="Nom du bénéficiaire"
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
        fields_to_fill=[
            FieldToFillSchema(
                field_name="montant_total",
                field_type="currency",
                value=None,
                required=True,
                label="Montant total"
            ),
            FieldToFillSchema(
                field_name="date_devis",
                field_type="date",
                value=None,
                required=True,
                label="Date du devis"
            ),
            FieldToFillSchema(
                field_name="description_sinistre",
                field_type="text",
                value=None,
                required=False,
                label="Description du sinistre"
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
        fields_to_fill=[
            FieldToFillSchema(
                field_name="montant_indemnisation",
                field_type="currency",
                value=None,
                required=True,
                label="Montant d'indemnisation"
            ),
            FieldToFillSchema(
                field_name="date_sinistre",
                field_type="date",
                value=None,
                required=True,
                label="Date du sinistre"
            ),
            FieldToFillSchema(
                field_name="lieu_sinistre",
                field_type="text",
                value=None,
                required=True,
                label="Lieu du sinistre"
            ),
            FieldToFillSchema(
                field_name="expert_nom",
                field_type="text",
                value=None,
                required=False,
                label="Nom de l'expert"
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
        fields_to_fill=[
            FieldToFillSchema(
                field_name="numero_contrat",
                field_type="text",
                value=None,
                required=True,
                label="Numéro de contrat"
            ),
            FieldToFillSchema(
                field_name="date_effet",
                field_type="date",
                value=None,
                required=True,
                label="Date d'effet"
            ),
            FieldToFillSchema(
                field_name="prime_annuelle",
                field_type="currency",
                value=None,
                required=True,
                label="Prime annuelle"
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
        fields_to_fill=[
            FieldToFillSchema(
                field_name="montant_reclame",
                field_type="currency",
                value=None,
                required=True,
                label="Montant réclamé"
            ),
            FieldToFillSchema(
                field_name="date_reclamation",
                field_type="date",
                value=None,
                required=True,
                label="Date de réclamation"
            ),
            FieldToFillSchema(
                field_name="motif_reclamation",
                field_type="text",
                value=None,
                required=True,
                label="Motif de réclamation"
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

