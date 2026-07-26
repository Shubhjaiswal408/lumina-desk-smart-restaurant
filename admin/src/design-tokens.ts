/**
 * Lumina Console — design tokens (single source of truth).
 *
 * AESTHETIC: editorial fine-dining. NOT "modern dashboard".
 * RULES (prescriptive — follow exactly):
 *  - ONE dominant colour: charcoal/ink surfaces. ONE sharp accent: Lumina red.
 *  - Red is earned, never decorative — brand mark, active nav, key totals,
 *    the tallest chart bars, allergen warnings. Everything else is ink/muted.
 *  - Display type is the Fraunces serif (matches the ePaper wordmark). Body/data
 *    is Geist. Never Inter/Roboto/Open Sans. No gradients.
 *  - Generous whitespace, thin hairline rules, tabular numerals for figures.
 */
export const brand = {
  red: "#e11d2a",
  redSoft: "rgba(225, 29, 42, 0.14)",
}

export const fonts = {
  display: "'Fraunces Variable', Georgia, serif",
  body: "'Geist Variable', system-ui, sans-serif",
}

export const diet = { veg: "#35d07f", nonVeg: "#e0684a" }

export const status = {
  new: "#8b98a8",
  preparing: "#ffb020",
  ready: "#35d07f",
  served: "#6b7688",
}
