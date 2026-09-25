# World.xyz：Embedded Wallet 有 USDC，但页面没有 Withdraw 按钮

> 场景：使用 Embedded Wallet，钱包里有 USDC，但 Portfolio 页面只有 Deposit，没有 Withdraw。

## 结论

这是一个前端显示条件问题。

World 前端曾出现 Withdraw 按钮的显示条件与实际 Withdraw Modal 能力不一致的情况。Withdraw Modal 本身支持普通 SPL Token，并通过当前 Embedded Wallet 的 `signTransaction()` 完成标准 Solana / SPL Token 转账。

因此可能出现：

- Embedded Wallet 里有 USDC；
- 页面总资产能看到 USDC；
- Portfolio 顶部没有 Withdraw 按钮；
- 实际 Withdraw 功能仍已加载在前端。

本案例通过打开前端已经存在的 Withdraw Modal，最终成功完成提款。

## 前端根因

从前端 bundle 可以看到，Portfolio Header 会根据某个内部余额条件决定是否渲染 Withdraw 按钮。

Withdraw Modal 本身支持 token selector，并调用：

```text
signTransaction
sendAndConfirmTransaction
TransferChecked
```

普通 SPL Token 的提款路径大致是：

1. 获取用户 Embedded Wallet 公钥；
2. 推导发送方 ATA；
3. 推导收款地址 ATA；
4. 如果收款 ATA 不存在，则尝试创建 ATA；
5. 添加 `TransferChecked`；
6. 使用 Embedded Wallet 签名；
7. 广播并确认交易。

所以 UI 条件和底层提款能力可能不一致。

## 实际解决方案

### 准备条件

建议先确认：

- Embedded Wallet 确实持有目标 SPL Token；
- Embedded Wallet 里有少量 SOL 用于交易手续费和可能的 ATA 创建成本；
- 第一次先小额测试。

### 打开 Chrome Console

macOS：

```text
Option + Command + J
```

Windows：

```text
Ctrl + Shift + J
```

如果 Chrome 阻止粘贴，在 Console 输入框手动键入：

```text
allow pasting
```

按 Enter 后再粘贴代码。

### 打开隐藏的 Withdraw Modal

使用配套脚本：

```text
scripts/world-open-withdraw-console.js
```

代码只负责把已经存在于 World 前端中的 Withdraw Modal 打开。

它不会：

- 导出私钥；
- 读取助记词；
- 读取 Cookie；
- 读取 JWT；
- 绕过钱包签名。

真正的转账仍由当前 Embedded Wallet 正常签名。

## 遇到过的错误

### Transaction expired

如果出现：

```text
Withdrawal failed
Transaction expired — please try again
```

通常意味着 recent blockhash 已过期。

处理：

1. 重新打开 Withdraw Modal；
2. 再次提交；
3. 前端重新获取 blockhash；
4. 重新签名广播。

不要复用已经过期的交易。

### Embedded Wallet 没有 SOL

SPL Token 转账仍需要 SOL 支付网络费。

如果还需要创建收款 ATA，也会产生账户创建成本。

## 安全说明

不要执行来源不明的 DevTools 代码。

公开分享这套 workaround 时应明确：

- 代码只打开网页已有 Modal；
- 最终交易仍由用户自己的钱包完成签名；
- 不要求私钥或助记词；
- 只在自己的账户中操作；
- 先小额测试；
- 网站更新前端后 React hook 位置可能变化，因此脚本可能失效。

## 最终状态

本案例最终成功完成提款。

这类问题的核心是：

```text
提款能力存在
+
UI 入口显示条件异常
=
用户看不到 Withdraw
```

因此属于前端状态 / 显示逻辑问题，可通过调用已经加载的 Modal 临时恢复入口。
