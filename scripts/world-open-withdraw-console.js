/*
World.xyz workaround
Purpose: open the Withdraw Modal that already exists in the World frontend.

Run only on your own World Portfolio page.
Review the code before executing it.
*/

(() => {
  const deposit = [...document.querySelectorAll("*")]
    .find(el =>
      el.children.length === 0 &&
      el.textContent?.trim() === "Deposit"
    );

  if (!deposit) {
    console.error("Deposit element not found");
    return;
  }

  const fiberKey = Object.keys(deposit)
    .find(k => k.startsWith("__reactFiber$"));

  if (!fiberKey) {
    console.error("React fiber not found");
    return;
  }

  let fiber = deposit[fiberKey];
  let target = null;

  while (fiber) {
    try {
      const src =
        typeof fiber.type === "function"
          ? Function.prototype.toString.call(fiber.type)
          : "";

      if (
        src.includes(
          "CASHx9KJUStyftLFWGvEVf59SGeG9sh5FfcnZMVPCASH"
        ) &&
        src.includes("Withdraw")
      ) {
        target = fiber;
        break;
      }
    } catch {}

    fiber = fiber.return;
  }

  if (!target) {
    console.error("Portfolio header component not found");
    return;
  }

  const candidates = [];
  let hook = target.memoizedState;
  let index = 0;

  while (hook) {
    if (
      typeof hook.memoizedState === "boolean" &&
      hook.queue &&
      typeof hook.queue.dispatch === "function"
    ) {
      candidates.push({
        index,
        value: hook.memoizedState,
        dispatch: hook.queue.dispatch
      });
    }

    hook = hook.next;
    index++;
  }

  console.log(
    "Boolean state hooks:",
    candidates.map(x => ({
      index: x.index,
      value: x.value
    }))
  );

  const modalState = candidates[candidates.length - 1];

  if (!modalState) {
    console.error("Withdraw modal state not found");
    return;
  }

  console.log(
    "Opening Withdraw modal with hook",
    modalState.index
  );

  modalState.dispatch(true);
})();
