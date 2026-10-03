"use server";

import type { Route } from "next";
import { redirect } from "next/navigation";
import { endSession, startSession } from "@/lib/auth/session";
import { passwordMatches, safeNextPath } from "@/lib/auth/token";
import { getAuthConfig } from "@/lib/env";

const FAILED_LOGIN_DELAY_MS = 1000;

export interface LoginState {
  error?: string;
}

export async function login(
  _prev: LoginState,
  formData: FormData,
): Promise<LoginState> {
  const config = getAuthConfig();
  if (!config) {
    return {
      error:
        "Login isn't configured on the server. Set APP_PASSWORD and a SESSION_SECRET of at least 32 characters.",
    };
  }

  const password = formData.get("password");
  if (
    typeof password !== "string" ||
    !passwordMatches(password, config.password)
  ) {
    await new Promise((resolve) => setTimeout(resolve, FAILED_LOGIN_DELAY_MS));
    return { error: "Incorrect password" };
  }

  await startSession(config.secret);
  redirect(safeNextPath(formData.get("next")) as Route);
}

export async function logout(): Promise<void> {
  await endSession();
  redirect("/login");
}
