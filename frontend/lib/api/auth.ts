import { apiRequest } from "./client";

import type {
  AdminRegisterRequest,
  FacultyRegisterRequest,
  LoginRequest,
  RegisterRequest,
  StudentProfileUpdateRequest,
  TokenResponse,
  UserResponse,
} from "@/types/auth";

export function registerUser(
  payload: RegisterRequest,
): Promise<UserResponse> {
  return apiRequest<UserResponse>("/api/auth/register", {
    method: "POST",
    body: payload,
  });
}

export function registerFaculty(
  payload: FacultyRegisterRequest,
): Promise<UserResponse> {
  return apiRequest<UserResponse>("/api/auth/register/faculty", {
    method: "POST",
    body: payload,
  });
}

export function registerAdmin(
  payload: AdminRegisterRequest,
): Promise<UserResponse> {
  return apiRequest<UserResponse>("/api/auth/register/admin", {
    method: "POST",
    body: payload,
  });
}

export function loginUser(
  payload: LoginRequest,
): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/api/auth/login", {
    method: "POST",
    body: payload,
  });
}

export function getCurrentUser(
  accessToken: string,
): Promise<UserResponse> {
  return apiRequest<UserResponse>("/api/auth/me", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

export function updateStudentProfile(
  accessToken: string,
  payload: StudentProfileUpdateRequest,
): Promise<UserResponse> {
  return apiRequest<UserResponse>("/api/auth/profile", {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: payload,
  });
}