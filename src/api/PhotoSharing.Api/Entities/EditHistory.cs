using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace PhotoSharing.Api.Entities;

[Table("edit_history")]
public class EditHistory
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Required]
    [Column("photo_id", TypeName = "char(64)")]
    [MaxLength(64)]
    public string PhotoId { get; set; } = string.Empty;

    [Required]
    [MaxLength(20)]
    [Column("field_type")]
    public string FieldType { get; set; } = string.Empty; // face_person, place, date, quality

    [Required]
    [MaxLength(100)]
    [Column("field_key")]
    public string FieldKey { get; set; } = string.Empty;

    [Column("old_value")]
    public string? OldValue { get; set; }

    [Column("new_value")]
    public string? NewValue { get; set; }

    [Required]
    [MaxLength(255)]
    [Column("changed_by")]
    public string ChangedBy { get; set; } = string.Empty; // Firebase UID

    [Column("changed_at")]
    public DateTime ChangedAt { get; set; }

    // Navigation property
    [ForeignKey(nameof(PhotoId))]
    public Photo Photo { get; set; } = null!;
}
