import type { Claims, Quantity } from "./types";

// A product description built only from the extracted claims. The claims have no
// field for a seller, store or brand, so a description made this way cannot carry one.
// The listing's own title is never used.

const CHEMISTRY: Record<string, string> = {
  "li-ion": "lithium-ion",
  nimh: "Ni-MH",
  alkaline: "alkaline",
  "zinc-carbon": "zinc-carbon",
  nicd: "Ni-Cd",
  "lithium-primary": "lithium primary",
};

const PRODUCT: Record<Claims["product_type"], string> = {
  loose_cell: "cell",
  battery_pack: "pack",
  power_bank: "power bank",
  unknown: "battery",
};

/** A number as a person would write it. Formatting only: nothing is calculated. */
export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US", { maximumSignificantDigits: 6 }).format(value);
}

export function formatQuantity(q: Pick<Quantity, "value" | "unit">): string {
  const value = typeof q.value === "number" ? formatNumber(q.value) : q.value;
  return q.unit ? `${value} ${q.unit}` : value;
}

export function describeProduct(claims: Claims | null | undefined): string {
  if (!claims) return "Battery listing";

  const head: string[] = [];
  if (claims.form_factors.length) head.push(claims.form_factors.map((f) => f.value).join("/"));
  if (claims.chemistry && CHEMISTRY[claims.chemistry.value]) head.push(CHEMISTRY[claims.chemistry.value]);
  head.push(PRODUCT[claims.product_type] ?? "battery");

  const facts: string[] = [];
  if (claims.capacity_mah) facts.push(`${formatNumber(claims.capacity_mah.value)} mAh`);
  if (claims.nominal_voltage_v) facts.push(`${formatNumber(claims.nominal_voltage_v.value)} V`);
  if (claims.energy_wh) facts.push(`${formatNumber(claims.energy_wh.value)} Wh`);
  if (claims.shelf_life_years) facts.push(`${formatNumber(claims.shelf_life_years.value)}-year shelf life`);
  if (!facts.length && claims.printed_terms.length) facts.push(claims.printed_terms[0].value.toLowerCase());

  const name = head.join(" ");
  const text = facts.length ? `${name}, ${facts.join(", ")}` : name;
  return text.charAt(0).toUpperCase() + text.slice(1);
}
