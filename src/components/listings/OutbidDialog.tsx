import { useEffect, useId, useRef, useState } from "react";
import type { CategoryId } from "../../types";
import { CATEGORIES } from "../../data/directory";
import { formatUsd } from "../../lib/format";

type Props = {
  open: boolean;
  defaultAmount: number;
  onClose: () => void;
  onSubmit: (input: { url: string; category: CategoryId; amount: number }) => void;
};

export function OutbidDialog({ open, defaultAmount, onClose, onSubmit }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const [url, setUrl] = useState("");
  const [category, setCategory] = useState<CategoryId>("defi");
  const [amount, setAmount] = useState(String(defaultAmount));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      setUrl("");
      setCategory("defi");
      setAmount(String(defaultAmount));
      setError(null);
      dialog.showModal();
    }
    if (!open && dialog.open) dialog.close();
  }, [open, defaultAmount]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (!("closedBy" in HTMLDialogElement.prototype)) {
      const onClick = (event: MouseEvent) => {
        if (event.target !== dialog) return;
        const rect = dialog.getBoundingClientRect();
        const inside =
          rect.top <= event.clientY &&
          event.clientY <= rect.bottom &&
          rect.left <= event.clientX &&
          event.clientX <= rect.right;
        if (!inside) dialog.close();
      };
      dialog.addEventListener("click", onClick);
      return () => dialog.removeEventListener("click", onClick);
    }
  }, []);

  return (
    <dialog
      ref={dialogRef}
      closedby="any"
      aria-labelledby={titleId}
      onClose={onClose}
      className="w-[min(520px,100%)]"
    >
      <form
        className="glass rounded-3xl p-6 sm:p-8"
        onSubmit={(event) => {
          event.preventDefault();
          const bid = Number(amount);
          if (!url.trim()) {
            setError("Enter a project URL.");
            return;
          }
          if (!Number.isFinite(bid) || bid < defaultAmount) {
            setError(`Bid at least ${formatUsd(defaultAmount)} to take the top spot.`);
            return;
          }
          onSubmit({ url: url.trim(), category, amount: bid });
        }}
      >
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--pink)]">Outbid desk</p>
        <h2 id={titleId} className="font-display mt-2 text-2xl font-bold">
          Claim visibility
        </h2>
        <p className="mt-2 text-sm text-[var(--mute)]">
          Rank is paid. The current #1 bid is {formatUsd(defaultAmount - 1)}. This sample stores the bid on this
          device only.
        </p>
        <div className="mt-6 flex flex-col gap-4">
          <label className="flex flex-col gap-2 text-sm">
            Project URL
            <input
              required
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://yourproject.xyz"
              autoComplete="url"
              className="rounded-2xl border border-[var(--line)] bg-black/20 px-4 py-3 outline-none focus:border-[var(--violet)]"
            />
          </label>
          <label className="flex flex-col gap-2 text-sm">
            Category
            <select
              value={category}
              onChange={(event) => setCategory(event.target.value as CategoryId)}
              className="rounded-2xl border border-[var(--line)] bg-black/20 px-4 py-3 outline-none"
            >
              {CATEGORIES.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-2 text-sm">
            Bid (USD)
            <input
              required
              inputMode="decimal"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              className="rounded-2xl border border-[var(--line)] bg-black/20 px-4 py-3 font-mono outline-none focus:border-[var(--pink)]"
            />
          </label>
        </div>
        {error && <p className="mt-3 text-sm text-[var(--pink)]">{error}</p>}
        <div className="mt-6 flex justify-end gap-3">
          <button type="button" onClick={onClose} className="rounded-full px-4 py-2 text-sm text-[var(--mute)]">
            Cancel
          </button>
          <button
            type="submit"
            className="rounded-full bg-gradient-to-r from-[#ff4d9d] to-[#ff8a4c] px-5 py-2 text-sm font-bold text-white"
          >
            Place bid
          </button>
        </div>
      </form>
    </dialog>
  );
}
