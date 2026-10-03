"use client";

import { useActionState } from "react";
import { login, type LoginState } from "@/lib/actions/auth";
import { btnPrimary, fieldError, input, label } from "@/components/ui";

export function LoginForm({ next }: { next: string }) {
  const [state, action, pending] = useActionState<LoginState, FormData>(
    login,
    {},
  );

  return (
    <form action={action} className="space-y-4">
      <input type="hidden" name="next" value={next} />
      {/* Lets password managers save the login; there is a single user. */}
      <input
        type="text"
        name="username"
        autoComplete="username"
        value="owner"
        readOnly
        hidden
      />
      <div>
        <label htmlFor="password" className={label}>
          Password
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          autoFocus
          aria-invalid={state.error ? true : undefined}
          aria-describedby={state.error ? "login-error" : undefined}
          className={input}
        />
        {state.error && (
          <p id="login-error" role="alert" className={fieldError}>
            {state.error}
          </p>
        )}
      </div>
      <button
        type="submit"
        disabled={pending}
        className={`${btnPrimary} w-full`}
      >
        {pending ? "Checking…" : "Log in"}
      </button>
    </form>
  );
}
