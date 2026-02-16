import { useEffect, useRef, useCallback, useState, useMemo } from 'react';
import { usePhotos } from '@/hooks/useApi';
import { api } from '@/services/api';
import { PlaceTreeSelector } from './PlaceTreeSelector';
import { PhotoThumbnail } from './PhotoThumbnail';
import { PhotoViewer } from './PhotoViewer';
import { AuthenticatedImage } from './AuthenticatedImage';
import type { PersonResponse, Place, PhotoListParams, DateRange, NavigationTarget, SimilarPhotoResponse } from '@/types/api';

interface LibraryViewProps {
  initialPersonId?: string;
  initialSimilarToId?: string;
  onNavigate?: (target: NavigationTarget) => void;
}

export const LibraryView = ({ initialPersonId, initialSimilarToId, onNavigate }: LibraryViewProps) => {
  const { photos, loading, error, hasMore, totalCount, fetchPhotos, loadMore } = usePhotos();
  const loaderRef = useRef<HTMLDivElement>(null);

  // Filter state
  const [persons, setPersons] = useState<PersonResponse[]>([]);
  const [places, setPlaces] = useState<Place[]>([]);
  const [dateRange, setDateRange] = useState<DateRange | null>(null);
  const [filters, setFilters] = useState<Omit<PhotoListParams, 'page' | 'pageSize'>>(
    initialPersonId ? { personId: initialPersonId } : {}
  );
  const [viewerIndex, setViewerIndex] = useState<number | null>(null);

  // Similar mode state
  const [similarResults, setSimilarResults] = useState<SimilarPhotoResponse[] | null>(null);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [similarSourceName, setSimilarSourceName] = useState<string | null>(null);
  const [maxDistance, setMaxDistance] = useState(1.0);
  const isSimilarMode = initialSimilarToId != null;

  // Fetch similar photos on mount when in similar mode
  useEffect(() => {
    if (!initialSimilarToId) return;
    let cancelled = false;
    setSimilarLoading(true);

    Promise.all([
      api.getSimilarPhotos(initialSimilarToId),
      api.getPhoto(initialSimilarToId),
    ]).then(([results, detail]) => {
      if (cancelled) return;
      setSimilarResults(results);
      setSimilarSourceName(detail.originalFilename);
      if (results.length > 0) {
        setMaxDistance(results[results.length - 1].distance);
      }
    }).catch(() => {}).finally(() => {
      if (!cancelled) setSimilarLoading(false);
    });

    return () => { cancelled = true; };
  }, [initialSimilarToId]);

  // Filtered similar results based on distance slider
  const filteredSimilarIds = useMemo(() => {
    if (!similarResults) return [];
    return similarResults
      .filter((r) => r.distance <= maxDistance)
      .map((r) => r.photoId);
  }, [similarResults, maxDistance]);

  // Load filter options on mount (only in normal mode)
  useEffect(() => {
    if (isSimilarMode) return;
    const loadFilterOptions = async () => {
      try {
        const [personsData, placesData, dateRangeData] = await Promise.all([
          api.getPersons(),
          api.getPlaces(),
          api.getDateRange(),
        ]);
        setPersons(personsData);
        setPlaces(placesData);
        setDateRange(dateRangeData);
      } catch {
        // Ignore - filters are optional
      }
    };
    loadFilterOptions();
  }, [isSimilarMode]);

  // Fetch photos when filters change (only in normal mode)
  useEffect(() => {
    if (isSimilarMode) return;
    fetchPhotos(filters);
  }, [fetchPhotos, filters, isSimilarMode]);

  // Infinite scroll (only in normal mode)
  const handleObserver = useCallback(
    (entries: IntersectionObserverEntry[]) => {
      const [entry] = entries;
      if (entry.isIntersecting && hasMore && !loading && !isSimilarMode) {
        loadMore();
      }
    },
    [hasMore, loading, loadMore, isSimilarMode]
  );

  useEffect(() => {
    const observer = new IntersectionObserver(handleObserver, {
      root: null,
      rootMargin: '100px',
      threshold: 0,
    });

    if (loaderRef.current) {
      observer.observe(loaderRef.current);
    }

    return () => observer.disconnect();
  }, [handleObserver]);

  const handleFilterChange = (key: keyof typeof filters, value: string | boolean | undefined) => {
    setFilters((prev) => {
      const next = { ...prev };
      if (value !== undefined && value !== false) {
        (next as Record<string, string | boolean>)[key] = value;
      } else {
        delete (next as Record<string, string | boolean | undefined>)[key];
      }
      return next;
    });
  };

  const clearFilters = () => {
    setFilters({});
  };

  const hasActiveFilters = Object.keys(filters).length > 0;

  // Which photo IDs to display
  const displayPhotoIds = isSimilarMode ? filteredSimilarIds : photos.map((p) => p.id);

  return (
    <div>
      {/* Filter pane */}
      {isSimilarMode ? (
        <div className="bg-white rounded-lg shadow p-4 mb-4 sticky top-0 z-10">
          <div className="flex flex-wrap gap-4 items-center">
            {/* Source thumbnail */}
            <div className="w-12 h-12 rounded overflow-hidden flex-shrink-0">
              <AuthenticatedImage
                src={api.getThumbnailUrl(initialSimilarToId!)}
                alt="Source photo"
                className="w-full h-full object-cover"
              />
            </div>

            {/* Label */}
            <div className="text-sm text-gray-700">
              Similar to <span className="font-medium">{similarSourceName || '...'}</span>
            </div>

            {/* Distance slider */}
            <div className="flex items-center gap-2">
              <label className="text-xs text-gray-500 whitespace-nowrap">Max distance</label>
              <input
                type="range"
                min={0}
                max={similarResults?.length ? similarResults[similarResults.length - 1].distance : 2}
                step={0.01}
                value={maxDistance}
                onChange={(e) => setMaxDistance(parseFloat(e.target.value))}
                className="w-40"
              />
              <span className="text-xs text-gray-500 tabular-nums w-10">{maxDistance.toFixed(2)}</span>
            </div>

            {/* Back to library */}
            <button
              onClick={() => onNavigate?.({ type: 'library' })}
              className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900"
            >
              Back to library
            </button>

            {/* Photo count */}
            <div className="ml-auto text-sm text-gray-500">
              {similarLoading
                ? null
                : similarResults
                  ? `${filteredSimilarIds.length} of ${similarResults.length} similar photos`
                  : 'No embedding found'}
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-4 mb-4 sticky top-0 z-10">
          <div className="flex flex-wrap gap-4 items-end">
            {/* Date filters */}
            <div className="flex gap-2 items-end">
              <div>
                <label className="block text-xs text-gray-500 mb-1">From</label>
                <input
                  type="date"
                  value={filters.dateStart || ''}
                  min={dateRange?.minDate?.substring(0, 10) || undefined}
                  max={dateRange?.maxDate?.substring(0, 10) || undefined}
                  onChange={(e) => handleFilterChange('dateStart', e.target.value || undefined)}
                  className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">To</label>
                <input
                  type="date"
                  value={filters.dateEnd || ''}
                  min={dateRange?.minDate?.substring(0, 10) || undefined}
                  max={dateRange?.maxDate?.substring(0, 10) || undefined}
                  onChange={(e) => handleFilterChange('dateEnd', e.target.value || undefined)}
                  className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Place filter */}
            <PlaceTreeSelector
              places={places}
              selectedId={filters.placeId}
              onChange={(id) => handleFilterChange('placeId', id)}
            />

            {/* Person filter */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">Person</label>
              <select
                value={filters.personId || ''}
                onChange={(e) => handleFilterChange('personId', e.target.value || undefined)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-[150px]"
              >
                <option value="">All people</option>
                {persons.map((person) => (
                  <option key={person.id} value={person.id}>
                    {person.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Include low quality */}
            <div className="flex items-center" title="Include duplicates, partial pictures, accidental screenshots and similar pictures">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.includeLowQuality || false}
                  onChange={(e) => handleFilterChange('includeLowQuality', e.target.checked)}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Include low quality</span>
              </label>
            </div>

            {/* Clear filters */}
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900"
              >
                Clear filters
              </button>
            )}

            {/* Photo count */}
            <div className="ml-auto text-sm text-gray-500">
              {totalCount > 0
                ? `${totalCount.toLocaleString()} photos`
                : !loading
                  ? 'No photos found'
                  : null}
            </div>
          </div>
        </div>
      )}

      {error && !isSimilarMode && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-4">
          <p className="text-red-800">Error loading photos: {error.message}</p>
        </div>
      )}

      {/* Photo grid */}
      <div className="flex flex-wrap gap-px justify-center">
        {isSimilarMode
          ? (similarLoading
              ? null
              : filteredSimilarIds.map((id, index) => (
                  <PhotoThumbnail
                    key={id}
                    photoId={id}
                    alt={`Similar photo ${index + 1}`}
                    onClick={() => setViewerIndex(index)}
                  />
                )))
          : photos.map((photo, index) => (
              <PhotoThumbnail
                key={photo.id}
                photoId={photo.id}
                alt={photo.originalFilename}
                onClick={() => setViewerIndex(index)}
              />
            ))}
      </div>

      {viewerIndex !== null && (
        <PhotoViewer
          photoIds={displayPhotoIds}
          currentIndex={viewerIndex}
          onClose={() => setViewerIndex(null)}
          onIndexChange={setViewerIndex}
          onReachEnd={!isSimilarMode && hasMore ? loadMore : undefined}
          onNavigate={onNavigate}
        />
      )}

      {/* Loader / infinite scroll trigger */}
      <div ref={loaderRef} className="py-8 text-center">
        {(loading || similarLoading) && <p className="text-gray-600">Loading...</p>}
        {!isSimilarMode && !loading && !hasMore && photos.length > 0 && (
          <p className="text-gray-400 text-sm">End of photos</p>
        )}
      </div>
    </div>
  );
};
