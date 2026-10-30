// board.js: the Board is no longer a view (the bar review, 2026-10-24: "rebuild by removal").
// Its one truth that survives is the Chain's road folded by stream, so this file only hands
// out the Chain already folded: the Map's "open its board" and any old #/board link land there.

import createChain from "./chain.js";

export default function createBoard() {
  return createChain({ fold: true });
}
