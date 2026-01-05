import { useState } from "react";
import { logout } from "../lib/api";
import { useAuth } from "../components/auth/AuthProvider";

export function SettingsPage() {
  const { email } = useAuth();
  const [loggingOut, setLoggingOut] = useState(false);

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await logout();
      window.location.reload();
    } catch {
      setLoggingOut(false);
    }
  };

  return (
    <div className="settings-page">
      <h1>Settings</h1>

      <section className="settings-section">
        <h2>Team Account</h2>
        <div className="settings-field">
          <label>Email</label>
          <div className="settings-value">{email || "Not logged in"}</div>
        </div>
        <button
          onClick={handleLogout}
          disabled={loggingOut}
          className="logout-button"
        >
          {loggingOut ? "Signing out..." : "Sign Out"}
        </button>
      </section>

      <style>{`
        .settings-page {
          max-width: 800px;
          margin: 0 auto;
          padding: 2rem;
        }

        .settings-page h1 {
          font-size: 1.75rem;
          font-weight: 600;
          color: #fff;
          margin-bottom: 2rem;
        }

        .settings-section {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          padding: 1.5rem;
          margin-bottom: 1.5rem;
        }

        .settings-section h2 {
          font-size: 1.125rem;
          font-weight: 600;
          color: #fff;
          margin-bottom: 1rem;
        }

        .settings-field {
          margin-bottom: 1rem;
        }

        .settings-field label {
          display: block;
          font-size: 0.75rem;
          font-weight: 500;
          color: rgba(255, 255, 255, 0.5);
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin-bottom: 0.25rem;
        }

        .settings-value {
          color: #fff;
          font-size: 1rem;
        }

        .logout-button {
          padding: 0.5rem 1rem;
          background: rgba(239, 68, 68, 0.2);
          border: 1px solid rgba(239, 68, 68, 0.4);
          border-radius: 6px;
          color: #f87171;
          font-size: 0.875rem;
          cursor: pointer;
          transition: background 0.2s;
        }

        .logout-button:hover:not(:disabled) {
          background: rgba(239, 68, 68, 0.3);
        }

        .logout-button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
}
