import { useEffect, useState } from 'react';
import { useFaceClusters } from '@/hooks/useApi';
import { api } from '@/services/api';
import { AuthenticatedImage } from './AuthenticatedImage';
import type { PersonResponse, FaceCluster } from '@/types/api';

export const FacesView = () => {
  const { clusters, loading, error, fetchClusters } = useFaceClusters();
  const [persons, setPersons] = useState<PersonResponse[]>([]);
  const [assigning, setAssigning] = useState<string | null>(null);

  useEffect(() => {
    fetchClusters();
    loadPersons();
  }, [fetchClusters]);

  const loadPersons = async () => {
    try {
      const result = await api.getPersons();
      setPersons(result);
    } catch {
      // Ignore - persons list is optional for autocomplete
    }
  };

  const handleAssign = async (cluster: FaceCluster, name: string) => {
    if (!name.trim()) return;

    setAssigning(cluster.clusterId);
    try {
      // Find existing person or create new one
      let person = persons.find(
        (p) => p.name.toLowerCase() === name.trim().toLowerCase()
      );

      if (!person) {
        person = await api.createPerson(name.trim());
        setPersons((prev) => [...prev, person!]);
      }

      // Assign all faces in the cluster to this person
      await Promise.all(
        cluster.faces.map((face) => api.assignFaceToPerson(face.id, person!.id))
      );

      // Refresh clusters (assigned faces will no longer appear)
      await fetchClusters();
    } catch (err) {
      console.error('Failed to assign faces:', err);
      alert('Failed to assign faces. Please try again.');
    } finally {
      setAssigning(null);
    }
  };

  if (loading && clusters.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">Loading face clusters...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <p className="text-red-800">Error loading faces: {error.message}</p>
      </div>
    );
  }

  if (clusters.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">No unassigned face clusters</p>
      </div>
    );
  }

  return (
    <div>
      <p className="text-sm text-gray-600 mb-4">
        {clusters.length} clusters with unassigned faces
      </p>

      <div className="space-y-6">
        {clusters.map((cluster) => (
          <ClusterCard
            key={cluster.clusterId}
            cluster={cluster}
            persons={persons}
            isAssigning={assigning === cluster.clusterId}
            onAssign={(name) => handleAssign(cluster, name)}
          />
        ))}
      </div>
    </div>
  );
};

interface ClusterCardProps {
  cluster: FaceCluster;
  persons: PersonResponse[];
  isAssigning: boolean;
  onAssign: (name: string) => void;
}

const ClusterCard = ({ cluster, persons, isAssigning, onAssign }: ClusterCardProps) => {
  const [name, setName] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);

  const filteredPersons = name.trim()
    ? persons.filter((p) =>
        p.name.toLowerCase().includes(name.toLowerCase())
      )
    : persons;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim() && !isAssigning) {
      onAssign(name);
    }
  };

  const handleSelectPerson = (personName: string) => {
    setName(personName);
    setShowSuggestions(false);
    onAssign(personName);
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex flex-wrap gap-2 mb-4">
        {cluster.faces.map((face) => (
          <div
            key={face.id}
            className="w-[80px] h-[80px] bg-gray-200 rounded overflow-hidden"
          >
            <AuthenticatedImage
              src={api.getThumbnailUrl(face.photoId)}
              alt={`Face ${face.id}`}
              className="w-full h-full object-cover"
              loading="lazy"
            />
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="relative">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onFocus={() => setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
              placeholder="Who is this?"
              disabled={isAssigning}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
            />
            {showSuggestions && filteredPersons.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-48 overflow-y-auto">
                {filteredPersons.map((person) => (
                  <button
                    key={person.id}
                    type="button"
                    onClick={() => handleSelectPerson(person.name)}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100"
                  >
                    {person.name}
                  </button>
                ))}
              </div>
            )}
          </div>
          <button
            type="submit"
            disabled={!name.trim() || isAssigning}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            {isAssigning ? 'Saving...' : 'Save'}
          </button>
        </div>
      </form>
    </div>
  );
};
