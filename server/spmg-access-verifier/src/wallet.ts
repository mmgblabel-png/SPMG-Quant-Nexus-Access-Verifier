import { randomBytes } from 'node:crypto';
import { getAddress, verifyMessage } from 'ethers';

export interface Challenge {
  wallet: string;
  nonce: string;
  message: string;
  expiresAt: string;
}

interface StoredChallenge extends Challenge {
  expiresAtMs: number;
}

export class NonceStore {
  private readonly challenges = new Map<string, StoredChallenge>();

  public create(wallet: string, now = Date.now()): Challenge {
    this.prune(now);
    const nonce = randomBytes(32).toString('base64url');
    const expiresAtMs = now + 5 * 60_000;
    const expiresAt = new Date(expiresAtMs).toISOString();
    const message = [
      'SPMG Quant Nexus wallet verification',
      `Wallet: ${wallet}`,
      `Nonce: ${nonce}`,
      `Expires: ${expiresAt}`,
      'Signing verifies wallet control only. It does not create a transaction.',
    ].join('\n');
    const challenge: StoredChallenge = { wallet, nonce, message, expiresAt, expiresAtMs };
    this.challenges.set(nonce, challenge);
    return challenge;
  }

  /** Reads and consumes a nonce exactly once before signature validation. */
  public consume(wallet: string, nonce: string, now = Date.now()): StoredChallenge | null {
    const challenge = this.challenges.get(nonce);
    this.challenges.delete(nonce);
    if (!challenge || challenge.expiresAtMs <= now || challenge.wallet !== wallet) {
      return null;
    }
    return challenge;
  }

  private prune(now: number): void {
    for (const [nonce, challenge] of this.challenges) {
      if (challenge.expiresAtMs <= now) this.challenges.delete(nonce);
    }
  }
}

export function normalizeWallet(value: string | undefined): string | null {
  try {
    return value && /^0x[0-9a-fA-F]{40}$/.test(value.trim()) ? getAddress(value.trim()) : null;
  } catch {
    return null;
  }
}

export function verifyWalletSignature(challenge: Challenge, signature: string): boolean {
  try {
    return getAddress(verifyMessage(challenge.message, signature)) === challenge.wallet;
  } catch {
    return false;
  }
}
