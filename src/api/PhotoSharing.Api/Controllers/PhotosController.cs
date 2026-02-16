using Azure;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using PhotoSharing.Api.Data;
using PhotoSharing.Api.DTOs;
using PhotoSharing.Api.DTOs.Photos;
using PhotoSharing.Api.Services;

namespace PhotoSharing.Api.Controllers;

[ApiController]
[Authorize]
[Route("photos")]
public class PhotosController : ControllerBase
{
    private readonly PhotoSharingDbContext _context;
    private readonly IBlobStorageService _blobService;
    private readonly IEditHistoryService _editHistoryService;
    private readonly IPlaceService _placeService;

    public PhotosController(
        PhotoSharingDbContext context,
        IBlobStorageService blobService,
        IEditHistoryService editHistoryService,
        IPlaceService placeService)
    {
        _context = context;
        _blobService = blobService;
        _editHistoryService = editHistoryService;
        _placeService = placeService;
    }

    [HttpGet]
    public async Task<ActionResult<PagedResponse<PhotoSummaryResponse>>> GetPhotos(
        [FromQuery] PhotoListRequest request,
        CancellationToken cancellationToken)
    {
        var query = _context.Photos
            .Include(p => p.Place)
            .Include(p => p.Faces)
            .AsQueryable();

        // Filter by quality
        if (!request.IncludeLowQuality)
        {
            query = query.Where(p => !p.IsLowQuality);
        }

        // Filter by date range (intersection)
        if (request.DateStart.HasValue)
        {
            query = query.Where(p => p.DateNotLaterThan == null || p.DateNotLaterThan >= request.DateStart.Value);
        }
        if (request.DateEnd.HasValue)
        {
            query = query.Where(p => p.DateNotEarlierThan == null || p.DateNotEarlierThan <= request.DateEnd.Value);
        }

        // Filter by place (including descendants)
        if (request.PlaceId.HasValue)
        {
            var placeIds = await _placeService.GetPlaceWithDescendantsAsync(request.PlaceId.Value, cancellationToken);
            query = query.Where(p => p.PlaceId.HasValue && placeIds.Contains(p.PlaceId.Value));
        }

        // Filter by person (via faces)
        if (request.PersonId.HasValue)
        {
            query = query.Where(p => p.Faces.Any(f => f.PersonId == request.PersonId.Value));
        }

        // Get total count before pagination
        var totalCount = await query.CountAsync(cancellationToken);

        // Apply sorting and pagination
        var photos = await query
            .OrderByDescending(p => p.DateNotEarlierThan ?? DateTime.MinValue)
            .ThenBy(p => p.OriginalFilename)
            .Skip((request.Page - 1) * request.PageSize)
            .Take(request.PageSize)
            .Select(p => new PhotoSummaryResponse
            {
                Id = p.Id,
                OriginalFilename = p.OriginalFilename,
                DateNotEarlierThan = p.DateNotEarlierThan,
                DateNotLaterThan = p.DateNotLaterThan,
                PlaceName = p.Place != null ? p.Place.NameEn : null,
                IsLowQuality = p.IsLowQuality,
                FaceCount = p.Faces.Count
            })
            .ToListAsync(cancellationToken);

        return new PagedResponse<PhotoSummaryResponse>
        {
            Items = photos,
            Page = request.Page,
            PageSize = request.PageSize,
            TotalCount = totalCount
        };
    }

