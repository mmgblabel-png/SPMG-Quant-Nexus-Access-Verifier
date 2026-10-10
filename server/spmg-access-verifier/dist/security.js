export class FixedWindowRateLimiter {
    entries = new Map();
    allow(key, now = Date.now(), limit = 30, windowMs = 60_000) {
        const current = this.entries.get(key);
        if (!current || current.resetAt <= now) {
            this.entries.set(key, { count: 1, resetAt: now + windowMs });
            return true;
        }
        if (current.count >= limit)
            return false;
        current.count += 1;
        return true;
    }
}
export function clientKey(request) {
    const forwarded = request.headers['x-forwarded-for'];
    const first = Array.isArray(forwarded) ? forwarded[0] : forwarded?.split(',')[0];
    return first?.trim() || request.socket.remoteAddress || 'unknown';
}
export function applyCors(request, response, origins) {
    const origin = request.headers.origin;
    if (!origin)
        return true;
    if (!origins.has(origin))
        return false;
    response.setHeader('Access-Control-Allow-Origin', origin);
    response.setHeader('Vary', 'Origin');
    response.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    response.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    return true;
}
export async function readJsonBody(request) {
    const chunks = [];
    let size = 0;
    for await (const chunk of request) {
        const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
        size += buffer.length;
        if (size > 16_384)
            throw new Error('Request body too large');
        chunks.push(buffer);
    }
    return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}
export function sendJson(response, status, body) {
    response.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
    response.end(JSON.stringify(body));
}
