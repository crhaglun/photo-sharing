using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using PhotoSharing.Api.Data;
using PhotoSharing.Api.DTOs.Faces;
using PhotoSharing.Api.Services;

namespace PhotoSharing.Api.Controllers;

[ApiController]
[Authorize]
[Route("faces")]
public class FacesController : ControllerBase
{
    private readonly PhotoSharingDbContext _context;
    private readonly IEditHistoryService _editHistoryService;

    public FacesController(PhotoSharingDbContext context, IEditHistoryService editHistoryService)
    {
        _context = context;
        _editHistoryService = editHistoryService;
    }

    [HttpGet("clusters")]
    public async Task<ActionResult<List<FaceClusterResponse>>> GetClusters(CancellationToken cancellationToken)
    {
        // Get unassigned faces grouped by cluster
        var clusters = await _context.Faces
            .Where(f => f.PersonId == null && f.ClusterId != null)
            .GroupBy(f => f.ClusterId)
            .Select(g => new FaceClusterResponse
            {
                ClusterId = g.Key!,
                Faces = g.Select(f => new FaceInClusterResponse
                {
                    Id = f.Id,
                    PhotoId = f.PhotoId,
                    BboxX = f.BboxX,
                    BboxY = f.BboxY,
                    BboxWidth = f.BboxWidth,
                    BboxHeight = f.BboxHeight
                }).ToList()
            })
            .ToListAsync(cancellationToken);

        return clusters;
    }

    [HttpPatch("{id}")]
    public async Task<IActionResult> AssignPerson(Guid id, [FromBody] FaceAssignRequest request, CancellationToken cancellationToken)
    {
        var face = await _context.Faces.FindAsync([id], cancellationToken);
        if (face == null)
        {
            return NotFound();
        }

        // Validate person exists if assigning
        if (request.PersonId.HasValue)
        {
            var personExists = await _context.Persons.AnyAsync(p => p.Id == request.PersonId.Value, cancellationToken);
            if (!personExists)
            {
                return BadRequest("Person not found");
            }
        }

        // Record edit history
        await _editHistoryService.RecordEditAsync(
            face.PhotoId,
            "face_person",
            face.Id.ToString(),
            face.PersonId?.ToString(),
            request.PersonId?.ToString(),
            cancellationToken);

        face.PersonId = request.PersonId;
        await _context.SaveChangesAsync(cancellationToken);

        return NoContent();
    }
}
