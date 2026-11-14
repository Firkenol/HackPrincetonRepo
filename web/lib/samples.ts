// Text versions of the nine SPEC fixtures. No seller, store or brand names.
// In mock mode the server matches these texts (or a file named fixture_NN.*) to
// fixtures/expected/fixture_NN.json. With the real API they are ordinary pasted listings.

export interface Sample {
  id: number;
  label: string;
  text: string;
}

export const SAMPLES: Sample[] = [
  {
    id: 1,
    label: "18650, 12,000 mAh",
    text: "18650 Li-ion rechargeable battery, 12000mAh 3.7V.\nSpec table: Package weight 0.600 kg. Package dimensions 15 x 15 x 15 cm.",
  },
  { id: 2, label: "AA Ni-MH, 700 mAh", text: "AA Ni-MH rechargeable battery, 700mAh 1.2V." },
  {
    id: 3,
    label: "“Alkaline” pack, R6/R03 cells",
    text: "Title: Alkaline AA and AAA battery pack.\nProduct photo: cells are printed R6 and R03 and \"Heavy Duty\".",
  },
  {
    id: 4,
    label: "Carbon zinc, 10-year shelf life",
    text: "Carbon zinc AA and AAA battery pack. 10-year shelf life.",
  },
  { id: 5, label: "Heavy duty multipack", text: "Carbon zinc AA and AAA heavy duty battery multipack." },
  {
    id: 6,
    label: "2S LiPo, 6200 mAh",
    text: "2S LiPo battery pack. Label: 7.4V 6200mAh 45.88Wh.\nSpec table: 139.5 x 47.5 x 26 mm, 315 g.",
  },
  {
    id: 7,
    label: "3S LiPo, 2200 mAh",
    text: "3S LiPo battery pack. Label: 11.1V 2200mAh 24.42Wh.\nSpec table: 106 x 33 x 23 mm, 179 g.",
  },
  {
    id: 8,
    label: "2S LiPo, 5200 mAh",
    text: "2S LiPo battery pack. Label: 7.4V 5200mAh 38.48Wh.\nSpec table: 25 x 47 x 139 mm, 307 g.",
  },
  {
    id: 9,
    label: "2S LiPo, no size or weight",
    text: "2S LiPo battery pack. Label: 7.4V 5200mAh 38.48Wh.",
  },
];

export const normalise = (text: string) => text.toLowerCase().replace(/\s+/g, " ").trim();
