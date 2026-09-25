/*
Generic Solstice / Clique Lock claim simulation.

Privacy:
- no wallet address is hard-coded;
- no stream/account IDs are committed;
- no private key is used;
- simulation only.

Required environment variables:
  WALLET
  PROGRAM
  STREAM
  TOKEN_MINT
  STREAM_VAULT
  NFT_BINDING
  NFT_HOLDER_ATA
  STREAM_ID

Optional:
  RPC_URL (defaults to a public Solana RPC)

Example:
  WALLET=... PROGRAM=... STREAM=... TOKEN_MINT=... \
  STREAM_VAULT=... NFT_BINDING=... NFT_HOLDER_ATA=... STREAM_ID=... \
  node scripts/solstice-simulate-claim.mjs
*/

import {
  Connection,
  PublicKey,
  TransactionInstruction,
  TransactionMessage,
  VersionedTransaction,
  ComputeBudgetProgram
} from "@solana/web3.js";

const required = [
  "WALLET",
  "PROGRAM",
  "STREAM",
  "TOKEN_MINT",
  "STREAM_VAULT",
  "NFT_BINDING",
  "NFT_HOLDER_ATA",
  "STREAM_ID"
];

for (const key of required) {
  if (!process.env[key]) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
}

const RPC = process.env.RPC_URL || "https://solana-rpc.publicnode.com";

const WALLET = new PublicKey(process.env.WALLET);
const PROGRAM = new PublicKey(process.env.PROGRAM);
const STREAM = new PublicKey(process.env.STREAM);
const TOKEN_MINT = new PublicKey(process.env.TOKEN_MINT);
const STREAM_VAULT = new PublicKey(process.env.STREAM_VAULT);
const NFT_BINDING = new PublicKey(process.env.NFT_BINDING);
const NFT_HOLDER_ATA = new PublicKey(process.env.NFT_HOLDER_ATA);
const STREAM_ID = new PublicKey(process.env.STREAM_ID);

const ATA_PROGRAM = new PublicKey(
  "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
);
const SYSTEM_PROGRAM = new PublicKey(
  "11111111111111111111111111111111"
);
const TOKEN_PROGRAM = new PublicKey(
  "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
);

const connection = new Connection(RPC, "confirmed");

const [RECIPIENT_ATA] = PublicKey.findProgramAddressSync(
  [WALLET.toBuffer(), TOKEN_PROGRAM.toBuffer(), TOKEN_MINT.toBuffer()],
  ATA_PROGRAM
);

console.log("Derived recipient ATA:", RECIPIENT_ATA.toBase58());

const ataInfo = await connection.getAccountInfo(RECIPIENT_ATA, "confirmed");
console.log("Recipient ATA:", ataInfo ? "EXISTS" : "MISSING");

const createAtaIx = new TransactionInstruction({
  programId: ATA_PROGRAM,
  keys: [
    { pubkey: WALLET, isSigner: true, isWritable: true },
    { pubkey: RECIPIENT_ATA, isSigner: false, isWritable: true },
    { pubkey: WALLET, isSigner: false, isWritable: false },
    { pubkey: TOKEN_MINT, isSigner: false, isWritable: false },
    { pubkey: SYSTEM_PROGRAM, isSigner: false, isWritable: false },
    { pubkey: TOKEN_PROGRAM, isSigner: false, isWritable: false }
  ],
  data: Buffer.alloc(0)
});

const claimData = Buffer.concat([
  Buffer.from([62, 198, 214, 193, 213, 159, 108, 210]),
  STREAM_ID.toBuffer()
]);

const claimIx = new TransactionInstruction({
  programId: PROGRAM,
  keys: [
    { pubkey: STREAM, isSigner: false, isWritable: true },
    { pubkey: RECIPIENT_ATA, isSigner: false, isWritable: true },
    { pubkey: TOKEN_MINT, isSigner: false, isWritable: false },
    { pubkey: STREAM_VAULT, isSigner: false, isWritable: true },
    { pubkey: TOKEN_PROGRAM, isSigner: false, isWritable: false },
    { pubkey: NFT_BINDING, isSigner: false, isWritable: false },
    { pubkey: NFT_HOLDER_ATA, isSigner: false, isWritable: false }
  ],
  data: claimData
});

const instructions = [];
if (!ataInfo) instructions.push(createAtaIx);

instructions.push(
  claimIx,
  ComputeBudgetProgram.setComputeUnitLimit({ units: 200000 }),
  ComputeBudgetProgram.setComputeUnitPrice({ microLamports: 200000 })
);

const { blockhash } = await connection.getLatestBlockhash("confirmed");

const message = new TransactionMessage({
  payerKey: WALLET,
  recentBlockhash: blockhash,
  instructions
}).compileToV0Message();

const tx = new VersionedTransaction(message);

console.log("\nSIMULATE ONLY");
console.log("No signature. No broadcast.");

const result = await connection.simulateTransaction(tx, {
  sigVerify: false,
  replaceRecentBlockhash: true,
  commitment: "confirmed"
});

console.log("\nSIMULATION ERROR:");
console.dir(result.value.err, { depth: null });

console.log("\nPROGRAM LOGS:");
for (const line of result.value.logs || []) {
  console.log(line);
}

console.log("\nUnits consumed:", result.value.unitsConsumed);
