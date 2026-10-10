import type { IncomingMessage, ServerResponse } from 'node:http';
import { URL } from 'node:url';

import type { VerifierConfig } from './config.js';
import type { OwnershipResolver } from './ownership.js';
import { applyCors, clientKey, FixedWindowRateLimiter, readJsonBody, sendJson } from './security.js';
import { SessionStore } from './session.js';
import { NonceStore, normalizeWallet, verifyWalletSignature } from './wallet.js';

export interface RouteDependencies {
  config: VerifierConfig;
  nonceStore: NonceStore;
  sessionStore: SessionStore;
  ownership: OwnershipResolver;
  rateLimiter: FixedWindowRateLimiter;
}

export async function handleRequest(
  request: IncomingMessage,
  response: ServerResponse,
  dependencies: RouteDependencies,
): Promise<void> {
  if (!applyCors(request, response, dependencies.config.allowedOrigins)) {
    return sendJson(response, 403, { error: 'origin_not_allowed' });
  }
  if (request.method === 'OPTIONS') {
    response.writeHead(204);
    response.end();
    return;
  }
  if (!dependencies.rateLimiter.allow(clientKey(request))) {
    return sendJson(response, 429, { error: 'rate_limited' });
  }

  const url = new URL(request.url ?? '/', 'https://spmg-verifier.invalid');
  try {
    if (request.method === 'POST' && url.pathname === '/api/spmg/wallet/challenge') {
      return await challenge(request, response, dependencies);
    }
    if (request.method === 'POST' && url.pathname === '/api/spmg/wallet/verify') {
      return await verify(request, response, dependencies);
    }
    if (request.method === 'GET' && url.pathname.startsWith('/api/spmg/session/')) {
      return session(response, dependencies, decodeURIComponent(url.pathname.slice('/api/spmg/session/'.length)));
    }
    if (request.method === 'GET' && url.pathname === '/api/spmg/access') {
      return await access(response, dependencies, url.searchParams.get('sessionToken') ?? undefined);
    }
    return sendJson(response, 404, { error: 'not_found' });
  } catch {
    return sendJson(response, 400, { error: 'invalid_request' });
  }
}

async function challenge(
  request: IncomingMessage,
  response: ServerResponse,
  dependencies: RouteDependencies,
): Promise<void> {
  const body = await readJsonBody(request) as { wallet?: unknown };
  const wallet = normalizeWallet(typeof body.wallet === 'string' ? body.wallet : undefined);
  if (!wallet) return sendJson(response, 400, { error: 'invalid_wallet' });
  const result = dependencies.nonceStore.create(wallet);
  return sendJson(response, 200, result);
}

async function verify(
  request: IncomingMessage,
  response: ServerResponse,
  dependencies: RouteDependencies,
): Promise<void> {
  const body = await readJsonBody(request) as { wallet?: unknown; nonce?: unknown; signature?: unknown };
  const wallet = normalizeWallet(typeof body.wallet === 'string' ? body.wallet : undefined);
  const nonce = typeof body.nonce === 'string' ? body.nonce : '';
  const signature = typeof body.signature === 'string' ? body.signature : '';
  if (!wallet || !nonce || !signature) return sendJson(response, 400, { error: 'invalid_verification_input' });

  const challenge = dependencies.nonceStore.consume(wallet, nonce);
  if (!challenge || !verifyWalletSignature(challenge, signature)) {
    return sendJson(response, 401, { verified: false, error: 'verification_failed' });
  }
  const walletSession = dependencies.sessionStore.create(wallet);
  return sendJson(response, 200, {
    verified: true,
    sessionToken: walletSession.token,
    expiresAt: walletSession.expiresAt,
  });
}

function session(response: ServerResponse, dependencies: RouteDependencies, token: string): void {
  const walletSession = dependencies.sessionStore.get(token);
  if (!walletSession) {
    return sendJson(response, 401, { connected: false, wallet: null, verification: 'FAILED' });
  }
  return sendJson(response, 200, {
    connected: true,
    wallet: walletSession.wallet,
    verification: 'VERIFIED',
  });
}

async function access(response: ServerResponse, dependencies: RouteDependencies, token: string | undefined): Promise<void> {
  const walletSession = dependencies.sessionStore.get(token);
  if (!walletSession) {
    return sendJson(response, 401, {
      wallet: null,
      tier: 'NONE',
      verified: false,
      checkedAt: new Date().toISOString(),
    });
  }
  const tier = await dependencies.ownership.resolveHighestTier(walletSession.wallet);
  return sendJson(response, 200, {
    wallet: walletSession.wallet,
    tier,
    verified: true,
    checkedAt: new Date().toISOString(),
  });
}
