# Champs Salesforce

Placez le fichier JSON contenant les champs du formulaire Salesforce dans ce dossier.

## Format requis

Le fichier doit s'appeler `fields.json` et suivre exactement le format de `final_form_fields_page_infor_des_circons.json` :

```json
{
  "fields": [
    {
      "label": "Evènement déclencheur de sinistre",
      "apiName": null,
      "type": "picklist",
      "required": true,
      "possibleValues": [
        "Accident",
        "Assistance",
        "Bris de glace",
        "Incendie",
        "Évènement Catastrophe/ climatique & naturel"
      ],
      "defaultValue": "Accident"
    },
    {
      "label": "Nombre de véhicules impliqués",
      "apiName": null,
      "type": "number",
      "required": false,
      "possibleValues": [],
      "defaultValue": null
    }
  ]
}
```

## Types de champs supportés

- `text` - Texte libre
- `picklist` - Liste déroulante avec `possibleValues`
- `radio` - Boutons radio avec `possibleValues`
- `number` - Nombre
- `textarea` - Zone de texte multiligne

## Instructions

1. Créez ou copiez votre fichier `fields.json` dans ce dossier
2. Assurez-vous que le format est correct (valide JSON)
3. Le script de test lira automatiquement ce fichier

