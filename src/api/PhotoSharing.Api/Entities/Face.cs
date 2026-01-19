using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Pgvector;

namespace PhotoSharing.Api.Entities;

[Table("faces")]
public class Face
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Required]
    [Column("photo_id", TypeName = "char(64)")]
    [MaxLength(64)]
    public string PhotoId { get; set; } = string.Empty;

    [Column("person_id")]
    public Guid? PersonId { get; set; }

    [Column("bbox_x")]
    public int BboxX { get; set; }

    [Column("bbox_y")]
    public int BboxY { get; set; }

    [Column("bbox_width")]
    public int BboxWidth { get; set; }

    [Column("bbox_height")]
    public int BboxHeight { get; set; }

    [Required]
    [Column("embedding", TypeName = "vector(512)")]
    public Vector Embedding { get; set; } = null!;

    [MaxLength(100)]
    [Column("cluster_id")]
    public string? ClusterId { get; set; }

    // Navigation properties
    [ForeignKey(nameof(PhotoId))]
    public Photo Photo { get; set; } = null!;

    [ForeignKey(nameof(PersonId))]
    public Person? Person { get; set; }
}
