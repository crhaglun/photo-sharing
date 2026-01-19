using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace PhotoSharing.Api.Entities;

[Table("places")]
public class Place
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Required]
    [MaxLength(255)]
    [Column("name_sv")]
    public string NameSv { get; set; } = string.Empty;

    [Required]
    [MaxLength(255)]
    [Column("name_en")]
    public string NameEn { get; set; } = string.Empty;

    [Column("parent_id")]
    public Guid? ParentId { get; set; }

    [Required]
    [MaxLength(20)]
    [Column("type")]
    public string Type { get; set; } = string.Empty; // country, state, city, street

    // Navigation properties
    [ForeignKey(nameof(ParentId))]
    public Place? Parent { get; set; }

    public ICollection<Place> Children { get; set; } = new List<Place>();

    public ICollection<Photo> Photos { get; set; } = new List<Photo>();
}
