const ONBOARDING_COMPLETE_KEY = "onboarding_complete";

export function isOnboardingComplete(): boolean {
  return sessionStorage.getItem(ONBOARDING_COMPLETE_KEY) === "true";
}

export function setOnboardingComplete(): void {
  sessionStorage.setItem(ONBOARDING_COMPLETE_KEY, "true");
}

export function clearOnboardingComplete(): void {
  sessionStorage.removeItem(ONBOARDING_COMPLETE_KEY);
  localStorage.removeItem(ONBOARDING_COMPLETE_KEY);
}
