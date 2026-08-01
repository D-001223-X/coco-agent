/** Clipboard helpers with legacy fallback. */

export async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (err) {
    // fall through to legacy path
  }
  try {
    // Legacy fallback (non-HTTPS contexts, older browsers)
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(textarea);
    return ok;
  } catch (err) {
    return false;
  }
}

export function jsonStringifyPretty(data: unknown): string {
  return JSON.stringify(data, null, 2);
}
