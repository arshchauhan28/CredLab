import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

type RouteContext = {
  params: Promise<{
    path: string[];
  }>;
};

async function proxyRequest(
  request: NextRequest,
  context: RouteContext,
): Promise<NextResponse> {
  if (!API_BASE_URL) {
    return NextResponse.json(
      { detail: "Backend API URL is not configured." },
      { status: 500 },
    );
  }

  const { path } = await context.params;
  const apiPath = path[0] === "proxy" ? path.slice(1) : path;

  const backendUrl = `${API_BASE_URL.replace(/\/+$/, "")}/api/${apiPath
    .map(encodeURIComponent)
    .join("/")}${request.nextUrl.search}`;

  const sessionCookie = request.cookies.get("scp_session")?.value;
  const isPublicCertRoute =
    apiPath[0] === "certificates" &&
    (apiPath[apiPath.length - 1] === "public" || apiPath[1] === "verify");

  if (!sessionCookie && !isPublicCertRoute) {
    return NextResponse.json(
      { detail: "Authentication required." },
      { status: 401 },
    );
  }

  const headers = new Headers();
  const contentType = request.headers.get("content-type");

  if (contentType) headers.set("content-type", contentType);
  if (sessionCookie) {
    headers.set("Authorization", `Bearer ${sessionCookie}`);
  }
  headers.set("Accept", request.headers.get("accept") ?? "application/json");

  const method = request.method;
  const body = method === "GET" || method === "HEAD"
    ? undefined
    : await request.arrayBuffer();

  try {
    const response = await fetch(backendUrl, {
      method,
      headers,
      body,
      cache: "no-store",
      redirect: "manual",
    });

    const responseBody = await response.arrayBuffer();
    const responseHeaders = new Headers();
    const responseContentType = response.headers.get("content-type");
    if (responseContentType) responseHeaders.set("content-type", responseContentType);

    return new NextResponse(responseBody, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch {
    return NextResponse.json(
      { detail: "Unable to connect to the backend API." },
      { status: 502 },
    );
  }
}

export async function GET(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}
export async function POST(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}
export async function PATCH(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}
export async function PUT(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}
export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}
