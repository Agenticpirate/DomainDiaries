const KEY = "krypto.theme";

export type Theme = "dark" | "light";

export function readTheme(): Theme {
  if (typeof localStorage === "undefined") return "dark";
  return localStorage.getItem(KEY) === "light" ? "light" : "dark";
}

export function writeTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
  if (typeof localStorage !== "undefined") localStorage.setItem(KEY, theme);
}

export function initTheme(): Theme {
  const theme = readTheme();
  writeTheme(theme);
  return theme;
}
