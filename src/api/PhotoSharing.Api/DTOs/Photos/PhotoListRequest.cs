namespace PhotoSharing.Api.DTOs.Photos;

public class PhotoListRequest
{
    public DateTime? DateStart { get; set; }
    public DateTime? DateEnd { get; set; }
    public Guid? PlaceId { get; set; }
    public Guid? PersonId { get; set; }
    public bool IncludeLowQuality { get; set; } = false;
    public int Page { get; set; } = 1;
    public int PageSize { get; set; } = 50;
}
