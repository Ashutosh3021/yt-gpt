export class ApiError extends Error {
  status: number;
  retryAfter?: number;
  constructor(message: string, status = 400, retryAfter?: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.retryAfter = retryAfter;
  }
}
