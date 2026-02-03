// Form grouping utility for pagination by form group (page)
import type { FormField } from '../types/form';

/** Default form group names in display order (five pages). */
export const DEFAULT_FORM_GROUP_ORDER = [
  'Véhicle et passagers adverses',
  'Passagers assurés',
  'Véhicles assurés',
  'Infos des circonstances',
  'Infos dommages autres parties',
] as const;

export type FormGroupName = (typeof DEFAULT_FORM_GROUP_ORDER)[number];

/**
 * Groups fields by formGroup. If formGroup is missing on fields, splits fields
 * into groupOrder.length chunks by index so the five blocks are always present and ordered.
 *
 * @param fields - All form fields (with optional formGroup)
 * @param groupOrder - Ordered list of group names (default: DEFAULT_FORM_GROUP_ORDER)
 * @returns Map from group name to fields for that group; groups appear in groupOrder order
 */
export function groupFieldsByFormGroup<T extends FormField>(
  fields: T[],
  groupOrder: string[] = [...DEFAULT_FORM_GROUP_ORDER]
): Map<string, T[]> {
  const hasFormGroup = fields.some((f) => f.formGroup != null && f.formGroup !== '');
  const result = new Map<string, T[]>();

  if (hasFormGroup) {
    for (const name of groupOrder) {
      result.set(name, []);
    }
    for (const field of fields) {
      const group = field.formGroup ?? groupOrder[0];
      if (!result.has(group)) {
        result.set(group, []);
      }
      result.get(group)!.push(field);
    }
    // Return map with groupOrder keys first (so order is stable), then any extra groups
    const ordered = new Map<string, T[]>();
    for (const name of groupOrder) {
      ordered.set(name, (result.get(name) ?? []) as T[]);
    }
    for (const [name, list] of result) {
      if (!ordered.has(name)) {
        ordered.set(name, list);
      }
    }
    return ordered;
  }

  // No formGroup: split into groupOrder.length chunks by index
  const n = groupOrder.length;
  const chunkSize = Math.ceil(fields.length / n);
  for (let i = 0; i < n; i++) {
    const start = i * chunkSize;
    const end = i === n - 1 ? fields.length : start + chunkSize;
    result.set(groupOrder[i], fields.slice(start, end));
  }
  return result;
}

/**
 * Returns the ordered list of group names (five blocks). Uses groupOrder.
 */
export function getOrderedGroupNames(
  groupOrder: string[] = [...DEFAULT_FORM_GROUP_ORDER]
): string[] {
  return [...groupOrder];
}
