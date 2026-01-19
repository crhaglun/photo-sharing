using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using PhotoSharing.Api.Data;
using PhotoSharing.Api.DTOs.Persons;
using PhotoSharing.Api.Entities;

namespace PhotoSharing.Api.Controllers;

[ApiController]
[Authorize]
[Route("persons")]
public class PersonsController : ControllerBase
{
    private readonly PhotoSharingDbContext _context;

    public PersonsController(PhotoSharingDbContext context)
    {
        _context = context;
    }

    [HttpGet]
    public async Task<ActionResult<List<PersonResponse>>> GetPersons(CancellationToken cancellationToken)
    {
        var persons = await _context.Persons
            .Select(p => new PersonResponse
            {
                Id = p.Id,
                Name = p.Name,
                FaceCount = p.Faces.Count,
                CreatedAt = p.CreatedAt
            })
            .OrderBy(p => p.Name)
            .ToListAsync(cancellationToken);

        return persons;
    }

    [HttpPost]
    public async Task<ActionResult<PersonResponse>> CreatePerson([FromBody] PersonCreateRequest request, CancellationToken cancellationToken)
    {
        // Check if name already exists
        var exists = await _context.Persons.AnyAsync(p => p.Name == request.Name, cancellationToken);
        if (exists)
        {
            return Conflict("A person with this name already exists");
        }

        var person = new Person
        {
            Id = Guid.NewGuid(),
            Name = request.Name,
            CreatedAt = DateTime.UtcNow
        };

        _context.Persons.Add(person);
        await _context.SaveChangesAsync(cancellationToken);

        var response = new PersonResponse
        {
            Id = person.Id,
            Name = person.Name,
            FaceCount = 0,
            CreatedAt = person.CreatedAt
        };

        return CreatedAtAction(nameof(GetPersons), response);
    }
}
