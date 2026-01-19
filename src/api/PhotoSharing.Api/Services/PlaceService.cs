using Microsoft.EntityFrameworkCore;
using PhotoSharing.Api.Data;

namespace PhotoSharing.Api.Services;

public class PlaceService : IPlaceService
{
    private readonly PhotoSharingDbContext _context;

    public PlaceService(PhotoSharingDbContext context)
    {
        _context = context;
    }

    public async Task<List<Guid>> GetPlaceWithDescendantsAsync(Guid placeId, CancellationToken cancellationToken = default)
    {
        // Use recursive CTE to get place and all descendants
        var sql = @"
            WITH RECURSIVE place_tree AS (
                SELECT id FROM places WHERE id = {0}
                UNION ALL
                SELECT p.id FROM places p
                INNER JOIN place_tree pt ON p.parent_id = pt.id
            )
            SELECT id FROM place_tree";

        return await _context.Database
            .SqlQueryRaw<Guid>(sql, placeId)
            .ToListAsync(cancellationToken);
    }
}
