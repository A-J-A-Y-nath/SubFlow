import api from "./api";

export const subflowService = {
  // Products
  async getProducts(params = {}) {
    return api.get("/products", { params });
  },

  // Plans
  async getPlans(params = {}) {
    return api.get("/plans", { params });
  },

  // Subscriptions
  async getSubscriptions(params = {}) {
    return api.get("/subscriptions", { params });
  },

  // Quotations
  async getQuotations(params = {}) {
    return api.get("/quotations", { params });
  },

  // Invoices
  async getInvoices(params = {}) {
    return api.get("/invoices", { params });
  },

  // Payments
  async getPayments(params = {}) {
    return api.get("/payments", { params });
  },

  // Discounts
  async getDiscounts(params = {}) {
    return api.get("/discounts", { params });
  },

  async validateCoupon(code) {
    return api.get(`/discounts/validate/${code}`);
  },
};

export default subflowService;
