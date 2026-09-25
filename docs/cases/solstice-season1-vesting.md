# Solstice Season 1：Vesting 显示 Claimable = 0 的链上排查

> 目标：确认领取长期显示 `Claimable: 0` 的真实原因，并判断是否存在用户侧领取方案。

## 结论

这个问题通过前端源码、历史交易、链上 Stream Account 和真实 `simulateTransaction` 完整定位。

核心状态：

```text
now < cliffTime
startUnlockPercentage = 0
```

因此 Clique Lock 合约当前计算的可领取数量为 0。

模拟官方 Claim 流程后，链上程序返回：

```text
Error Code: NothingToClaim
Error Number: 6001
```

说明限制来自链上 vesting stream schedule。

修改网页按钮、直接构造 Claim、切换 RPC 都不能改变链上时间与 stream 状态。

## 排查步骤

### 1. 确认初始 Claim 已成功

通过历史交易确认初始资格 Claim 成功，并创建 NFT-bound vesting stream。

关键日志：

```text
Instruction: Claim
Instruction: CreateNftBoundStream
```

### 2. 读取 Stream Account

重点读取：

```text
startTime
cliffTime
endTime
startUnlockPercentage
cliffUnlockPercentage
pieceDuration
claimedAmount
```

确认资金仍在 stream 中，同时当前时间尚未达到可解锁条件。

### 3. 对照前端解锁公式

前端大致逻辑：

```js
if (now < startTime) return 0n;
if (now >= endTime) return amount;

const startUnlock =
  amount * startUnlockPercentage / 1000000000n;

if (now < cliffTime) return startUnlock;

// 后续再根据 cliffUnlockPercentage / pieceDuration 计算
```

如果：

```text
now < cliffTime
startUnlockPercentage = 0
```

则：

```text
unlocked = 0
claimable = 0
```

页面显示与链上参数一致。

### 4. 模拟官方 Claim

第一次模拟如果目标 ATA 不存在，可能先返回：

```text
AccountNotInitialized
```

因此完整模拟需要复制前端真实流程：

```text
1. Create Associated Token Account（必要时）
2. Clique Lock Claim
3. Compute Budget
4. simulateTransaction
```

完整 simulation 中：

```text
sigVerify: false
不签名
不广播
不花 SOL
```

当 Claim 最终返回：

```text
NothingToClaim (6001)
```

即可确认是合约基于 stream schedule 主动拒绝。

## 为什么用户侧无法强制领取

Claim 指令本身不让客户端任意指定“应该释放多少”。

领取金额由 Clique Lock 程序根据：

- Stream 状态；
- 当前链上时间；
- 已领取数量；
- unlock schedule；

自行计算。

因此修改前端显示、绕过按钮、手动发送相同 Claim 指令，都不会让合约提前释放。

## 项目方可执行的修复

如果 stream schedule 确实配置异常，通常需要项目方或协议管理员处理，例如：

- 迁移错误 stream；
- revoke 后重建正确 stream；
- 对受影响账户补发；
- 通过程序升级处理旧 stream；
- 使用协议支持的管理员恢复路径。

普通用户无法直接修改 program-owned Stream Account 的时间参数。

## 可复现脚本

见：

```text
scripts/solstice-simulate-claim.mjs
```

脚本已改为参数化，不包含任何个人钱包、stream、交易签名或个人金额。

它只进行 `simulateTransaction`：

```text
不要求私钥
不签名
不广播
不花 SOL
```
