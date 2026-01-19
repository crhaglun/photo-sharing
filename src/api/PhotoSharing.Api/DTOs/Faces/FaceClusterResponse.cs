namespace PhotoSharing.Api.DTOs.Faces;

public class FaceClusterResponse
{
    public required string ClusterId { get; init; }
    public required List<FaceInClusterResponse> Faces { get; init; }
}

public class FaceInClusterResponse
{
    public Guid Id { get; init; }
    public required string PhotoId { get; init; }
    public int BboxX { get; init; }
    public int BboxY { get; init; }
    public int BboxWidth { get; init; }
    public int BboxHeight { get; init; }
}
