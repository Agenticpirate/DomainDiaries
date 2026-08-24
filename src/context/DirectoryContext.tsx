import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import type { CategoryId, OutbidEvent, Project } from "../types";
import { applyOutbid, loadDirectory } from "../lib/directory";

type DirectoryContextValue = {
  projects: Project[];
  events: OutbidEvent[];
  outbid: (input: { url: string; category: CategoryId; amount: number; name?: string }) => Project;
};

const DirectoryContext = createContext<DirectoryContextValue | null>(null);

export function DirectoryProvider({ children }: { children: ReactNode }) {
  const [{ projects, events }, setState] = useState(loadDirectory);
  const value = useMemo<DirectoryContextValue>(
    () => ({
      projects,
      events,
      outbid: (input) => {
        const next = applyOutbid(input);
        setState(next);
        return next.projects[0];
      },
    }),
    [projects, events],
  );
  return <DirectoryContext.Provider value={value}>{children}</DirectoryContext.Provider>;
}

export function useDirectory() {
  const ctx = useContext(DirectoryContext);
  if (!ctx) throw new Error("useDirectory must be used inside DirectoryProvider");
  return ctx;
}
