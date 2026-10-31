import React, { useState } from "react";
import { UserPlus, Mail, Lock, User, Check, X, Shield, Eye, EyeOff } from "lucide-react";
import { useAuth } from "../../hooks/useAuth";
import Modal from "../ui/Modal";
import Input from "../ui/Input";
import Button from "../ui/Button";
import Alert from "./Alert";

export function CreateStaffModal({ isOpen, onClose, onSuccess }) {
  const { createStaff } = useAuth();
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    first_name: "",
    last_name: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Password validation rules
  const password = formData.password;
  const checks = [
    { label: "More than 8 characters", valid: password.length > 8 },
    { label: "At least one uppercase letter (A-Z)", valid: /[A-Z]/.test(password) },
    { label: "At least one lowercase letter (a-z)", valid: /[a-z]/.test(password) },
    { label: "At least one special character (!@#$...)", valid: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]/.test(password) },
  ];
  const isPasswordValid = checks.every((c) => c.valid);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);

    if (!isPasswordValid) {
      setError("Please ensure password satisfies all security requirements.");
      return;
    }

    setIsLoading(true);
    try {
      const res = await createStaff(formData);
      setSuccessMsg(`Staff account created successfully for ${formData.email}!`);
      setFormData({ email: "", password: "", first_name: "", last_name: "" });
      if (onSuccess) onSuccess(res);
      setTimeout(() => {
        onClose();
        setSuccessMsg(null);
      }, 1500);
    } catch (err) {
      setError(err.message || "Failed to create staff account.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Provision Staff Account"
      description="Create a role-restricted staff member account with internal operations access."
      maxWidth="max-w-md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <Alert type="error" message={error} onClose={() => setError(null)} />}
        {successMsg && <Alert type="success" message={successMsg} />}

        <div className="grid grid-cols-2 gap-3">
          <Input
            label="First Name"
            placeholder="Jane"
            icon={User}
            value={formData.first_name}
            onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
            required
          />
          <Input
            label="Last Name"
            placeholder="Staff"
            icon={User}
            value={formData.last_name}
            onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
            required
          />
        </div>

        <Input
          label="Staff Email"
          type="email"
          placeholder="staff.member@subflow.io"
          icon={Mail}
          value={formData.email}
          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
          required
        />

        <div className="space-y-2">
          <Input
            label="Temporary Password"
            type={showPassword ? "text" : "password"}
            placeholder="••••••••••••"
            icon={Lock}
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            required
            rightElement={
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="text-slate-400 hover:text-slate-200 transition focus:outline-none p-1 rounded"
                title={showPassword ? "Hide password" : "Show password"}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  <EyeOff className="w-4 h-4 text-slate-400 hover:text-slate-200" />
                ) : (
                  <Eye className="w-4 h-4 text-slate-400 hover:text-slate-200" />
                )}
              </button>
            }
          />

          {/* Real-time Password Rules Checklist */}
          {formData.password.length > 0 && (
            <div className="rounded-lg bg-slate-950/60 p-2.5 border border-slate-800 space-y-1">
              <p className="text-[11px] font-semibold text-slate-400">Password Requirements:</p>
              {checks.map((c, i) => (
                <div key={i} className="flex items-center gap-1.5 text-[11px]">
                  {c.valid ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  ) : (
                    <X className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                  )}
                  <span className={c.valid ? "text-emerald-400" : "text-slate-400"}>
                    {c.label}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="pt-2 flex items-center justify-end gap-2.5">
          <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" size="sm" isLoading={isLoading} disabled={!isPasswordValid}>
            <Shield className="w-4 h-4 mr-1.5" />
            Create Staff
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default CreateStaffModal;
