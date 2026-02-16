#:package Npgsql@9.*
#:package Azure.Identity@1.*

using Azure.Core;
using Azure.Identity;
using Npgsql;

var limit = 20;
for (int i = 0; i < args.Length; i++)
{
    if (args[i] == "--limit" && i + 1 < args.Length && int.TryParse(args[i + 1], out var n))
        limit = n;
}

var host = "psql-photosharing.postgres.database.azure.com";
var database = "photosharing";
var credential = new DefaultAzureCredential();
var token = credential.GetToken(new TokenRequestContext(["https://ossrdbms-aad.database.windows.net/.default"]));

var user = "christoffer.haglund_live.se#EXT#@christofferhaglundlive798.onmicrosoft.com";
var connString = $"Host={host};Database={database};Username={user};Password={token.Token};SSL Mode=Require";

await using var conn = new NpgsqlConnection(connString);
await conn.OpenAsync();

await using var cmd = new NpgsqlCommand("""
    SELECT eh.photo_id, eh.field_type, eh.field_key,
           eh.old_value, eh.new_value, eh.changed_by, eh.changed_at,
           p.original_filename
    FROM edit_history eh
    LEFT JOIN photos p ON p.id = eh.photo_id
    ORDER BY eh.changed_at DESC
    LIMIT @limit
    """, conn);

cmd.Parameters.AddWithValue("limit", limit);

await using var reader = await cmd.ExecuteReaderAsync();

var count = 0;
while (await reader.ReadAsync())
{
    count++;
    var photoId = reader.GetString(0);
    var fieldType = reader.GetString(1);
    var fieldKey = reader.GetString(2);
    var oldValue = reader.IsDBNull(3) ? "(empty)" : reader.GetString(3);
    var newValue = reader.IsDBNull(4) ? "(empty)" : reader.GetString(4);
    var changedBy = reader.GetString(5);
    var changedAt = reader.GetDateTime(6);
    var filename = reader.IsDBNull(7) ? "unknown" : reader.GetString(7);

    Console.WriteLine($"  {changedAt:yyyy-MM-dd HH:mm:ss}  {fieldType}/{fieldKey}");
    Console.WriteLine($"    Photo: {filename} ({photoId[..12]}...)");
    Console.WriteLine($"    {oldValue} -> {newValue}");
    Console.WriteLine($"    By: {changedBy}");
    Console.WriteLine();
}

if (count == 0)
    Console.WriteLine("No edits found.");
else
    Console.WriteLine($"Showing {count} most recent edits.");
