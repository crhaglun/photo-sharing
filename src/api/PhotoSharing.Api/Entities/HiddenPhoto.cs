using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace PhotoSharing.Api.Entities;

[Table("hidden_photos")]
public class HiddenPhoto
{
    [Column("photo_id", TypeName = "char(64)")]
    [MaxLength(64)]
    public string PhotoId { get; set; } = string.Empty;

    [Column("user_id")]
    [MaxLength(128)]
    public string UserId { get; set; } = string.Empty;

    [Column("hidden_at")]
    public DateTime HiddenAt { get; set; }

    // Navigation properties
    [ForeignKey(nameof(PhotoId))]
    public Photo Photo { get; set; } = null!;

    [ForeignKey(nameof(UserId))]
    public User User { get; set; } = null!;
}
