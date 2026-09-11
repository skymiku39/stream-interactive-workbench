# Integration guide

## StreamSuite

StreamSuite can keep its event bus and send the normalized event payload to this module's overlay bridge. The module should not import StreamSuite internals.

## Other hosts

1. Serve the generated overlay HTML and `/assets` directory.
2. Open `/overlay/games` as an OBS Browser Source or iframe.
3. Forward host events as JSON to the browser.
4. Keep accounting and authorization in the host.

The `mode` argument can render a focused overlay such as `coin`, `dice`, `gacha`, or `donation`; `all` renders the unified overlay.

## Result consistency

For coin and dice, the host result is passed before the throw starts. The overlay performs the throw and natural settling, then reveals the same event result. It must not infer a different result from a visually ambiguous last frame.
