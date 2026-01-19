namespace PhotoSharing.Api.Services;

public interface IPlaceService
{
    Task<List<Guid>> GetPlaceWithDescendantsAsync(Guid placeId, CancellationToken cancellationToken = default);
}
