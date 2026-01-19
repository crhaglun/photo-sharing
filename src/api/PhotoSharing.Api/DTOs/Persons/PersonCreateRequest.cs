using System.ComponentModel.DataAnnotations;

namespace PhotoSharing.Api.DTOs.Persons;

public class PersonCreateRequest
{
    [Required]
    [MaxLength(255)]
    public required string Name { get; set; }
}
