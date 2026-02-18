using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace PhotoSharing.Api.Migrations
{
    /// <inheritdoc />
    public partial class AddIsHeroToPhoto : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<bool>(
                name: "is_hero",
                table: "photos",
                type: "boolean",
                nullable: false,
                defaultValue: false);

            migrationBuilder.CreateIndex(
                name: "idx_photos_hero",
                table: "photos",
                column: "is_hero",
                filter: "is_hero = true");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropIndex(
                name: "idx_photos_hero",
                table: "photos");

            migrationBuilder.DropColumn(
                name: "is_hero",
                table: "photos");
        }
    }
}
