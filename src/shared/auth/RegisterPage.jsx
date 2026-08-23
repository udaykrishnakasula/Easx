import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Loader2, AlertTriangle } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { useAuth } from "@/shared/context/AuthContext";
import { apiError } from "@/shared/lib/api";
import { usePublicMaintenance } from "@/admin/adminApi";
import AuthLayout from "./AuthLayout";
import { REGISTER } from "@/constants/testIds/auth";

const schema = z
  .object({
    name: z.string().min(2, "Enter your full name"),
    email: z.string().email("Enter a valid email"),
    phone: z
      .string()
      .min(6, "Enter a valid phone number")
      .regex(/^\+?[0-9]{6,15}$/, "Digits only, optional leading +"),
    password: z.string().min(8, "At least 8 characters"),
    passwordConfirm: z.string(),
    referral_code: z.string().optional(),
  })
  .refine((d) => d.password === d.passwordConfirm, {
    message: "Passwords do not match",
    path: ["passwordConfirm"],
  });

export default function RegisterPage() {
  const { register: registerUser, user, loading } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [submitting, setSubmitting] = useState(false);
  const { data: maintenance } = usePublicMaintenance();

  React.useEffect(() => {
    if (!loading && user) {
      navigate(user.role === "admin" ? "/admin" : "/dashboard", { replace: true });
    }
  }, [user, loading, navigate]);

  const isRegistrationBlocked =
    Boolean(maintenance?.is_enabled) || maintenance?.features?.registration === false;

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      email: "",
      phone: "",
      password: "",
      passwordConfirm: "",
      referral_code: params.get("ref") || "",
    },
  });

  const onSubmit = async (values) => {
    if (isRegistrationBlocked) {
      toast.error(
        maintenance?.message || "Registration is currently disabled for system maintenance."
      );
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        name: values.name,
        email: values.email,
        phone: values.phone,
        password: values.password,
      };
      if (values.referral_code) payload.referral_code = values.referral_code;
      const user = await registerUser(payload);
      toast.success(`Welcome to EasyX, ${user.name}!`);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      toast.error(apiError(err, "Unable to create account."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Start investing with EasyX in minutes."
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="text-white underline underline-offset-4" data-testid={REGISTER.loginLink}>
            Sign in
          </Link>
        </>
      }
    >
      {isRegistrationBlocked && (
        <div
          className="mb-4 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200 flex items-start gap-2.5"
          data-testid="registration-disabled-notice"
        >
          <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400 mt-0.5" />
          <div>
            <div className="font-semibold text-amber-300">Registration Temporarily Paused</div>
            <div className="text-amber-200/80 mt-0.5">
              {maintenance?.message || "New account creation is temporarily disabled during scheduled platform maintenance."}
            </div>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" data-testid="register-form">
        <div className="space-y-1.5">
          <Label htmlFor="name" className="text-white/80">Full name</Label>
          <Input id="name" placeholder="Jane Doe"
            disabled={isRegistrationBlocked}
            className="bg-white/5 border-white/15 text-white placeholder:text-white/30 disabled:opacity-50"
            data-testid={REGISTER.nameInput} {...register("name")} />
          {errors.name && <p className="text-xs text-red-400">{errors.name.message}</p>}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="email" className="text-white/80">Email</Label>
          <Input id="email" type="email" autoComplete="email" placeholder="you@example.com"
            disabled={isRegistrationBlocked}
            className="bg-white/5 border-white/15 text-white placeholder:text-white/30 disabled:opacity-50"
            data-testid={REGISTER.emailInput} {...register("email")} />
          {errors.email && <p className="text-xs text-red-400">{errors.email.message}</p>}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="phone" className="text-white/80">Phone</Label>
          <Input id="phone" type="tel" autoComplete="tel" placeholder="+91XXXXXXXXXX"
            disabled={isRegistrationBlocked}
            className="bg-white/5 border-white/15 text-white placeholder:text-white/30 disabled:opacity-50"
            data-testid="register-phone-input" {...register("phone")} />
          {errors.phone && <p className="text-xs text-red-400">{errors.phone.message}</p>}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="password" className="text-white/80">Password</Label>
            <Input id="password" type="password" autoComplete="new-password" placeholder="At least 8 chars"
              disabled={isRegistrationBlocked}
              className="bg-white/5 border-white/15 text-white placeholder:text-white/30 disabled:opacity-50"
              data-testid={REGISTER.passwordInput} {...register("password")} />
            {errors.password && <p className="text-xs text-red-400">{errors.password.message}</p>}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="passwordConfirm" className="text-white/80">Confirm</Label>
            <Input id="passwordConfirm" type="password" autoComplete="new-password" placeholder="Repeat password"
              disabled={isRegistrationBlocked}
              className="bg-white/5 border-white/15 text-white placeholder:text-white/30 disabled:opacity-50"
              data-testid={REGISTER.passwordConfirmInput} {...register("passwordConfirm")} />
            {errors.passwordConfirm && <p className="text-xs text-red-400">{errors.passwordConfirm.message}</p>}
          </div>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="referral_code" className="text-white/80">Referral code <span className="text-white/40">(optional)</span></Label>
          <Input id="referral_code" placeholder="e.g. AB12CD34"
            disabled={isRegistrationBlocked}
            className="bg-white/5 border-white/15 text-white placeholder:text-white/30 uppercase disabled:opacity-50"
            data-testid="register-referral-input" {...register("referral_code")} />
        </div>
        <Button type="submit" disabled={submitting || isRegistrationBlocked}
          className="w-full bg-white text-black hover:bg-white/90 rounded-full h-11 font-semibold disabled:opacity-50"
          data-testid={REGISTER.submitButton}>
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : isRegistrationBlocked ? "Registration Unavailable" : "Create account"}
        </Button>
      </form>
    </AuthLayout>
  );
}