    [HttpGet("{id}")]
    public async Task<ActionResult<PhotoDetailResponse>> GetPhoto(string id, CancellationToken cancellationToken)
    {
        var photo = await _context.Photos
            .Include(p => p.Place)
                .ThenInclude(pl => pl!.Parent)
            .Include(p => p.ExifMetadata)
            .Include(p => p.Faces)
                .ThenInclude(f => f.Person)
            .Include(p => p.EditHistory.OrderByDescending(e => e.ChangedAt))
            .FirstOrDefaultAsync(p => p.Id == id, cancellationToken);

        if (photo == null)
        {
            return NotFound();
        }

        return new PhotoDetailResponse
        {
            Id = photo.Id,
            OriginalFilename = photo.OriginalFilename,
            DateNotEarlierThan = photo.DateNotEarlierThan,
            DateNotLaterThan = photo.DateNotLaterThan,
            IsLowQuality = photo.IsLowQuality,
            CreatedAt = photo.CreatedAt,
            UpdatedAt = photo.UpdatedAt,
            Place = photo.Place != null ? MapPlace(photo.Place) : null,
            Exif = photo.ExifMetadata != null ? new ExifResponse
            {
                CameraMake = photo.ExifMetadata.CameraMake,
                CameraModel = photo.ExifMetadata.CameraModel,
                Lens = photo.ExifMetadata.Lens,
                FocalLength = photo.ExifMetadata.FocalLength,
                Aperture = photo.ExifMetadata.Aperture,
                ShutterSpeed = photo.ExifMetadata.ShutterSpeed,
                Iso = photo.ExifMetadata.Iso,
                TakenAt = photo.ExifMetadata.TakenAt
            } : null,
            Faces = photo.Faces.Select(f => new FaceInPhotoResponse
            {
                Id = f.Id,
                PersonId = f.PersonId,
                PersonName = f.Person?.Name,
                ClusterId = f.ClusterId,
                BboxX = f.BboxX,
                BboxY = f.BboxY,
                BboxWidth = f.BboxWidth,
                BboxHeight = f.BboxHeight
            }).ToList(),
            EditHistory = photo.EditHistory.Select(e => new EditHistoryResponse
            {
                FieldType = e.FieldType,
                FieldKey = e.FieldKey,
                OldValue = e.OldValue,
                NewValue = e.NewValue,
                ChangedBy = e.ChangedBy,
                ChangedAt = e.ChangedAt
            }).ToList()
        };
    }

    [HttpPatch("{id}")]
    public async Task<IActionResult> UpdatePhoto(string id, [FromBody] PhotoUpdateRequest request, CancellationToken cancellationToken)
    {
        var photo = await _context.Photos.FindAsync([id], cancellationToken);
        if (photo == null)
        {
            return NotFound();
        }

        // Track changes for edit history
        if (request.DateNotEarlierThan.HasValue && request.DateNotEarlierThan != photo.DateNotEarlierThan)
        {
            await _editHistoryService.RecordEditAsync(
                id, "date", "date_not_earlier_than",
                photo.DateNotEarlierThan?.ToString("o"),
                request.DateNotEarlierThan.Value.ToString("o"),
                cancellationToken);
            photo.DateNotEarlierThan = request.DateNotEarlierThan.Value;
        }

        if (request.DateNotLaterThan.HasValue && request.DateNotLaterThan != photo.DateNotLaterThan)
        {
            await _editHistoryService.RecordEditAsync(
                id, "date", "date_not_later_than",
                photo.DateNotLaterThan?.ToString("o"),
                request.DateNotLaterThan.Value.ToString("o"),
                cancellationToken);
            photo.DateNotLaterThan = request.DateNotLaterThan.Value;
        }

        if (request.PlaceId.HasValue && request.PlaceId != photo.PlaceId)
        {
            await _editHistoryService.RecordEditAsync(
                id, "place", "place_id",
                photo.PlaceId?.ToString(),
                request.PlaceId.Value.ToString(),
                cancellationToken);
            photo.PlaceId = request.PlaceId.Value;
        }

        if (request.IsLowQuality.HasValue && request.IsLowQuality != photo.IsLowQuality)
        {
            await _editHistoryService.RecordEditAsync(
                id, "quality", "is_low_quality",
                photo.IsLowQuality.ToString(),
                request.IsLowQuality.Value.ToString(),
                cancellationToken);
            photo.IsLowQuality = request.IsLowQuality.Value;
        }

        photo.UpdatedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync(cancellationToken);

        return NoContent();
    }

