import client from './client';

const auctionsAPI = {
  /**
   * List active auctions with optional filters.
   */
  list: (params = {}) => client.get('/auctions/', { params }),

  /**
   * Get auction detail by slug.
   */
  getBySlug: (slug) => client.get(`/auctions/${slug}/`),

  /**
   * Get auction detail by ID.
   */
  getById: (id) => client.get(`/auctions/${id}/`),

  /**
   * Create a new auction (multipart/form-data for images).
   */
  create: (data) => {
    const formData = new FormData();
    Object.keys(data).forEach((key) => {
      if (key === 'images') {
        data.images.forEach((image) => {
          formData.append('images', image);
        });
      } else {
        formData.append(key, data[key]);
      }
    });
    return client.post('/auctions/create/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  /**
   * Update an auction by slug.
   */
  update: (slug, data) => client.patch(`/auctions/${slug}/`, data),

  /**
   * Delete/cancel an auction by slug.
   */
  delete: (slug) => client.delete(`/auctions/${slug}/`),

  /**
   * List auction categories.
   */
  getCategories: () => client.get('/auctions/categories/'),

  /**
   * Get category detail by slug.
   */
  getCategory: (slug) => client.get(`/auctions/categories/${slug}/`),

  /**
   * Get auctions in a category.
   */
  getCategoryAuctions: (slug, params = {}) =>
    client.get(`/auctions/categories/${slug}/auctions/`, { params }),

  /**
   * Get featured auctions.
   */
  getFeatured: () => client.get('/auctions/featured/'),

  /**
   * Get seller dashboard data.
   */
  getSellerDashboard: () => client.get('/auctions/seller-dashboard/'),

  /**
   * Get seller's own auctions.
   */
  getMyAuctions: (params = {}) =>
    client.get('/auctions/my-auctions/', { params }),

  /**
   * Toggle watchlist for an auction.
   */
  toggleWatchlist: (auctionId) =>
    client.post('/watchlist/toggle/', { auction_id: auctionId }),
};

export default auctionsAPI;
