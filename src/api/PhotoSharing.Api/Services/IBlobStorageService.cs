namespace PhotoSharing.Api.Services;

public enum BlobType
{
    Original,
    Thumbnail,
    Default
}

public interface IBlobStorageService
{
    Task<Stream> GetBlobAsync(string photoId, BlobType type, CancellationToken cancellationToken = default);
    Task<bool> ExistsAsync(string photoId, BlobType type, CancellationToken cancellationToken = default);
}
