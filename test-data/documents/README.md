# Documents de test

Placez vos fichiers PDF de test dans ce dossier.

## Formats supportés

- PDF (`.pdf`)
- Images JPEG/PNG (`.jpg`, `.jpeg`, `.png`) - pourront être ajoutés plus tard

## Instructions

1. Copiez vos fichiers PDF dans ce dossier
2. Les fichiers seront servis par un serveur HTTP local sur le port 8003
3. Les URLs seront automatiquement générées : `http://localhost:8003/documents/{filename}`

## Exemple

Si vous placez `facture_001.pdf` dans ce dossier, il sera accessible via :
`http://localhost:8003/documents/facture_001.pdf`

## Note

Les documents sont téléchargés et convertis en base64 automatiquement par le pipeline backend. Vous n'avez pas besoin de les convertir manuellement.

