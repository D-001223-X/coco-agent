import { useEffect } from "react";

interface ToastProps {
  message: string | null;
  onDismiss: () => void;
  duration?: number;
}

/** Minimal top-center toast used for copy feedback (no external deps). */
export function Toast({ message, onDismiss, duration = 2000 }: ToastProps) {
  useEffect(() => {
    if (!message) return;
    const timer = window.setTimeout(onDismiss, duration);
    return () => window.clearTimeout(timer);
  }, [message, duration, onDismiss]);

  if (!message) return null;

  return (
    <div className="fixed top-5 left-1/2 -translate-x-1/2 z-[100] animate-message-in">
      <div className="px-4 py-2 rounded-button bg-gray-800 text-white text-sm shadow-lg">
        {message}
      </div>
    </div>
  );
}
