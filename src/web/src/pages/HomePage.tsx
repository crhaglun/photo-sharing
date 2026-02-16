import { useCallback, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { LibraryView } from '@/components/LibraryView';
import { FacesView } from '@/components/FacesView';
import type { NavigationTarget } from '@/types/api';

type Tab = 'library' | 'faces';

export const HomePage = () => {
  const { user, signOut } = useAuth();
  const [activeTab, setActiveTab] = useState<Tab>('library');
  const [navTarget, setNavTarget] = useState<NavigationTarget | null>(null);

  const handleNavigate = useCallback((target: NavigationTarget) => {
    if (target.type === 'library') {
      setNavTarget(null);
      setActiveTab('library');
    } else {
      setNavTarget(target);
      setActiveTab(target.type === 'cluster' ? 'faces' : 'library');
    }
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-xl font-bold text-gray-900">Photo Sharing</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">
              {user?.displayName || user?.email}
            </span>
            <button
              onClick={signOut}
              className="text-sm text-blue-600 hover:text-blue-500 cursor-pointer"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex gap-8">
            <button
              onClick={() => { setNavTarget(null); setActiveTab('library'); }}
              className={`py-4 text-sm font-medium border-b-2 cursor-pointer ${
                activeTab === 'library'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Library
            </button>
            <button
              onClick={() => { setNavTarget(null); setActiveTab('faces'); }}
              className={`py-4 text-sm font-medium border-b-2 cursor-pointer ${
                activeTab === 'faces'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Faces
            </button>
          </nav>
        </div>
      </div>

      {/* Main content */}
      <main className="py-6 px-2 sm:px-4">
        {activeTab === 'library' && (
          <LibraryView
            key={navTarget?.type === 'person' ? navTarget.personId : navTarget?.type === 'similar' ? navTarget.photoId : 'default'}
            initialPersonId={navTarget?.type === 'person' ? navTarget.personId : undefined}
            initialSimilarToId={navTarget?.type === 'similar' ? navTarget.photoId : undefined}
            onNavigate={handleNavigate}
          />
        )}
        {activeTab === 'faces' && (
          <FacesView
            key={navTarget?.type === 'cluster' ? navTarget.clusterId : 'default'}
            initialClusterId={navTarget?.type === 'cluster' ? navTarget.clusterId : undefined}
            onNavigate={handleNavigate}
          />
        )}
      </main>
    </div>
  );
};
