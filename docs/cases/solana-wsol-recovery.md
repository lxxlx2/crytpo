# Solana：钱包显示 WSOL / SOL，但 Swap 无法使用

> 场景：历史上使用过 Solana LP、集中流动性或 DEX。退出后钱包仍显示一部分 SOL / WSOL，但钱包内直接 Swap 会失败。

## 结论

问题可能来自多个独立的 native WSOL SPL Token Account。

Solana 的 WSOL 使用标准 Wrapped SOL Mint。历史 LP / DEX 操作可能创建多个临时或辅助 WSOL token account。退出流动性、Collect Fees 或 Close Position 后，一部分 WSOL 可能继续留在这些账户里。

钱包 UI 往往会把这些余额汇总显示，但 Swap builder 不一定会自动使用所有辅助账户，因此会出现：

```text
钱包能看到余额
+
普通 Swap 无法消费这些辅助账户
=
Swap 失败
```

对于确认过的 native WSOL，恢复原生 SOL 不需要走 DEX。标准方案是关闭对应 WSOL Token Account，让其中的 SOL 与 rent 一起退回当前钱包。

## 排查思路

### 1. 查 WSOL token account 层

不能只看钱包首页的汇总余额。

目标账户必须逐个验证：

```text
mint = 标准 Wrapped SOL Mint
isNative = true
owner = 当前钱包
program = 标准 SPL Token Program
state = initialized
```

如果这些条件有任何一项不满足，就不要关闭。

### 2. 必要时回看历史来源

如果想确认这些 account 为什么存在，可以查看它们的历史交易。

常见来源包括：

```text
OpenPosition
DecreaseLiquidity
CollectFees
ClosePosition
普通 Wrap / Unwrap SOL
DEX 临时账户
```

这些辅助 WSOL account 本身通常不等于 LP Position，也不等于 Position NFT。

### 3. 可回收值要看 account lamports

native WSOL token account 中包含：

```text
WSOL 对应的 lamports
+
Token Account rent reserve
```

因此关闭账户时实际退回的 SOL 可能高于钱包 UI 单独显示的 WSOL token amount。

### 4. 真实签名前必须模拟

对确认过的账户构造标准 SPL Token：

```text
CloseAccount
```

然后使用 `simulateTransaction`。

理想的模拟结果应满足：

- transaction error 为 null；
- 只出现标准 SPL Token Program；
- 没有 DEX / LP program 调用；
- 没有向第三方转账；
- 目标 token account 在模拟后被关闭；
- lamports 返回当前钱包。

确认无异常后再交给钱包扩展签名和广播。

## 浏览器公共 RPC 返回 403

本案例制作本地 Web UI 时还遇到浏览器直接访问公共 Solana RPC 返回：

```text
403 Access forbidden
```

这属于 RPC endpoint / 浏览器访问策略问题，与 WSOL 资产状态无关。

最终采用：

```text
浏览器
  ↓
localhost Python RPC proxy
  ↓
用户自己的可信 Solana RPC
```

RPC URL 只保存在本机 Python 进程中，不写入 HTML，也不提交仓库。

## 通用工具

配套工具：

```text
scripts/solana-wsol-recover.py
```

运行：

```bash
python3 scripts/solana-wsol-recover.py
```

随后：

1. 粘贴自己的 Solana Mainnet HTTPS RPC URL；
2. 浏览器打开 `http://localhost:8765/`；
3. 连接 Solana 钱包；
4. 扫描 native WSOL accounts；
5. 选择要处理的账户；
6. 重新链上核验；
7. 先模拟；
8. 检查钱包签名内容后手动确认。

## 安全边界

工具不会：

- 保存或上传助记词；
- 要求私钥；
- 把 RPC key 写进网页；
- 自动选择未知 token account；
- 调用 DEX；
- 自动执行 Swap；
- 绕过钱包签名。

每个 account 在交易前都会重新验证 owner、mint 与 `isNative`。

最终真实广播仍由用户自己的钱包手动签名。

## 什么时候不要使用

以下情况不要直接关闭：

- mint 不是标准 WSOL；
- `isNative` 不是 true；
- owner 不是当前钱包；
- 无法确认账户来源；
- 钱包模拟显示额外 program 调用；
- 签名弹窗出现第三方收款或陌生指令。

遇到这些情况应停止操作并继续做链上排查。
