export type UserRole = "STUDENT" | "FACULTY" | "ADMIN";

export interface UserResponse {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;

  enrollment_number: string | null;
  admin_job_role: string | null;

  student_id_number: string | null;
  academic_course: string | null;
  academic_year: string | null;
  semester: string | null;
  year_of_study: string | null;

  profile_completed: boolean;
  assigned_courses: string[] | null;
  enrolled_courses: string[] | null;
  created_at: string | null;
}

export interface RegisterRequest {
  name: string;
  email: string;
  enrollment_number: string;
  academic_course: string;
  year_of_study: string;
  semester: string;
  password: string;
}

export interface FacultyRegisterRequest {
  name: string;
  email: string;
  enrollment_number: string;
  teaching_subjects: string[];
  password: string;
}

export interface AdminRegisterRequest {
  name: string;
  email: string;
  enrollment_number: string;
  admin_job_role: string;
  password: string;
}

export interface LoginRequest {
  enrollment_number: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  user: UserResponse;
}

export interface StudentProfileUpdateRequest {
  student_id_number: string;
  academic_course: string;
  academic_year: string;
  semester: string;
  year_of_study: string;
}