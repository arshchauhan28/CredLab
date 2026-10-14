import { NextRequest, NextResponse } from "next/server";
import type { TokenResponse } from "@/types/auth";

const API_BASE_URL = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function POST(request: NextRequest) {
  if (!API_BASE_URL) {
    return NextResponse.json(
      { detail: "Backend API URL is not configured." },
      { status: 500 },
    );
  }

  let credentials: {
    enrollment_number?: unknown;
    password?: unknown;
  };

  try {
    credentials = await request.json();
  } catch {
    return NextResponse.json(
      { detail: "Invalid request body." },
      { status: 400 },
    );
  }

  if (
    typeof credentials.enrollment_number !== "string" ||
    typeof credentials.password !== "string" ||
    !credentials.enrollment_number.trim() ||
    !credentials.password
  ) {
    return NextResponse.json(
      { detail: "Enrollment number and password are required." },
      { status: 400 },
    );
  }

  const enrollmentNumber = credentials.enrollment_number
    .trim()
    .toUpperCase();

  if (!/^[A-Z]{3}[0-9]{7}$/.test(enrollmentNumber)) {
    return NextResponse.json(
      {
        detail:
          "Enter a valid enrollment number containing three letters followed by seven digits.",
      },
      { status: 400 },
    );
  }

  let backendResponse: Response;

  try {
    backendResponse = await fetch(
      `${API_BASE_URL.replace(/\/+$/, "")}/api/auth/login`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          enrollment_number: enrollmentNumber,
          password: credentials.password,
        }),
        cache: "no-store",
      },
    );
  } catch {
    return NextResponse.json(
      { detail: "Unable to connect to the authentication server." },
      { status: 502 },
    );
  }

  const responseText = await backendResponse.text();

  if (!backendResponse.ok) {
    let detail = "Login failed.";

    try {
      const data: unknown = JSON.parse(responseText);

      if (
        typeof data === "object" &&
        data !== null &&
        "detail" in data &&
        typeof data.detail === "string"
      ) {
        detail = data.detail;
      }
    } catch {
      // Keep the generic login error.
    }

    const status =
      backendResponse.status >= 400 &&
      backendResponse.status < 600
        ? backendResponse.status
        : 502;

    return NextResponse.json({ detail }, { status });
  }

  let result: TokenResponse;

  try {
    result = JSON.parse(responseText) as TokenResponse;

    if (
      typeof result.access_token !== "string" ||
      !result.access_token ||
      typeof result.user?.id !== "number" ||
      !["STUDENT", "FACULTY", "ADMIN"].includes(result.user.role) ||
      typeof result.user.is_active !== "boolean" ||
      !result.user.is_active
    ) {
      throw new Error("Unexpected authentication response.");
    }
  } catch {
    return NextResponse.json(
      { detail: "The authentication server returned an invalid response." },
      { status: 502 },
    );
  }

  const response = NextResponse.json({
    user: result.user,
  });

  response.cookies.set("scp_session", result.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60,
  });

  return response;
}