using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace PhotoSharing.Api.Migrations
{
    /// <inheritdoc />
    public partial class ReplaceDeletedWithPerUserHidden : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "hidden_photos",
                columns: table => new
                {
                    photo_id = table.Column<string>(type: "char(64)", fixedLength: true, maxLength: 64, nullable: false),
                    user_id = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    hidden_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_hidden_photos", x => new { x.photo_id, x.user_id });
                    table.ForeignKey(
                        name: "FK_hidden_photos_photos_photo_id",
                        column: x => x.photo_id,
                        principalTable: "photos",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_hidden_photos_users_user_id",
                        column: x => x.user_id,
                        principalTable: "users",
                        principalColumn: "firebase_uid",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "idx_hidden_photos_user",
                table: "hidden_photos",
                column: "user_id");

            // Migrate existing "deleted" photos to per-user hidden_photos table.
            // Uses edit_history to determine which user set visibility to 'deleted'.
            // Takes the most recent visibility change to 'deleted' per photo.
            migrationBuilder.Sql(@"
                INSERT INTO hidden_photos (photo_id, user_id, hidden_at)
                SELECT DISTINCT ON (eh.photo_id) eh.photo_id, eh.changed_by, eh.changed_at
                FROM edit_history eh
                JOIN photos p ON p.id = eh.photo_id
                WHERE eh.field_type = 'visibility'
                  AND eh.new_value = 'deleted'
                  AND p.visibility = 'deleted'
                  AND eh.changed_by IN (SELECT firebase_uid FROM users)
                ORDER BY eh.photo_id, eh.changed_at DESC
            ");

            // Restore visibility of formerly-deleted photos to the value before deletion,
            // or 'visible' if no prior value is recorded.
            migrationBuilder.Sql(@"
                UPDATE photos
                SET visibility = COALESCE(
                    (SELECT eh.old_value
                     FROM edit_history eh
                     WHERE eh.photo_id = photos.id
                       AND eh.field_type = 'visibility'
                       AND eh.new_value = 'deleted'
                     ORDER BY eh.changed_at DESC
                     LIMIT 1),
                    'visible')
                WHERE visibility = 'deleted'
            ");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            // Restore 'deleted' visibility for photos that are in hidden_photos
            migrationBuilder.Sql(@"
                UPDATE photos
                SET visibility = 'deleted'
                WHERE id IN (SELECT photo_id FROM hidden_photos)
            ");

            migrationBuilder.DropTable(
                name: "hidden_photos");
        }
    }
}
