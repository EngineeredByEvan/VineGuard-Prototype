import { FormEvent, useState } from 'react';

interface Props {
  onSubmit: (email: string, password: string) => Promise<void>;
  isSubmitting?: boolean;
  error?: string | null;
}

const LoginForm = ({ onSubmit, isSubmitting = false, error }: Props) => {
  const [email, setEmail] = useState('demo@vineguard.io');
  const [password, setPassword] = useState('ChangeMe123!');

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await onSubmit(email, password);
  };

  return (
    <div className="auth-container">
      <div className="card">
        <h1>VineGuard Login</h1>
        <p>Monitor vines, soil moisture, and node health in real time.</p>
        <form onSubmit={handleSubmit}>
          <label>
            Email
            <input
              type="email"
              value={email}
              autoComplete="email"
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              autoComplete="current-password"
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          {error && <span style={{ color: '#dc2626' }}>{error}</span>}
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginForm;
