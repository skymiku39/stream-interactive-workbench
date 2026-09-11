# Event Protocol

互動模組接收 JSON event。`type` 是必要欄位；其餘欄位由動畫使用。事件結果是 authoritative，動畫不應在結算時改寫結果。

## Games

```json
{"type":"game.coin.flipped","user_name":"viewer","side":"正面"}
{"type":"game.dice.rolled","user_name":"viewer","total":8,"rolls":[3,5],"detail":"2d6 (3 + 5) = 8"}
{"type":"game.bwei.tossed","result":"sheng","name":"聖筊","desc":"神明應允"}
{"type":"game.gashapon.pulled","toy":{"name":"機甲守衛 Q 版公仔","image":"/assets/toys/toy_robot.png"}}
{"type":"game.wheel.spun","items":["100 點","再來一次"],"target_index":0}
{"type":"gacha.card.pulled","card":{"name":"星海夏日","rarity":"SSR"}}
```

## Reset

```json
{"type":"overlay.reset","target":"all"}
```

## Delivery options

- Production bridge: send JSON over a WebSocket and let the overlay dispatch by `type`.
- Static demo: send `{ "type": "interactive.demo.event", "payload": event }` with `window.postMessage` to the overlay iframe.

The module does not perform point accounting, Twitch authorization, or persistence. Those responsibilities stay in the host application.
