import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { api } from '@/services/api';
import { AuthenticatedImage } from './AuthenticatedImage';
import type { PhotoDetail, PlaceResponse, FaceInPhotoResponse } from '@/types/api';

const FILMSTRIP_RADIUS = 3;

interface PhotoViewerProps {
  photoIds: string[];
  currentIndex: number;
  onClose: () => void;
  onIndexChange: (index: number) => void;
  onReachEnd?: () => void;
}

export const PhotoViewer = ({ photoIds, currentIndex, onClose, onIndexChange, onReachEnd }: PhotoViewerProps) => {
  const [index, setIndex] = useState(currentIndex);

  useEffect(() => {
    setIndex(currentIndex);
  }, [currentIndex]);

  const canGoPrev = index > 0;
  const canGoNext = index < photoIds.length - 1;

  const goNext = useCallback(() => {
    if (canGoNext) {
      const newIndex = index + 1;
      setIndex(newIndex);
      onIndexChange(newIndex);
      if (newIndex >= photoIds.length - 3 && onReachEnd) {
        onReachEnd();
      }
    }
  }, [index, canGoNext, photoIds.length, onIndexChange, onReachEnd]);

  const goPrev = useCallback(() => {
    if (canGoPrev) {
      const newIndex = index - 1;
      setIndex(newIndex);
      onIndexChange(newIndex);
    }
  }, [index, canGoPrev, onIndexChange]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'Escape': onClose(); break;
        case 'ArrowLeft': goPrev(); break;
        case 'ArrowRight': goNext(); break;
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose, goPrev, goNext]);

  // Prevent body scroll while viewer is open
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);

  const currentPhotoId = photoIds[index];

  // Metadata pane
  const [showInfo, setShowInfo] = useState(false);
  const [detail, setDetail] = useState<PhotoDetail | null>(null);

  useEffect(() => {
    if (!showInfo) return;
    let cancelled = false;
    setDetail(null);
    api.getPhoto(currentPhotoId).then((d) => {
      if (!cancelled) setDetail(d);
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [showInfo, currentPhotoId]);

  // Face bbox hover
  const [hoveredFaceId, setHoveredFaceId] = useState<string | null>(null);
  const imageAreaRef = useRef<HTMLDivElement>(null);
  const hoveredFace = detail?.faces.find((f) => f.id === hoveredFaceId) ?? null;

  const getBboxStyle = useCallback(
    (face: FaceInPhotoResponse): React.CSSProperties | null => {
      if (!detail?.width || !detail?.height || !imageAreaRef.current) return null;
      const img = imageAreaRef.current.querySelector('img');
      if (!img) return null;

      const containerRect = imageAreaRef.current.getBoundingClientRect();
      const imgRect = img.getBoundingClientRect();
      const offsetX = imgRect.left - containerRect.left;
      const offsetY = imgRect.top - containerRect.top;
      const scaleX = imgRect.width / detail.width;
      const scaleY = imgRect.height / detail.height;

      return {
        left: offsetX + face.bboxX * scaleX,
        top: offsetY + face.bboxY * scaleY,
        width: face.bboxWidth * scaleX,
        height: face.bboxHeight * scaleY,
      };
    },
    [detail]
  );

  const filmstripIndices = useMemo(() => {
    const start = Math.max(0, index - FILMSTRIP_RADIUS);
    const end = Math.min(photoIds.length - 1, index + FILMSTRIP_RADIUS);
    const indices: number[] = [];
    for (let i = start; i <= end; i++) indices.push(i);
    return indices;
  }, [index, photoIds.length]);

  const goTo = useCallback((i: number) => {
    setIndex(i);
    onIndexChange(i);
    if (i >= photoIds.length - 3 && onReachEnd) {
      onReachEnd();
    }
  }, [photoIds.length, onIndexChange, onReachEnd]);

  return (
    <div className="fixed inset-0 z-50 bg-black flex flex-col">
      {/* Top-right controls */}
      <div className="absolute top-4 right-4 z-10 flex gap-2">
        <button
          onClick={() => setShowInfo((v) => !v)}
          className={`p-2 cursor-pointer ${showInfo ? 'text-white' : 'text-white/70 hover:text-white'}`}
          aria-label="Toggle info"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <circle cx="12" cy="12" r="10" />
            <path strokeLinecap="round" d="M12 16v-4M12 8h.01" />
          </svg>
        </button>
        <button
          onClick={onClose}
          className="text-white/70 hover:text-white p-2 cursor-pointer"
          aria-label="Close"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Main image area */}
      <div ref={imageAreaRef} className="flex-1 min-h-0 flex items-center justify-center relative">
        {/* Previous button */}
        {canGoPrev && (
          <button
            onClick={goPrev}
            className="absolute left-4 top-1/2 -translate-y-1/2 z-10 text-white/70 hover:text-white p-2 cursor-pointer"
            aria-label="Previous photo"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
        )}

        {/* Next button */}
        {canGoNext && (
          <button
            onClick={goNext}
            className="absolute right-4 top-1/2 -translate-y-1/2 z-10 text-white/70 hover:text-white p-2 cursor-pointer"
            aria-label="Next photo"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        )}

        <AuthenticatedImage
          key={currentPhotoId}
          src={api.getDefaultUrl(currentPhotoId)}
          alt={`Photo ${index + 1}`}
          className="max-h-full max-w-full object-contain"
        />

        {/* Face bounding box overlay */}
        {hoveredFace && (() => {
          const style = getBboxStyle(hoveredFace);
          if (!style) return null;
          return (
            <div
              className="absolute border-2 border-yellow-400 rounded-sm pointer-events-none"
              style={style}
            />
          );
        })()}
      </div>

      {/* Metadata overlay */}
      {showInfo && (
        <div className="absolute bottom-20 left-4 z-10 bg-black/70 rounded-lg px-4 py-3 text-white/70 text-xs leading-relaxed max-w-[300px]">
          {detail ? (
            <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5">
              {detail.originalFilename && (
                <><dt className="text-white/40">File</dt><dd>{detail.originalFilename}</dd></>
              )}
              {detail.exif?.takenAt && (
                <><dt className="text-white/40">Date</dt><dd>{new Date(detail.exif.takenAt).toLocaleDateString()}</dd></>
              )}
              {detail.place && (
                <><dt className="text-white/40">Place</dt><dd>{formatPlace(detail.place)}</dd></>
              )}
              {(detail.exif?.cameraMake || detail.exif?.cameraModel) && (
                <><dt className="text-white/40">Camera</dt><dd>{[detail.exif.cameraMake, detail.exif.cameraModel].filter(Boolean).join(' ')}</dd></>
              )}
              {detail.exif?.lens && (
                <><dt className="text-white/40">Lens</dt><dd>{detail.exif.lens}</dd></>
              )}
              {(detail.exif?.focalLength || detail.exif?.aperture || detail.exif?.shutterSpeed || detail.exif?.iso) && (
                <><dt className="text-white/40">Settings</dt><dd>{[detail.exif.focalLength, detail.exif.aperture, detail.exif.shutterSpeed, detail.exif.iso ? `ISO ${detail.exif.iso}` : null].filter(Boolean).join('  ')}</dd></>
              )}
              {detail.faces.length > 0 && (
                <><dt className="text-white/40">People</dt><dd>{detail.faces.map((f, i) => (
                  <span key={f.id}>
                    {i > 0 && ', '}
                    <span
                      className="cursor-default hover:text-white transition-colors"
                      onMouseEnter={() => setHoveredFaceId(f.id)}
                      onMouseLeave={() => setHoveredFaceId(null)}
                    >
                      {f.personName || f.clusterId || '?'}
                    </span>
                  </span>
                ))}</dd></>
              )}
            </dl>
          ) : (
            <span className="text-white/40">Loading...</span>
          )}
        </div>
      )}

      {/* Filmstrip */}
      <div className="flex items-center justify-center gap-1 py-2 bg-black/80">
        <span className="text-white/50 text-xs mr-2">
          {index + 1} / {photoIds.length}
        </span>
        {filmstripIndices.map((i) => (
          <button
            key={photoIds[i]}
            onClick={() => goTo(i)}
            className={`w-[60px] h-[60px] rounded overflow-hidden cursor-pointer flex-shrink-0 transition-opacity ${
              i === index ? 'ring-2 ring-white opacity-100' : 'opacity-50 hover:opacity-80'
            }`}
          >
            <AuthenticatedImage
              src={api.getThumbnailUrl(photoIds[i])}
              alt={`Thumbnail ${i + 1}`}
              className="w-full h-full object-cover"
            />
          </button>
        ))}
      </div>
    </div>
  );
};

function formatPlace(place: PlaceResponse): string {
  const parts: string[] = [place.nameEn];
  let current: PlaceResponse | null = place.parent;
  while (current) {
    parts.push(current.nameEn);
    current = current.parent;
  }
  return parts.join(', ');
}
