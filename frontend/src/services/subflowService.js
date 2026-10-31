import api from "./api";

export const subflowService = {
  // ── Products ──────────────────────────────────────────────────────────────
  async getProducts(params = {}) {
    return api.get("/products", { params });
  },
  async getProductById(id) {
    return api.get(`/products/${id}`);
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

  // ── Plans ─────────────────────────────────────────────────────────────────
  async getPlans(params = {}) {
    return api.get("/plans", { params });
  },
  async getPlanById(id) {
    return api.get(`/plans/${id}`);
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

  // ── Subscriptions ─────────────────────────────────────────────────────────
  async getSubscriptions(params = {}) {
    return api.get("/subscriptions", { params });
  },
  async getSubscriptionById(id) {
    return api.get(`/subscriptions/${id}`);
  },
  async createSubscription(data) {
    return api.post("/subscriptions", data);
  },
  async updateSubscriptionStatus(id, status, reason = null) {
    return api.patch(`/subscriptions/${id}/status`, { status, reason });
  },
  async renewSubscription(id) {
    return api.post(`/subscriptions/${id}/renew`);
  },

  // ── Quotations ────────────────────────────────────────────────────────────
  async getQuotations(params = {}) {
    return api.get("/quotations", { params });
  },
  async getQuotationById(id) {
    return api.get(`/quotations/${id}`);
  },
  async createQuotation(data) {
    return api.post("/quotations", data);
  },
  async updateQuotation(id, data) {
    return api.patch(`/quotations/${id}`, data);
  },
  async sendQuotation(id) {
    return api.post(`/quotations/${id}/send`);
  },
  async confirmQuotation(id, data = {}) {
    return api.post(`/quotations/${id}/confirm`, data);
  },

  // ── Invoices ──────────────────────────────────────────────────────────────
  async getInvoices(params = {}) {
    return api.get("/invoices", { params });
  },
  async getInvoice(id) {
    return api.get(`/invoices/${id}`);
  },
  async getInvoiceById(id) {
    return api.get(`/invoices/${id}`);
  },
  async createInvoice(data) {
    return api.post("/invoices", data);
  },
  async confirmInvoice(id) {
    return api.post(`/invoices/${id}/confirm`);
  },
  async issueInvoice(id) {
    return api.post(`/invoices/${id}/issue`);
  },
  async cancelInvoice(id) {
    return api.post(`/invoices/${id}/cancel`);
  },
  async generateInvoiceFromSubscription(subscriptionId) {
    return api.post(`/invoices/from-subscription/${subscriptionId}`);
  },
  async runRecurringBilling(data = {}) {
    return api.post("/invoices/recurring-billing/run", data);
  },
  async previewRecurringBilling(params = {}) {
    return api.get("/invoices/recurring-billing/preview", { params });
  },
  async getReceivablesSummary() {
    return api.get("/invoices/receivables/summary");
  },
  async getInvoicingCustomers() {
    return api.get("/invoices/customers");
  },
  async getInvoicingSubscriptions(customerId = null) {
    const params = customerId ? { customer_id: customerId } : {};
    return api.get("/invoices/active-subscriptions", { params });
  },

  // ── Billing ───────────────────────────────────────────────────────────────
  async runBillingCycle(asOfDate = null) {
    return api.post("/billing/run", asOfDate ? { as_of_date: asOfDate } : {});
  },
  async getBillingDue(asOfDate = null) {
    const params = asOfDate ? { as_of_date: asOfDate } : {};
    return api.get("/billing/due", { params });
  },

  // ── Payments ──────────────────────────────────────────────────────────────
  async getPayments(params = {}) {
    return api.get("/payments", { params });
  },
  async getPayment(id) {
    return api.get(`/payments/${id}`);
  },
  async recordPayment(data) {
    return api.post("/payments", data);
  },
  async allocatePayment(paymentId, allocations) {
    return api.post(`/payments/${paymentId}/allocate`, { allocations });
  },
  async getInvoicePayments(invoiceId) {
    return api.get(`/invoices/${invoiceId}/payments`);
  },

  // ── Discounts ─────────────────────────────────────────────────────────────
  async getDiscounts(params = {}) {
    return api.get("/discounts", { params });
  },
  async getDiscount(id) {
    return api.get(`/discounts/${id}`);
  },
  async createDiscount(data) {
    return api.post("/discounts", data);
  },
  async updateDiscount(id, data) {
    return api.put(`/discounts/${id}`, data);
  },
  async toggleDiscountStatus(id) {
    return api.post(`/discounts/${id}/toggle-status`);
  },
  async validateCoupon(code, params = {}) {
    return api.get(`/discounts/validate/${code}`, { params });
  },

  // ── Analytics & Reports ───────────────────────────────────────────────────
  async getAnalytics(params = {}) {
    return api.get("/reports/analytics", { params });
  },
  async getRevenueReport(params = {}) {
    return api.get("/reports/revenue", { params });
  },
  async getAgingReport() {
    return api.get("/reports/aging");
  },

  // ── Customers ─────────────────────────────────────────────────────────────
  async getCustomers(params = {}) {
    return api.get("/customers", { params });
  },
  async getCustomer(customerId) {
    return api.get(`/customers/${customerId}`);
  },
  async createCustomer(data) {
    return api.post("/customers", data);
  },
  async updateCustomer(customerId, data) {
    return api.put(`/customers/${customerId}`, data);
  },
  async deleteCustomer(customerId) {
    return api.delete(`/customers/${customerId}`);
  },
};

export default subflowService;
