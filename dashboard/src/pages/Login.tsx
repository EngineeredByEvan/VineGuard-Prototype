import { useState } from 'react';
import LoginForm from '../components/LoginForm';
import { useAuth } from '../hooks/useAuth';

const Login = () => {
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setSubmitting] = useState(false);

  const handleSubmit = async (email: string, password: string) => {
    setSubmitting(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err) {
      setError('Unable to sign in. Check credentials and backend availability.');
    } finally {
      setSubmitting(false);
    }
  };

  return <LoginForm onSubmit={handleSubmit} isSubmitting={isSubmitting} error={error} />;
};

export default Login;
