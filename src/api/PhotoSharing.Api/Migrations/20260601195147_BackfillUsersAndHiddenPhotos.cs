using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace PhotoSharing.Api.Migrations
{
    /// <inheritdoc />
    public partial class BackfillUsersAndHiddenPhotos : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // Insert users from edit_history that don't exist yet.
            // Uses firebase_uid as placeholder email since real emails aren't available during migration.
            // The OnTokenValidated handler will have the real email on next login.
            migrationBuilder.Sql(@"
                INSERT INTO users (firebase_uid, email, display_name, created_at)
                SELECT DISTINCT eh.changed_by, eh.changed_by, NULL, NOW()
                FROM edit_history eh
                WHERE eh.changed_by != 'system'
                  AND eh.changed_by NOT IN (SELECT firebase_uid FROM users)
            ");

            // Populate hidden_photos from old deletion edit history.
            // The previous migration's insert was a no-op because users table was empty.
            migrationBuilder.Sql(@"
                INSERT INTO hidden_photos (photo_id, user_id, hidden_at)
                SELECT DISTINCT ON (eh.photo_id) eh.photo_id, eh.changed_by, eh.changed_at
                FROM edit_history eh
                JOIN photos p ON p.id = eh.photo_id
                WHERE eh.field_type = 'visibility'
                  AND eh.new_value = 'deleted'
                  AND p.visibility != 'deleted'
                  AND eh.changed_by IN (SELECT firebase_uid FROM users)
                  AND NOT EXISTS (
                      SELECT 1 FROM hidden_photos hp
                      WHERE hp.photo_id = eh.photo_id AND hp.user_id = eh.changed_by
                  )
                ORDER BY eh.photo_id, eh.changed_at DESC
            ");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            // Remove hidden_photos that were backfilled
            migrationBuilder.Sql(@"
                DELETE FROM hidden_photos
                WHERE (photo_id, user_id) IN (
                    SELECT DISTINCT ON (eh.photo_id) eh.photo_id, eh.changed_by
                    FROM edit_history eh
                    WHERE eh.field_type = 'visibility'
                      AND eh.new_value = 'deleted'
                    ORDER BY eh.photo_id, eh.changed_at DESC
                )
            ");
        }
    }
}
