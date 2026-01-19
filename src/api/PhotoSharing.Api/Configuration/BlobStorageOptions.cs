namespace PhotoSharing.Api.Configuration;

public class BlobStorageOptions
{
    public const string SectionName = "BlobStorage";

    public string StorageAccountName { get; set; } = string.Empty;
    public string OriginalsContainer { get; set; } = "originals";
    public string ThumbnailsContainer { get; set; } = "thumbnails";
    public string DefaultContainer { get; set; } = "default";
}
