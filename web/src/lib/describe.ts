import type { Claims, EvidenceReport, PackClaims, Quantity } from "./types";

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

// ---- check packs: projector, magnifying glass, monocular

const RESOLUTION: Record<string, string> = { "720p": "720p", "1080p": "1080p", "4k": "4K", "8k": "8K" };

function field(claims: PackClaims, name: string): Record<string, unknown> | null {
  const value = claims[name];
  return value && typeof value === "object" ? (value as Record<string, unknown>) : null;
}

function num(claims: PackClaims, name: string, key = "value"): number | null {
  const value = field(claims, name)?.[key];
  return typeof value === "number" ? value : null;
}

function text(claims: PackClaims, name: string): string | null {
  const value = field(claims, name)?.value;
  return typeof value === "string" ? value : null;
}

const PACK_DESCRIBERS: Record<string, (claims: PackClaims) => string> = {
  projector_resolution: (claims) => {
    const facts: string[] = [];
    const headline = text(claims, "claimed_resolution");
    if (headline) facts.push(`${RESOLUTION[headline] ?? headline} headline`);
    const width = num(claims, "native_pixels", "width_px");
    const height = num(claims, "native_pixels", "height_px");
    const nativeName = text(claims, "native_name");
    if (width !== null && height !== null) facts.push(`native ${formatNumber(width)} × ${formatNumber(height)}`);
    else if (nativeName) facts.push(`native ${RESOLUTION[nativeName] ?? nativeName}`);
    return ["Projector", ...facts].join(", ");
  },
  magnifier_lens: (claims) => {
    const facts: string[] = [];
    const power = num(claims, "magnification");
    const diameter = num(claims, "lens_diameter_mm");
    if (power !== null) facts.push(`${formatNumber(power)}×`);
    if (diameter !== null) facts.push(`${formatNumber(diameter)} mm lens`);
    return ["Magnifying glass", ...facts].join(", ");
  },
  monocular_optics: (claims) => {
    const power = num(claims, "magnification");
    const objective = num(claims, "objective_mm");
    const facts: string[] = [];
    if (power !== null && objective !== null) facts.push(`${formatNumber(power)}×${formatNumber(objective)}`);
    else if (power !== null) facts.push(`${formatNumber(power)}×`);
    else if (objective !== null) facts.push(`${formatNumber(objective)} mm objective`);
    return ["Monocular", ...facts].join(", ");
  },
};

/**
 * A description of the product a report is about, built only from its extracted
 * claims: the battery description, or the pack's own for a projector, magnifying
 * glass or monocular.
 */
export function describeReport(report: EvidenceReport | null | undefined): string {
  if (!report) return "Listing";
  if (report.pack) return PACK_DESCRIBERS[report.pack]?.(report.claims as PackClaims) ?? "Listing";
  return describeProduct(report.claims as Claims);
}
