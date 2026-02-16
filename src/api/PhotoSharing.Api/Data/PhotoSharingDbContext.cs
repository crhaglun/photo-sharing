using Microsoft.EntityFrameworkCore;
using PhotoSharing.Api.Entities;

namespace PhotoSharing.Api.Data;

public class PhotoSharingDbContext : DbContext
{
    public PhotoSharingDbContext(DbContextOptions<PhotoSharingDbContext> options)
        : base(options)
    {
    }

    public DbSet<Photo> Photos => Set<Photo>();
    public DbSet<Place> Places => Set<Place>();
    public DbSet<Person> Persons => Set<Person>();
    public DbSet<Face> Faces => Set<Face>();
    public DbSet<ImageEmbedding> ImageEmbeddings => Set<ImageEmbedding>();
    public DbSet<ExifMetadata> ExifMetadata => Set<ExifMetadata>();
    public DbSet<EditHistory> EditHistory => Set<EditHistory>();
    public DbSet<User> Users => Set<User>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // Enable pgvector extension
        modelBuilder.HasPostgresExtension("vector");
        modelBuilder.HasPostgresExtension("uuid-ossp");

        // Photo configuration
        modelBuilder.Entity<Photo>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id).HasColumnType("char(64)").IsFixedLength();

            entity.HasIndex(e => new { e.DateNotEarlierThan, e.DateNotLaterThan })
                .HasDatabaseName("idx_photos_date_range");
            entity.HasIndex(e => e.PlaceId)
                .HasDatabaseName("idx_photos_place");
            entity.HasIndex(e => e.Visibility)
                .HasDatabaseName("idx_photos_visibility");

            entity.HasOne(e => e.Place)
                .WithMany(p => p.Photos)
                .HasForeignKey(e => e.PlaceId)
                .OnDelete(DeleteBehavior.SetNull);

            entity.HasOne(e => e.ImageEmbedding)
                .WithOne(ie => ie.Photo)
                .HasForeignKey<ImageEmbedding>(ie => ie.PhotoId);

            entity.HasOne(e => e.ExifMetadata)
                .WithOne(em => em.Photo)
                .HasForeignKey<ExifMetadata>(em => em.PhotoId);
        });

        // Place configuration (self-referencing hierarchy)
        modelBuilder.Entity<Place>(entity =>
        {
            entity.HasKey(e => e.Id);

            entity.HasIndex(e => e.ParentId)
                .HasDatabaseName("idx_places_parent");
            entity.HasIndex(e => e.NameSv)
                .HasDatabaseName("idx_places_name_sv");
            entity.HasIndex(e => e.NameEn)
                .HasDatabaseName("idx_places_name_en");
            entity.HasIndex(e => new { e.NameSv, e.ParentId })
                .IsUnique()
                .HasDatabaseName("idx_places_name_parent_unique");

            entity.HasOne(e => e.Parent)
                .WithMany(p => p.Children)
                .HasForeignKey(e => e.ParentId)
                .OnDelete(DeleteBehavior.Restrict);
        });

        // Person configuration
        modelBuilder.Entity<Person>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.HasIndex(e => e.Name).IsUnique();
        });

        // Face configuration
        modelBuilder.Entity<Face>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.PhotoId).HasColumnType("char(64)").IsFixedLength();
            entity.Property(e => e.Embedding).HasColumnType("vector(512)");

            entity.HasIndex(e => e.PhotoId)
                .HasDatabaseName("idx_faces_photo");
            entity.HasIndex(e => e.PersonId)
                .HasDatabaseName("idx_faces_person");
            entity.HasIndex(e => e.ClusterId)
                .HasDatabaseName("idx_faces_cluster");

            entity.HasOne(e => e.Photo)
                .WithMany(p => p.Faces)
                .HasForeignKey(e => e.PhotoId)
                .OnDelete(DeleteBehavior.Cascade);

            entity.HasOne(e => e.Person)
                .WithMany(p => p.Faces)
                .HasForeignKey(e => e.PersonId)
                .OnDelete(DeleteBehavior.SetNull);
        });

        // ImageEmbedding configuration
        modelBuilder.Entity<ImageEmbedding>(entity =>
        {
            entity.HasKey(e => e.PhotoId);
            entity.Property(e => e.PhotoId).HasColumnType("char(64)").IsFixedLength();
            entity.Property(e => e.Embedding).HasColumnType("vector(768)");
        });

        // ExifMetadata configuration
        modelBuilder.Entity<ExifMetadata>(entity =>
        {
            entity.HasKey(e => e.PhotoId);
            entity.Property(e => e.PhotoId).HasColumnType("char(64)").IsFixedLength();
            entity.Property(e => e.RawExif).HasColumnType("jsonb");
        });

        // EditHistory configuration
        modelBuilder.Entity<EditHistory>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.PhotoId).HasColumnType("char(64)").IsFixedLength();

            entity.HasIndex(e => e.PhotoId)
                .HasDatabaseName("idx_edit_history_photo");
            entity.HasIndex(e => e.ChangedBy)
                .HasDatabaseName("idx_edit_history_user");
            entity.HasIndex(e => e.ChangedAt)
                .IsDescending()
                .HasDatabaseName("idx_edit_history_time");

            entity.HasOne(e => e.Photo)
                .WithMany(p => p.EditHistory)
                .HasForeignKey(e => e.PhotoId)
                .OnDelete(DeleteBehavior.Cascade);
        });

        // User configuration
        modelBuilder.Entity<User>(entity =>
        {
            entity.HasKey(e => e.FirebaseUid);
            entity.HasIndex(e => e.Email).IsUnique();
        });
    }
}
