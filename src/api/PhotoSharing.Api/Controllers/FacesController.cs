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
        // Load all unassigned clustered faces
        var faces = await _context.Faces
            .Where(f => f.PersonId == null && f.ClusterId != null)
            .ToListAsync(cancellationToken);

        // Group by cluster and order faces by embedding magnitude (quality)
        var clusters = faces
            .GroupBy(f => f.ClusterId!)
            .Select(g => new FaceClusterResponse
            {
                ClusterId = g.Key,
                TotalFaces = g.Count(),
                Faces = OrderFacesByQuality(g).ToList()
            })
            .OrderByDescending(c => c.TotalFaces)
            .ToList();

        return clusters;
    }

    private static IEnumerable<FaceInClusterResponse> OrderFacesByQuality(IEnumerable<Entities.Face> faces)
    {
        // Calculate embedding magnitude for each face and order by quality (highest first)
        return faces
            .Select(f => new
            {
                Face = f,
                Magnitude = CalculateEmbeddingMagnitude(f.Embedding)
            })
            .OrderByDescending(x => x.Magnitude)
            .Select(x => new FaceInClusterResponse
            {
                Id = x.Face.Id,
                PhotoId = x.Face.PhotoId,
                BboxX = x.Face.BboxX,
                BboxY = x.Face.BboxY,
                BboxWidth = x.Face.BboxWidth,
                BboxHeight = x.Face.BboxHeight
            });
    }

    private static double CalculateEmbeddingMagnitude(Pgvector.Vector embedding)
    {
        // L2 norm: sqrt(sum of squares)
        var values = embedding.ToArray();
        return Math.Sqrt(values.Sum(x => x * x));
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
