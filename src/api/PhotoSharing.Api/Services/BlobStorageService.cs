using Azure.Identity;
using Azure.Storage.Blobs;
using Microsoft.Extensions.Options;
using PhotoSharing.Api.Configuration;

namespace PhotoSharing.Api.Services;

public class BlobStorageService : IBlobStorageService
{
    private readonly BlobServiceClient _blobServiceClient;
    private readonly BlobStorageOptions _options;

    public BlobStorageService(IOptions<BlobStorageOptions> options)
    {
        _options = options.Value;
        var credential = new DefaultAzureCredential();
        var serviceUri = new Uri($"https://{_options.StorageAccountName}.blob.core.windows.net");
        _blobServiceClient = new BlobServiceClient(serviceUri, credential);
    }

    public async Task<Stream> GetBlobAsync(string photoId, BlobType type, CancellationToken cancellationToken = default)
    {
        var containerName = GetContainerName(type);
        var containerClient = _blobServiceClient.GetBlobContainerClient(containerName);
        var blobClient = containerClient.GetBlobClient(photoId);

        return await blobClient.OpenReadAsync(cancellationToken: cancellationToken);
    }

    public async Task<bool> ExistsAsync(string photoId, BlobType type, CancellationToken cancellationToken = default)
    {
        var containerName = GetContainerName(type);
        var containerClient = _blobServiceClient.GetBlobContainerClient(containerName);
        var blobClient = containerClient.GetBlobClient(photoId);

        return await blobClient.ExistsAsync(cancellationToken);
    }

    private string GetContainerName(BlobType type) => type switch
    {
        BlobType.Original => _options.OriginalsContainer,
        BlobType.Thumbnail => _options.ThumbnailsContainer,
        BlobType.Default => _options.DefaultContainer,
        _ => throw new ArgumentOutOfRangeException(nameof(type))
    };
}
