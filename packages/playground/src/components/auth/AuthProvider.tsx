import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { getSession, logout as logoutApi } from "../../lib/api";
import { LoginPage } from "../../pages/LoginPage";

interface AuthContextValue {
  authenticated: boolean;
  email: string | null;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [email, setEmail] = useState<string | null>(null);

  const checkSession = async () => {
    try {
      const session = await getSession();
      setAuthenticated(session.authenticated);
      setEmail(session.email);
    } catch {
      setAuthenticated(false);
      setEmail(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkSession();
  }, []);

  const logout = async () => {
    await logoutApi();
    setAuthenticated(false);
    setEmail(null);
  };

  if (loading) {
    return (
      <div className="auth-loading">
        <div className="auth-spinner"></div>
        <style>{`
          .auth-loading {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #1a1a2e;
          }
          .auth-spinner {
            width: 40px;
            height: 40px;
            border: 3px solid rgba(255, 255, 255, 0.1);
            border-top-color: #6366f1;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
          }
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  // Show login page if not authenticated
  if (!authenticated) {
    return <LoginPage onSuccess={checkSession} />;
  }

  return (
    <AuthContext.Provider value={{ authenticated, email, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
