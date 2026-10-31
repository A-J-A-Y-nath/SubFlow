import api from "./api";

export const subflowService = {
  // Products
  async getProducts(params = {}) {
    return api.get("/products", { params });
  },

  async getProduct(productId) {
    return api.get(`/products/${productId}`);
  },

  async createProduct(data) {
    return api.post("/products", data);
  },

  async updateProduct(productId, data) {
    return api.put(`/products/${productId}`, data);
  },

  async toggleProductStatus(productId, isActive) {
    return api.patch(`/products/${productId}/status`, { is_active: isActive });
  },

  async deleteProduct(productId) {
    return api.delete(`/products/${productId}`);
  },

  // Product Variants
  async getProductVariants(productId, params = {}) {
    return api.get(`/products/${productId}/variants`, { params });
  },

  async getVariant(productId, variantId) {
    return api.get(`/products/${productId}/variants/${variantId}`);
  },

  async createVariant(productId, data) {
    return api.post(`/products/${productId}/variants`, data);
  },

  async updateVariant(productId, variantId, data) {
    return api.put(`/products/${productId}/variants/${variantId}`, data);
  },

  async toggleVariantStatus(productId, variantId, isActive) {
    return api.patch(`/products/${productId}/variants/${variantId}/status`, { is_active: isActive });
  },

  async deleteVariant(productId, variantId) {
    return api.delete(`/products/${productId}/variants/${variantId}`);
  },

  // Plans
  async getPlans(params = {}) {
    return api.get("/plans", { params });
  },

  async getPlan(planId) {
    return api.get(`/plans/${planId}`);
  },

  async createPlan(data) {
    return api.post("/plans", data);
  },

  async updatePlan(planId, data) {
    return api.put(`/plans/${planId}`, data);
  },

  async togglePlanStatus(planId, isActive) {
    return api.patch(`/plans/${planId}/status`, { is_active: isActive });
  },

  async deletePlan(planId) {
    return api.delete(`/plans/${planId}`);
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
