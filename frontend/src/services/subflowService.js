import api from "./api";

export const subflowService = {
  // ── Products ──────────────────────────────────────────────────────────────
  async getProducts(params = {}) {
    return api.get("/products", { params });
  },
  async getProductById(id) {
    return api.get(`/products/${id}`);
  },

  // ── Plans ─────────────────────────────────────────────────────────────────
  async getPlans(params = {}) {
    return api.get("/plans", { params });
  },
  async getPlanById(id) {
    return api.get(`/plans/${id}`);
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
  async getInvoiceById(id) {
    return api.get(`/invoices/${id}`);
  },
  async createInvoice(data) {
    return api.post("/invoices", data);
  },
  async confirmInvoice(id) {
    return api.post(`/invoices/${id}/confirm`);
  },
  async cancelInvoice(id) {
    return api.post(`/invoices/${id}/cancel`);
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
  async getInvoicePayments(invoiceId) {
    return api.get(`/invoices/${invoiceId}/payments`);
  },

  // ── Discounts ─────────────────────────────────────────────────────────────
  async getDiscounts(params = {}) {
    return api.get("/discounts", { params });
  },
  async validateCoupon(code) {
    return api.get(`/discounts/validate/${code}`);
  },

  // ── Customers (for selects) ───────────────────────────────────────────────
  async getCustomers(params = {}) {
    return api.get("/customers", { params });
  },
};

export default subflowService;
