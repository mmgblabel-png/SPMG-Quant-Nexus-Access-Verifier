import { Contract, JsonRpcProvider } from 'ethers';

import type { AccessTier, VerifierConfig } from './config.js';

const ERC1155_ABI = ['function balanceOf(address account, uint256 id) view returns (uint256)'];
const POLYGON_CHAIN_ID = 137n;
const RPC_TIMEOUT_MS = 8_000;

export interface OwnershipResolver {
  resolveHighestTier(wallet: string): Promise<AccessTier>;
}

export class PolygonErc1155OwnershipResolver implements OwnershipResolver {
  private readonly provider: JsonRpcProvider;
  private readonly contract: Contract;

  public constructor(private readonly config: VerifierConfig) {
    this.provider = new JsonRpcProvider(config.polygonRpcUrl, 137, { staticNetwork: true });
    this.contract = new Contract(config.contract, ERC1155_ABI, this.provider);
  }

  public async resolveHighestTier(wallet: string): Promise<AccessTier> {
    try {
      const network = await withTimeout(this.provider.getNetwork());
      if (network.chainId !== POLYGON_CHAIN_ID) return 'NONE';
      for (const tier of ['FOUNDER', 'QUANT', 'GOLD', 'SILVER', 'BRONZE'] as const) {
        const balance = await withTimeout(this.contract.balanceOf(wallet, this.config.tokenIds[tier]));
        if (BigInt(balance) > 0n) return tier;
      }
      return 'NONE';
    } catch {
      return 'NONE';
    }
  }
}

export async function resolveHighestTierFromBalances(
  balances: Partial<Record<Exclude<AccessTier, 'NONE'>, bigint>>,
): Promise<AccessTier> {
  for (const tier of ['FOUNDER', 'QUANT', 'GOLD', 'SILVER', 'BRONZE'] as const) {
    if ((balances[tier] ?? 0n) > 0n) return tier;
  }
  return 'NONE';
}

function withTimeout<T>(promise: Promise<T>): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) => setTimeout(() => reject(new Error('RPC timeout')), RPC_TIMEOUT_MS)),
  ]);
}
