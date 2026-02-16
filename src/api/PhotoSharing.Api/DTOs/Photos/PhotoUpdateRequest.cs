namespace PhotoSharing.Api.DTOs.Photos;

public class PhotoUpdateRequest
{
    public DateTime? DateNotEarlierThan { get; set; }
    public DateTime? DateNotLaterThan { get; set; }
    public Guid? PlaceId { get; set; }
    public string? Visibility { get; set; }
}
