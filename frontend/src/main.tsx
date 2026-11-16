import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import './styles/fonts.css';
import './engine/tokens.css';
import './engine/engine.css';
import './styles/app.css';
import './styles/login.css';
import './styles/dashboard.css';
import './styles/workspace.css';
import './styles/transcript.css';
import './styles/settings.css';
import './styles/notfound.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
