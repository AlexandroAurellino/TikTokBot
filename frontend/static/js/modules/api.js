// Centralized API handling
export const API = {
  async get(endpoint) {
    try {
      const res = await fetch(endpoint);
      return await res.json();
    } catch (e) {
      console.error(`GET ${endpoint} failed`, e);
      throw e;
    }
  },

  async post(endpoint, body) {
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      return await res.json();
    } catch (e) {
      console.error(`POST ${endpoint} failed`, e);
      throw e;
    }
  },

  async upload(endpoint, formData) {
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        body: formData, // No Content-Type header for FormData!
      });
      return await res.json();
    } catch (e) {
      console.error(`UPLOAD ${endpoint} failed`, e);
      throw e;
    }
  },
};
