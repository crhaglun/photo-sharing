import { useEffect, useRef, useCallback, useState, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { usePhotos } from '@/hooks/useApi';
import { api } from '@/services/api';
import { PlaceTreeSelector } from './PlaceTreeSelector';
import { PhotoThumbnail } from './PhotoThumbnail';
import { PhotoViewer } from './PhotoViewer';
import { AuthenticatedImage } from './AuthenticatedImage';
import type { PersonResponse, Place, DateRange, SimilarPhotoResponse } from '@/types/api';

export const LibraryView = () => {
  const { photos, loading, error, hasMore, totalCount, fetchPhotos, loadMore } = usePhotos();
  const loaderRef = useRef<HTMLDivElement>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // Derive state from URL search params
  const dateStart = searchParams.get('dateStart') || undefined;
  const dateEnd = searchParams.get('dateEnd') || undefined;
  const placeId = searchParams.get('placeId') || undefined;
  const personId = searchParams.get('personId') || undefined;
  const includeLowQuality = searchParams.get('lowQuality') === '1';
  const similarToId = searchParams.get('similar') || undefined;
  const activePhotoId = searchParams.get('photo') || undefined;

  const filters = useMemo(() => {
    const f: Record<string, string | boolean> = {};
    if (dateStart) f.dateStart = dateStart;
    if (dateEnd) f.dateEnd = dateEnd;
    if (placeId) f.placeId = placeId;
    if (personId) f.personId = personId;
    if (includeLowQuality) f.includeLowQuality = true;
    return f;
  }, [dateStart, dateEnd, placeId, personId, includeLowQuality]);

  // Filter option data
  const [persons, setPersons] = useState<PersonResponse[]>([]);
  const [places, setPlaces] = useState<Place[]>([]);
  const [dateRange, setDateRange] = useState<DateRange | null>(null);

  // Similar mode state
  const [similarResults, setSimilarResults] = useState<SimilarPhotoResponse[] | null>(null);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [similarSourceName, setSimilarSourceName] = useState<string | null>(null);
  const [maxDistance, setMaxDistance] = useState(1.0);
  const isSimilarMode = similarToId != null;

  // Fetch similar photos when in similar mode
  useEffect(() => {
    if (!similarToId) return;
    let cancelled = false;
    setSimilarLoading(true);

    Promise.all([
      api.getSimilarPhotos(similarToId),
      api.getPhoto(similarToId),
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
  }, [similarToId]);

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

  const handleFilterChange = (key: string, value: string | boolean | undefined) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (key === 'includeLowQuality') {
        if (value) {
          next.set('lowQuality', '1');
        } else {
          next.delete('lowQuality');
        }
      } else if (value !== undefined && value !== false && value !== '') {
        next.set(key, String(value));
      } else {
        next.delete(key);
      }
      // Remove photo param when filters change
      next.delete('photo');
      return next;
    }, { replace: true });
  };

  const clearFilters = () => {
    setSearchParams({}, { replace: true });
  };

  const hasActiveFilters = dateStart || dateEnd || placeId || personId || includeLowQuality;

  // Which photo IDs to display
  const displayPhotoIds = isSimilarMode ? filteredSimilarIds : photos.map((p) => p.id);

  // Determine viewer index from photo param
  const viewerIndex = useMemo(() => {
    if (!activePhotoId) return null;
    const idx = displayPhotoIds.indexOf(activePhotoId);
    if (idx !== -1) return idx;
    // Photo not in loaded results — show standalone
    if (displayPhotoIds.length > 0) return null; // Results loaded but photo not found — don't force open
    return 0; // Results still loading, we'll show standalone
  }, [activePhotoId, displayPhotoIds]);

  // Build the photo list for the viewer — if the target photo is not in results, show standalone
  const viewerPhotoIds = useMemo(() => {
    if (!activePhotoId) return displayPhotoIds;
    if (displayPhotoIds.includes(activePhotoId)) return displayPhotoIds;
    // Standalone mode: just the one photo
    return [activePhotoId];
  }, [activePhotoId, displayPhotoIds]);

  const openViewer = (photoId: string) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set('photo', photoId);
      return next;
    });
  };

  const closeViewer = () => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete('photo');
      return next;
    });
  };

  const handlePhotoChange = useCallback((photoId: string) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set('photo', photoId);
      return next;
    }, { replace: true });
  }, [setSearchParams]);

  const handleNavigateToPerson = useCallback((pid: string) => {
    navigate(`/?personId=${encodeURIComponent(pid)}`);
  }, [navigate]);

  const handleNavigateToSimilar = useCallback((photoId: string) => {
    navigate(`/?similar=${encodeURIComponent(photoId)}`);
  }, [navigate]);

  const handleNavigateToCluster = useCallback((clusterId: string) => {
    navigate(`/faces?cluster=${encodeURIComponent(clusterId)}`);
  }, [navigate]);

  return (
    <div>
      {/* Filter pane */}
      {isSimilarMode ? (
        <div className="bg-white rounded-lg shadow p-4 mb-4 sticky top-0 z-10">
          <div className="flex flex-wrap gap-4 items-center">
            {/* Source thumbnail */}
            <div className="w-12 h-12 rounded overflow-hidden flex-shrink-0">
              <AuthenticatedImage
                src={api.getThumbnailUrl(similarToId!)}
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
              onClick={() => navigate('/')}
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
                  value={dateStart || ''}
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
                  value={dateEnd || ''}
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
              selectedId={placeId}
              onChange={(id) => handleFilterChange('placeId', id)}
            />

            {/* Person filter */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">Person</label>
              <select
                value={personId || ''}
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
                  checked={includeLowQuality}
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
                    onClick={() => openViewer(id)}
                  />
                )))
          : photos.map((photo) => (
              <PhotoThumbnail
                key={photo.id}
                photoId={photo.id}
                alt={photo.originalFilename}
                onClick={() => openViewer(photo.id)}
              />
            ))}
      </div>

      {activePhotoId && viewerIndex !== null && (
        <PhotoViewer
          photoIds={viewerPhotoIds}
          currentIndex={viewerIndex}
          onClose={closeViewer}
          onIndexChange={(i) => handlePhotoChange(viewerPhotoIds[i])}
          onReachEnd={!isSimilarMode && hasMore ? loadMore : undefined}
          onPhotoChange={handlePhotoChange}
          onNavigateToPerson={handleNavigateToPerson}
          onNavigateToSimilar={handleNavigateToSimilar}
          onNavigateToCluster={handleNavigateToCluster}
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
