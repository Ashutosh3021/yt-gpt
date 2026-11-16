import type { Api } from '../types';
import { httpClient } from './http';
import { mockApi } from './mock';

export { ApiError } from './error';

export const api: Api = import.meta.env.VITE_API_MODE === 'http' ? httpClient : mockApi;
export const isDemo = import.meta.env.VITE_API_MODE !== 'http';
