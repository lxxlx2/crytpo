# Crypto / Web3 故障排查记录

这个目录记录已经实际排查过、并尽量通过链上数据、前端源码或交易模拟验证的 Web3 问题。

所有公开案例都遵循脱敏原则：
- 不记录个人钱包地址；
- 不记录交易签名；
- 不记录 API Key、私钥、助记词或认证信息；
- 不记录个人资金金额；
- 示例只保留复现问题所需的通用技术信息。

## Cases

### World.xyz：USDC 有余额但没有 Withdraw 按钮

文件：

```text
docs/cases/world-hidden-withdraw.md
```

结论：

```text
前端 Withdraw 按钮的显示条件与实际 Withdraw Modal 能力不一致。
```

通过打开前端已存在的 Withdraw Modal，最终成功完成提款。

配套脚本：

```text
scripts/world-open-withdraw-console.js
```

### Solstice Season 1：Vesting 长期 Claimable = 0

文件：

```text
docs/cases/solstice-season1-vesting.md
```

结论：

```text
链上 vesting stream 的 cliff / unlock schedule 导致当前可领取数量为 0。
```

完整模拟官方 Claim 后，链上返回：

```text
NothingToClaim (6001)
```

说明限制来自链上 stream schedule，用户侧无法通过修改前端提前领取。

配套模拟脚本：

```text
scripts/solstice-simulate-claim.mjs
```

### Solana：钱包显示 WSOL / SOL，但 Swap 无法使用

文件：

```text
docs/cases/solana-wsol-recovery.md
```

结论：

```text
历史 LP / DEX 操作可能留下多个 auxiliary native WSOL token accounts。
钱包 UI 会汇总显示，但 Swap 路由不一定能自动使用这些账户。
```

解决方式是先验证这些账户确实属于当前钱包、mint 为标准 WSOL 且 `isNative = true`，再模拟标准 SPL Token `CloseAccount`，确认无异常后由钱包签名关闭并取回 SOL 与 rent。

配套工具：

```text
scripts/solana-wsol-recover.py
```

## 记录原则

区分：
- 已确认链上事实；
- 前端源码行为；
- simulation 结果；
- 高可信推断；
- 尚未确认的项目方内部原因。

涉及真实资金时，优先使用只读查询和 `simulateTransaction`，确认后再考虑真实签名与广播。
