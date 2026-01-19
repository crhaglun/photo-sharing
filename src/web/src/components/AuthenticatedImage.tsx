import { useState, useEffect } from 'react';
import { getIdToken } from '@/services/firebase';

interface AuthenticatedImageProps {
  src: string;
  alt: string;
  className?: string;
  loading?: 'lazy' | 'eager';
}

export const AuthenticatedImage = ({ src, alt, className, loading }: AuthenticatedImageProps) => {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const fetchImage = async () => {
      try {
        const token = await getIdToken();
        const response = await fetch(src, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });

        if (!response.ok) {
          throw new Error('Failed to load image');
        }

        const blob = await response.blob();
        if (!cancelled) {
          const url = URL.createObjectURL(blob);
          setBlobUrl(url);
        }
      } catch {
        if (!cancelled) {
          setError(true);
        }
      }
    };

    fetchImage();

    return () => {
      cancelled = true;
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
      }
    };
  }, [src]);

  if (error) {
    return <div className={className} style={{ background: '#e5e7eb' }} />;
  }

  if (!blobUrl) {
    return <div className={className} style={{ background: '#e5e7eb' }} />;
  }

  return <img src={blobUrl} alt={alt} className={className} loading={loading} />;
};
