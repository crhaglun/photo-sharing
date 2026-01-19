import { useState, useCallback, useRef } from 'react';
import { api } from '@/services/api';
import type { PhotoSummary, PhotoListParams, ApiError, FaceCluster } from '@/types/api';

export function usePhotos() {
  const [photos, setPhotos] = useState<PhotoSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [totalCount, setTotalCount] = useState(0);

  const currentPage = useRef(0);
  const currentParams = useRef<Omit<PhotoListParams, 'page'>>({});

  const fetchPhotos = useCallback(async (params?: Omit<PhotoListParams, 'page'>) => {
    setLoading(true);
    setError(null);
    setPhotos([]);
    currentPage.current = 1;
    currentParams.current = params || {};

    try {
      const result = await api.getPhotos({ ...params, page: 1, pageSize: 50 });
      setPhotos(result.items);
      setTotalCount(result.totalCount);
      setHasMore(result.page < result.totalPages);
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMore = useCallback(async () => {
    if (loading || !hasMore) return;

    setLoading(true);
    currentPage.current += 1;

    try {
      const result = await api.getPhotos({
        ...currentParams.current,
        page: currentPage.current,
        pageSize: 50
      });
      setPhotos(prev => [...prev, ...result.items]);
      setHasMore(result.page < result.totalPages);
    } catch (err) {
      setError(err as ApiError);
      currentPage.current -= 1; // Revert on error
    } finally {
      setLoading(false);
    }
  }, [loading, hasMore]);

  return { photos, loading, error, hasMore, totalCount, fetchPhotos, loadMore };
}

export function useFaceClusters() {
  const [clusters, setClusters] = useState<FaceCluster[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const fetchClusters = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.getFaceClusters();
      setClusters(result);
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setLoading(false);
    }
  }, []);

  return { clusters, loading, error, fetchClusters };
}
