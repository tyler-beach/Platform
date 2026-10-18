import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './site.jsx';
import DemoGate from './components/DemoGate.jsx';
import './styles.css';
import { BASE_URL } from './content.js';

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter basename={BASE_URL.replace(/\/$/, '')}>
      <DemoGate>
        <App />
      </DemoGate>
    </BrowserRouter>
  </React.StrictMode>,
);
