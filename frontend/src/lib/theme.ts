/** CSS variable references for SVG, charts, and inline styles. */
const v = (token: string) => `var(--${token})`;

export const colors = {
  brand: {
    subtle: v("brand-subtle"),
    light: v("brand-light"),
    accent: v("brand-accent"),
    DEFAULT: v("brand"),
  },
  fg: {
    secondary: v("fg-secondary"),
    muted: v("fg-muted"),
  },
  bg: {
    DEFAULT: v("bg"),
  },
  border: v("border"),
} as const;
