import { createServer } from 'node:http';

import { loadConfig } from './config.js';
import { PolygonErc1155OwnershipResolver } from './ownership.js';
import { handleRequest } from './routes.js';
import { FixedWindowRateLimiter } from './security.js';
import { SessionStore } from './session.js';
import { NonceStore } from './wallet.js';

const config = loadConfig();
if (!config) {
  throw new Error('Invalid verifier configuration: set POLYGON_RPC_URL and valid SPMG access configuration.');
}

const dependencies = {
  config,
  nonceStore: new NonceStore(),
  sessionStore: new SessionStore(),
  ownership: new PolygonErc1155OwnershipResolver(config),
  rateLimiter: new FixedWindowRateLimiter(),
};

createServer((request, response) => {
  void handleRequest(request, response, dependencies);
}).listen(config.port, '0.0.0.0', () => {
  console.log(`SPMG access verifier listening on 0.0.0.0:${config.port}`);
});
