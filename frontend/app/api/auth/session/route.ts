import { NextRequest, NextResponse } from "next/server";
import type { UserResponse } from "@/types/auth";

const API_BASE_URL =
  process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function GET(request: NextRequest) {
  const token = request.cookies.get("scp_session")?.value;

  if (!token) {
    return NextResponse.json(
      { detail: "Not authenticated." },
      { status: 401 },
    );
  }

  let backendResponse: Response;

  try {
    backendResponse = await fetch(
      `${API_BASE_URL.replace(/\/+$/, "")}/api/auth/me`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        cache: "no-store",
      },
    );
  } catch {
    return NextResponse.json(
      { detail: "Unable to connect to the authentication server." },
      { status: 502 },
    );
  }

  if (!backendResponse.ok) {
    const response = NextResponse.json(
      { detail: "Your session is invalid or has expired." },
      { status: backendResponse.status === 401 ? 401 : 502 },
    );

    if (backendResponse.status === 401) {
      response.cookies.delete("scp_session");
    }

    return response;
  }

  try {
    const user = (await backendResponse.json()) as UserResponse;

    return NextResponse.json({ user });
  } catch {
    return NextResponse.json(
      { detail: "Invalid response from the authentication server." },
      { status: 502 },
    );
  }
}