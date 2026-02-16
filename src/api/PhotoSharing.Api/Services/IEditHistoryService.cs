namespace PhotoSharing.Api.Services;

public interface IEditHistoryService
{
    Task RecordEditAsync(
        string photoId,
        string fieldType,
        string fieldKey,
        string? oldValue,
        string? newValue,
        string changedBy,
        CancellationToken cancellationToken = default);
}
