import { useState, useRef, useEffect, useMemo } from 'react';
import type { Place } from '@/types/api';

interface PlaceNode {
  place: Place;
  children: PlaceNode[];
}

interface PlaceTreeSelectorProps {
  places: Place[];
  selectedId: string | undefined;
  onChange: (placeId: string | undefined) => void;
}

function buildTree(places: Place[]): PlaceNode[] {
  const placeMap = new Map<string, PlaceNode>();
  const roots: PlaceNode[] = [];

  // Create nodes for all places
  for (const place of places) {
    placeMap.set(place.id, { place, children: [] });
  }

  // Build tree structure
  for (const place of places) {
    const node = placeMap.get(place.id)!;
    if (place.parentId && placeMap.has(place.parentId)) {
      placeMap.get(place.parentId)!.children.push(node);
    } else {
      roots.push(node);
    }
  }

  // Sort children alphabetically at each level
  const sortChildren = (nodes: PlaceNode[]) => {
    nodes.sort((a, b) => a.place.nameEn.localeCompare(b.place.nameEn));
    for (const node of nodes) {
      sortChildren(node.children);
    }
  };
  sortChildren(roots);

  return roots;
}

interface TreeNodeProps {
  node: PlaceNode;
  depth: number;
  expandedIds: Set<string>;
  onToggle: (id: string) => void;
  onSelect: (id: string) => void;
}

const TreeNode = ({ node, depth, expandedIds, onToggle, onSelect }: TreeNodeProps) => {
  const hasChildren = node.children.length > 0;
  const isExpanded = expandedIds.has(node.place.id);

  return (
    <div>
      <div
        className="flex items-center py-1 px-2 hover:bg-gray-100 cursor-pointer"
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {hasChildren ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onToggle(node.place.id);
            }}
            className="w-5 h-5 flex items-center justify-center text-gray-500 hover:text-gray-700"
          >
            <svg
              className={`w-3 h-3 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        ) : (
          <span className="w-5" />
        )}
        <span
          onClick={() => onSelect(node.place.id)}
          className="flex-1 text-sm"
        >
          {node.place.nameEn}
        </span>
      </div>
      {hasChildren && isExpanded && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.place.id}
              node={child}
              depth={depth + 1}
              expandedIds={expandedIds}
              onToggle={onToggle}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const PlaceTreeSelector = ({ places, selectedId, onChange }: PlaceTreeSelectorProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const containerRef = useRef<HTMLDivElement>(null);

  const tree = useMemo(() => buildTree(places), [places]);

  const selectedPlace = useMemo(
    () => places.find((p) => p.id === selectedId),
    [places, selectedId]
  );

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const handleToggle = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleSelect = (id: string | undefined) => {
    onChange(id);
    setIsOpen(false);
  };

  return (
    <div ref={containerRef} className="relative">
      <label className="block text-xs text-gray-500 mb-1">Place</label>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full px-3 py-2 border border-gray-300 rounded-md text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-[150px]"
      >
        <span className={selectedPlace ? 'text-gray-900' : 'text-gray-500'}>
          {selectedPlace?.nameEn || 'All places'}
        </span>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute z-20 mt-1 w-64 max-h-80 overflow-y-auto bg-white border border-gray-200 rounded-md shadow-lg">
          {/* All places option */}
          <div
            onClick={() => handleSelect(undefined)}
            className="py-2 px-3 text-sm text-gray-600 hover:bg-gray-100 cursor-pointer border-b border-gray-100"
          >
            All places
          </div>
          {/* Tree */}
          <div className="py-1">
            {tree.map((node) => (
              <TreeNode
                key={node.place.id}
                node={node}
                depth={0}
                expandedIds={expandedIds}
                onToggle={handleToggle}
                onSelect={handleSelect}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
