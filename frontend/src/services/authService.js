import api from "./api";

export const authService = {
  async register(data) {
    return api.post("/auth/register", data);
  },

  async login(email, password) {
    return api.post("/auth/login", { email, password });
  },

  async getMe() {
    return api.get("/auth/me");
  },

  async createStaff(data) {
    return api.post("/auth/create-staff", data);
  },

  async refreshToken() {
    return api.post("/auth/refresh");
  },
};

export default authService;
