using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Pgvector;

namespace PhotoSharing.Api.Entities;

[Table("image_embeddings")]
public class ImageEmbedding
{
    [Key]
    [Column("photo_id", TypeName = "char(64)")]
    [MaxLength(64)]
    public string PhotoId { get; set; } = string.Empty;

    [Required]
    [Column("embedding", TypeName = "vector(768)")]
    public Vector Embedding { get; set; } = null!;

    // Navigation property
    [ForeignKey(nameof(PhotoId))]
    public Photo Photo { get; set; } = null!;
}
