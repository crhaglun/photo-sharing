namespace PhotoSharing.Api.DTOs.Persons;

public class PersonResponse
{
    public Guid Id { get; init; }
    public required string Name { get; init; }
    public int FaceCount { get; init; }
    public DateTime CreatedAt { get; init; }
}
