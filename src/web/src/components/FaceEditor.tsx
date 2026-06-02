import { useState, useEffect, useRef } from 'react';
import { api } from '@/services/api';
import type { FaceInPhotoResponse, PersonResponse } from '@/types/api';

interface FaceEditorProps {
  face: FaceInPhotoResponse;
  onHover: (faceId: string | null) => void;
  onUpdated: () => void;
  onNavigateToPerson?: (personId: string) => void;
  onNavigateToCluster?: (clusterId: string) => void;
}

export const FaceEditor = ({ face, onHover, onUpdated, onNavigateToPerson, onNavigateToCluster }: FaceEditorProps) => {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  const canNavigate = (onNavigateToPerson && face.personId) || (onNavigateToCluster && face.clusterId);

  const handleUnlink = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!face.personId || saving) return;
    setSaving(true);
    try {
      await api.unassignFace(face.id);
      onUpdated();
    } catch (err) {
      console.error('Failed to unassign face:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleSwitch = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditing(true);
  };

  const handleAssigned = () => {
    setEditing(false);
    onUpdated();
  };

  if (editing) {
    return (
      <PersonPicker
        faceId={face.id}
        currentPersonName={face.personName}
        onDone={handleAssigned}
        onCancel={() => setEditing(false)}
      />
    );
  }

  return (
    <span
      className="inline-flex items-center gap-1 group"
      onMouseEnter={() => onHover(face.id)}
      onMouseLeave={() => onHover(null)}
    >
      <span
        className={`hover:text-white transition-colors ${canNavigate ? 'cursor-pointer underline decoration-dotted underline-offset-2' : 'cursor-default'}`}
        onClick={canNavigate ? () => {
          if (face.personId && onNavigateToPerson) onNavigateToPerson(face.personId);
          else if (face.clusterId && onNavigateToCluster) onNavigateToCluster(face.clusterId);
        } : undefined}
      >
        {face.personName || face.clusterId || '?'}
      </span>
        {face.personId ? (
        <>
          <button
            onClick={handleSwitch}
            className="opacity-0 group-hover:opacity-100 text-white/50 hover:text-blue-400 transition-opacity cursor-pointer"
            title="Reassign to different person"
            disabled={saving}
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
            </svg>
          </button>
          <button
            onClick={handleUnlink}
            className="opacity-0 group-hover:opacity-100 text-white/50 hover:text-red-400 transition-opacity cursor-pointer"
            title="Remove person assignment"
            disabled={saving}
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </>
        ) : (
          <button
            onClick={handleSwitch}
            className="opacity-0 group-hover:opacity-100 text-white/50 hover:text-blue-400 transition-opacity cursor-pointer"
            title="Assign person"
            disabled={saving}
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
          </button>
        )}
    </span>
  );
};

interface PersonPickerProps {
  faceId: string;
  currentPersonName: string | null;
  onDone: () => void;
  onCancel: () => void;
}

const PersonPicker = ({ faceId, currentPersonName, onDone, onCancel }: PersonPickerProps) => {
  const [name, setName] = useState('');
  const [persons, setPersons] = useState<PersonResponse[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.getPersons().then(setPersons).catch(() => {});
    inputRef.current?.focus();
  }, []);

  // Close on Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onCancel();
      }
    };
    window.addEventListener('keydown', handleKey, true);
    return () => window.removeEventListener('keydown', handleKey, true);
  }, [onCancel]);

  const filteredPersons = name.trim()
    ? persons.filter((p) =>
        p.name.toLowerCase().includes(name.toLowerCase()) &&
        p.name.toLowerCase() !== currentPersonName?.toLowerCase()
      )
    : persons.filter((p) => p.name.toLowerCase() !== currentPersonName?.toLowerCase());

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await assignByName(name);
  };

  const assignByName = async (personName: string) => {
    if (!personName.trim() || saving) return;
    setSaving(true);
    try {
      let person = persons.find(
        (p) => p.name.toLowerCase() === personName.trim().toLowerCase()
      );
      if (!person) {
        person = await api.createPerson(personName.trim());
      }
      await api.assignFaceToPerson(faceId, person.id);
      onDone();
    } catch (err) {
      console.error('Failed to reassign face:', err);
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="inline-flex items-center gap-1 relative" onClick={(e) => e.stopPropagation()}>
      <input
        ref={inputRef}
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        onFocus={() => setShowSuggestions(true)}
        onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
        placeholder="Type name..."
        disabled={saving}
        className="w-24 px-1 py-0 bg-white/10 border border-white/30 rounded text-xs text-white placeholder-white/40 focus:outline-none focus:border-blue-400"
      />
      {showSuggestions && filteredPersons.length > 0 && (
        <div className="absolute top-full left-0 mt-1 w-36 bg-gray-900 border border-white/20 rounded shadow-lg max-h-32 overflow-y-auto z-50">
          {filteredPersons.slice(0, 8).map((person) => (
            <button
              key={person.id}
              type="button"
              onMouseDown={() => assignByName(person.name)}
              className="w-full text-left px-2 py-1 text-xs text-white/80 hover:bg-white/10"
            >
              {person.name}
            </button>
          ))}
        </div>
      )}
      <button
        type="button"
        onClick={onCancel}
        disabled={saving}
        className="text-white/50 hover:text-white cursor-pointer"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </form>
  );
};
