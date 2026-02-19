import { api } from '@/services/api';
import { AuthenticatedImage } from './AuthenticatedImage';

interface DefaultImageProps {
  photoId: string;
  alt: string;
  className?: string;
}

export const DefaultImage = ({ photoId, alt, className }: DefaultImageProps) => {
  return (
    <AuthenticatedImage
      src={api.getDefaultUrl(photoId)}
      alt={alt}
      className={className}
    />
  );
};
