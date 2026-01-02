// API response types

export interface ApiError {
  code: string;
  message: string;
  details?: any;
}

export interface ApiResponse<T> {
  status: "success" | "error";
  data?: T;
  error?: ApiError;
}

