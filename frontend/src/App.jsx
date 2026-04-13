import React from 'react';
import { Routes, Route } from 'react-router-dom';
import './assets/css/custom.css';
import { AuthProvider } from './contexts/AuthContext';
import { MessageProvider } from './contexts/MessageContext';
import ScrollRestoration from './components/ScrollRestoration';

//auth
import BaseAuth from './pages/auth/BaseAuth';
import Login from './pages/auth/Login';
import Logout from './pages/auth/Logout';
import Register from './pages/auth/Register';
import ActivateAccount from './pages/auth/ActivateAccount';
import PasswordReset from './pages/auth/PasswordReset';
import PasswordResetConfirm from './pages/auth/PasswordResetConfirm';
import ActivateConfirm from './pages/auth/ActivateConfirm';
//settings
import Settings from './pages/settings/Settings';
import VerifyEmail from './pages/settings/VerifyEmail';

//partials
import Header from './partials/Header';
import Footer from './partials/Footer';
import Home from './pages/Home';
import NotFound from './pages/NotFound';

//pages
import Capabilities from './pages/Capabilities';
import CapabilityNodes from './pages/CapabilityNodes';
import NodeDetail from './pages/NodeDetail';
import User from './pages/User';
import UserNodes from './components/UserNodes';
import ActiveProjects from './pages/ActiveProjects';
import HomeFeed from './pages/HomeFeed';
import Trending from './pages/Trending';
import Leaderboard from './pages/Leaderboard';
import ResearchLandscape from './pages/ResearchLandscape';
import SearchResults from './pages/SearchResults';
import PaperDetail from './pages/PaperDetail';
import Dashboard from './pages/Dashboard';
import Library from './pages/Library';



// Layout component for non-auth pages
const MainLayout = ({ children }) => (
  <div className="flex flex-col min-h-screen">
    <Header />
    <main className="flex-grow bg-zinc-800">{children}</main>
    <Footer />
  </div>
);

function App() {
  return (
    <AuthProvider>
        <ScrollRestoration />
        <MessageProvider>
          <Routes>
            {/* Auth routes */}
            <Route path="/register" element={
              
              <BaseAuth>
                <Register />
              </BaseAuth>
            
            } />
            <Route path="/login" element={
              
                <BaseAuth>
                  <Login />
                </BaseAuth>
              
            } />
            <Route path="/logout" element={
              
                <BaseAuth>
                  <Logout />
                </BaseAuth>
              
            } />
            <Route path="/activate-confirm" element={

              <BaseAuth>
                <ActivateConfirm />
              </BaseAuth>

              } />
            <Route path="/activate/:uidb64/:token" element={

              <BaseAuth>
                <ActivateAccount />
              </BaseAuth>
              
              } />
            <Route path="/password-reset" element={

              <BaseAuth>
                <PasswordReset />
              </BaseAuth>

              } />
              <Route path="/verify-email/:uidb64/:token/:signedEmail" element={

                <BaseAuth>
                  <VerifyEmail />
                </BaseAuth>

                } />
            {/* Settings route */}
            <Route path="/settings" element={ <Settings/> } />
            <Route path="/password-reset-confirm/:uid/:token" element={

              <BaseAuth>
                <PasswordResetConfirm />
              </BaseAuth>

              } />

            {/* Dashboard Route */}
            <Route path="/dashboard" element={
              <MainLayout>
                <Dashboard />
              </MainLayout>
            } />

            {/* Non-auth routes */}
            <Route path="/" element={
                <Home />
            } />
            <Route path="*" element={
              <MainLayout>
                <NotFound />
              </MainLayout>
            } />
            <Route path="/categories" element={
              <MainLayout>
                <Capabilities />
              </MainLayout>
            } />
            <Route path="/categories/:slug" element={
              <MainLayout>
                <CapabilityNodes />
              </MainLayout>
              } />
            <Route path="/explore" element={
              <MainLayout>
                <CapabilityNodes />
              </MainLayout>
              } />
            <Route path="/node/:id" element={
              <MainLayout>
                <NodeDetail />
              </MainLayout>
              } />
              <Route path="/user/:userId" element={
              <MainLayout>
                <User />
              </MainLayout>
              } />
              <Route path="/library" element={
              <MainLayout>
                <Library />
              </MainLayout>
              } />
              <Route path="/active-assignments" element={
              <MainLayout>
                <ActiveProjects />
              </MainLayout>
              } />

              <Route path="/home-feed" element={
                <MainLayout>
                  <HomeFeed />
                </MainLayout>
              } />

              <Route path="/trending" element={
                <MainLayout>
                  <Trending />
                </MainLayout>
              } />

              <Route path="/leaderboard" element={
                <MainLayout>
                  <Leaderboard />
                </MainLayout>
              } />

              <Route path="/research-landscape" element={
                <MainLayout>
                  <ResearchLandscape />
                </MainLayout>
              } />
              <Route path="/search" element={
                <MainLayout>
                  <SearchResults />
                </MainLayout>
              } />
              <Route path="/paper/:id" element={
                <MainLayout>
                  <PaperDetail />
                </MainLayout>
              } />
          </Routes>
        </MessageProvider>
      </AuthProvider>
  );
}

export default App;
