import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { getCurrentUser, login as loginRequest, loginDemo as loginDemoRequest, logout as logoutRequest } from "../services/api.js";

const AuthContext = createContext(null);
const ACCESS_TOKEN_KEY = "roboops.access_token";

function readToken() {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

export function AuthProvider({ children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [token, setToken] = useState(readToken);
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState(null);

  const clearSession = () => {
    sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    setToken(null);
    setUser(null);
    setStatus("unauthenticated");
  };

  useEffect(() => {
    let cancelled = false;
    const storedToken = readToken();
    if (!storedToken) {
      setStatus("unauthenticated");
      return () => {
        cancelled = true;
      };
    }

    getCurrentUser()
      .then((currentUser) => {
        if (!cancelled) {
          setUser(currentUser);
          setStatus("authenticated");
        }
      })
      .catch((requestError) => {
        if (!cancelled) {
          clearSession();
          setError(requestError);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const handleUnauthorized = () => {
      clearSession();
      if (location.pathname !== "/login") {
        navigate("/login", { replace: true, state: { from: location } });
      }
    };
    window.addEventListener("roboops:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("roboops:unauthorized", handleUnauthorized);
  }, [location, navigate]);

  const establishSession = async (requestToken) => {
    setError(null);
    const response = await requestToken();
    if (!response?.access_token) {
      throw new Error("Login response did not include an access token.");
    }
    sessionStorage.setItem(ACCESS_TOKEN_KEY, response.access_token);
    setToken(response.access_token);
    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      setStatus("authenticated");
      return currentUser;
    } catch (requestError) {
      clearSession();
      setError(requestError);
      throw requestError;
    }
  };

  const login = (email, password) => establishSession(() => loginRequest(email, password));
  const loginDemo = () => establishSession(loginDemoRequest);

  const logout = async () => {
    try {
      await logoutRequest();
    } catch {
      // The browser must still discard its token when the API is unreachable.
    } finally {
      clearSession();
      navigate("/login", { replace: true });
    }
  };

  const value = useMemo(
    () => ({ error, login, loginDemo, logout, status, token, user }),
    [error, status, token, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
