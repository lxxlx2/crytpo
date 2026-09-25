#!/usr/bin/env python3
"""
Recover SOL from native WSOL SPL token accounts.

This local tool:
- connects to a browser Solana wallet;
- discovers native WSOL token accounts owned by that wallet;
- lets the user choose which accounts to close;
- re-verifies mint, owner and isNative;
- simulates the transaction first;
- asks the wallet to sign standard SPL Token CloseAccount instructions.

Privacy:
- no wallet address is hard-coded;
- no amount is hard-coded;
- no RPC key is committed;
- no seed phrase or private key is requested.

Usage:
    python3 scripts/solana-wsol-recover.py

Then paste a trusted Solana Mainnet HTTPS RPC URL when prompted and open:
    http://localhost:8765/
"""

import getpass
import json
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8765
RPC_URL = None

HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Solana WSOL Recovery</title>
  <script src="https://cdn.jsdelivr.net/npm/@solana/web3.js@1.98.4/lib/index.iife.min.js"></script>
  <style>
    body { font-family: system-ui,-apple-system,sans-serif; max-width:980px; margin:32px auto; padding:0 18px; line-height:1.55; }
    code,pre { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }
    .box { border:1px solid #ccc; border-radius:12px; padding:16px; margin:14px 0; }
    button { padding:10px 16px; margin:6px 8px 6px 0; font-size:15px; cursor:pointer; }
    table { width:100%; border-collapse:collapse; }
    th,td { text-align:left; border-bottom:1px solid #ddd; padding:8px; vertical-align:top; }
    #log { white-space:pre-wrap; overflow-wrap:anywhere; min-height:180px; }
    .small { font-size:13px; opacity:.8; }
    .warn { font-weight:600; }
  </style>
</head>
<body>
  <h1>Solana WSOL Recovery</h1>

  <div class="box">
    <p>用于处理钱包里能看到 WSOL / SOL，但普通 Swap 无法使用的场景。</p>
    <p>工具只关闭你主动选择的 <strong>native WSOL SPL Token Account</strong>，将其中的 SOL 与账户 rent 退回当前钱包。</p>
    <p class="warn">不会调用 DEX，不会执行市场 Swap，也不会要求私钥或助记词。</p>
  </div>

  <div class="box">
    <button id="connect">1. 连接钱包</button>
    <button id="discover">2. 扫描 WSOL Accounts</button>
    <button id="selectAll">选择全部</button>
    <button id="simulate">3. 重新核验并模拟</button>
    <button id="send">4. 请求钱包签名并发送</button>
    <div class="small">第 4 步仍需要你在钱包扩展中手动确认。</div>
  </div>

  <div class="box">
    <div>当前钱包：<code id="wallet">未连接</code></div>
    <div>选择账户可回收：<strong id="recoverable">0 SOL</strong></div>
  </div>

  <div class="box">
    <strong>发现的 native WSOL accounts</strong>
    <table>
      <thead>
        <tr><th>选择</th><th>Token Account</th><th>WSOL</th><th>账户总 lamports</th></tr>
      </thead>
      <tbody id="accounts"></tbody>
    </table>
  </div>

  <div class="box">
    <strong>日志</strong>
    <pre id="log"></pre>
  </div>

<script>
const { Connection, PublicKey, Transaction, TransactionInstruction } = solanaWeb3;
const connection = new Connection(location.origin + "/rpc", "confirmed");

const TOKEN_PROGRAM = new PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA");
const WSOL_MINT = new PublicKey("So11111111111111111111111111111111111111112");

let provider = null;
let owner = null;
let discovered = [];

function log(x) {
  document.getElementById("log").textContent += String(x) + "\n";
}

function detectProvider() {
  return window.okxwallet?.solana
      || window.phantom?.solana
      || window.backpack?.solana
      || window.solana
      || null;
}

async function connectWallet() {
  provider = detectProvider();
  if (!provider) throw new Error("未检测到 Solana 浏览器钱包。");

  const result = await provider.connect();
  const candidate = provider.publicKey || result?.publicKey || result?.address;
  if (!candidate) throw new Error("钱包已连接，但无法读取 publicKey。");

  owner = new PublicKey(candidate.toString());
  document.getElementById("wallet").textContent = owner.toBase58();
  log("已连接钱包。");
}

async function discoverAccounts() {
  if (!owner) await connectWallet();

  const resp = await connection.getParsedTokenAccountsByOwner(
    owner,
    { mint: WSOL_MINT },
    "confirmed"
  );

  discovered = resp.value
    .map(x => {
      const info = x.account.data?.parsed?.info;
      return {
        pubkey: x.pubkey,
        lamports: x.account.lamports,
        info
      };
    })
    .filter(x =>
      x.info &&
      x.info.isNative === true &&
      x.info.owner === owner.toBase58() &&
      x.info.mint === WSOL_MINT.toBase58()
    );

  render();
  log("发现 " + discovered.length + " 个 native WSOL account。");

  if (!discovered.length) {
    log("没有发现可通过本工具关闭的 native WSOL account。");
  }
}

function render() {
  const tbody = document.getElementById("accounts");
  tbody.innerHTML = "";

  for (const x of discovered) {
    const tr = document.createElement("tr");

    const tdCheck = document.createElement("td");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.dataset.account = x.pubkey.toBase58();
    checkbox.onchange = updateRecoverable;
    tdCheck.appendChild(checkbox);

    const tdAddr = document.createElement("td");
    tdAddr.innerHTML = "<code>" + x.pubkey.toBase58() + "</code>";

    const tdAmount = document.createElement("td");
    tdAmount.textContent = x.info.tokenAmount.uiAmountString + " WSOL";

    const tdLamports = document.createElement("td");
    tdLamports.textContent = (x.lamports / 1e9).toFixed(9) + " SOL";

    tr.append(tdCheck, tdAddr, tdAmount, tdLamports);
    tbody.appendChild(tr);
  }

  updateRecoverable();
}

function selectedAccounts() {
  const selected = new Set(
    [...document.querySelectorAll('input[type="checkbox"][data-account]:checked')]
      .map(x => x.dataset.account)
  );

  return discovered.filter(x => selected.has(x.pubkey.toBase58()));
}

function updateRecoverable() {
  const total = selectedAccounts().reduce((s, x) => s + x.lamports, 0);
  document.getElementById("recoverable").textContent =
    (total / 1e9).toFixed(9) + " SOL before tx fee";
}

function selectAll() {
  for (const el of document.querySelectorAll('input[type="checkbox"][data-account]')) {
    el.checked = true;
  }
  updateRecoverable();
}

async function verifySelected() {
  if (!owner) await connectWallet();

  const selected = selectedAccounts();
  if (!selected.length) throw new Error("请先选择至少一个 WSOL account。");

  for (const item of selected) {
    const info = await connection.getParsedAccountInfo(item.pubkey, "confirmed");
    if (!info.value) throw new Error("目标 account 已不存在。");
    if (!info.value.owner.equals(TOKEN_PROGRAM)) {
      throw new Error("目标 account 已不属于标准 SPL Token Program。");
    }

    const p = info.value.data?.parsed?.info;
    if (!p) throw new Error("目标 account 无法解析。");
    if (p.mint !== WSOL_MINT.toBase58()) throw new Error("目标 account mint 已变化。");
    if (p.owner !== owner.toBase58()) throw new Error("目标 account owner 已变化。");
    if (p.isNative !== true) throw new Error("目标 account 已不再是 native WSOL。");
  }

  log("所选账户重新核验通过。");
  return selected;
}

function closeAccountIx(account) {
  return new TransactionInstruction({
    programId: TOKEN_PROGRAM,
    keys: [
      { pubkey: account, isSigner: false, isWritable: true },
      { pubkey: owner,   isSigner: false, isWritable: true },
      { pubkey: owner,   isSigner: true,  isWritable: false }
    ],
    data: Uint8Array.from([9])
  });
}

async function buildTransaction(selected) {
  const latest = await connection.getLatestBlockhash("confirmed");
  const tx = new Transaction({
    feePayer: owner,
    recentBlockhash: latest.blockhash
  });

  for (const x of selected) tx.add(closeAccountIx(x.pubkey));
  return { tx, latest };
}

async function simulateSelected() {
  const selected = await verifySelected();
  const { tx } = await buildTransaction(selected);

  const sim = await connection.simulateTransaction(tx, undefined, true);
  if (sim.value.err) throw new Error("模拟失败: " + JSON.stringify(sim.value.err));

  const logs = sim.value.logs || [];
  const unexpected = logs.filter(line => {
    const m = line.match(/^Program ([1-9A-HJ-NP-Za-km-z]+) invoke/);
    return m && m[1] !== TOKEN_PROGRAM.toBase58();
  });

  if (unexpected.length) {
    throw new Error("模拟出现非预期 Program，停止。");
  }

  log("模拟成功，仅调用标准 SPL Token Program。");
  return true;
}

async function signAndSend() {
  if (!owner) await connectWallet();

  const selected = await verifySelected();
  await simulateSelected();

  const { tx, latest } = await buildTransaction(selected);
  log("即将请求钱包签名，共 " + selected.length + " 条 CloseAccount 指令。");

  let signature;
  if (typeof provider.signAndSendTransaction === "function") {
    const res = await provider.signAndSendTransaction(tx);
    signature = typeof res === "string" ? res : (res.signature || res.txid);
  } else if (typeof provider.signTransaction === "function") {
    const signed = await provider.signTransaction(tx);
    const raw = typeof signed.serialize === "function" ? signed.serialize() : signed;
    signature = await connection.sendRawTransaction(raw, { skipPreflight: false });
  } else {
    throw new Error("当前钱包 provider 不支持签名接口。");
  }

  if (!signature) throw new Error("钱包没有返回 transaction signature。");
  log("交易已广播，等待确认。");

  const conf = await connection.confirmTransaction({
    signature,
    blockhash: latest.blockhash,
    lastValidBlockHeight: latest.lastValidBlockHeight
  }, "confirmed");

  if (conf.value.err) {
    throw new Error("交易确认失败: " + JSON.stringify(conf.value.err));
  }

  log("交易 confirmed。");
  await discoverAccounts();
}

document.getElementById("connect").onclick = () => connectWallet().catch(e => log("ERROR: " + e.message));
document.getElementById("discover").onclick = () => discoverAccounts().catch(e => log("ERROR: " + e.message));
document.getElementById("selectAll").onclick = () => selectAll();
document.getElementById("simulate").onclick = () => simulateSelected().catch(e => log("ERROR: " + e.message));
document.getElementById("send").onclick = () => {
  const n = selectedAccounts().length;
  if (!n) return log("ERROR: 请先选择至少一个账户。");
  if (!confirm("确认请求钱包签名关闭所选 native WSOL accounts，并将 SOL 退回当前钱包？")) return;
  signAndSend().catch(e => log("ERROR: " + e.message));
};
</script>
</body>
</html>
"""

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stdout.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            data = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        self.send_error(404)

    def do_POST(self):
        if self.path != "/rpc":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)

        try:
            req = urllib.request.Request(
                RPC_URL,
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "solana-wsol-recover/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            data = json.dumps({"error": str(e)}).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

def main():
    global RPC_URL

    print("Solana WSOL Recovery")
    print("Paste a trusted Solana Mainnet HTTPS RPC URL.")
    print("The RPC URL stays only in this local Python process.")
    RPC_URL = getpass.getpass("Solana RPC URL: ").strip()

    if not (RPC_URL.startswith("https://") or RPC_URL.startswith("http://")):
        print("Invalid RPC URL.")
        sys.exit(1)

    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Open: http://localhost:{PORT}/")
    print("Press Control+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
