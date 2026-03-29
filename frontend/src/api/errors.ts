import axios from "axios";

/** Вытаскивает текст ошибки из ответа FastAPI: `detail` строка или список. */
export function getApiErrorMessage(err: unknown, fallback: string): string {
  if (!axios.isAxiosError(err)) {
    return fallback;
  }
  const data = err.response?.data as { detail?: unknown } | undefined;
  const detail = data?.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (typeof item === "string") return item;
      if (item && typeof item === "object" && "msg" in item) {
        return String((item as { msg: string }).msg);
      }
      return JSON.stringify(item);
    });
    return parts.join("; ") || fallback;
  }
  return fallback;
}
