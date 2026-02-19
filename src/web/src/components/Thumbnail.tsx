import { api } from '@/services/api';

interface ThumbnailProps {
  photoId: string;
  alt: string;
  className?: string;
}

export const Thumbnail = ({ photoId, alt, className }: ThumbnailProps) => {
  return (
    <img
      src={api.getThumbnailUrl(photoId)}
      alt={alt}
      className={className}
      loading="lazy"
    />
  );
};
