import assert from 'node:assert/strict';
import test from 'node:test';
import { Wallet } from 'ethers';

import { loadConfig, validateAddress } from './config.js';
import { resolveHighestTierFromBalances } from './ownership.js';
import { SessionStore } from './session.js';
import { NonceStore, normalizeWallet, verifyWalletSignature } from './wallet.js';

test('rejects an invalid wallet', () => {
  assert.equal(normalizeWallet('not-a-wallet'), null);
  assert.equal(validateAddress('0x1234'), null);
});

test('expires and consumes nonces exactly once', () => {
  const store = new NonceStore();
  const wallet = '0x8624CF5Aa8c6528Ea22C10e5885E9EC122bb541b';
  const challenge = store.create(wallet, 1_000);
  assert.equal(store.consume(wallet, challenge.nonce, 1_000 + 5 * 60_000), null);

  const fresh = store.create(wallet, 1_000);
  assert.ok(store.consume(wallet, fresh.nonce, 1_001));
  assert.equal(store.consume(wallet, fresh.nonce, 1_002), null);
});

test('rejects a signature from a different wallet', async () => {
  const requestedWallet = Wallet.createRandom();
  const otherWallet = Wallet.createRandom();
  const store = new NonceStore();
  const challenge = store.create(requestedWallet.address, Date.now());
  const signature = await otherWallet.signMessage(challenge.message);
  assert.equal(verifyWalletSignature(challenge, signature), false);
});

test('expires sessions', () => {
  const store = new SessionStore();
  const session = store.create('0x8624CF5Aa8c6528Ea22C10e5885E9EC122bb541b', 1_000);
  assert.equal(store.get(session.token, 1_000 + 15 * 60_000), null);
});

test('resolves zero balances to NONE', async () => {
  assert.equal(await resolveHighestTierFromBalances({}), 'NONE');
});

test('resolves every hierarchy tier', async () => {
  assert.equal(await resolveHighestTierFromBalances({ BRONZE: 1n }), 'BRONZE');
  assert.equal(await resolveHighestTierFromBalances({ BRONZE: 1n, SILVER: 1n }), 'SILVER');
  assert.equal(await resolveHighestTierFromBalances({ GOLD: 1n, SILVER: 1n }), 'GOLD');
  assert.equal(await resolveHighestTierFromBalances({ QUANT: 1n, GOLD: 1n }), 'QUANT');
  assert.equal(await resolveHighestTierFromBalances({ FOUNDER: 1n, QUANT: 1n }), 'FOUNDER');
});

test('fails closed when RPC configuration is absent', () => {
  assert.equal(loadConfig({}), null);
});
