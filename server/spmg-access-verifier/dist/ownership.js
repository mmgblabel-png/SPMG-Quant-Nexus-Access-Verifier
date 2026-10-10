import { Contract, JsonRpcProvider } from 'ethers';
const ERC1155_ABI = ['function balanceOf(address account, uint256 id) view returns (uint256)'];
const POLYGON_CHAIN_ID = 137n;
const RPC_TIMEOUT_MS = 8_000;
export class PolygonErc1155OwnershipResolver {
    config;
    provider;
    contract;
    constructor(config) {
        this.config = config;
        this.provider = new JsonRpcProvider(config.polygonRpcUrl, 137, { staticNetwork: true });
        this.contract = new Contract(config.contract, ERC1155_ABI, this.provider);
    }
    async resolveHighestTier(wallet) {
        try {
            const network = await withTimeout(this.provider.getNetwork());
            if (network.chainId !== POLYGON_CHAIN_ID)
                return 'NONE';
            for (const tier of ['FOUNDER', 'QUANT', 'GOLD', 'SILVER', 'BRONZE']) {
                const balance = await withTimeout(this.contract.balanceOf(wallet, this.config.tokenIds[tier]));
                if (BigInt(balance) > 0n)
                    return tier;
            }
            return 'NONE';
        }
        catch {
            return 'NONE';
        }
    }
}
export async function resolveHighestTierFromBalances(balances) {
    for (const tier of ['FOUNDER', 'QUANT', 'GOLD', 'SILVER', 'BRONZE']) {
        if ((balances[tier] ?? 0n) > 0n)
            return tier;
    }
    return 'NONE';
}
function withTimeout(promise) {
    return Promise.race([
        promise,
        new Promise((_, reject) => setTimeout(() => reject(new Error('RPC timeout')), RPC_TIMEOUT_MS)),
    ]);
}
