import React, { useState, useEffect } from "react";
import { Package, Search, Plus, Filter, Tag, CheckCircle2 } from "lucide-react";
import subflowService from "../services/subflowService";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "../components/ui/Table";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import Input from "../components/ui/Input";
import EmptyState from "../components/common/EmptyState";
import LoadingSpinner from "../components/common/LoadingSpinner";
import Alert from "../components/common/Alert";
import { formatCurrency, formatDate } from "../lib/utils";

export function ProductsPage() {
  const [products, setProducts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    async function fetchProducts() {
      try {
        const res = await subflowService.getProducts({ search });
        if (isMounted && res.success) {
          setProducts(res.data?.items || []);
        }
      } catch (err) {
        if (isMounted) setError(err.message || "Failed to load products.");
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    fetchProducts();
    return () => {
      isMounted = false;
    };
  }, [search]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Product Catalog</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Manage recurring subscription components, add-ons, and pricing units
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="primary" size="sm" onClick={() => alert("Ready for Product Developer to connect Create Product modal!")}>
            <Plus className="w-4 h-4 mr-1.5" />
            Add Product
          </Button>
        </div>
      </div>

      {/* Developer note */}
      <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400 flex items-center justify-between">
        <span className="font-mono text-slate-300">
          <strong className="text-brand-400 font-semibold">Teammate Module:</strong> Products & Variants API endpoint: <code className="text-slate-200">GET /api/v1/products</code>
        </span>
        <Badge variant="brand" className="text-[10px]">Ready to Extend</Badge>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

      {/* Search and Filters */}
      <div className="flex items-center gap-3">
        <div className="max-w-xs w-full">
          <Input
            placeholder="Search by name or SKU..."
            icon={Search}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <LoadingSpinner message="Fetching product catalog..." />
      ) : products.length === 0 ? (
        <EmptyState
          title="No Products Found"
          description="Your catalog has no products matching the current criteria. Add products or run 'flask seed' on the backend to load sample catalog data."
          developerNote="Model: backend/models/product.py | Controller: backend/routes/products.py"
          icon={Package}
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Product Name</TableHead>
              <TableHead>SKU</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Default Price</TableHead>
              <TableHead>Unit</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {products.map((prod) => (
              <TableRow key={prod.id}>
                <TableCell className="font-medium text-white">{prod.name}</TableCell>
                <TableCell className="font-mono text-xs text-slate-400">{prod.sku}</TableCell>
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
                  <Badge status={prod.is_active ? "active" : "cancelled"}>
                    {prod.is_active ? "Active" : "Inactive"}
                  </Badge>
                </TableCell>
                <TableCell className="text-xs text-slate-400">{formatDate(prod.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}

export default ProductsPage;
