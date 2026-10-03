"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";

const TOAST_MS = 6000;

interface Toast {
  id: number;
  message: string;
  tone: "info" | "error";
  undo?: () => Promise<void>;
}

type ShowToast = (
  toast: Omit<Toast, "id" | "tone"> & { tone?: Toast["tone"] },
) => void;

const ToastContext = createContext<ShowToast>(() => {});

export function useToast(): ShowToast {
  return useContext(ToastContext);
}

// Lives in the app layout so a toast outlives the card that raised it
// (a skipped card leaves the list but its Undo must stay).
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<Toast | null>(null);
  const [undoing, setUndoing] = useState(false);
  const nextId = useRef(0);

  const show = useCallback<ShowToast>(({ tone = "info", ...rest }) => {
    nextId.current += 1;
    setToast({ id: nextId.current, tone, ...rest });
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), TOAST_MS);
    return () => clearTimeout(timer);
  }, [toast]);

  async function undo() {
    if (!toast?.undo) return;
    setUndoing(true);
    try {
      await toast.undo();
    } finally {
      setUndoing(false);
      setToast(null);
    }
  }

  return (
    <ToastContext.Provider value={show}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex justify-center p-4"
      >
        {toast && (
          <div
            key={toast.id}
            role={toast.tone === "error" ? "alert" : "status"}
            className={`pointer-events-auto flex w-full max-w-md items-center gap-3 rounded-xl px-4 py-2 text-sm shadow-lg ${
              toast.tone === "error"
                ? "bg-danger text-on-accent"
                : "bg-inverse text-on-inverse"
            }`}
          >
            <span className="min-w-0 flex-1 truncate">{toast.message}</span>
            {toast.undo && (
              <button
                type="button"
                onClick={undo}
                disabled={undoing}
                className="tap rounded-lg px-3 font-semibold underline underline-offset-2"
              >
                {undoing ? "Undoing…" : "Undo"}
              </button>
            )}
          </div>
        )}
      </div>
    </ToastContext.Provider>
  );
}
