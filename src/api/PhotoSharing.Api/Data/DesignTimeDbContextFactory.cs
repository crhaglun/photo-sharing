using Azure.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;
using Microsoft.Extensions.Configuration;
using Npgsql;

namespace PhotoSharing.Api.Data;

public class DesignTimeDbContextFactory : IDesignTimeDbContextFactory<PhotoSharingDbContext>
{
    public PhotoSharingDbContext CreateDbContext(string[] args)
    {
        var configuration = new ConfigurationBuilder()
            .SetBasePath(Directory.GetCurrentDirectory())
            .AddJsonFile("appsettings.json", optional: false)
            .AddJsonFile("appsettings.Development.json", optional: true)
            .Build();

        var connectionString = configuration.GetConnectionString("PhotoSharing")
            ?? throw new InvalidOperationException("Connection string 'PhotoSharing' not found");

        // Build data source with pgvector and Entra auth
        var dataSourceBuilder = new NpgsqlDataSourceBuilder(connectionString);
        dataSourceBuilder.UseVector();

        var credential = new DefaultAzureCredential();
        dataSourceBuilder.UsePeriodicPasswordProvider(async (_, ct) =>
        {
            var token = await credential.GetTokenAsync(
                new Azure.Core.TokenRequestContext(["https://ossrdbms-aad.database.windows.net/.default"]),
                ct);
            return token.Token;
        }, TimeSpan.FromMinutes(55), TimeSpan.FromSeconds(5));

        var dataSource = dataSourceBuilder.Build();

        var optionsBuilder = new DbContextOptionsBuilder<PhotoSharingDbContext>();
        optionsBuilder.UseNpgsql(dataSource, npgsql => npgsql.UseVector());

        return new PhotoSharingDbContext(optionsBuilder.Options);
    }
}
