namespace PhotoSharing.Api.DTOs.Photos;

public class SimilarPhotoResponse
{
    public required string PhotoId { get; init; }
    public double Distance { get; init; }
}
