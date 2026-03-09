import React, { useEffect } from 'react';
import { Route, Routes } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import Header from './components/layout/Header';
import Footer from './components/layout/Footer';
import HomePage from './pages/HomePage';
import AuctionPage from './pages/AuctionPage';
import CategoryPage from './pages/CategoryPage';
import CreateAuctionPage from './pages/CreateAuctionPage';
import SellerDashboard from './pages/SellerDashboard';
import WatchlistPage from './pages/WatchlistPage';
import ProfilePage from './pages/ProfilePage';
import LoginForm from './components/auth/LoginForm';
import RegisterForm from './components/auth/RegisterForm';
import { loadUser } from './store/authSlice';

function App() {
  const dispatch = useDispatch();

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      dispatch(loadUser());
    }
  }, [dispatch]);

  return (
    <div className="app">
      <Header />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/auction/:slug" element={<AuctionPage />} />
          <Route path="/category/:slug" element={<CategoryPage />} />
          <Route path="/create-auction" element={<CreateAuctionPage />} />
          <Route path="/seller-dashboard" element={<SellerDashboard />} />
          <Route path="/watchlist" element={<WatchlistPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/login" element={<LoginForm />} />
          <Route path="/register" element={<RegisterForm />} />
        </Routes>
      </main>
      <Footer />
    </div>
  );
}

export default App;
