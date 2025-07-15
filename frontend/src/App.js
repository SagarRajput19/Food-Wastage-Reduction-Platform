import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';


function App() {
  const [user, setUser] = useState(null);
  const [currentView, setCurrentView] = useState('login');
  const [loading, setLoading] = useState(false);
  const [token, setToken] = useState(localStorage.getItem('token'));

  // Check if user is logged in on app start
  useEffect(() => {
    if (token) {
      fetchCurrentUser();
    }
  }, [token]);


  const fetchCurrentUser = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        setCurrentView('dashboard');
      } else {
        localStorage.removeItem('token');
        setToken(null);
      }
    } catch (error) {
      console.error('Error fetching user:', error);
      localStorage.removeItem('token');
      setToken(null);
    }
  };

  const handleLogin = async (credentials) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      });

      const data = await response.json();
      if (response.ok) {
        localStorage.setItem('token', data.token);
        setToken(data.token);
        setUser(data.user);
        setCurrentView('dashboard');
      } else {
        alert(data.detail || 'Login failed');
      }
    } catch (error) {
      alert('Login failed. Please try again.');
    }
    setLoading(false);
  };

  const handleRegister = async (userData) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      });

      const data = await response.json();
      if (response.ok) {
        localStorage.setItem('token', data.token);
        setToken(data.token);
        setUser(data.user);
        setCurrentView('dashboard');
      } else {
        alert(data.detail || 'Registration failed');
      }
    } catch (error) {
      alert('Registration failed. Please try again.');
    }
    setLoading(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setCurrentView('login');
  };

  const renderLoginForm = () => (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-xl shadow-lg p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">🍽️ Food Bridge</h1>
          <p className="text-gray-600">Connecting donors with those in need</p>
        </div>

        <form onSubmit={(e) => {
          e.preventDefault();
          const formData = new FormData(e.target);
          handleLogin({
            email: formData.get('email'),
            password: formData.get('password')
          });
        }}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                name="email"
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                placeholder="Enter your email"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <input
                type="password"
                name="password"
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                placeholder="Enter your password"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </div>
        </form>

        <div className="mt-6 text-center">
          <p className="text-gray-600">
            Don't have an account?{' '}
            <button
              onClick={() => setCurrentView('register')}
              className="text-green-600 hover:text-green-700 font-medium"
            >
              Sign up
            </button>
          </p>
        </div>
      </div>
    </div>
  );

  const renderRegisterForm = () => (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-xl shadow-lg p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">🍽️ Food Bridge</h1>
          <p className="text-gray-600">Join the fight against food waste</p>
        </div>

        <form onSubmit={(e) => {
          e.preventDefault();
          const formData = new FormData(e.target);
          handleRegister({
            name: formData.get('name'),
            email: formData.get('email'),
            password: formData.get('password'),
            role: formData.get('role'),
            phone: formData.get('phone'),
            address: formData.get('address'),
            organization: formData.get('organization')
          });
        }}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">I am a:</label>
              <select
                name="role"
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
              >
                <option value="">Select your role</option>
                <option value="donor">Food Donor (Restaurant/Individual)</option>
                <option value="ngo">NGO/Volunteer</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                type="text"
                name="name"
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                placeholder="Your name or business name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                name="email"
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                placeholder="Enter your email"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <input
                type="password"
                name="password"
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                placeholder="Create a password"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Phone (Optional)</label>
              <input
                type="tel"
                name="phone"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                placeholder="Your phone number"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
              <input
                type="text"
                name="address"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                placeholder="Your address"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Organization (Optional)</label>
              <input
                type="text"
                name="organization"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                placeholder="Restaurant/NGO name"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Creating account...' : 'Create Account'}
            </button>
          </div>
        </form>

        <div className="mt-6 text-center">
          <p className="text-gray-600">
            Already have an account?{' '}
            <button
              onClick={() => setCurrentView('login')}
              className="text-green-600 hover:text-green-700 font-medium"
            >
              Sign in
            </button>
          </p>
        </div>
      </div>
    </div>
  );

  if (!user) {
    return currentView === 'login' ? renderLoginForm() : renderRegisterForm();
  }

  // Main Dashboard Component
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-800">🍽️ Food Bridge</h1>
              <span className="ml-4 px-3 py-1 text-xs bg-green-100 text-green-800 rounded-full">
                {user.role === 'donor' ? 'Donor' : 'NGO'}
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-gray-700">Welcome, {user.name}</span>
              <button
                onClick={handleLogout}
                className="text-gray-500 hover:text-gray-700 px-3 py-1 rounded"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {user.role === 'donor' ? (
          <DonorDashboard token={token} />
        ) : (
          <NGODashboard token={token} />
        )}
      </div>
    </div>
  );
}

