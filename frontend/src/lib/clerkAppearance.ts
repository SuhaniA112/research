import type { SignIn } from "@clerk/clerk-react";
import type { ComponentProps } from "react";

/** Roughly matches the app's slate/white palette (see LoginPage's prior placeholder card). */
export const CLERK_APPEARANCE: ComponentProps<typeof SignIn>["appearance"] = {
  variables: {
    colorPrimary: "#0f172a", // slate-900
    colorText: "#0f172a",
    colorTextSecondary: "#475569", // slate-600
    colorBackground: "#ffffff",
    colorInputBackground: "#ffffff",
    colorInputText: "#0f172a",
    borderRadius: "0.75rem",
  },
  elements: {
    card: "shadow-sm border border-slate-200",
    headerTitle: "text-slate-900",
    headerSubtitle: "text-slate-600",
    formButtonPrimary: "bg-slate-900 hover:bg-slate-800 text-sm normal-case",
    footerActionLink: "text-slate-900 hover:text-slate-700",
  },
};
