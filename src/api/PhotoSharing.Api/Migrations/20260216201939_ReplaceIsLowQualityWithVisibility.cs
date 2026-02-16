using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace PhotoSharing.Api.Migrations
{
    /// <inheritdoc />
    public partial class ReplaceIsLowQualityWithVisibility : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // Add new column with default
            migrationBuilder.AddColumn<string>(
                name: "visibility",
                table: "photos",
                type: "character varying(20)",
                maxLength: 20,
                nullable: false,
                defaultValue: "visible");

            // Migrate data: false -> 'visible', true -> 'low_quality'
            migrationBuilder.Sql(
                "UPDATE photos SET visibility = CASE WHEN is_low_quality THEN 'low_quality' ELSE 'visible' END");

            // Drop old index and column
            migrationBuilder.DropIndex(
                name: "idx_photos_low_quality",
                table: "photos");

            migrationBuilder.DropColumn(
                name: "is_low_quality",
                table: "photos");

            // Create new index
            migrationBuilder.CreateIndex(
                name: "idx_photos_visibility",
                table: "photos",
                column: "visibility");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<bool>(
                name: "is_low_quality",
                table: "photos",
                type: "boolean",
                nullable: false,
                defaultValue: false);

            // Reverse data migration (both 'low_quality' and 'deleted' map to true)
            migrationBuilder.Sql(
                "UPDATE photos SET is_low_quality = (visibility != 'visible')");

            migrationBuilder.DropIndex(
                name: "idx_photos_visibility",
                table: "photos");

            migrationBuilder.DropColumn(
                name: "visibility",
                table: "photos");

            migrationBuilder.CreateIndex(
                name: "idx_photos_low_quality",
                table: "photos",
                column: "is_low_quality");
        }
    }
}
