using Azure.Identity;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;
using Microsoft.IdentityModel.Tokens;
using Npgsql;
using PhotoSharing.Api.Configuration;
using PhotoSharing.Api.Data;
using PhotoSharing.Api.Services;

var builder = WebApplication.CreateBuilder(args);

// Configure Npgsql to use pgvector and Entra authentication
var connectionString = builder.Configuration.GetConnectionString("PhotoSharing");

// Connection pool settings
// Retry strategy handles token expiration by clearing pool and retrying with fresh token
var connStringBuilder = new NpgsqlConnectionStringBuilder(connectionString)
{
    MinPoolSize = 0, // Allow pool to fully drain when idle
};

var dataSourceBuilder = new NpgsqlDataSourceBuilder(connStringBuilder.ConnectionString);
dataSourceBuilder.UseVector();

// Password provider for Azure Entra ID tokens
// Called when opening new physical connections - DefaultAzureCredential handles caching internally
// Combined with retry strategy: on token expiry, pool is cleared, new connection triggers fresh token
var credential = new DefaultAzureCredential();
var tokenRequest = new Azure.Core.TokenRequestContext(["https://ossrdbms-aad.database.windows.net/.default"]);

dataSourceBuilder.UsePasswordProvider(
    _ => credential.GetToken(tokenRequest, default).Token,
    async (_, ct) =>
    {
        var token = await credential.GetTokenAsync(tokenRequest, ct);
        return token.Token;
    });

var dataSource = dataSourceBuilder.Build();

// Register data source for use by execution strategy
builder.Services.AddSingleton(dataSource);

builder.Services.AddDbContext<PhotoSharingDbContext>((services, options) =>
{
    var ds = services.GetRequiredService<NpgsqlDataSource>();
    options.UseNpgsql(ds, npgsql => npgsql.UseVector())
           .ReplaceService<Microsoft.EntityFrameworkCore.Storage.IExecutionStrategyFactory,
                          TokenExpiryRetryStrategyFactory>();
});

// Configure blob storage
builder.Services.Configure<BlobStorageOptions>(
    builder.Configuration.GetSection(BlobStorageOptions.SectionName));

// Register services
builder.Services.AddScoped<IBlobStorageService, BlobStorageService>();
builder.Services.AddScoped<IEditHistoryService, EditHistoryService>();
builder.Services.AddScoped<IPlaceService, PlaceService>();

// Configure Firebase JWT authentication
var firebaseProjectId = builder.Configuration["Firebase:ProjectId"]
    ?? throw new InvalidOperationException("Firebase:ProjectId configuration is required");

builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.Authority = $"https://securetoken.google.com/{firebaseProjectId}";
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidIssuer = $"https://securetoken.google.com/{firebaseProjectId}",
            ValidateAudience = true,
            ValidAudience = firebaseProjectId,
            ValidateLifetime = true,
        };
        options.Events = new JwtBearerEvents
        {
            OnAuthenticationFailed = context =>
            {
                Console.WriteLine($"Auth failed: {context.Exception.Message}");
                return Task.CompletedTask;
            },
            OnTokenValidated = context =>
            {
                Console.WriteLine($"Token validated for: {context.Principal?.Identity?.Name}");
                return Task.CompletedTask;
            }
        };
    });

builder.Services.AddAuthorization();

// Configure CORS
builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

builder.Services.AddControllers();
builder.Services.AddOpenApi();

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.UseCors();
app.UseAuthentication();
app.UseAuthorization();
app.MapControllers();

app.Run();
