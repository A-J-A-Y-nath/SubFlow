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

  async getInvoice(id) {
    return api.get(`/invoices/${id}`);
  },

  async createInvoice(data) {
    return api.post("/invoices", data);
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

  // Payments
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
    return api.get(`/payments/invoice/${invoiceId}`);
  },

  // Discounts
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

  // Analytics & Reports
  async getAnalytics(params = {}) {
    return api.get("/reports/analytics", { params });
  },

  async getRevenueReport(params = {}) {
    return api.get("/reports/revenue", { params });
  },

  async getAgingReport() {
    return api.get("/reports/aging");
  },
};

export default subflowService;
