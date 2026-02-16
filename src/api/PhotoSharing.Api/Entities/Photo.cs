using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace PhotoSharing.Api.Entities;

public static class PhotoVisibility
{
    public const string Visible = "visible";
    public const string LowQuality = "low_quality";
    public const string Deleted = "deleted";

    public static readonly string[] All = [Visible, LowQuality, Deleted];
}

[Table("photos")]
public class Photo
{
    [Key]
    [Column("id", TypeName = "char(64)")]
    [MaxLength(64)]
    public string Id { get; set; } = string.Empty; // SHA-256 hash

    [Required]
    [MaxLength(255)]
    [Column("original_filename")]
    public string OriginalFilename { get; set; } = string.Empty;

    [Column("date_not_earlier_than")]
    public DateTime? DateNotEarlierThan { get; set; }

    [Column("date_not_later_than")]
    public DateTime? DateNotLaterThan { get; set; }

    [Column("place_id")]
    public Guid? PlaceId { get; set; }

    [Column("width")]
    public int? Width { get; set; }

    [Column("height")]
    public int? Height { get; set; }

    [Column("visibility")]
    [MaxLength(20)]
    public string Visibility { get; set; } = PhotoVisibility.Visible;

    [Column("created_at")]
    public DateTime CreatedAt { get; set; }

    [Column("updated_at")]
    public DateTime UpdatedAt { get; set; }

    // Navigation properties
    [ForeignKey(nameof(PlaceId))]
    public Place? Place { get; set; }

    public ICollection<Face> Faces { get; set; } = new List<Face>();

    public ImageEmbedding? ImageEmbedding { get; set; }

    public ExifMetadata? ExifMetadata { get; set; }

    public ICollection<EditHistory> EditHistory { get; set; } = new List<EditHistory>();
}
