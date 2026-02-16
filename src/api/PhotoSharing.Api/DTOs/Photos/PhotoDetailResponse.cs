namespace PhotoSharing.Api.DTOs.Photos;

public class PhotoDetailResponse
{
    public required string Id { get; init; }
    public required string OriginalFilename { get; init; }
    public DateTime? DateNotEarlierThan { get; init; }
    public DateTime? DateNotLaterThan { get; init; }
    public int? Width { get; init; }
    public int? Height { get; init; }
    public required string Visibility { get; init; }
    public DateTime CreatedAt { get; init; }
    public DateTime UpdatedAt { get; init; }
    public PlaceResponse? Place { get; init; }
    public ExifResponse? Exif { get; init; }
    public required List<FaceInPhotoResponse> Faces { get; init; }
    public required List<EditHistoryResponse> EditHistory { get; init; }
}

public class PlaceResponse
{
    public Guid Id { get; init; }
    public required string NameSv { get; init; }
    public required string NameEn { get; init; }
    public required string Type { get; init; }
    public PlaceResponse? Parent { get; init; }
}

public class ExifResponse
{
    public string? CameraMake { get; init; }
    public string? CameraModel { get; init; }
    public string? Lens { get; init; }
    public string? FocalLength { get; init; }
    public string? Aperture { get; init; }
    public string? ShutterSpeed { get; init; }
    public int? Iso { get; init; }
    public DateTime? TakenAt { get; init; }
}

public class FaceInPhotoResponse
{
    public Guid Id { get; init; }
    public Guid? PersonId { get; init; }
    public string? PersonName { get; init; }
    public string? ClusterId { get; init; }
    public int BboxX { get; init; }
    public int BboxY { get; init; }
    public int BboxWidth { get; init; }
    public int BboxHeight { get; init; }
}

public class EditHistoryResponse
{
    public required string FieldType { get; init; }
    public required string FieldKey { get; init; }
    public string? OldValue { get; init; }
    public string? NewValue { get; init; }
    public required string ChangedBy { get; init; }
    public DateTime ChangedAt { get; init; }
}
