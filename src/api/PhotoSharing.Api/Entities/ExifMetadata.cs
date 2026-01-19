using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace PhotoSharing.Api.Entities;

[Table("exif_metadata")]
public class ExifMetadata
{
    [Key]
    [Column("photo_id", TypeName = "char(64)")]
    [MaxLength(64)]
    public string PhotoId { get; set; } = string.Empty;

    [MaxLength(100)]
    [Column("camera_make")]
    public string? CameraMake { get; set; }

    [MaxLength(100)]
    [Column("camera_model")]
    public string? CameraModel { get; set; }

    [MaxLength(100)]
    [Column("lens")]
    public string? Lens { get; set; }

    [MaxLength(20)]
    [Column("focal_length")]
    public string? FocalLength { get; set; }

    [MaxLength(20)]
    [Column("aperture")]
    public string? Aperture { get; set; }

    [MaxLength(20)]
    [Column("shutter_speed")]
    public string? ShutterSpeed { get; set; }

    [Column("iso")]
    public int? Iso { get; set; }

    [Column("taken_at")]
    public DateTime? TakenAt { get; set; }

    [Column("raw_exif", TypeName = "jsonb")]
    public string? RawExif { get; set; }

    // Navigation property
    [ForeignKey(nameof(PhotoId))]
    public Photo Photo { get; set; } = null!;
}
