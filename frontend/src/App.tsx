import { useEffect, useRef } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './auth/AuthContext';
import { ToastProvider } from './components/Toast';
import { RequireAuth } from './components/RequireAuth';
import { LoginPage } from './pages/Login';
import { DashboardPage } from './pages/Dashboard';
import { WorkspacePage } from './pages/Workspace';
import { TranscriptPage } from './pages/Transcript';
import { SettingsPage } from './pages/Settings';
import { NotFoundPage } from './pages/NotFound';
import { boot, cleanup, enter } from './engine';
import { setupMotion } from './motion/setup';
import { takePendingTransition, transitionNavigate } from './motion/navigate';

function RouterLifecycle() {
  const navigate = useNavigate();
  const location = useLocation();
  const first = useRef(true);
  const popped = useRef(false);

  useEffect(() => {
    const onPop = () => {
      cleanup();
      popped.current = true;
    };
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const target = e.target instanceof Element ? e.target.closest<HTMLAnchorElement>('a') : null;
      if (!target) return;
      const href = target.getAttribute('href');
      if (!href || href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:')) return;
      if (target.target && target.target !== '_self') return;
      if (target.hasAttribute('download')) return;
      let url: URL;
      try {
        url = new URL(href, window.location.href);
      } catch {
        return;
      }
      if (url.origin !== window.location.origin) return;
      if (url.pathname === location.pathname) return;
      e.preventDefault();
      void transitionNavigate(navigate, `${url.pathname}${url.search}${url.hash}`);
    };
    document.addEventListener('click', onClick);
    return () => document.removeEventListener('click', onClick);
  }, [navigate, location.pathname]);

  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    const transition = takePendingTransition();
    const isPop = popped.current;
    popped.current = false;
    void enter({ transition, scrollTop: !isPop }).then(() => {
      document.getElementById('main')?.focus({ preventScroll: true });
    });
  }, [location.pathname]);

  return null;
}

function AppBoot() {
  useEffect(() => {
    setupMotion();
    void boot();
  }, []);
  return null;
}

function MotionSync() {
  const { loading } = useAuth();
  useEffect(() => {
    if (loading) return;
    const frame = requestAnimationFrame(() => {
      const pending = [...document.querySelectorAll<HTMLElement>('[data-intro], [data-reveal], [data-split]')].some(
        (el) => getComputedStyle(el).visibility === 'hidden',
      );
      if (pending) void enter({ transition: false, scrollTop: false });
    });
    return () => cancelAnimationFrame(frame);
  }, [loading]);
  return null;
}

export function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter>
          <AppBoot />
          <MotionSync />
          <RouterLifecycle />
          <div id="curtain" aria-hidden="true">
            <div className="curtain__panel">
              <span className="curtain__label">Routing</span>
              <span className="curtain__label">yt-gpt · local</span>
            </div>
          </div>
          <div id="cursor" aria-hidden="true">
            <span data-cursor-label="" />
          </div>
          <Routes>
            <Route
              path="/"
              element={
                <RequireAuth>
                  <Navigate to="/app" replace />
                </RequireAuth>
              }
            />
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/app"
              element={
                <RequireAuth>
                  <DashboardPage />
                </RequireAuth>
              }
            />
            <Route
              path="/w/:wsId"
              element={
                <RequireAuth>
                  <WorkspacePage />
                </RequireAuth>
              }
            />
            <Route
              path="/w/:wsId/transcript"
              element={
                <RequireAuth>
                  <TranscriptPage />
                </RequireAuth>
              }
            />
            <Route
              path="/settings"
              element={
                <RequireAuth>
                  <SettingsPage />
                </RequireAuth>
              }
            />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  );
}
