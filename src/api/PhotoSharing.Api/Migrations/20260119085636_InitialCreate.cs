using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Pgvector;

#nullable disable

namespace PhotoSharing.Api.Migrations
{
    /// <inheritdoc />
    public partial class InitialCreate : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AlterDatabase()
                .Annotation("Npgsql:PostgresExtension:uuid-ossp", ",,")
                .Annotation("Npgsql:PostgresExtension:vector", ",,");

            migrationBuilder.CreateTable(
                name: "persons",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    name = table.Column<string>(type: "character varying(255)", maxLength: 255, nullable: false),
                    created_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_persons", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "places",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    name_sv = table.Column<string>(type: "character varying(255)", maxLength: 255, nullable: false),
                    name_en = table.Column<string>(type: "character varying(255)", maxLength: 255, nullable: false),
                    parent_id = table.Column<Guid>(type: "uuid", nullable: true),
                    type = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_places", x => x.id);
                    table.ForeignKey(
                        name: "FK_places_places_parent_id",
                        column: x => x.parent_id,
                        principalTable: "places",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "users",
                columns: table => new
                {
                    firebase_uid = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    email = table.Column<string>(type: "character varying(255)", maxLength: 255, nullable: false),
                    display_name = table.Column<string>(type: "character varying(255)", maxLength: 255, nullable: true),
                    created_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_users", x => x.firebase_uid);
                });

            migrationBuilder.CreateTable(
                name: "photos",
                columns: table => new
                {
                    id = table.Column<string>(type: "char(64)", fixedLength: true, maxLength: 64, nullable: false),
                    original_filename = table.Column<string>(type: "character varying(255)", maxLength: 255, nullable: false),
                    date_not_earlier_than = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    date_not_later_than = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    place_id = table.Column<Guid>(type: "uuid", nullable: true),
                    is_low_quality = table.Column<bool>(type: "boolean", nullable: false),
                    created_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false),
                    updated_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_photos", x => x.id);
                    table.ForeignKey(
                        name: "FK_photos_places_place_id",
                        column: x => x.place_id,
                        principalTable: "places",
                        principalColumn: "id",
                        onDelete: ReferentialAction.SetNull);
                });

            migrationBuilder.CreateTable(
                name: "edit_history",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    photo_id = table.Column<string>(type: "char(64)", fixedLength: true, maxLength: 64, nullable: false),
                    field_type = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    field_key = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    old_value = table.Column<string>(type: "text", nullable: true),
                    new_value = table.Column<string>(type: "text", nullable: true),
                    changed_by = table.Column<string>(type: "character varying(255)", maxLength: 255, nullable: false),
                    changed_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_edit_history", x => x.id);
                    table.ForeignKey(
                        name: "FK_edit_history_photos_photo_id",
                        column: x => x.photo_id,
                        principalTable: "photos",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "exif_metadata",
                columns: table => new
                {
                    photo_id = table.Column<string>(type: "char(64)", fixedLength: true, maxLength: 64, nullable: false),
                    camera_make = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    camera_model = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    lens = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    focal_length = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: true),
                    aperture = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: true),
                    shutter_speed = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: true),
                    iso = table.Column<int>(type: "integer", nullable: true),
                    taken_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    raw_exif = table.Column<string>(type: "jsonb", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_exif_metadata", x => x.photo_id);
                    table.ForeignKey(
                        name: "FK_exif_metadata_photos_photo_id",
                        column: x => x.photo_id,
                        principalTable: "photos",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "faces",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    photo_id = table.Column<string>(type: "char(64)", fixedLength: true, maxLength: 64, nullable: false),
                    person_id = table.Column<Guid>(type: "uuid", nullable: true),
                    bbox_x = table.Column<int>(type: "integer", nullable: false),
                    bbox_y = table.Column<int>(type: "integer", nullable: false),
                    bbox_width = table.Column<int>(type: "integer", nullable: false),
                    bbox_height = table.Column<int>(type: "integer", nullable: false),
                    embedding = table.Column<Vector>(type: "vector(512)", nullable: false),
                    cluster_id = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_faces", x => x.id);
                    table.ForeignKey(
                        name: "FK_faces_persons_person_id",
                        column: x => x.person_id,
                        principalTable: "persons",
                        principalColumn: "id",
                        onDelete: ReferentialAction.SetNull);
                    table.ForeignKey(
                        name: "FK_faces_photos_photo_id",
                        column: x => x.photo_id,
                        principalTable: "photos",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "image_embeddings",
                columns: table => new
                {
                    photo_id = table.Column<string>(type: "char(64)", fixedLength: true, maxLength: 64, nullable: false),
                    embedding = table.Column<Vector>(type: "vector(768)", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_image_embeddings", x => x.photo_id);
                    table.ForeignKey(
                        name: "FK_image_embeddings_photos_photo_id",
                        column: x => x.photo_id,
                        principalTable: "photos",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "idx_edit_history_photo",
                table: "edit_history",
                column: "photo_id");

            migrationBuilder.CreateIndex(
                name: "idx_edit_history_time",
                table: "edit_history",
                column: "changed_at",
                descending: new bool[0]);

            migrationBuilder.CreateIndex(
                name: "idx_edit_history_user",
                table: "edit_history",
                column: "changed_by");

            migrationBuilder.CreateIndex(
                name: "idx_faces_cluster",
                table: "faces",
                column: "cluster_id");

            migrationBuilder.CreateIndex(
                name: "idx_faces_person",
                table: "faces",
                column: "person_id");

            migrationBuilder.CreateIndex(
                name: "idx_faces_photo",
                table: "faces",
                column: "photo_id");

            migrationBuilder.CreateIndex(
                name: "IX_persons_name",
                table: "persons",
                column: "name",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "idx_photos_date_range",
                table: "photos",
                columns: new[] { "date_not_earlier_than", "date_not_later_than" });

            migrationBuilder.CreateIndex(
                name: "idx_photos_low_quality",
                table: "photos",
                column: "is_low_quality");

            migrationBuilder.CreateIndex(
                name: "idx_photos_place",
                table: "photos",
                column: "place_id");

            migrationBuilder.CreateIndex(
                name: "idx_places_name_en",
                table: "places",
                column: "name_en");

            migrationBuilder.CreateIndex(
                name: "idx_places_name_parent_unique",
                table: "places",
                columns: new[] { "name_sv", "parent_id" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "idx_places_name_sv",
                table: "places",
                column: "name_sv");

            migrationBuilder.CreateIndex(
                name: "idx_places_parent",
                table: "places",
                column: "parent_id");

            migrationBuilder.CreateIndex(
                name: "IX_users_email",
                table: "users",
                column: "email",
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "edit_history");

            migrationBuilder.DropTable(
                name: "exif_metadata");

            migrationBuilder.DropTable(
                name: "faces");

            migrationBuilder.DropTable(
                name: "image_embeddings");

            migrationBuilder.DropTable(
                name: "users");

            migrationBuilder.DropTable(
                name: "persons");

            migrationBuilder.DropTable(
                name: "photos");

            migrationBuilder.DropTable(
                name: "places");
        }
    }
}
