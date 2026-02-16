import { useEffect, useRef, useCallback, useState } from 'react';
import { usePhotos } from '@/hooks/useApi';
import { api } from '@/services/api';
import { PlaceTreeSelector } from './PlaceTreeSelector';
import { PhotoThumbnail } from './PhotoThumbnail';
import { PhotoViewer } from './PhotoViewer';
import type { PersonResponse, Place, PhotoListParams, DateRange } from '@/types/api';

export const LibraryView = () => {
  const { photos, loading, error, hasMore, totalCount, fetchPhotos, loadMore } = usePhotos();
  const loaderRef = useRef<HTMLDivElement>(null);

  // Filter state
  const [persons, setPersons] = useState<PersonResponse[]>([]);
  const [places, setPlaces] = useState<Place[]>([]);
  const [dateRange, setDateRange] = useState<DateRange | null>(null);
  const [filters, setFilters] = useState<Omit<PhotoListParams, 'page' | 'pageSize'>>({});
  const [viewerIndex, setViewerIndex] = useState<number | null>(null);

  // Load filter options on mount
  useEffect(() => {
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
  }, []);

  // Fetch photos when filters change
  useEffect(() => {
    fetchPhotos(filters);
  }, [fetchPhotos, filters]);

  // Infinite scroll
  const handleObserver = useCallback(
    (entries: IntersectionObserverEntry[]) => {
      const [entry] = entries;
      if (entry.isIntersecting && hasMore && !loading) {
        loadMore();
      }
    },
    [hasMore, loading, loadMore]
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

  return (
    <div>
      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-4">
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
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-4">
          <p className="text-red-800">Error loading photos: {error.message}</p>
        </div>
      )}

      {totalCount > 0 && (
        <p className="text-sm text-gray-600 mb-4">
          {photos.length} of {totalCount} photos
        </p>
      )}

      {!loading && totalCount === 0 && (
        <p className="text-sm text-gray-600 mb-4">No photos found</p>
      )}

      {/* Photo grid */}
      <div className="flex flex-wrap gap-px justify-center">
        {photos.map((photo, index) => (
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
          photoIds={photos.map((p) => p.id)}
          currentIndex={viewerIndex}
          onClose={() => setViewerIndex(null)}
          onIndexChange={setViewerIndex}
          onReachEnd={hasMore ? loadMore : undefined}
        />
      )}

      {/* Loader / infinite scroll trigger */}
      <div ref={loaderRef} className="py-8 text-center">
        {loading && <p className="text-gray-600">Loading...</p>}
        {!loading && !hasMore && photos.length > 0 && (
          <p className="text-gray-400 text-sm">End of photos</p>
        )}
      </div>
    </div>
  );
};
