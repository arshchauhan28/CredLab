export function getApiBaseUrl(): string {
  const envUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.API_BASE_URL;

  if (envUrl) {
    return envUrl.replace(/\/+$/, "");
  }

  if (process.env.NODE_ENV === "production") {
    return "https://credlab-backend.onrender.com";
  }

  return "http://127.0.0.1:8000";
}

type ApiRequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiRequest<T>(
  endpoint: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const { body, headers, ...requestOptions } = options;
  const baseUrl = getApiBaseUrl();

  const response = await fetch(
    `${baseUrl}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`,
    {
      ...requestOptions,
      headers: {
        ...(body === undefined
          ? {}
          : { "Content-Type": "application/json" }),
        ...headers,
      },
      ...(body === undefined
        ? {}
        : { body: JSON.stringify(body) }),
      cache: "no-store",
    },
  );

  if (!response.ok) {
    const responseText = await response.text();

    let message = `Request failed with status ${response.status}`;

    if (responseText) {
      try {
        const data: unknown = JSON.parse(responseText);

        if (
          typeof data === "object" &&
          data !== null &&
          "detail" in data &&
          typeof data.detail === "string"
        ) {
          message = data.detail;
        } else if (
          typeof data === "object" &&
          data !== null &&
          "message" in data &&
          typeof data.message === "string"
        ) {
          message = data.message;
        } else {
          message = responseText;
        }
      } catch {
        message = responseText;
      }
    }

    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}