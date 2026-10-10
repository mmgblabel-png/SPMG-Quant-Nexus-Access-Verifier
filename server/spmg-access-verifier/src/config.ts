import { getAddress } from 'ethers';

export const ACCESS_TIERS = ['NONE', 'BRONZE', 'SILVER', 'GOLD', 'QUANT', 'FOUNDER'] as const;
export type AccessTier = (typeof ACCESS_TIERS)[number];
type OwnedTier = Exclude<AccessTier, 'NONE'>;

export interface VerifierConfig {
  port: number;
  polygonRpcUrl: string;
  contract: string;
  tokenIds: Record<OwnedTier, bigint>;
  allowedOrigins: Set<string>;
}

const DEFAULT_CONTRACT = '0x8624CF5Aa8c6528Ea22C10e5885E9EC122bb541b';
const DEFAULT_TOKEN_IDS = {
  BRONZE: '1',
  SILVER: '2',
  GOLD: '3',
  QUANT: '4',
  FOUNDER: '5',
} as const;

/** Returns null until every server-only production value is valid. */
export function loadConfig(env: NodeJS.ProcessEnv = process.env): VerifierConfig | null {
  const polygonRpcUrl = validateHttpsUrl(env.POLYGON_RPC_URL);
  const contract = validateAddress(env.SPMG_ACCESS_CONTRACT ?? DEFAULT_CONTRACT);
  const tokenValues = {
    BRONZE: env.SPMG_TOKEN_BRONZE ?? DEFAULT_TOKEN_IDS.BRONZE,
    SILVER: env.SPMG_TOKEN_SILVER ?? DEFAULT_TOKEN_IDS.SILVER,
    GOLD: env.SPMG_TOKEN_GOLD ?? DEFAULT_TOKEN_IDS.GOLD,
    QUANT: env.SPMG_TOKEN_QUANT ?? DEFAULT_TOKEN_IDS.QUANT,
    FOUNDER: env.SPMG_TOKEN_FOUNDER ?? DEFAULT_TOKEN_IDS.FOUNDER,
  };
  const tokenIds = parseTokenIds(tokenValues);
  const port = parsePort(env.PORT);
  const allowedOrigins = new Set(
    (env.ALLOWED_ORIGINS ?? '').split(',').map(value => value.trim()).filter(Boolean),
  );

  if (!polygonRpcUrl || !contract || !tokenIds || !port) {
    return null;
  }
  return { port, polygonRpcUrl, contract, tokenIds, allowedOrigins };
}

export function validateAddress(value: string | undefined): string | null {
  try {
    return value ? getAddress(value) : null;
  } catch {
    return null;
  }
}

function parseTokenIds(values: Record<OwnedTier, string>): Record<OwnedTier, bigint> | null {
  try {
    const tokenIds = {
      BRONZE: BigInt(values.BRONZE),
      SILVER: BigInt(values.SILVER),
      GOLD: BigInt(values.GOLD),
      QUANT: BigInt(values.QUANT),
      FOUNDER: BigInt(values.FOUNDER),
    };
    const ids = Object.values(tokenIds);
    return ids.every(value => value >= 0n) && new Set(ids.map(String)).size === ids.length
      ? tokenIds
      : null;
  } catch {
    return null;
  }
}

function validateHttpsUrl(value: string | undefined): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' ? url.toString() : null;
  } catch {
    return null;
  }
}

function parsePort(value: string | undefined): number | null {
  const port = Number(value ?? '3000');
  return Number.isInteger(port) && port > 0 && port <= 65_535 ? port : null;
}
