import React from 'react';
import { ReactKeycloakProvider } from '@react-keycloak/web';
import Keycloak, { KeycloakConfig, KeycloakInitOptions } from 'keycloak-js';
import ReportPage from './components/ReportPage';

const keycloakConfig: KeycloakConfig = {
  url: process.env.REACT_APP_KEYCLOAK_URL,
  realm: process.env.REACT_APP_KEYCLOAK_REALM || "reports-realm",
  clientId: process.env.REACT_APP_KEYCLOAK_CLIENT_ID || "reports-frontend"
};

const keycloak = new Keycloak(keycloakConfig);

// Настройки инициализации с поддержкой PKCE
const initOptions: KeycloakInitOptions = {
  onLoad: 'check-sso',
  checkLoginIframe: false,
  pkceMethod: 'S256' // Включение поддержки PKCE (SHA256)
};

const App: React.FC = () => {
  return (
    <ReactKeycloakProvider 
      authClient={keycloak} 
      initOptions={initOptions}
    >
      <div className="App">
        <ReportPage />
      </div>
    </ReactKeycloakProvider>
  );
};

export default App;