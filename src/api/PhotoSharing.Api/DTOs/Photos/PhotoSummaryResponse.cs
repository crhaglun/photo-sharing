namespace PhotoSharing.Api.DTOs.Photos;

public class PhotoSummaryResponse
{
    public required string Id { get; init; }
    public required string OriginalFilename { get; init; }
    public DateTime? DateNotEarlierThan { get; init; }
    public DateTime? DateNotLaterThan { get; init; }
    public string? PlaceName { get; init; }
    public bool IsLowQuality { get; init; }
    public int FaceCount { get; init; }
}
