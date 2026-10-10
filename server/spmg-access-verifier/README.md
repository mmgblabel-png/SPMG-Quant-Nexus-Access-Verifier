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

Use `.env.example` as the variable template. Keep the RPC URL server-side. The collection contract and token IDs are public configuration, but they are still validated at boot.

## Local commands

```bash
npm install
npm run typecheck
npm run build
npm test
npm start
```

## Endpoints

- `GET /health`
- `POST /api/spmg/wallet/challenge`
- `POST /api/spmg/wallet/verify`
- `GET /api/spmg/session/:token`
- `GET /api/spmg/access?sessionToken=...`

## Railway

Deploy this repository with the service root directory set to:

```
/server/spmg-access-verifier
```

Use the included Dockerfile and configure:

- `POLYGON_RPC_URL`
- `SPMG_ACCESS_CONTRACT`
- `SPMG_TOKEN_BRONZE`
- `SPMG_TOKEN_SILVER`
- `SPMG_TOKEN_GOLD`
- `SPMG_TOKEN_QUANT`
- `SPMG_TOKEN_FOUNDER`
- `ALLOWED_ORIGINS`
- `PORT`

Set the Railway healthcheck path to `/health`. Do not commit live RPC credentials.
