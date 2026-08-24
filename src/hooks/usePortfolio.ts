import { useCallback, useState } from "react";
import { loadHoldings, saveHoldings } from "../lib/storage";
import type { Holding } from "../types";

export function usePortfolio() {
  const [holdings, setHoldings] = useState<Holding[]>(() => loadHoldings());

  const add = useCallback((holding: Holding) => {
    setHoldings((prev) => {
      const existing = prev.find((row) => row.id === holding.id);
      const next = existing
        ? prev.map((row) =>
            row.id === holding.id
              ? {
                  ...row,
                  amount: row.amount + holding.amount,
                  costUsd: row.costUsd + holding.costUsd,
                }
              : row,
          )
        : [...prev, holding];
      saveHoldings(next);
      return next;
    });
  }, []);

  const remove = useCallback((id: string) => {
    setHoldings((prev) => {
      const next = prev.filter((row) => row.id !== id);
      saveHoldings(next);
      return next;
    });
  }, []);

  return { holdings, add, remove };
}
