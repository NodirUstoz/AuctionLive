import client from './client';

const authAPI = {
  /**
   * Register a new user.
   */
  register: (data) => client.post('/auth/register/', data),

  /**
   * Log in and get JWT tokens.
   */
  login: (email, password) =>
    client.post('/auth/login/', { email, password }),

  /**
   * Refresh the access token.
   */
  refresh: (refreshToken) =>
    client.post('/auth/refresh/', { refresh: refreshToken }),

  /**
   * Log out (blacklist the refresh token).
   */
  logout: (refreshToken) =>
    client.post('/auth/logout/', { refresh: refreshToken }),

  /**
   * Get the authenticated user's profile.
   */
  getProfile: () => client.get('/auth/profile/'),

  /**
   * Update the authenticated user's profile.
   */
  updateProfile: (data) => {
    if (data instanceof FormData) {
      return client.patch('/auth/profile/', data, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    }
    return client.patch('/auth/profile/', data);
  },

  /**
   * Get seller profile.
   */
  getSellerProfile: () => client.get('/auth/profile/seller/'),

  /**
   * Update seller profile.
   */
  updateSellerProfile: (data) => client.patch('/auth/profile/seller/', data),

  /**
   * Change password.
   */
  changePassword: (oldPassword, newPassword) =>
    client.put('/auth/change-password/', {
      old_password: oldPassword,
      new_password: newPassword,
    }),
};

export default authAPI;