// Donor Dashboard Component
function DonorDashboard({ token }) {
  const [view, setView] = useState('overview');
  const [listings, setListings] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(false);

  const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

  useEffect(() => {
    fetchListings();
    fetchStats();
  }, []);

  const fetchListings = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/listings`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setListings(data.listings);
      }
    } catch (error) {
      console.error('Error fetching listings:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/dashboard/stats`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const createListing = async (listingData) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/listings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(listingData),
      });

      if (response.ok) {
        alert('Food listing created successfully!');
        fetchListings();
        fetchStats();
        setView('overview');
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to create listing');
      }
    } catch (error) {
      alert('Failed to create listing. Please try again.');
    }
    setLoading(false);
  };

  const markComplete = async (listingId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/listings/${listingId}/complete`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        alert('Pickup marked as complete!');
        fetchListings();
        fetchStats();
      }
    } catch (error) {
      console.error('Error marking complete:', error);
    }
  };

  if (view === 'create') {
    return (
      <div>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-800">Create Food Listing</h2>
          <button
            onClick={() => setView('overview')}
            className="text-gray-600 hover:text-gray-800"
          >
            ← Back to Dashboard
          </button>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <form onSubmit={(e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            createListing({
              title: formData.get('title'),
              description: formData.get('description'),
              quantity: formData.get('quantity'),
              food_type: formData.get('food_type'),
              pickup_address: formData.get('pickup_address'),
              expiry_hours: parseInt(formData.get('expiry_hours')),
              image_url: formData.get('image_url') || null
            });
          }}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Food Title</label>
                <input
                  type="text"
                  name="title"
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                  placeholder="e.g., Fresh Vegetable Biryani"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Quantity</label>
                <input
                  type="text"
                  name="quantity"
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                  placeholder="e.g., 30 plates, 5kg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Food Type</label>
                <select
                  name="food_type"
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                >
                  <option value="">Select type</option>
                  <option value="veg">Vegetarian</option>
                  <option value="non-veg">Non-Vegetarian</option>
                  <option value="both">Both</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Expiry (Hours)</label>
                <select
                  name="expiry_hours"
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                >
                  <option value="">Select expiry time</option>
                  <option value="2">2 hours</option>
                  <option value="4">4 hours</option>
                  <option value="6">6 hours</option>
                  <option value="12">12 hours</option>
                  <option value="24">24 hours</option>
                </select>
              </div>
            </div>
            <div className="mt-6">
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                name="description"
                required
                rows="3"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                placeholder="Describe the food, freshness, any special instructions..."
              ></textarea>
            </div>
            <div className="mt-6">
              <label className="block text-sm font-medium text-gray-700 mb-1">Pickup Address</label>
              <textarea
                name="pickup_address"
                required
                rows="2"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                placeholder="Full pickup address with landmarks"
              ></textarea>
            </div>
            <div className="mt-6">
              <label className="block text-sm font-medium text-gray-700 mb-1">Image URL (Optional)</label>
              <input
                type="url"
                name="image_url"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                placeholder="https://example.com/food-image.jpg"
              />
            </div>
            <div className="mt-8">
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-green-600 text-white py-3 px-4 rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
              >
                {loading ? 'Creating Listing...' : 'Create Food Listing'}
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Donor Dashboard</h2>
        <button
          onClick={() => setView('create')}
          className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
        >
          + Create Food Listing
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="text-3xl text-blue-500 mr-4">📋</div>
            <div>
              <p className="text-sm text-gray-600">Total Listings</p>
              <p className="text-2xl font-bold text-gray-800">{stats.total_listings || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="text-3xl text-orange-500 mr-4">⏰</div>
            <div>
              <p className="text-sm text-gray-600">Active Listings</p>
              <p className="text-2xl font-bold text-gray-800">{stats.active_listings || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="text-3xl text-green-500 mr-4">✅</div>
            <div>
              <p className="text-sm text-gray-600">Completed Pickups</p>
              <p className="text-2xl font-bold text-gray-800">{stats.completed_pickups || 0}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Listings */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b">
          <h3 className="text-lg font-semibold text-gray-800">Your Food Listings</h3>
        </div>
        <div className="p-6">
          {listings.length === 0 ? (
            <div className="text-center py-8">
              <div className="text-4xl mb-4">🍽️</div>
              <p className="text-gray-600">No food listings yet. Create your first listing to help reduce food waste!</p>
            </div>
          ) : (
            <div className="space-y-4">
              {listings.map((listing) => (
                <div key={listing.listing_id} className="border rounded-lg p-4">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h4 className="font-semibold text-gray-800">{listing.title}</h4>
                      <p className="text-gray-600 mt-1">{listing.description}</p>
                      <div className="mt-2 flex flex-wrap gap-2 text-sm">
                        <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded">
                          {listing.quantity}
                        </span>
                        <span className="bg-green-100 text-green-800 px-2 py-1 rounded">
                          {listing.food_type}
                        </span>
                        <span className="bg-orange-100 text-orange-800 px-2 py-1 rounded">
                          {listing.hours_remaining}h remaining
                        </span>
                      </div>
                      <p className="text-sm text-gray-500 mt-2">📍 {listing.pickup_address}</p>
                    </div>
                    <div className="ml-4 text-right">
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                        listing.status === 'available' ? 'bg-green-100 text-green-800' :
                        listing.status === 'requested' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {listing.status}
                      </span>
                      {listing.status === 'requested' && (
                        <button
                          onClick={() => markComplete(listing.listing_id)}
                          className="block mt-2 bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700"
                        >
                          Mark Complete
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// NGO Dashboard Component
function NGODashboard({ token }) {
  const [listings, setListings] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(false);

  const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

  useEffect(() => {
    fetchListings();
    fetchStats();
  }, []);

  const fetchListings = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/listings`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setListings(data.listings);
      }
    } catch (error) {
      console.error('Error fetching listings:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/dashboard/stats`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const requestPickup = async (listingId, message = '') => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/listings/${listingId}/request`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ listing_id: listingId, message }),
      });

      if (response.ok) {
        alert('Pickup request sent successfully!');
        fetchListings();
        fetchStats();
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to send request');
      }
    } catch (error) {
      alert('Failed to send request. Please try again.');
    }
    setLoading(false);
  };

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800">NGO Dashboard</h2>
        <p className="text-gray-600">Browse available food donations in your area</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="text-3xl text-blue-500 mr-4">📨</div>
            <div>
              <p className="text-sm text-gray-600">Total Requests</p>
              <p className="text-2xl font-bold text-gray-800">{stats.total_requests || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="text-3xl text-green-500 mr-4">✅</div>
            <div>
              <p className="text-sm text-gray-600">Accepted Requests</p>
              <p className="text-2xl font-bold text-gray-800">{stats.accepted_requests || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="text-3xl text-orange-500 mr-4">🚚</div>
            <div>
              <p className="text-sm text-gray-600">Completed Pickups</p>
              <p className="text-2xl font-bold text-gray-800">{stats.completed_pickups || 0}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Available Food Listings */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b">
          <h3 className="text-lg font-semibold text-gray-800">Available Food Donations</h3>
        </div>
        <div className="p-6">
          {listings.length === 0 ? (
            <div className="text-center py-8">
              <div className="text-4xl mb-4">🔍</div>
              <p className="text-gray-600">No food donations available at the moment. Check back soon!</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {listings.map((listing) => (
                <div key={listing.listing_id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                  {listing.image_url && (
                    <img
                      src={listing.image_url}
                      alt={listing.title}
                      className="w-full h-48 object-cover rounded-lg mb-4"
                    />
                  )}
                  <h4 className="font-semibold text-gray-800 mb-2">{listing.title}</h4>
                  <p className="text-gray-600 text-sm mb-3">{listing.description}</p>
                  
                  <div className="space-y-2 mb-4">
                    <div className="flex items-center text-sm">
                      <span className="text-gray-500 w-20">Quantity:</span>
                      <span className="text-gray-800">{listing.quantity}</span>
                    </div>
                    <div className="flex items-center text-sm">
                      <span className="text-gray-500 w-20">Type:</span>
                      <span className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">
                        {listing.food_type}
                      </span>
                    </div>
                    <div className="flex items-center text-sm">
                      <span className="text-gray-500 w-20">Expires:</span>
                      <span className="text-orange-600 font-medium">
                        {listing.hours_remaining}h remaining
                      </span>
                    </div>
                    <div className="flex items-center text-sm">
                      <span className="text-gray-500 w-20">By:</span>
                      <span className="text-gray-800">{listing.posted_by_name}</span>
                    </div>
                  </div>

                  <div className="text-sm text-gray-600 mb-4">
                    <p><strong>📍 Pickup Address:</strong></p>
                    <p className="text-xs">{listing.pickup_address}</p>
                  </div>

                  <button
                    onClick={() => {
                      const message = prompt("Add a message with your request (optional):");
                      if (message !== null) {
                        requestPickup(listing.listing_id, message);
                      }
                    }}
                    disabled={loading}
                    className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                  >
                    {loading ? 'Requesting...' : 'Request Pickup'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;