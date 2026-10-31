import React, { useState, useEffect, useCallback } from "react";
import {
  Package,
  Search,
  Plus,
  Pencil,
  Trash2,
  Layers,
  CheckCircle2,
  XCircle,
  Tag,
  DollarSign,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";
import subflowService from "../services/subflowService";
import { useAuth } from "../hooks/useAuth";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "../components/ui/Table";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import Input from "../components/ui/Input";
import Modal from "../components/ui/Modal";
import EmptyState from "../components/common/EmptyState";
import LoadingSpinner from "../components/common/LoadingSpinner";
import Alert from "../components/common/Alert";
import { formatCurrency, formatDate } from "../lib/utils";

const INITIAL_PRODUCT_FORM = {
  name: "",
  sku: "",
  description: "",
  default_price: "",
  currency: "USD",
  unit_of_measure: "unit",
  is_recurring: true,
  is_active: true,
};

const INITIAL_VARIANT_FORM = {
  name: "",
  sku: "",
  price_extra: "0.00",
  description: "",
  is_active: true,
};

export function ProductsPage() {
  const { isAdmin, isStaff } = useAuth();
  const canManage = isAdmin || isStaff;

  const [products, setProducts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Modals state
  const [isProductModalOpen, setIsProductModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [productForm, setProductForm] = useState(INITIAL_PRODUCT_FORM);
  const [formErrors, setFormErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Variant modal state
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [isVariantModalOpen, setIsVariantModalOpen] = useState(false);
  const [variants, setVariants] = useState([]);
  const [isLoadingVariants, setIsLoadingVariants] = useState(false);
  const [variantForm, setVariantForm] = useState(INITIAL_VARIANT_FORM);
  const [editingVariant, setEditingVariant] = useState(null);
  const [isVariantFormOpen, setIsVariantFormOpen] = useState(false);
  const [variantFormErrors, setVariantFormErrors] = useState({});

  // Confirmation dialog state
  const [deleteTarget, setDeleteTarget] = useState(null); // { type: 'product' | 'variant', data: ... }
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  // Fetch products
  const loadProductData = useCallback(async () => {
    try {
      const params = {};
      if (search.trim()) params.search = search.trim();
      if (filterType === "recurring") params.is_recurring = true;
      if (filterType === "one-off") params.is_recurring = false;
      if (filterStatus === "active") params.is_active = true;
      if (filterStatus === "inactive") params.is_active = false;

      const res = await subflowService.getProducts(params);
      if (res.success) {
        setProducts(res.data?.items || []);
      }
    } catch (err) {
      setError(err.message || "Failed to load products.");
    } finally {
      setIsLoading(false);
    }
  }, [search, filterType, filterStatus]);

  useEffect(() => {
    let isMounted = true;
    async function init() {
      try {
        const params = {};
        if (search.trim()) params.search = search.trim();
        if (filterType === "recurring") params.is_recurring = true;
        if (filterType === "one-off") params.is_recurring = false;
        if (filterStatus === "active") params.is_active = true;
        if (filterStatus === "inactive") params.is_active = false;

        const res = await subflowService.getProducts(params);
        if (isMounted && res.success) {
          setProducts(res.data?.items || []);
        }
      } catch (err) {
        if (isMounted) setError(err.message || "Failed to load products.");
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    init();
    return () => {
      isMounted = false;
    };
  }, [search, filterType, filterStatus]);

  const refreshProducts = () => {
    setIsLoading(true);
    loadProductData();
  };

  // Load variants for selected product
  const loadVariants = async (product) => {
    setSelectedProduct(product);
    setIsVariantModalOpen(true);
    setIsLoadingVariants(true);
    setIsVariantFormOpen(false);
    setEditingVariant(null);
    setVariantForm(INITIAL_VARIANT_FORM);
    setVariantFormErrors({});
    try {
      const res = await subflowService.getProductVariants(product.id);
      if (res.success) {
        setVariants(res.data?.items || []);
      }
    } catch (err) {
      setError(err.message || "Failed to load variants.");
    } finally {
      setIsLoadingVariants(false);
    }
  };

  // Product CRUD Handlers
  const handleOpenCreateProduct = () => {
    setEditingProduct(null);
    setProductForm(INITIAL_PRODUCT_FORM);
    setFormErrors({});
    setIsProductModalOpen(true);
  };

  const handleOpenEditProduct = (prod) => {
    setEditingProduct(prod);
    setProductForm({
      name: prod.name,
      sku: prod.sku,
      description: prod.description || "",
      default_price: prod.default_price,
      currency: prod.currency || "USD",
      unit_of_measure: prod.unit_of_measure || "unit",
      is_recurring: prod.is_recurring,
      is_active: prod.is_active,
    });
    setFormErrors({});
    setIsProductModalOpen(true);
  };

  const validateProductForm = () => {
    const errors = {};
    if (!productForm.name.trim()) errors.name = "Product name is required";
    if (!productForm.sku.trim()) errors.sku = "Product SKU is required";
    if (productForm.default_price === "" || isNaN(productForm.default_price)) {
      errors.default_price = "Base price must be a valid number";
    } else if (parseFloat(productForm.default_price) < 0) {
      errors.default_price = "Base price cannot be negative";
    }
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSaveProduct = async (e) => {
    e.preventDefault();
    if (!validateProductForm()) return;

    setIsSubmitting(true);
    setError(null);
    try {
      const payload = {
        ...productForm,
        default_price: parseFloat(productForm.default_price),
      };

      if (editingProduct) {
        await subflowService.updateProduct(editingProduct.id, payload);
        setSuccessMessage(`Product '${productForm.name}' updated successfully.`);
      } else {
        await subflowService.createProduct(payload);
        setSuccessMessage(`Product '${productForm.name}' created successfully.`);
      }
      setIsProductModalOpen(false);
      refreshProducts();
    } catch (err) {
      setError(err.message || "Failed to save product.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleProductStatus = async (product) => {
    try {
      await subflowService.toggleProductStatus(product.id, !product.is_active);
      setSuccessMessage(`Product '${product.name}' ${!product.is_active ? "activated" : "deactivated"}.`);
      refreshProducts();
    } catch (err) {
      setError(err.message || "Failed to change product status.");
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setIsSubmitting(true);
    try {
      if (deleteTarget.type === "product") {
        await subflowService.deleteProduct(deleteTarget.data.id);
        setSuccessMessage(`Product '${deleteTarget.data.name}' deleted successfully.`);
        refreshProducts();
      } else if (deleteTarget.type === "variant") {
        await subflowService.deleteVariant(selectedProduct.id, deleteTarget.data.id);
        setSuccessMessage(`Variant '${deleteTarget.data.name}' deleted successfully.`);
        // Refresh variants list & products
        const res = await subflowService.getProductVariants(selectedProduct.id);
        if (res.success) setVariants(res.data?.items || []);
        refreshProducts();
      }
      setIsDeleteModalOpen(false);
      setDeleteTarget(null);
    } catch (err) {
      setError(err.message || "Deletion failed. Record may be in use by quotations or subscriptions.");
      setIsDeleteModalOpen(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Variant CRUD Handlers
  const handleOpenAddVariant = () => {
    setEditingVariant(null);
    const generatedSku = `${selectedProduct.sku}-VAR-${(variants.length + 1).toString().padStart(2, "0")}`;
    setVariantForm({
      name: "",
      sku: generatedSku,
      price_extra: "0.00",
      description: "",
      is_active: true,
    });
    setVariantFormErrors({});
    setIsVariantFormOpen(true);
  };

  const handleOpenEditVariant = (variant) => {
    setEditingVariant(variant);
    setVariantForm({
      name: variant.name,
      sku: variant.sku,
      price_extra: variant.price_extra,
      description: variant.description || "",
      is_active: variant.is_active,
    });
    setVariantFormErrors({});
    setIsVariantFormOpen(true);
  };

  const validateVariantForm = () => {
    const errors = {};
    if (!variantForm.name.trim()) errors.name = "Variant name is required";
    if (!variantForm.sku.trim()) errors.sku = "Variant SKU is required";
    if (variantForm.price_extra === "" || isNaN(variantForm.price_extra)) {
      errors.price_extra = "Additional price must be a valid number";
    } else if (parseFloat(variantForm.price_extra) < 0) {
      errors.price_extra = "Additional price cannot be negative";
    }
    setVariantFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSaveVariant = async (e) => {
    e.preventDefault();
    if (!validateVariantForm()) return;

    setIsSubmitting(true);
    try {
      const payload = {
        ...variantForm,
        price_extra: parseFloat(variantForm.price_extra),
      };

      if (editingVariant) {
        await subflowService.updateVariant(selectedProduct.id, editingVariant.id, payload);
        setSuccessMessage(`Variant '${variantForm.name}' updated successfully.`);
      } else {
        await subflowService.createVariant(selectedProduct.id, payload);
        setSuccessMessage(`Variant '${variantForm.name}' added successfully.`);
      }

      setIsVariantFormOpen(false);
      const res = await subflowService.getProductVariants(selectedProduct.id);
      if (res.success) setVariants(res.data?.items || []);
      refreshProducts();
    } catch (err) {
      setError(err.message || "Failed to save variant.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleVariantStatus = async (variant) => {
    try {
      await subflowService.toggleVariantStatus(selectedProduct.id, variant.id, !variant.is_active);
      const res = await subflowService.getProductVariants(selectedProduct.id);
      if (res.success) setVariants(res.data?.items || []);
      refreshProducts();
    } catch (err) {
      setError(err.message || "Failed to update variant status.");
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <Package className="w-5 h-5 text-brand-400" />
            Product Catalog & Variants
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Manage recurring catalog components, configurable pricing add-ons, and product variants
          </p>
        </div>
        {canManage && (
          <div className="flex items-center gap-2">
            <Button variant="primary" size="sm" onClick={handleOpenCreateProduct}>
              <Plus className="w-4 h-4 mr-1.5" />
              Add Product
            </Button>
          </div>
        )}
      </div>

      {/* Notifications */}
      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}
      {successMessage && <Alert type="success" message={successMessage} onClose={() => setSuccessMessage(null)} />}

      {/* Search & Filter Toolbar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800">
        <div className="max-w-xs w-full">
          <Input
            placeholder="Search by name or SKU..."
            icon={Search}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Type Filter */}
          <div className="flex items-center gap-1 p-1 rounded-lg bg-slate-900 border border-slate-800 text-xs">
            {["all", "recurring", "one-off"].map((t) => (
              <button
                key={t}
                onClick={() => setFilterType(t)}
                className={`px-2.5 py-1 rounded capitalize transition-all ${
                  filterType === t ? "bg-brand-600 text-white font-medium" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {t === "all" ? "All Types" : t}
              </button>
            ))}
          </div>

          {/* Status Filter (Staff/Admin) */}
          {canManage && (
            <div className="flex items-center gap-1 p-1 rounded-lg bg-slate-900 border border-slate-800 text-xs">
              {["all", "active", "inactive"].map((s) => (
                <button
                  key={s}
                  onClick={() => setFilterStatus(s)}
                  className={`px-2.5 py-1 rounded capitalize transition-all ${
                    filterStatus === s ? "bg-slate-700 text-white font-medium" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {s === "all" ? "All Status" : s}
                </button>
              ))}
            </div>
          )}

          <Button variant="ghost" size="sm" onClick={refreshProducts} title="Refresh catalog">
            <RefreshCw className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      {/* Products Table / Loading / Empty */}
      {isLoading ? (
        <LoadingSpinner message="Fetching product catalog..." />
      ) : products.length === 0 ? (
        <EmptyState
          title="No Products Found"
          description={
            search || filterType !== "all" || filterStatus !== "all"
              ? "No products matched your search or filter criteria. Try adjusting your filters."
              : "Your catalog is empty. Click 'Add Product' to create your first catalog item."
          }
          icon={Package}
        />
      ) : (
        <div className="rounded-xl border border-slate-800 overflow-hidden bg-slate-900/50">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Product Name</TableHead>
                <TableHead>SKU</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Base Unit Price</TableHead>
                <TableHead>Unit</TableHead>
                <TableHead>Variants</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                {canManage && <TableHead className="text-right">Actions</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {products.map((prod) => (
                <TableRow key={prod.id}>
                  <TableCell>
                    <div>
                      <div className="font-semibold text-white">{prod.name}</div>
                      {prod.description && (
                        <div className="text-xs text-slate-400 truncate max-w-xs">{prod.description}</div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-slate-300">{prod.sku}</TableCell>
                  <TableCell>
                    <Badge variant={prod.is_recurring ? "brand" : "warning"}>
                      {prod.is_recurring ? "Recurring" : "One-off"}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-semibold text-slate-200">
                    {formatCurrency(prod.default_price, prod.currency)}
                  </TableCell>
                  <TableCell className="text-xs text-slate-400 capitalize">{prod.unit_of_measure}</TableCell>
                  <TableCell>
                    <button
                      onClick={() => loadVariants(prod)}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-800 hover:bg-brand-950/60 hover:text-brand-300 border border-slate-700 hover:border-brand-500/40 text-slate-300 transition"
                      title="Manage product variants"
                    >
                      <Layers className="w-3.5 h-3.5 text-brand-400" />
                      <span>{prod.variants_count || 0} variants</span>
                    </button>
                  </TableCell>
                  <TableCell>
                    <Badge status={prod.is_active ? "active" : "inactive"}>
                      {prod.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs text-slate-400">{formatDate(prod.created_at)}</TableCell>

                  {canManage && (
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => loadVariants(prod)}
                          title="Manage Variants"
                        >
                          <Layers className="w-3.5 h-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleOpenEditProduct(prod)}
                          title="Edit Product"
                        >
                          <Pencil className="w-3.5 h-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleToggleProductStatus(prod)}
                          title={prod.is_active ? "Deactivate" : "Activate"}
                          className={prod.is_active ? "hover:text-amber-400" : "hover:text-emerald-400"}
                        >
                          {prod.is_active ? <XCircle className="w-3.5 h-3.5" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setDeleteTarget({ type: "product", data: prod });
                            setIsDeleteModalOpen(true);
                          }}
                          title="Delete Product"
                          className="hover:text-rose-400"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* ====================================================================== */}
      {/* Create / Edit Product Modal */}
      {/* ====================================================================== */}
      <Modal
        isOpen={isProductModalOpen}
        onClose={() => setIsProductModalOpen(false)}
        title={editingProduct ? "Edit Product" : "Create New Product"}
        description={
          editingProduct
            ? "Update pricing, unit of measure, and billing cadence for this item."
            : "Add a new sellable item, add-on, or service to your catalog."
        }
        maxWidth="max-w-xl"
      >
        <form onSubmit={handleSaveProduct} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Product Name *"
              placeholder="e.g. Dedicated Server Hosting"
              value={productForm.name}
              onChange={(e) => setProductForm({ ...productForm, name: e.target.value })}
              error={formErrors.name}
            />
            <Input
              label="SKU / Item Code *"
              placeholder="e.g. PROD-SRV-01"
              value={productForm.sku}
              onChange={(e) => setProductForm({ ...productForm, sku: e.target.value.toUpperCase() })}
              error={formErrors.sku}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Input
              label="Base Price *"
              type="number"
              step="0.01"
              min="0"
              placeholder="0.00"
              icon={DollarSign}
              value={productForm.default_price}
              onChange={(e) => setProductForm({ ...productForm, default_price: e.target.value })}
              error={formErrors.default_price}
            />
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                Currency
              </label>
              <select
                value={productForm.currency}
                onChange={(e) => setProductForm({ ...productForm, currency: e.target.value })}
                className="w-full rounded-lg bg-slate-900/90 border border-slate-700/80 px-3.5 py-2.5 text-sm text-slate-100 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value="USD">USD ($)</option>
                <option value="INR">INR (₹)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                Unit of Measure
              </label>
              <input
                type="text"
                placeholder="unit, seat, month, GB"
                value={productForm.unit_of_measure}
                onChange={(e) => setProductForm({ ...productForm, unit_of_measure: e.target.value })}
                className="w-full rounded-lg bg-slate-900/90 border border-slate-700/80 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Description
            </label>
            <textarea
              rows={3}
              placeholder="Product summary and service details..."
              value={productForm.description}
              onChange={(e) => setProductForm({ ...productForm, description: e.target.value })}
              className="w-full rounded-lg bg-slate-900/90 border border-slate-700/80 p-3 text-sm text-slate-100 placeholder-slate-500 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>

          <div className="flex items-center gap-6 pt-2 border-t border-slate-800">
            <label className="flex items-center gap-2 cursor-pointer select-none text-xs text-slate-300 font-medium">
              <input
                type="checkbox"
                checked={productForm.is_recurring}
                onChange={(e) => setProductForm({ ...productForm, is_recurring: e.target.checked })}
                className="rounded border-slate-700 bg-slate-900 text-brand-600 focus:ring-brand-500 w-4 h-4"
              />
              Recurring Subscription Component
            </label>

            <label className="flex items-center gap-2 cursor-pointer select-none text-xs text-slate-300 font-medium">
              <input
                type="checkbox"
                checked={productForm.is_active}
                onChange={(e) => setProductForm({ ...productForm, is_active: e.target.checked })}
                className="rounded border-slate-700 bg-slate-900 text-brand-600 focus:ring-brand-500 w-4 h-4"
              />
              Active (Sellable)
            </label>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsProductModalOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm" isLoading={isSubmitting}>
              {editingProduct ? "Save Changes" : "Create Product"}
            </Button>
          </div>
        </form>
      </Modal>

      {/* ====================================================================== */}
      {/* Product Variants Modal */}
      {/* ====================================================================== */}
      <Modal
        isOpen={isVariantModalOpen}
        onClose={() => setIsVariantModalOpen(false)}
        title={
          selectedProduct
            ? `Variants: ${selectedProduct.name}`
            : "Product Variants"
        }
        description={
          selectedProduct
            ? `Base Price: ${formatCurrency(selectedProduct.default_price, selectedProduct.currency)} / ${selectedProduct.unit_of_measure} | Formula: Final Unit Price = Base Price + Variant Additional Price`
            : "Manage configurable variant dimensions and pricing add-ons."
        }
        maxWidth="max-w-3xl"
      >
        <div className="space-y-4">
          {/* Header Action */}
          {canManage && (
            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <span className="text-xs text-slate-300 font-medium">
                {variants.length} variant{variants.length !== 1 ? "s" : ""} configured
              </span>
              {!isVariantFormOpen && (
                <Button variant="primary" size="sm" onClick={handleOpenAddVariant}>
                  <Plus className="w-3.5 h-3.5 mr-1.5" />
                  Add Variant
                </Button>
              )}
            </div>
          )}

          {/* Inline Variant Form */}
          {isVariantFormOpen && (
            <form onSubmit={handleSaveVariant} className="p-4 rounded-xl bg-slate-950 border border-brand-500/40 space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <h4 className="text-sm font-semibold text-white">
                  {editingVariant ? `Edit Variant: ${editingVariant.name}` : "Configure New Variant"}
                </h4>
                <button
                  type="button"
                  onClick={() => setIsVariantFormOpen(false)}
                  className="text-xs text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input
                  label="Variant Name *"
                  placeholder="e.g. 100GB Storage Tier"
                  value={variantForm.name}
                  onChange={(e) => setVariantForm({ ...variantForm, name: e.target.value })}
                  error={variantFormErrors.name}
                />
                <Input
                  label="Variant SKU *"
                  placeholder="e.g. VAR-100GB"
                  value={variantForm.sku}
                  onChange={(e) => setVariantForm({ ...variantForm, sku: e.target.value.toUpperCase() })}
                  error={variantFormErrors.sku}
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input
                  label="Additional Price (₹ / $ surcharge) *"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00"
                  icon={DollarSign}
                  value={variantForm.price_extra}
                  onChange={(e) => setVariantForm({ ...variantForm, price_extra: e.target.value })}
                  helperText={
                    selectedProduct && !isNaN(parseFloat(variantForm.price_extra || 0))
                      ? `Calculated Final Unit Price: ${formatCurrency(
                          parseFloat(selectedProduct.default_price || 0) +
                            parseFloat(variantForm.price_extra || 0),
                          selectedProduct.currency
                        )}`
                      : ""
                  }
                  error={variantFormErrors.price_extra}
                />

                <Input
                  label="Description / Attribute Notes"
                  placeholder="e.g. Adds 100GB NVMe storage"
                  value={variantForm.description}
                  onChange={(e) => setVariantForm({ ...variantForm, description: e.target.value })}
                />
              </div>

              <div className="flex items-center justify-between pt-2">
                <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300">
                  <input
                    type="checkbox"
                    checked={variantForm.is_active}
                    onChange={(e) => setVariantForm({ ...variantForm, is_active: e.target.checked })}
                    className="rounded border-slate-700 bg-slate-900 text-brand-600 focus:ring-brand-500 w-4 h-4"
                  />
                  Active Variant
                </label>

                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setIsVariantFormOpen(false)}
                    disabled={isSubmitting}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" variant="primary" size="sm" isLoading={isSubmitting}>
                    {editingVariant ? "Update Variant" : "Save Variant"}
                  </Button>
                </div>
              </div>
            </form>
          )}

          {/* Variants Table */}
          {isLoadingVariants ? (
            <LoadingSpinner message="Loading variants..." />
          ) : variants.length === 0 ? (
            <div className="text-center py-8 px-4 rounded-xl border border-dashed border-slate-800 text-slate-400">
              <Tag className="w-8 h-8 text-slate-500 mx-auto mb-2 opacity-60" />
              <p className="text-xs font-medium text-slate-300">No Variants Defined</p>
              <p className="text-[11px] text-slate-500 mt-1 max-w-sm mx-auto">
                This product currently uses only its base unit price. Add variants to configure add-on tiers or extra capacity.
              </p>
            </div>
          ) : (
            <div className="rounded-xl border border-slate-800 overflow-hidden bg-slate-950/60">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Variant Name</TableHead>
                    <TableHead>SKU</TableHead>
                    <TableHead>Extra Price</TableHead>
                    <TableHead>Final Price</TableHead>
                    <TableHead>Status</TableHead>
                    {canManage && <TableHead className="text-right">Actions</TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {variants.map((variant) => (
                    <TableRow key={variant.id}>
                      <TableCell>
                        <div className="font-medium text-white">{variant.name}</div>
                        {variant.description && (
                          <div className="text-[11px] text-slate-400 truncate max-w-xs">{variant.description}</div>
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-slate-300">{variant.sku}</TableCell>
                      <TableCell className="text-slate-300 text-xs font-medium">
                        +{formatCurrency(variant.price_extra, variant.currency)}
                      </TableCell>
                      <TableCell>
                        <span className="font-bold text-emerald-400 text-sm">
                          {formatCurrency(variant.final_price, variant.currency)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge status={variant.is_active ? "active" : "inactive"}>
                          {variant.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                      {canManage && (
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleOpenEditVariant(variant)}
                              title="Edit Variant"
                            >
                              <Pencil className="w-3.5 h-3.5" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleToggleVariantStatus(variant)}
                              title={variant.is_active ? "Deactivate" : "Activate"}
                              className={variant.is_active ? "hover:text-amber-400" : "hover:text-emerald-400"}
                            >
                              {variant.is_active ? <XCircle className="w-3.5 h-3.5" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setDeleteTarget({ type: "variant", data: variant });
                                setIsDeleteModalOpen(true);
                              }}
                              title="Delete Variant"
                              className="hover:text-rose-400"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </Button>
                          </div>
                        </TableCell>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </Modal>

      {/* ====================================================================== */}
      {/* Confirmation Dialog for Destructive Actions */}
      {/* ====================================================================== */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        title={
          deleteTarget?.type === "product"
            ? `Delete Product: ${deleteTarget.data.name}?`
            : `Delete Variant: ${deleteTarget?.data?.name}?`
        }
        description="This action cannot be undone. Products and variants referenced by active quotations or subscriptions cannot be deleted and must be deactivated instead."
        maxWidth="max-w-md"
      >
        <div className="space-y-4">
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
            <div>
              <p className="font-semibold text-rose-200">Notice:</p>
              <p className="mt-0.5">
                Are you sure you want to delete SKU{" "}
                <code className="font-mono text-rose-100">{deleteTarget?.data?.sku}</code>?
              </p>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsDeleteModalOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="danger"
              size="sm"
              onClick={handleConfirmDelete}
              isLoading={isSubmitting}
            >
              Yes, Delete
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

export default ProductsPage;
