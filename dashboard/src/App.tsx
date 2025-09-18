import { useAuth } from './hooks/useAuth';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';

const App = () => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="loading-screen">
        <p>Loading VineGuard…</p>
      </div>
    );
  }

  return user ? <Dashboard /> : <Login />;
};

export default App;
