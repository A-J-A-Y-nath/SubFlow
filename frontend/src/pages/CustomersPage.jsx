import React, { useState, useEffect, useCallback } from "react";
import {
  Users,
  Plus,
  Search,
  RefreshCw,
  Mail,
  Phone,
  MapPin,
  Building,
  Edit2,
  CheckCircle,
  XCircle,
  CreditCard,
  FileText,
} from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import subflowService from "../services/subflowService";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "../components/ui/Table";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import Input from "../components/ui/Input";
import Modal from "../components/ui/Modal";
import EmptyState from "../components/common/EmptyState";
import LoadingSpinner from "../components/common/LoadingSpinner";
import Alert from "../components/common/Alert";
import { formatDate } from "../lib/utils";

export function CustomersPage({ onNavigate }) {
  const { isAdmin, isStaff } = useAuth();
  const isAdminOrStaff = isAdmin || isStaff;

  const [customers, setCustomers] = useState([]);
  const [pagination, setPagination] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Filters
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(1);

  // Modals
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [formError, setFormError] = useState(null);

  const initialForm = {
    company_name: "",
    contact_name: "",
    email: "",
    phone: "",
    billing_street: "",
    billing_city: "",
    billing_state: "",
    billing_postal_code: "",
    billing_country: "United States",
    currency: "USD",
    payment_terms_days: 30,
    credit_limit: "0.00",
    is_active: true,
  };

  const [form, setForm] = useState(initialForm);

  const fetchCustomers = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = { page, per_page: 15 };
      if (search.trim()) params.search = search.trim();
      if (statusFilter !== "all") params.is_active = statusFilter === "active";
      const res = await subflowService.getCustomers(params);
      if (res.success) {
        setCustomers(Array.isArray(res.data) ? res.data : res.data?.items || []);
        setPagination(res.data?.pagination || null);
      }
    } catch (err) {
      setError(err.message || "Failed to load customers.");
    } finally {
      setIsLoading(false);
    }
  }, [page, search, statusFilter]);

  useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  useEffect(() => {
    setPage(1);
  }, [search, statusFilter]);

  const handleOpenCreate = () => {
    setEditingCustomer(null);
    setForm(initialForm);
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (customer) => {
    setEditingCustomer(customer);
    setForm({
      company_name: customer.company_name || "",
      contact_name: customer.contact_name || "",
      email: customer.email || "",
      phone: customer.phone || "",
      billing_street: customer.billing_address?.street || "",
      billing_city: customer.billing_address?.city || "",
      billing_state: customer.billing_address?.state || "",
      billing_postal_code: customer.billing_address?.postal_code || "",
      billing_country: customer.billing_address?.country || "United States",
      currency: customer.currency || "USD",
      payment_terms_days: customer.payment_terms_days || 30,
      credit_limit: customer.credit_limit || "0.00",
      is_active: customer.is_active ?? true,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setFormError(null);
    setIsSaving(true);
    try {
      if (editingCustomer) {
        await subflowService.updateCustomer(editingCustomer.id, form);
        setSuccess("Customer updated successfully.");
      } else {
        await subflowService.createCustomer(form);
        setSuccess("Customer created successfully.");
      }
      setIsModalOpen(false);
      fetchCustomers();
    } catch (err) {
      setFormError(err.message || "Failed to save customer.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggleStatus = async (customer) => {
    try {
      await subflowService.updateCustomer(customer.id, { is_active: !customer.is_active });
      setSuccess(`Customer ${!customer.is_active ? "activated" : "deactivated"} successfully.`);
      fetchCustomers();
    } catch (err) {
      setError(err.message || "Failed to update customer status.");
    }
  };

  const selectClass =
    "w-full rounded-lg bg-slate-900/90 border border-slate-700/80 px-3.5 py-2.5 text-sm text-slate-100 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-brand-400" /> Customer Management
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Manage corporate accounts, contacts, billing profiles, and client relationships
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchCustomers}
            className="p-2 rounded-lg border border-slate-700 text-slate-400 hover:text-white hover:border-slate-500 transition"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          {isAdminOrStaff && (
            <Button variant="primary" size="sm" onClick={handleOpenCreate}>
              <Plus className="w-4 h-4 mr-1.5" /> New Customer
            </Button>
          )}
        </div>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}
      {success && <Alert type="success" message={success} onClose={() => setSuccess(null)} />}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search company, contact, or email…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 transition"
          />
        </div>

        <div className="flex items-center gap-1 p-1 rounded-xl bg-slate-900 border border-slate-800 self-start sm:self-auto">
          {["all", "active", "inactive"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all ${
                statusFilter === st
                  ? "bg-brand-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content */}
      {isLoading ? (
        <LoadingSpinner message="Loading customer profiles…" />
      ) : customers.length === 0 ? (
        <EmptyState
          title="No Customers Found"
          description={
            search
              ? "No customers matched your search query."
              : "No customer accounts exist yet. Create a customer to begin issuing subscriptions."
          }
          icon={Users}
          actionText={isAdminOrStaff ? "Add First Customer" : undefined}
          onAction={isAdminOrStaff ? handleOpenCreate : undefined}
        />
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Customer</TableHead>
                <TableHead>Contact Info</TableHead>
                <TableHead>Location</TableHead>
                <TableHead>Billing Details</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {customers.map((c) => (
                <TableRow key={c.id} className="hover:bg-slate-800/40 transition">
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400 font-bold text-xs uppercase">
                        {(c.company_name || c.contact_name || c.email || "C").slice(0, 2)}
                      </div>
                      <div>
                        <div className="font-semibold text-white text-sm">
                          {c.company_name || c.contact_name}
                        </div>
                        {c.contact_name && c.company_name && (
                          <div className="text-xs text-slate-400">{c.contact_name}</div>
                        )}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="space-y-0.5 text-xs">
                      <div className="flex items-center gap-1.5 text-slate-300">
                        <Mail className="w-3.5 h-3.5 text-slate-500" />
                        <span>{c.email}</span>
                      </div>
                      {c.phone && (
                        <div className="flex items-center gap-1.5 text-slate-400">
                          <Phone className="w-3.5 h-3.5 text-slate-500" />
                          <span>{c.phone}</span>
                        </div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="text-xs text-slate-300 flex items-center gap-1.5">
                      <MapPin className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
                      <span>
                        {[c.billing_address?.city, c.billing_address?.country].filter(Boolean).join(", ") || "—"}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="space-y-0.5 text-xs text-slate-300">
                      <div>
                        <span className="text-slate-500">Currency: </span>
                        <span className="font-medium text-white">{c.currency || "USD"}</span>
                      </div>
                      <div>
                        <span className="text-slate-500">Terms: </span>
                        <span>Net {c.payment_terms_days || 30} days</span>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge status={c.is_active ? "active" : "cancelled"}>
                      {c.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      {isAdminOrStaff && (
                        <>
                          <button
                            onClick={() => handleOpenEdit(c)}
                            className="p-1.5 rounded-lg border border-slate-700 text-slate-400 hover:text-white hover:border-slate-500 transition"
                            title="Edit Customer"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleToggleStatus(c)}
                            className={`p-1.5 rounded-lg border transition ${
                              c.is_active
                                ? "border-slate-700 text-slate-400 hover:text-rose-400 hover:border-rose-500/50"
                                : "border-emerald-700 text-emerald-400 hover:text-emerald-300 hover:border-emerald-500"
                            }`}
                            title={c.is_active ? "Deactivate" : "Activate"}
                          >
                            {c.is_active ? <XCircle className="w-3.5 h-3.5" /> : <CheckCircle className="w-3.5 h-3.5" />}
                          </button>
                        </>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {/* Pagination */}
          {pagination && pagination.total_pages > 1 && (
            <div className="flex items-center justify-between text-xs text-slate-400 pt-2">
              <span>
                Page {pagination.page} of {pagination.total_pages} — {pagination.total_items} total
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => p - 1)}
                  disabled={!pagination.has_prev}
                  className="px-3 py-1.5 rounded-lg border border-slate-700 disabled:opacity-40 hover:border-slate-500 transition"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={!pagination.has_next}
                  className="px-3 py-1.5 rounded-lg border border-slate-700 disabled:opacity-40 hover:border-slate-500 transition"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Customer Create/Edit Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingCustomer ? "Edit Customer Profile" : "Create Customer Account"}
        description={
          editingCustomer
            ? `Update profile details for ${editingCustomer.company_name || editingCustomer.contact_name}`
            : "Register a new corporate customer profile with billing details."
        }
        maxWidth="max-w-2xl"
      >
        <form onSubmit={handleSave} className="space-y-4">
          {formError && <Alert type="error" message={formError} onClose={() => setFormError(null)} />}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Company / Account Name *"
              placeholder="e.g. Acme Corp"
              icon={Building}
              value={form.company_name}
              onChange={(e) => setForm({ ...form, company_name: e.target.value })}
              required
            />
            <Input
              label="Contact Person Name"
              placeholder="e.g. John Doe"
              icon={Users}
              value={form.contact_name}
              onChange={(e) => setForm({ ...form, contact_name: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Email Address *"
              type="email"
              placeholder="billing@company.com"
              icon={Mail}
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
            />
            <Input
              label="Phone Number"
              placeholder="+1 (555) 000-0000"
              icon={Phone}
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
            />
          </div>

          <div className="space-y-1.5">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
              Billing Address
            </label>
            <input
              className={selectClass}
              placeholder="Street Address"
              value={form.billing_street}
              onChange={(e) => setForm({ ...form, billing_street: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <input
              className={selectClass}
              placeholder="City"
              value={form.billing_city}
              onChange={(e) => setForm({ ...form, billing_city: e.target.value })}
            />
            <input
              className={selectClass}
              placeholder="State / Region"
              value={form.billing_state}
              onChange={(e) => setForm({ ...form, billing_state: e.target.value })}
            />
            <input
              className={selectClass}
              placeholder="Postal Code"
              value={form.billing_postal_code}
              onChange={(e) => setForm({ ...form, billing_postal_code: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
                Country
              </label>
              <input
                className={selectClass}
                placeholder="Country"
                value={form.billing_country}
                onChange={(e) => setForm({ ...form, billing_country: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
                Currency
              </label>
              <select
                className={selectClass}
                value={form.currency}
                onChange={(e) => setForm({ ...form, currency: e.target.value })}
              >
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
                <option value="INR">INR (₹)</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
                Payment Terms (Days)
              </label>
              <input
                type="number"
                min="0"
                className={selectClass}
                value={form.payment_terms_days}
                onChange={(e) => setForm({ ...form, payment_terms_days: parseInt(e.target.value) || 0 })}
              />
            </div>
          </div>

          <div className="flex items-center gap-2.5 pt-1">
            <label className="flex items-center gap-2.5 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-brand-500"
              />
              <span className="text-sm text-slate-300">Account is Active</span>
            </label>
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsModalOpen(false)}
              disabled={isSaving}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm" isLoading={isSaving}>
              {editingCustomer ? "Update Customer" : "Create Customer"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

export default CustomersPage;
