import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { StartView } from '@/components/StartView';
import { LibraryView } from '@/components/LibraryView';
import { FacesView } from '@/components/FacesView';
import { LegalView } from '@/components/LegalView';

export const HomePage = () => {
  const { user, signOut } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const activeTab = location.pathname === '/faces'
    ? 'faces'
    : location.pathname === '/library'
      ? 'library'
      : location.pathname === '/legal'
        ? 'legal'
        : 'start';

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
              onClick={() => navigate('/')}
              className={`py-4 text-sm font-medium border-b-2 cursor-pointer ${
                activeTab === 'start'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Start
            </button>
            <button
              onClick={() => navigate('/library')}
              className={`py-4 text-sm font-medium border-b-2 cursor-pointer ${
                activeTab === 'library'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Library
            </button>
            <button
              onClick={() => navigate('/faces')}
              className={`py-4 text-sm font-medium border-b-2 cursor-pointer ${
                activeTab === 'faces'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Faces
            </button>
            <button
              onClick={() => navigate('/legal')}
              className={`py-4 text-sm font-medium border-b-2 cursor-pointer ${
                activeTab === 'legal'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Legal
            </button>
          </nav>
        </div>
      </div>

      {/* Main content */}
      <main className="py-6 px-2 sm:px-4">
        {activeTab === 'start' && <StartView />}
        {activeTab === 'library' && <LibraryView />}
        {activeTab === 'faces' && <FacesView />}
        {activeTab === 'legal' && <LegalView />}
      </main>
    </div>
  );
};
