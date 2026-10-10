# SPMG Access Verifier

Standalone Node.js service for SPMG Quant Nexus Polygon ERC-1155 ownership checks.

## Security model

- Wallets are verified with a short-lived, one-use signed nonce.
- Sessions are opaque, random, and expire after 15 minutes.
- Polygon RPC is read only and server-side (`POLYGON_RPC_URL`).
- No wallet private keys, transaction signing, transfers, or purchases exist here.
- Missing configuration, invalid sessions, malformed RPC results, and RPC failures resolve to `NONE` / no access.
- Configure `ALLOWED_ORIGINS` explicitly; wildcard origins are not supported.

## Configure

Copy `.env.example` into deployment secrets and set `POLYGON_RPC_URL` to a server-only HTTPS Polygon RPC URL. The public contract and tier IDs are prefilled from the verified project configuration but are still validated at boot.

## Run

```bash
npm install
npm run build
npm start
```

## Endpoints

- `POST /api/spmg/wallet/challenge`
- `POST /api/spmg/wallet/verify`
- `GET /api/spmg/session/:token`
- `GET /api/spmg/access?sessionToken=...`

Deploy behind HTTPS. The service intentionally does not enable or configure the Studio client endpoint; provide that separately after deployment.
