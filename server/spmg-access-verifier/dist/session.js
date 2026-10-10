import { randomBytes } from 'node:crypto';
export class SessionStore {
    sessions = new Map();
    create(wallet, now = Date.now()) {
        this.prune(now);
        const expiresAtMs = now + 15 * 60_000;
        const session = {
            wallet,
            token: randomBytes(32).toString('base64url'),
            expiresAt: new Date(expiresAtMs).toISOString(),
            expiresAtMs,
        };
        this.sessions.set(session.token, session);
        return session;
    }
    get(token, now = Date.now()) {
        if (!token)
            return null;
        const session = this.sessions.get(token);
        if (!session || session.expiresAtMs <= now) {
            this.sessions.delete(token);
            return null;
        }
        return session;
    }
    prune(now) {
        for (const [token, session] of this.sessions) {
            if (session.expiresAtMs <= now)
                this.sessions.delete(token);
        }
    }
}
