using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using PhotoSharing.Api.Data;

namespace PhotoSharing.Api.Controllers;

[ApiController]
[Authorize]
[Route("places")]
public class PlacesController : ControllerBase
{
    private readonly PhotoSharingDbContext _context;

    public PlacesController(PhotoSharingDbContext context)
    {
        _context = context;
    }

    [HttpGet]
    public async Task<ActionResult<List<PlaceDto>>> GetPlaces(CancellationToken cancellationToken)
    {
        var places = await _context.Places
            .OrderBy(p => p.NameEn)
            .Select(p => new PlaceDto
            {
                Id = p.Id,
                NameSv = p.NameSv,
                NameEn = p.NameEn,
                Type = p.Type,
                ParentId = p.ParentId
            })
            .ToListAsync(cancellationToken);

        return places;
    }
}

public class PlaceDto
{
    public Guid Id { get; init; }
    public required string NameSv { get; init; }
    public required string NameEn { get; init; }
    public required string Type { get; init; }
    public Guid? ParentId { get; init; }
}
