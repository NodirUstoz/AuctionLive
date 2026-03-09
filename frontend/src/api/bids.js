import client from './client';

const bidsAPI = {
  /**
   * Place a bid on an auction.
   */
  placeBid: (auctionId, amount) =>
    client.post('/bids/', { auction_id: auctionId, amount }),

  /**
   * Get bid history for an auction.
   */
  getAuctionBids: (auctionId, params = {}) =>
    client.get(`/bids/auction/${auctionId}/`, { params }),

  /**
   * Get bid audit history for an auction.
   */
  getBidHistory: (auctionId, params = {}) =>
    client.get(`/bids/auction/${auctionId}/history/`, { params }),

  /**
   * Get the current user's bids.
   */
  getMyBids: (params = {}) => client.get('/bids/my-bids/', { params }),

  /**
   * Create or update an auto-bid.
   */
  createAutoBid: (auctionId, maxAmount, increment) =>
    client.post('/bids/auto-bid/', {
      auction_id: auctionId,
      max_amount: maxAmount,
      increment,
    }),

  /**
   * List the user's auto-bids.
   */
  getAutoBids: () => client.get('/bids/auto-bid/list/'),

  /**
   * Deactivate an auto-bid.
   */
  deactivateAutoBid: (autoBidId) =>
    client.delete(`/bids/auto-bid/${autoBidId}/`),
};

export default bidsAPI;
