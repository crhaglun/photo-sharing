using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;
using Microsoft.Extensions.DependencyInjection;
using Npgsql;

namespace PhotoSharing.Api.Data;

/// <summary>
/// Execution strategy that handles Azure AD token expiration by clearing
/// the connection pool and retrying the operation.
/// </summary>
public class TokenExpiryRetryStrategy : ExecutionStrategy
{
    private readonly NpgsqlDataSource _dataSource;

    public TokenExpiryRetryStrategy(
        DbContext context,
        NpgsqlDataSource dataSource,
        int maxRetryCount = 3)
        : base(context, maxRetryCount, TimeSpan.FromSeconds(30))
    {
        _dataSource = dataSource;
    }

    public TokenExpiryRetryStrategy(
        ExecutionStrategyDependencies dependencies,
        NpgsqlDataSource dataSource,
        int maxRetryCount = 3)
        : base(dependencies, maxRetryCount, TimeSpan.FromSeconds(30))
    {
        _dataSource = dataSource;
    }

    protected override bool ShouldRetryOn(Exception exception)
    {
        // Check for token expiration error
        if (IsTokenExpiredException(exception))
        {
            Console.WriteLine("Detected token expiration - clearing connection pool and retrying...");

            // Clear all pooled connections - new connections will get fresh tokens
            // from the periodic password provider
            NpgsqlConnection.ClearPool(_dataSource.CreateConnection());

            return true;
        }

        // Also retry on transient Npgsql errors
        if (exception is NpgsqlException npgsqlEx && npgsqlEx.IsTransient)
        {
            return true;
        }

        return false;
    }

    private static bool IsTokenExpiredException(Exception? exception)
    {
        while (exception != null)
        {
            if (exception is PostgresException pgEx)
            {
                // PostgreSQL error code 28000 = invalid_authorization_specification
                // Check message for token expiration
                if (pgEx.SqlState == "28000" &&
                    pgEx.Message.Contains("access token has expired", StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }

            exception = exception.InnerException;
        }

        return false;
    }

    protected override TimeSpan? GetNextDelay(Exception lastException)
    {
        // Short delay for token expiry - the new connection should work immediately
        if (IsTokenExpiredException(lastException))
        {
            return TimeSpan.FromMilliseconds(100);
        }

        // Default exponential backoff for other transient errors
        return base.GetNextDelay(lastException);
    }
}

/// <summary>
/// Factory for creating TokenExpiryRetryStrategy instances.
/// Required by EF Core's service replacement mechanism.
/// </summary>
public class TokenExpiryRetryStrategyFactory : IExecutionStrategyFactory
{
    private readonly ExecutionStrategyDependencies _dependencies;
    private readonly NpgsqlDataSource _dataSource;

    public TokenExpiryRetryStrategyFactory(
        ExecutionStrategyDependencies dependencies,
        NpgsqlDataSource dataSource)
    {
        _dependencies = dependencies;
        _dataSource = dataSource;
    }

    public IExecutionStrategy Create()
    {
        return new TokenExpiryRetryStrategy(_dependencies, _dataSource);
    }
}
