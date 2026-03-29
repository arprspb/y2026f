import axios from "axios";

/** Без глобального Content-Type: для JSON axios выставит сам, для FormData — браузер (boundary). */
const api = axios.create({
  baseURL: "",
});

export function setAuthToken(token: string | null) {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common.Authorization;
  }
}

export default api;
