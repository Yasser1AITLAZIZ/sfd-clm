#!/usr/bin/env node
/**
 * Restructure steps JSON to record_id_fields.json format.
 * Reads steps_source.json (root: { steps: [ { stepLabel, stepKey, fields: [...] } ] })
 * Outputs { fields: [ ... ] } with formGroup, canonical types, no ui.
 *
 * Form group order (frontend DEFAULT_FORM_GROUP_ORDER):
 * 1. Véhicle et passagers adverses
 * 2. Passagers assurés
 * 3. Véhicles assurés
 * 4. Infos des circonstances
 * 5. Infos dommages autres parties
 */

const fs = require('fs');
const path = require('path');

const FORM_GROUP_ORDER = [
  'Véhicle et passagers adverses',
  'Passagers assurés',
  'Véhicles assurés',
  'Infos des circonstances',
  'Infos dommages autres parties',
];

const STEP_LABEL_TO_FORM_GROUP = {
  'Véhicule(s) et passager(s) adverse(s)': 'Véhicle et passagers adverses',
  'Passager(s) assuré(s)': 'Passagers assurés',
  'Véhicule assuré': 'Véhicles assurés',
  'Informations des Circonstances': 'Infos des circonstances',
  'Info dommages autres parties': 'Infos dommages autres parties',
  'Récapitulatif': null, // skip or put in last group
};

const VALID_TYPES = ['text', 'picklist', 'radio', 'number', 'textarea'];
function normalizeType(t) {
  if (!t || typeof t !== 'string') return 'text';
  const lower = t.toLowerCase();
  if (VALID_TYPES.includes(lower)) return lower;
  if (['date', 'search', 'lookup'].includes(lower)) return 'text';
  return 'text';
}

function normalizeField(raw, formGroup) {
  return {
    label: raw.label != null ? String(raw.label).trim() : '',
    apiName: raw.apiName != null ? raw.apiName : null,
    type: normalizeType(raw.type),
    required: Boolean(raw.required),
    possibleValues: Array.isArray(raw.possibleValues) ? raw.possibleValues : [],
    defaultValue: raw.defaultValue != null ? raw.defaultValue : null,
    formGroup,
  };
}

function main() {
  const base = path.join(__dirname, '..', 'test-data', 'fields');
  const defaultSource = path.join(base, '001XX000001_fields.json');
  const sourcePath = process.argv[2] ? path.resolve(process.argv[2]) : defaultSource;
  const outPath = path.join(base, '001XX000001_fields.json');

  if (!fs.existsSync(sourcePath)) {
    console.error('Missing source file:', sourcePath);
    process.exit(1);
  }

  const data = JSON.parse(fs.readFileSync(sourcePath, 'utf8'));
  const steps = data.steps;
  if (!Array.isArray(steps)) {
    console.error('Expected data.steps to be an array in', sourcePath);
    process.exit(1);
  }

  const formGroupToStepLabels = {};
  for (const [label, group] of Object.entries(STEP_LABEL_TO_FORM_GROUP)) {
    if (group) {
      formGroupToStepLabels[group] = formGroupToStepLabels[group] || [];
      formGroupToStepLabels[group].push(label);
    }
  }

  const outputFields = [];
  for (const formGroup of FORM_GROUP_ORDER) {
    const stepLabels = formGroupToStepLabels[formGroup];
    if (!stepLabels) continue;
    for (const step of steps) {
      if (!stepLabels.includes(step.stepLabel)) continue;
      const fields = Array.isArray(step.fields) ? step.fields : [];
      for (const f of fields) {
        outputFields.push(normalizeField(f, formGroup));
      }
      break;
    }
  }

  fs.writeFileSync(outPath, JSON.stringify({ fields: outputFields }, null, 2), 'utf8');
  console.log('Wrote', outputFields.length, 'fields to', outPath);
}

main();
