import { Thumbnail } from './Thumbnail';

interface PhotoThumbnailProps {
  photoId: string;
  alt: string;
  size?: number;
  onClick?: () => void;
}

export const PhotoThumbnail = ({ photoId, alt, size = 100, onClick }: PhotoThumbnailProps) => {
  return (
    <div
      style={{ width: size, height: size }}
      className="bg-gray-200 rounded overflow-hidden cursor-pointer transition-transform hover:scale-105"
      onClick={onClick}
    >
      <Thumbnail photoId={photoId} alt={alt} className="w-full h-full object-cover" />
    </div>
  );
};
