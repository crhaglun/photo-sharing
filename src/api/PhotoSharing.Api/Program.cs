using Azure.Identity;
using Microsoft.EntityFrameworkCore;
using Npgsql;
using PhotoSharing.Api.Data;

var builder = WebApplication.CreateBuilder(args);

// Configure Npgsql to use pgvector and Entra authentication
var dataSourceBuilder = new NpgsqlDataSourceBuilder(
    builder.Configuration.GetConnectionString("PhotoSharing"));
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

builder.Services.AddDbContext<PhotoSharingDbContext>(options =>
    options.UseNpgsql(dataSource, npgsql =>
        npgsql.UseVector()));

builder.Services.AddControllers();
builder.Services.AddOpenApi();

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.UseHttpsRedirection();
app.UseAuthorization();
app.MapControllers();

app.Run();