    [HttpGet("{id}/thumbnail")]
    public async Task<IActionResult> GetThumbnail(string id, CancellationToken cancellationToken)
    {
        try
        {
            var stream = await _blobService.GetBlobAsync(id, BlobType.Thumbnail, cancellationToken);
            // Content-addressed (SHA-256 ID) so immutable - cache for 1 year
            Response.Headers.CacheControl = "public, max-age=31536000, immutable";
            return File(stream, "image/jpeg");
        }
        catch (RequestFailedException ex) when (ex.Status == 404)
        {
            return NotFound();
        }
    }

    [HttpGet("{id}/default")]
    public async Task<IActionResult> GetDefault(string id, CancellationToken cancellationToken)
    {
        try
        {
            var stream = await _blobService.GetBlobAsync(id, BlobType.Default, cancellationToken);
            Response.Headers.CacheControl = "public, max-age=31536000, immutable";
            return File(stream, "image/jpeg");
        }
        catch (RequestFailedException ex) when (ex.Status == 404)
        {
            return NotFound();
        }
    }

    [HttpGet("{id}/original")]
    public async Task<IActionResult> GetOriginal(string id, CancellationToken cancellationToken)
    {
        var photo = await _context.Photos.FindAsync([id], cancellationToken);
        if (photo == null)
        {
            return NotFound();
        }

        try
        {
            var stream = await _blobService.GetBlobAsync(id, BlobType.Original, cancellationToken);
            Response.Headers.CacheControl = "public, max-age=31536000, immutable";
            return File(stream, "image/jpeg", photo.OriginalFilename);
        }
        catch (RequestFailedException ex) when (ex.Status == 404)
        {
            return NotFound();
        }
    }

    [HttpGet("date-range")]
    public async Task<ActionResult<DateRangeResponse>> GetDateRange(CancellationToken cancellationToken)
    {
        var result = await _context.Photos
            .Where(p => p.DateNotEarlierThan != null || p.DateNotLaterThan != null)
            .GroupBy(p => 1)
            .Select(g => new DateRangeResponse
            {
                MinDate = g.Min(p => p.DateNotEarlierThan ?? p.DateNotLaterThan),
                MaxDate = g.Max(p => p.DateNotLaterThan ?? p.DateNotEarlierThan)
            })
            .FirstOrDefaultAsync(cancellationToken);

        return result ?? new DateRangeResponse();
    }

    [HttpGet("{id}/similar")]
    public async Task<ActionResult<List<SimilarPhotoResponse>>> GetSimilar(
        string id,
        [FromQuery] int limit = 20,
        CancellationToken cancellationToken = default)
    {
        // Get the source embedding
        var sourceEmbedding = await _context.ImageEmbeddings
            .Where(e => e.PhotoId == id)
            .Select(e => e.Embedding)
            .FirstOrDefaultAsync(cancellationToken);

        if (sourceEmbedding == null)
        {
            return NotFound("No embedding found for this photo");
        }

        // Use raw SQL for pgvector cosine distance query
        var sql = @"
            SELECT photo_id as ""PhotoId"", embedding <=> {0}::vector(768) AS ""Distance""
            FROM image_embeddings
            WHERE photo_id != {1}
            ORDER BY ""Distance""
            LIMIT {2}";

        var similar = await _context.Database
            .SqlQueryRaw<SimilarPhotoResponse>(sql, sourceEmbedding.ToArray(), id, limit)
            .ToListAsync(cancellationToken);

        return similar;
    }

    private static PlaceResponse MapPlace(Entities.Place place)
    {
        return new PlaceResponse
        {
            Id = place.Id,
            NameSv = place.NameSv,
            NameEn = place.NameEn,
            Type = place.Type,
            Parent = place.Parent != null ? MapPlace(place.Parent) : null
        };
    }
}
