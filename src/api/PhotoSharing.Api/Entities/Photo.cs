using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace PhotoSharing.Api.Entities;

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

    [Column("is_low_quality")]
    public bool IsLowQuality { get; set; }

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
