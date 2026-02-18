import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '@/services/api';
import { AuthenticatedImage } from './AuthenticatedImage';

const CYCLE_INTERVAL_MS = 8000;

function shuffle<T>(array: T[]): T[] {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

export const StartView = () => {
  const [heroIds, setHeroIds] = useState<string[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [transitioning, setTransitioning] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.getHeroPhotos().then((ids) => {
      if (!cancelled) {
        setHeroIds(shuffle(ids));
        setLoading(false);
      }
    }).catch(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, []);

  const advance = useCallback(() => {
    if (heroIds.length <= 1) return;
    setTransitioning(true);
    setTimeout(() => {
      setCurrentIndex((prev) => (prev + 1) % heroIds.length);
      setTransitioning(false);
    }, 500);
  }, [heroIds.length]);

  useEffect(() => {
    if (heroIds.length <= 1) return;
    timerRef.current = setInterval(advance, CYCLE_INTERVAL_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [advance, heroIds.length]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh] text-gray-400">
        Loading...
      </div>
    );
  }

  if (heroIds.length === 0) {
    return (
      <div className="flex items-center justify-center h-[60vh] text-gray-400 text-lg text-center px-4">
        No photos have been selected for the start page yet.
        <br />
        Open a photo and use the info panel to mark it for the start page.
      </div>
    );
  }

  const currentId = heroIds[currentIndex];

  return (
    <div className="relative w-full h-[calc(100vh-8rem)] bg-black overflow-hidden rounded-lg">
      <div
        className={`absolute inset-0 flex items-center justify-center transition-opacity duration-500 ${
          transitioning ? 'opacity-0' : 'opacity-100'
        }`}
      >
        <AuthenticatedImage
          key={currentId}
          src={api.getDefaultUrl(currentId)}
          alt={`Hero photo ${currentIndex + 1}`}
          className="max-h-full max-w-full object-contain"
        />
      </div>

      {heroIds.length > 1 && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2">
          {heroIds.map((_, i) => (
            <button
              key={i}
              onClick={() => setCurrentIndex(i)}
              className={`w-2 h-2 rounded-full cursor-pointer transition-colors ${
                i === currentIndex ? 'bg-white' : 'bg-white/40'
              }`}
              aria-label={`Go to photo ${i + 1}`}
            />
          ))}
        </div>
      )}
    </div>
  );
};
