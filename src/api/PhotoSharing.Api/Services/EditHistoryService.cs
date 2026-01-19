using PhotoSharing.Api.Data;
using PhotoSharing.Api.Entities;

namespace PhotoSharing.Api.Services;

public class EditHistoryService : IEditHistoryService
{
    private readonly PhotoSharingDbContext _context;

    public EditHistoryService(PhotoSharingDbContext context)
    {
        _context = context;
    }

    public async Task RecordEditAsync(
        string photoId,
        string fieldType,
        string fieldKey,
        string? oldValue,
        string? newValue,
        CancellationToken cancellationToken = default)
    {
        var entry = new EditHistory
        {
            Id = Guid.NewGuid(),
            PhotoId = photoId,
            FieldType = fieldType,
            FieldKey = fieldKey,
            OldValue = oldValue,
            NewValue = newValue,
            ChangedBy = "system", // TODO: Replace with Firebase UID when auth is added
            ChangedAt = DateTime.UtcNow
        };

        _context.EditHistory.Add(entry);
        await _context.SaveChangesAsync(cancellationToken);
    }
}
