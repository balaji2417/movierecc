import React, { useState } from 'react';
import './App.css';
import { Link, useNavigate } from 'react-router-dom';

function App() {
  const navigate = useNavigate();
  const [userNameError, setUsernameError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [invalidCredentials, setInvalidCredentials] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    const username = e.target.username.value;
    const password = e.target.password.value;
    
    // Reset errors
    setUsernameError("");
    setPasswordError("");
    setInvalidCredentials("");
    
    // Validate
    if (username === "") {
      setUsernameError("Username is required");
      return;
    }
    if (password === "") {
      setPasswordError("Password is required");
      return;
    }
    
    setIsLoading(true);
    
    try {
      const response = await fetch('http://localhost:5000/api/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: username,
          password: password
        }),
      });
      
      const data = await response.json();
      
      if (response.ok) {
        // Save token and user data to localStorage
        localStorage.setItem('token', data.token);
        localStorage.setItem('user', JSON.stringify(data.user));
        
        // Redirect to dashboard
        navigate('/dashboard');
      } else {
        if (data.error_password) {
          setPasswordError(data.error_password);
        }
        if (data.error_username) {
          setUsernameError(data.error_username);
        }
        setInvalidCredentials(data.error);
      }
    } catch (error) {
      console.error('Error during login:', error);
      setInvalidCredentials('Network error. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Card */}
      <div className="relative">
        {/* Title */}
        <div className='text-center mb-8'>
          <h1 className="text-4xl font-bold text-white">🎬 Movie Recommender</h1>
        </div>
        
        {/* Glow effect behind card */}
        <div className="absolute -inset-1 bg-gradient-to-r from-purple-600 to-pink-600 rounded-2xl blur-lg opacity-50"></div>
        
        {/* Main card */}
        <div className="relative bg-slate-900/90 backdrop-blur-sm px-10 py-12 rounded-2xl shadow-2xl border border-slate-700/50 w-96">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="mx-auto w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center mb-4 shadow-lg shadow-purple-500/30">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-white">Welcome Back</h1>
            <p className="text-slate-400 text-sm mt-1">Sign in to continue</p>
          </div>

          {/* Form */}
          <form className="space-y-5" onSubmit={handleLogin}>
            {/* Error Message */}
            {invalidCredentials && (
              <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm text-center">
                {invalidCredentials}
              </div>
            )}
            
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-slate-300 mb-2">
                Username
              </label>
              <input
                type="text"
                id="username"
                name="username"
                className={`w-full px-4 py-3 bg-slate-800/50 border ${userNameError ? 'border-red-500' : 'border-slate-600/50'} rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all duration-200`}
                placeholder="Enter your username"
              />
              {userNameError && <p className="text-xs text-red-400 mt-1">{userNameError}</p>}
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-2">
                Password
              </label>
              <input
                type="password"
                id="password"
                name="password"
                className={`w-full px-4 py-3 bg-slate-800/50 border ${passwordError ? 'border-red-500' : 'border-slate-600/50'} rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all duration-200`}
                placeholder="Enter your password"
              />
              {passwordError && <p className="text-xs text-red-400 mt-1">{passwordError}</p>}
            </div>

            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center text-slate-400 cursor-pointer">
                <input type="checkbox" className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-purple-500 focus:ring-purple-500 focus:ring-offset-0 mr-2" />
                Remember me
              </label>
              <a href="#" className="text-purple-400 hover:text-purple-300 transition-colors">
                Forgot password?
              </a>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 px-4 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-semibold rounded-lg shadow-lg shadow-purple-500/30 transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Signing In...
                </span>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          {/* Footer */}
          <p className="text-center text-slate-400 text-sm mt-8">
            Don't have an account?{' '}
            <Link to="/register" className="text-purple-400 hover:text-purple-300 font-medium transition-colors">
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default App;