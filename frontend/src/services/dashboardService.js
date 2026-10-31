import api from "./api";

export const dashboardService = {
  async getSummary() {
    return api.get("/dashboard/summary");
  },

  async getAnalytics() {
    return api.get("/reports/analytics");
  },

  async getHealth() {
    return api.get("/health");
  },
};

export default dashboardService;
