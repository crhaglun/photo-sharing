import { getIdToken } from './firebase';
import type { PagedResponse, PhotoSummary, PhotoListParams, PhotoDetail, PersonResponse, ApiError, FaceCluster, Place, DateRange } from '@/types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5161';

class ApiClient {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = await getIdToken();

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error: ApiError = {
        status: response.status,
        message: response.statusText,
      };
      throw error;
    }

    return response.json();
  }

  async getPhotos(params?: PhotoListParams): Promise<PagedResponse<PhotoSummary>> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.dateStart) searchParams.set('dateStart', params.dateStart);
      if (params.dateEnd) searchParams.set('dateEnd', params.dateEnd);
      if (params.placeId) searchParams.set('placeId', params.placeId);
      if (params.personId) searchParams.set('personId', params.personId);
      if (params.includeLowQuality !== undefined)
        searchParams.set('includeLowQuality', String(params.includeLowQuality));
      if (params.page) searchParams.set('page', String(params.page));
      if (params.pageSize) searchParams.set('pageSize', String(params.pageSize));
    }
    const query = searchParams.toString();
    return this.request<PagedResponse<PhotoSummary>>(`/photos${query ? `?${query}` : ''}`);
  }

  async getPhoto(id: string): Promise<PhotoDetail> {
    return this.request<PhotoDetail>(`/photos/${id}`);
  }

  async getPersons(): Promise<PersonResponse[]> {
    return this.request<PersonResponse[]>('/persons');
  }

  async getFaceClusters(): Promise<FaceCluster[]> {
    return this.request<FaceCluster[]>('/faces/clusters');
  }

  async createPerson(name: string): Promise<PersonResponse> {
    return this.request<PersonResponse>('/persons', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  }

  async assignFaceToPerson(faceId: string, personId: string): Promise<void> {
    await this.request(`/faces/${faceId}`, {
      method: 'PATCH',
      body: JSON.stringify({ personId }),
    });
  }

  async getPlaces(): Promise<Place[]> {
    return this.request<Place[]>('/places');
  }

  async getDateRange(): Promise<DateRange> {
    return this.request<DateRange>('/photos/date-range');
  }

  getThumbnailUrl(id: string): string {
    return `${API_BASE_URL}/photos/${id}/thumbnail`;
  }

  getDefaultUrl(id: string): string {
    return `${API_BASE_URL}/photos/${id}/default`;
  }

  getOriginalUrl(id: string): string {
    return `${API_BASE_URL}/photos/${id}/original`;
  }
}

export const api = new ApiClient();
