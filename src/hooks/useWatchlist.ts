import { useCallback, useState } from "react";
import { loadWatchlist, saveWatchlist } from "../lib/storage";

export function useWatchlist() {
  const [ids, setIds] = useState<string[]>(() => loadWatchlist());

  const toggle = useCallback((id: string) => {
    setIds((prev) => {
      const next = prev.includes(id) ? prev.filter((item) => item !== id) : [id, ...prev];
      saveWatchlist(next);
      return next;
    });
  }, []);

  const has = useCallback((id: string) => ids.includes(id), [ids]);

  return { ids, toggle, has };
}
