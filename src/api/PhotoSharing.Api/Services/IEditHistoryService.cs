namespace PhotoSharing.Api.Services;

public interface IEditHistoryService
{
    Task RecordEditAsync(
        string photoId,
        string fieldType,
        string fieldKey,
        string? oldValue,
        string? newValue,
        CancellationToken cancellationToken = default);
}
