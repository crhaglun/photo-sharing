using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace PhotoSharing.Api.Entities;

[Table("users")]
public class User
{
    [Key]
    [Column("firebase_uid")]
    [MaxLength(128)]
    public string FirebaseUid { get; set; } = string.Empty;

    [Required]
    [MaxLength(255)]
    [Column("email")]
    public string Email { get; set; } = string.Empty;

    [MaxLength(255)]
    [Column("display_name")]
    public string? DisplayName { get; set; }

    [Column("created_at")]
    public DateTime CreatedAt { get; set; }
}
