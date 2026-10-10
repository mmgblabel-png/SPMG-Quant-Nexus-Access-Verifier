import { randomBytes } from 'node:crypto';

export interface WalletSession {
  wallet: string;
  token: string;
  expiresAt: string;
  expiresAtMs: number;
}

export class SessionStore {
  private readonly sessions = new Map<string, WalletSession>();

  public create(wallet: string, now = Date.now()): WalletSession {
    this.prune(now);
    const expiresAtMs = now + 15 * 60_000;
    const session: WalletSession = {
      wallet,
      token: randomBytes(32).toString('base64url'),
      expiresAt: new Date(expiresAtMs).toISOString(),
      expiresAtMs,
    };
    this.sessions.set(session.token, session);
    return session;
  }

  public get(token: string | undefined, now = Date.now()): WalletSession | null {
    if (!token) return null;
    const session = this.sessions.get(token);
    if (!session || session.expiresAtMs <= now) {
      this.sessions.delete(token);
      return null;
    }
    return session;
  }

  private prune(now: number): void {
    for (const [token, session] of this.sessions) {
      if (session.expiresAtMs <= now) this.sessions.delete(token);
    }
  }
}
