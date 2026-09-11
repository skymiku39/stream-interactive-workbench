# Stream Interactive Workbench

可重用的直播互動動畫與中控展示模組。

這個專案不依賴 StreamSuite。它提供一套可被不同直播工具、OBS 工作流或自製中控整合的瀏覽器疊加層：

- 硬幣、骰子、骰寶與其他互動遊戲動畫
- WebGL 3D 與 CSS fallback
- 自然投擲、碰撞、落地與結果展示
- GitHub Pages 公開展示中控台
- 通用事件 payload，可由任何後端或直播工具發布
- 不綁定 Twitch、RabbitMQ、SQLite、Mem0 或特定機器人

## 公開展示

部署 GitHub Pages 後，網站根目錄就是互動中控台：

`https://<github-user>.github.io/<repository>/`

按鈕會在同頁 iframe 中傳送展示事件，因此展示版不需要後端。展示版可以展示動畫與視覺效果，但不代表正式 Twitch、OBS 或帳務整合已連線。

第一次啟用請在 GitHub repository 的 **Settings → Pages → Build and deployment → Source** 選擇 **GitHub Actions**。之後推送 `master` 或 `main` 就會自動部署。

## 本機展示

```powershell
$env:PYTHONPATH = "src"
python scripts/build_github_pages.py --output site
python -m http.server 18768 --directory site
```

開啟 `http://127.0.0.1:18768/`。

## 給整合者的 API

後端只需要發布事件物件；前端事件名稱與結果欄位見 [`docs/EVENT_PROTOCOL.md`](docs/EVENT_PROTOCOL.md)。

若要在自己的 Python bridge 產生 OBS HTML：

```python
from stream_interactive import render_game_overlay_html

html = render_game_overlay_html(ws_path="/surface", mode="all")
```

整合端負責提供事件傳輸（WebSocket、postMessage、SSE 或其他方式）；本模組只負責呈現與動畫。

## 來源與邊界

本模組從 StreamSuite 的互動展示層抽出，保留通用動畫、資產與結果一致性修正；StreamSuite 專屬的帳務、Twitch 授權、RabbitMQ、SQLite 與 Mem0 不在此 repo。
