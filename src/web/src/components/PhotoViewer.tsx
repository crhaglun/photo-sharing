import { useState, useEffect, useCallback } from 'react';
import { api } from '@/services/api';
import { AuthenticatedImage } from './AuthenticatedImage';

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

  return (
    <div className="fixed inset-0 z-50 bg-black flex items-center justify-center">
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute top-4 right-4 z-10 text-white/70 hover:text-white p-2 cursor-pointer"
        aria-label="Close"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

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

      {/* Photo counter */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-white/70 text-sm">
        {index + 1} / {photoIds.length}
      </div>

      {/* Main image */}
      <AuthenticatedImage
        key={currentPhotoId}
        src={api.getDefaultUrl(currentPhotoId)}
        alt={`Photo ${index + 1}`}
        className="max-h-full max-w-full object-contain"
      />
    </div>
  );
};
