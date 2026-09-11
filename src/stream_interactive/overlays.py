"""OBS Game Overlays & Interactive Preview (inspired by GACHAGO! / ChiwaBots).

High-fidelity, result-locked, physically-inspired animated overlays & VFX for:
1. 擲筊 (BwaBwei): 3D crescent moon blocks, contact shadow, wood-clack acoustics, incense dust & sacred seals.
2. 拉霸老虎機 (Slot 777): 3D curved cylinder drum reels, mechanical lever, optical blur, elastic overshoot, laser payline.
3. 實體扭蛋機 (Gashapon): Physical Japanese capsule machine with 360° mechanical crank, chute roll-down, pop-open capsule & vector toy drop.
4. 二次元星空抽卡 (Card Gacha / 10-Pull): Cinematic shooting stars, screen-shake shockwave, god rays, 3D card flip & holographic SSR celestial crest.
5. 幸運大轉盤 (Lucky Wheel): 12-segment wheel, physical needle flipper damping, realistic clicker ticking, decelerating physics.
6. 3D 擲硬幣 (Coin Flip): High-speed air tumble, edge rotation, heads/tails/standing edge physics.
7. 3D 擲骰子 (Dice Roll): 3D isometric dice throw, tumbling bounce & settle.

Design Guiding Principles:
- 100% Vector & Procedural Aesthetics: Zero dependence on mismatched or low-res third-party sprites.
- Resolution-independent: Crisp at 720p, 1080p, and 4K OBS canvas.
- Graceful Custom Image Support: Displays custom image if and only if validly provided in event payload, with instant vector fallback.
- Instant Frame-1 State Reset: Cancels all previous running timers & animations on rapid re-click without stuck states.
- In-repo Studio Audio: Authentic casino/foley recordings for cards, chips, dice, and clicks.
- Result lock: the event payload is authoritative; animation and physics never redraw the game result.
"""

from __future__ import annotations


def render_game_overlay_html(
    ws_path: str = "/surface",
    mode: str = "all",
    *,
    static_demo: bool = False,
    asset_prefix: str = "/assets",
) -> str:
    """Return self-contained, high-fidelity transparent HTML for OBS Browser Source."""
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <title>Stream Interactive Workbench - {mode.upper()}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    :root {{
      --gold: #6b5db8;
      --gold-bright: #806fc7;
      --gold-light: #e9e5f7;
      --primary: #0ea5b0;
      --accent: #6b5db8;
      --purple: #806fc7;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    html, body {{
      width: 100vw;
      height: 100vh;
      overflow: hidden;
      background: transparent;
      font-family: -apple-system, BlinkMacSystemFont, "Microsoft JhengHei UI", "Noto Sans TC", "Segoe UI", sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      user-select: none;
    }}

    /* Global VFX Canvas for Confetti, Sparks & Smoke */
    #vfx-canvas {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 1000;
    }}

    /* 全景聚光燈暗角 (Cinematic Vignette) */
    #spotlight-vignette {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: radial-gradient(circle at center, transparent 30%, rgba(0, 0, 0, 0.72) 90%);
      opacity: 0;
      transition: opacity 0.4s ease;
      pointer-events: none;
      z-index: 50;
    }}
    #spotlight-vignette.active {{ opacity: 1; }}

    /* 金色聖光光芒射線 (God Rays Sunburst) */
    #god-rays {{
      position: absolute;
      width: 900px;
      height: 900px;
      border-radius: 50%;
      background: repeating-conic-gradient(from 0deg, rgba(245, 158, 11, 0.11) 0deg 15deg, transparent 15deg 30deg);
      animation: rotate-rays 20s linear infinite;
      opacity: 0;
      transition: opacity 0.5s ease;
      pointer-events: none;
      z-index: 40;
    }}
    #god-rays.active {{ opacity: 0.72; }}
    @keyframes rotate-rays {{
      0% {{ transform: rotate(0deg); }}
      100% {{ transform: rotate(360deg); }}
    }}

    /* 向量級高解析衝擊波光環 (Vector Shockwave Blast) */
    #shockwave-ring {{
      position: absolute;
      width: 50px;
      height: 50px;
      border-radius: 50%;
      border: 4px solid var(--gold-bright);
      box-shadow: 0 0 35px var(--gold-bright), inset 0 0 25px var(--gold-bright);
      pointer-events: none;
      z-index: 60;
      opacity: 0;
    }}
    .blast-active {{
      animation: shockwave-expand 0.75s cubic-bezier(0.1, 0.85, 0.25, 1) forwards !important;
    }}
    @keyframes shockwave-expand {{
      0% {{ transform: scale(0.6); opacity: 1; border-width: 8px; }}
      100% {{ transform: scale(36); opacity: 0; border-width: 1px; }}
    }}

    /* 主舞台容器 (支援螢幕相機震動 Camera Trauma Shake) */
    #overlay-root {{
      position: relative;
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      perspective: 1400px;
      transition: transform 0.05s ease;
    }}

    /*
       所有投擲類互動共用的舞台與接觸面。
       - CSS 與 WebGL 都把這個平面視為 y=0。
       - 500x240 是三種投擲展示的共同畫布基準；各模組只改物件與 HUD，
         不再各自發明一個地面高度。
       - 平面保持半透明，適合透明 OBS Browser Source，也能在本機預覽中
         提供一致的接觸陰影與落地視覺線索。
    */
    .throw-physics-arena {{
      position: relative;
      width: 500px;
      height: 240px;
      perspective: 900px;
      perspective-origin: 50% 20%;
      transform-style: preserve-3d;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .throw-plane {{
      position: absolute;
      left: 50%;
      bottom: -26px;
      width: 420px;
      height: 250px;
      border-radius: 26px;
      background:
        radial-gradient(circle at 50% 44%, rgba(56, 189, 248, 0.12), transparent 52%),
        linear-gradient(135deg, rgba(8, 25, 43, 0.92), rgba(15, 45, 59, 0.78));
      border: 1px solid rgba(125, 211, 252, 0.30);
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.16),
        inset 0 -18px 34px rgba(2, 6, 23, 0.28),
        0 18px 34px rgba(2, 6, 23, 0.38),
        0 0 0 1px rgba(15, 23, 42, 0.22);
      /* 這是一個真正的 CSS 3D 水平面，不再用橢圓陰影假裝桌面。 */
      transform: translateX(-50%) rotateX(64deg);
      transform-origin: center center;
      pointer-events: none;
      z-index: 0;
    }}
    .throw-plane::before {{
      content: "";
      position: absolute;
      inset: 14px;
      border: 1px solid rgba(186, 230, 253, 0.16);
      border-radius: 18px;
      background:
        linear-gradient(90deg, transparent 49.7%, rgba(186, 230, 253, 0.08) 50%, transparent 50.3%),
        linear-gradient(0deg, transparent 49.7%, rgba(186, 230, 253, 0.08) 50%, transparent 50.3%),
        radial-gradient(ellipse at 50% 45%, rgba(56, 189, 248, 0.09), transparent 68%);
      box-shadow: inset 0 0 18px rgba(2, 6, 23, 0.24);
    }}
    .throw-plane::after {{
      content: "";
      position: absolute;
      left: 18px;
      right: 18px;
      bottom: 14px;
      height: 1px;
      background: linear-gradient(90deg, transparent, rgba(226, 232, 240, 0.22), transparent);
      filter: blur(2px);
    }}

    .throw-physics-arena > .throw-plane {{
      /* Keep the DOM floor under both CSS objects and the WebGL canvas. */
      z-index: 0;
    }}
    .throw-physics-arena.uses-webgl > .throw-plane {{
      /* WebGL uses the actual PlaneGeometry below; never double-render a CSS floor. */
      opacity: 0;
    }}
    .screen-shake {{
      animation: camera-shake 0.45s cubic-bezier(0.36, 0.07, 0.19, 0.97) both;
    }}
    @keyframes camera-shake {{
      10%, 90% {{ transform: translate3d(-4px, 2px, 0) rotate(-0.5deg); }}
      20%, 80% {{ transform: translate3d(6px, -4px, 0) rotate(1deg); }}
      30%, 50%, 70% {{ transform: translate3d(-7px, 5px, 0) rotate(-1.2deg); }}
      40%, 60% {{ transform: translate3d(7px, -3px, 0) rotate(0.9deg); }}
    }}

    #status-indicator {{
      position: absolute;
      top: 8px;
      right: 12px;
      font-size: 11px;
      color: rgba(255, 255, 255, 0.45);
      background: rgba(0, 0, 0, 0.6);
      padding: 3px 8px;
      border-radius: 4px;
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.5s ease;
      z-index: 9999;
    }}
    #status-indicator.visible {{ opacity: 1; }}

    /* =========================================================================
       1. 擲筊 (BwaBwei)
       ========================================================================= */
    .bwei-stage {{
      position: absolute;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transform: scale(0.7) translateY(40px);
      transition: opacity 0.35s ease, transform 0.55s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      pointer-events: none;
      z-index: 100;
    }}
    .bwei-stage.active {{ opacity: 1; transform: scale(1) translateY(0); }}

    .bwei-arena {{
      position: relative;
      width: 440px;
      height: 260px;
      display: flex;
      align-items: center;
      justify-content: space-around;
      transform-style: preserve-3d;
    }}
    .bwei-arena::before {{
      content: "";
      position: absolute;
      left: 50%;
      bottom: 18px;
      width: 360px;
      height: 112px;
      border-radius: 50%;
      background: radial-gradient(ellipse at center, rgba(15, 23, 42, 0.26), transparent 70%);
      transform: translateX(-50%) rotateX(64deg) translateZ(-18px);
      filter: blur(7px);
      pointer-events: none;
      z-index: -1;
    }}
    .bwei-cup-wrap {{
      position: relative;
      width: 140px;
      height: 90px;
      display: flex;
      align-items: center;
      justify-content: center;
      perspective: 520px;
    }}
    .bwei-shadow {{
      position: absolute;
      bottom: -15px;
      width: 110px;
      height: 35px;
      background: radial-gradient(ellipse at center, rgba(0, 0, 0, 0.65) 0%, rgba(0, 0, 0, 0) 70%);
      border-radius: 50%;
      transform: scale(0.3);
      opacity: 0;
      filter: blur(4px);
    }}
    .bwei-cup-svg {{
      width: 130px;
      height: 80px;
      filter: drop-shadow(0 18px 18px rgba(0, 0, 0, 0.50)) drop-shadow(0 4px 0 rgba(0, 0, 0, 0.38)) drop-shadow(0 0 8px rgba(248, 113, 113, 0.18));
      transform-origin: center center;
      transform-style: preserve-3d;
      backface-visibility: visible;
    }}

    .toss-active-left {{
      animation: physical-toss-left 1.35s cubic-bezier(0.2, 0.85, 0.25, 1) forwards;
    }}
    .toss-active-right {{
      animation: physical-toss-right 1.4s cubic-bezier(0.25, 0.9, 0.3, 1) forwards;
    }}
    .shadow-active-left {{
      animation: shadow-animate-left 1.35s cubic-bezier(0.2, 0.85, 0.25, 1) forwards;
    }}
    .shadow-active-right {{
      animation: shadow-animate-right 1.4s cubic-bezier(0.25, 0.9, 0.3, 1) forwards;
    }}

    @keyframes physical-toss-left {{
      0% {{ transform: translateY(-460px) translateX(-50px) rotateX(720deg) rotateY(360deg) rotateZ(180deg) scale(1.6); opacity: 0; }}
      30% {{ opacity: 1; }}
      60% {{ transform: translateY(18px) translateX(10px) rotateX(30deg) rotateY(-15deg) rotateZ(-12deg) scale(0.92); }}
      75% {{ transform: translateY(-38px) translateX(-4px) rotateX(-15deg) rotateY(8deg) rotateZ(5deg) scale(1.05); }}
      88% {{ transform: translateY(8px) translateX(2px) rotateX(6deg) rotateY(-3deg) rotateZ(-2deg) scale(0.98); }}
      100% {{ transform: translateY(0) translateX(0) rotateX(8deg) rotateY(-7deg) scale(1); }}
    }}

    @keyframes physical-toss-right {{
      0% {{ transform: translateY(-480px) translateX(60px) rotateX(-720deg) rotateY(-540deg) rotateZ(-220deg) scale(1.7); opacity: 0; }}
      30% {{ opacity: 1; }}
      62% {{ transform: translateY(22px) translateX(-12px) rotateX(-35deg) rotateY(20deg) rotateZ(15deg) scale(0.9); }}
      77% {{ transform: translateY(-44px) translateX(6px) rotateX(18deg) rotateY(-10deg) rotateZ(-8deg) scale(1.06); }}
      90% {{ transform: translateY(10px) translateX(-2px) rotateX(-6deg) rotateY(4deg) rotateZ(2deg) scale(0.98); }}
      100% {{ transform: translateY(0) translateX(0) rotateX(8deg) rotateY(7deg) scale(1); }}
    }}

    @keyframes shadow-animate-left {{
      0% {{ opacity: 0; transform: scale(1.8); filter: blur(14px); }}
      60% {{ opacity: 0.9; transform: scale(1); filter: blur(3px); }}
      75% {{ opacity: 0.4; transform: scale(0.7); filter: blur(8px); }}
      88% {{ opacity: 0.85; transform: scale(1); filter: blur(3px); }}
      100% {{ opacity: 0.75; transform: scale(1); filter: blur(4px); }}
    }}
    @keyframes shadow-animate-right {{
      0% {{ opacity: 0; transform: scale(1.9); filter: blur(15px); }}
      62% {{ opacity: 0.95; transform: scale(1.05); filter: blur(3px); }}
      77% {{ opacity: 0.35; transform: scale(0.65); filter: blur(9px); }}
      90% {{ opacity: 0.9; transform: scale(1); filter: blur(3px); }}
      100% {{ opacity: 0.8; transform: scale(1); filter: blur(4px); }}
    }}

    .standing-wobble {{
      transform-origin: 30% 90%;
      animation: standing-decay 1.8s ease-out forwards !important;
    }}
    @keyframes standing-decay {{
      0% {{ transform: translateY(0) rotate(-22deg); }}
      25% {{ transform: translateY(0) rotate(16deg); }}
      45% {{ transform: translateY(0) rotate(-10deg); }}
      65% {{ transform: translateY(0) rotate(5deg); }}
      100% {{ transform: translateY(0) rotate(0deg); }}
    }}

    .bwei-banner {{
      margin-top: 18px;
      padding: 12px 32px;
      background: linear-gradient(135deg, rgba(20, 24, 39, 0.95) 0%, rgba(10, 14, 26, 0.98) 100%);
      border: 2px solid var(--gold);
      border-radius: 50px;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.8), 0 0 25px rgba(245, 158, 11, 0.45);
      display: flex;
      flex-direction: column;
      align-items: center;
      transform: translateY(24px);
      opacity: 0;
      transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) 0.8s;
    }}
    .bwei-stage.active .bwei-banner {{ transform: translateY(0); opacity: 1; }}
    .bwei-user {{ font-size: 14px; color: #cbd5e1; }}
    .bwei-title {{ font-size: 32px; font-weight: 900; letter-spacing: 6px; margin: 4px 0; }}
    .bwei-desc {{ font-size: 14px; color: #fde047; font-weight: 600; }}

    .res-sheng {{ color: #4ade80; text-shadow: 0 0 20px rgba(74, 222, 128, 0.8); }}
    .res-xiao {{ color: #38bdf8; text-shadow: 0 0 20px rgba(56, 189, 248, 0.8); }}
    .res-yin {{ color: #f87171; text-shadow: 0 0 20px rgba(248, 113, 113, 0.8); }}
    .res-standing {{
      background: linear-gradient(45deg, #fbbf24, #ec4899, #8b5cf6, #38bdf8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      animation: rainbow 2s linear infinite;
    }}
    @keyframes rainbow {{
      0% {{ filter: hue-rotate(0deg); }}
      100% {{ filter: hue-rotate(360deg); }}
    }}

    /* =========================================================================
       2. 拉霸老虎機 (Slot Machine)
       ========================================================================= */
    .slot-stage {{
      position: absolute;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transform: scale(0.8);
      transition: opacity 0.35s ease, transform 0.45s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      pointer-events: none;
      z-index: 100;
    }}
    .slot-stage.active {{ opacity: 1; transform: scale(1); }}

    .slot-cabinet {{
      position: relative;
      background:
        linear-gradient(112deg, rgba(255,255,255,0.13), transparent 18%, transparent 72%, rgba(0,0,0,0.24)),
        linear-gradient(160deg, #334155 0%, #111827 42%, #050810 100%);
      border: 4px solid #c49b3a;
      box-shadow: 0 28px 64px rgba(0, 0, 0, 0.92), 0 0 35px rgba(245, 158, 11, 0.42), inset 0 1px 0 rgba(255,255,255,0.24), inset 0 -18px 26px rgba(0,0,0,0.38);
      border-radius: 24px;
      padding: 24px 32px;
      display: flex;
      flex-direction: column;
      align-items: center;
      transform-style: preserve-3d;
      perspective: 900px;
    }}
    .slot-cabinet::before {{
      content: "";
      position: absolute;
      inset: 8px;
      border: 1px solid rgba(255, 255, 255, 0.14);
      border-radius: 17px;
      pointer-events: none;
      transform: translateZ(1px);
    }}
    .slot-cabinet::after {{
      content: "";
      position: absolute;
      left: 18px;
      right: 18px;
      top: 9px;
      height: 12px;
      border-radius: 50%;
      background: linear-gradient(90deg, transparent, rgba(255,255,255,0.26), transparent);
      filter: blur(1px);
      pointer-events: none;
    }}

    .slot-title {{
      font-size: 22px;
      font-weight: 900;
      color: #fde047;
      letter-spacing: 3px;
      text-transform: uppercase;
      text-shadow: 0 0 12px rgba(253, 224, 71, 0.6);
      margin-bottom: 14px;
    }}

    .slot-reels-frame {{
      display: flex;
      gap: 14px;
      background: #020617;
      padding: 14px;
      border-radius: 16px;
      border: 3px solid #334155;
      box-shadow: inset 0 8px 18px rgba(0, 0, 0, 0.9), inset 0 -8px 18px rgba(0, 0, 0, 0.9);
      position: relative;
      transform: rotateX(5deg) translateZ(10px);
      transform-style: preserve-3d;
    }}

    .slot-reel-viewport {{
      width: 84px;
      height: 112px;
      background:
        linear-gradient(100deg, rgba(15,23,42,0.18), transparent 18%, transparent 78%, rgba(15,23,42,0.24)),
        linear-gradient(180deg, #ffffff, #e2e8f0 50%, #cbd5e1);
      border-radius: 10px;
      overflow: hidden;
      position: relative;
      box-shadow: inset 0 16px 20px rgba(0, 0, 0, 0.45), inset 0 -16px 20px rgba(0, 0, 0, 0.45);
      border: 2px solid #cbd5e1;
      transform: translateZ(4px);
      box-sizing: border-box;
    }}
    .slot-reel-viewport::before,
    .slot-reel-viewport::after {{
      content: "";
      position: absolute;
      left: 0;
      right: 0;
      height: 22px;
      z-index: 5;
      pointer-events: none;
    }}
    .slot-reel-viewport::before {{
      top: 0;
      background: linear-gradient(#020617cc, transparent);
    }}
    .slot-reel-viewport::after {{
      bottom: 0;
      background: linear-gradient(transparent, #020617cc);
    }}

    .slot-reel-strip {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      display: flex;
      flex-direction: column;
      align-items: center;
      transform: translateY(0);
    }}
    .reel-item {{
      width: 84px;
      height: 112px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 52px;
      flex-shrink: 0;
      text-shadow: 0 3px 0 rgba(15, 23, 42, 0.35), 0 6px 10px rgba(15, 23, 42, 0.22);
    }}

    .spinning-blur {{
      animation: reel-spinning 0.1s linear infinite;
      filter: blur(5px);
    }}
    @keyframes reel-spinning {{
      0% {{ transform: translateY(0); }}
      100% {{ transform: translateY(-336px); }}
    }}

    .stopping-elastic {{
      animation: reel-overshoot 0.45s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards !important;
    }}
    @keyframes reel-overshoot {{
      0% {{ transform: translateY(-60px); filter: blur(2px); }}
      65% {{ transform: translateY(14px); filter: blur(0); }}
      85% {{ transform: translateY(-6px); }}
      100% {{ transform: translateY(0); }}
    }}

    .slot-payline {{
      position: absolute;
      top: 50%;
      left: 6px;
      right: 6px;
      height: 4px;
      background: linear-gradient(90deg, #ec4899, #f59e0b, #ec4899);
      box-shadow: 0 0 16px #f59e0b, 0 0 24px #ec4899;
      transform: translateY(-50%) scaleX(0);
      transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      z-index: 10;
      pointer-events: none;
    }}
    .slot-payline.active {{ transform: translateY(-50%) scaleX(1); }}

    .slot-lever {{
      position: absolute;
      right: -36px;
      top: 65px;
      width: 14px;
      height: 80px;
      background: linear-gradient(90deg, #64748b, #94a3b8, #475569);
      border-radius: 6px;
      transform-origin: bottom center;
      transition: transform 0.35s cubic-bezier(0.2, 0.8, 0.2, 1);
    }}
    .slot-lever-knob {{
      position: absolute;
      top: -20px;
      left: -11px;
      width: 36px;
      height: 36px;
      background: radial-gradient(circle at 35% 35%, #ef4444, #7f1d1d);
      border-radius: 50%;
      box-shadow: 0 6px 14px rgba(0, 0, 0, 0.6);
    }}
    .slot-lever.pulled {{ transform: rotate(70deg) scaleY(0.65); }}

    .slot-footer {{ margin-top: 16px; text-align: center; }}
    .slot-result-text {{ font-size: 20px; font-weight: 800; color: #f8fafc; }}
    .slot-jackpot-badge {{
      display: inline-block;
      margin-top: 6px;
      padding: 4px 18px;
      border-radius: 30px;
      background: linear-gradient(90deg, #ec4899, #f59e0b);
      color: #ffffff;
      font-weight: 900;
      font-size: 16px;
      box-shadow: 0 0 25px rgba(245, 158, 11, 0.85);
    }}

    /* =========================================================================
       3. 實體日式扭蛋機 (Realistic Bandai-style Gashapon)
       ========================================================================= */
    .gashapon-machine-stage {{
      position: absolute;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transform: translateY(18px) scale(0.94);
      transition: opacity 0.4s ease, transform 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      pointer-events: none;
      z-index: 100;
      width: 100vw;
      height: 100vh;
    }}
    .gashapon-machine-stage.active {{
      opacity: 1;
      transform: translateY(0) scale(1);
    }}

    .gashapon-machine {{
      position: relative;
      width: 340px;
      transform: perspective(900px) rotateX(1deg);
      transform-style: preserve-3d;
      filter: drop-shadow(0 30px 42px rgba(0, 0, 0, 0.78));
    }}

    .gashapon-sign {{
      position: absolute;
      top: -18px;
      left: 50%;
      transform: translateX(-50%);
      background: linear-gradient(180deg, #f8fafc 0%, #cbd5e1 100%);
      color: #b91c1c;
      font-weight: 900;
      font-size: 13px;
      letter-spacing: 4px;
      padding: 4px 18px;
      border-radius: 6px;
      border: 2px solid #94a3b8;
      box-shadow: 0 4px 10px rgba(0,0,0,0.35);
      z-index: 5;
    }}

    /* 透明壓克力圓頂 */
    .gashapon-dome {{
      position: relative;
      width: 280px;
      height: 250px;
      margin: 0 auto;
      z-index: 3;
    }}
    .dome-glass {{
      position: absolute;
      left: 20px;
      top: 10px;
      width: 240px;
      height: 240px;
      border-radius: 50%;
      background:
        radial-gradient(ellipse at 28% 20%, rgba(255,255,255,0.72) 0%, rgba(255,255,255,0.12) 18%, transparent 38%),
        radial-gradient(circle at 50% 55%, rgba(186, 230, 253, 0.20), rgba(14, 116, 144, 0.30) 100%);
      border: 4px solid rgba(241, 245, 249, 0.68);
      box-shadow:
        inset 0 -18px 40px rgba(15, 23, 42, 0.25),
        inset 0 10px 24px rgba(255, 255, 255, 0.35),
        0 8px 20px rgba(0, 0, 0, 0.25);
      overflow: hidden;
      backdrop-filter: blur(0.5px);
    }}
    .dome-shine {{
      position: absolute;
      top: 18px;
      left: 34px;
      width: 70px;
      height: 42px;
      background: linear-gradient(135deg, rgba(255,255,255,0.85), rgba(255,255,255,0));
      border-radius: 50%;
      transform: rotate(-28deg);
      pointer-events: none;
      z-index: 4;
    }}
    .dome-rim {{
      position: absolute;
      left: 8px;
      bottom: 0;
      width: 264px;
      height: 28px;
      background: linear-gradient(180deg, #e2e8f0 0%, #94a3b8 45%, #64748b 100%);
      border-radius: 50%;
      box-shadow: 0 6px 12px rgba(0,0,0,0.35);
      z-index: 2;
    }}
    .dome-capsules {{
      position: absolute;
      inset: 18px;
      border-radius: 50%;
      overflow: hidden;
    }}
    .mini-capsule {{
      position: absolute;
      left: 0;
      top: 0;
      width: 36px;
      height: 36px;
      border-radius: 50%;
      overflow: hidden;
      border: 1.5px solid rgba(255,255,255,0.7);
      box-shadow: 0 5px 9px rgba(0,0,0,0.44), inset 4px 4px 7px rgba(255,255,255,0.30), inset 0 -5px 7px rgba(0,0,0,0.28);
      will-change: transform;
      transform: translate(-999px, -999px);
    }}
    .mini-capsule::before,
    .mini-capsule::after {{
      content: "";
      position: absolute;
      left: 0;
      width: 100%;
      height: 50%;
    }}
    .mini-capsule::before {{ top: 0; }}
    .mini-capsule::after {{ bottom: 0; }}
    .mini-capsule.c1::before {{ background: #f59e0b; }}
    .mini-capsule.c1::after {{ background: #ffffff; }}
    .mini-capsule.c2::before {{ background: #3b82f6; }}
    .mini-capsule.c2::after {{ background: #f8fafc; }}
    .mini-capsule.c3::before {{ background: #ec4899; }}
    .mini-capsule.c3::after {{ background: #ffffff; }}
    .mini-capsule.c4::before {{ background: #10b981; }}
    .mini-capsule.c4::after {{ background: #fefce8; }}
    .mini-capsule.c5::before {{ background: #a855f7; }}
    .mini-capsule.c5::after {{ background: #ffffff; }}
    .mini-capsule.c6::before {{ background: #ef4444; }}
    .mini-capsule.c6::after {{ background: #f8fafc; }}
    .mini-capsule.c7::before {{ background: #22d3ee; }}
    .mini-capsule.c7::after {{ background: #ffffff; }}
    .mini-capsule.c8::before {{ background: #eab308; }}
    .mini-capsule.c8::after {{ background: #1e293b; }}
    .mini-capsule.c9::before {{ background: #f97316; }}
    .mini-capsule.c9::after {{ background: #fff7ed; }}
    .mini-capsule.c10::before {{ background: #6366f1; }}
    .mini-capsule.c10::after {{ background: #e0e7ff; }}
    .mini-capsule::after {{ filter: brightness(0.88); }}

    /* 機身櫃體 */
    .gashapon-cabinet {{
      position: relative;
      margin: -8px auto 0;
      width: 300px;
      background:
        linear-gradient(180deg, #dc2626 0%, #b91c1c 35%, #991b1b 70%, #7f1d1d 100%);
      border-radius: 8px 8px 14px 14px;
      border: 3px solid #450a0a;
      box-shadow:
        inset 0 2px 0 rgba(255,255,255,0.25),
        inset 0 -10px 20px rgba(0,0,0,0.35);
      padding: 18px 18px 16px;
      z-index: 1;
      transform: translateZ(3px);
    }}
    .gashapon-cabinet::after {{
      content: "";
      position: absolute;
      top: 6px;
      right: 8px;
      width: 8px;
      height: calc(100% - 12px);
      border-radius: 8px;
      background: linear-gradient(180deg, rgba(255,255,255,0.42), rgba(255,255,255,0.04));
      opacity: 0.55;
      pointer-events: none;
    }}
    .cabinet-chrome {{
      position: absolute;
      top: 0;
      left: 10%;
      width: 80%;
      height: 3px;
      background: linear-gradient(90deg, transparent, rgba(255,255,255,0.55), transparent);
    }}
    .cabinet-sticker {{
      background: linear-gradient(180deg, #fff7ed, #fed7aa);
      border: 2px solid #f59e0b;
      border-radius: 8px;
      text-align: center;
      padding: 6px 10px;
      color: #9a3412;
      font-weight: 900;
      font-size: 12px;
      letter-spacing: 1px;
      line-height: 1.25;
      box-shadow: 0 3px 8px rgba(0,0,0,0.25);
      margin-bottom: 12px;
    }}
    .cabinet-sticker small {{
      display: block;
      font-size: 10px;
      letter-spacing: 2px;
      color: #c2410c;
      font-weight: 700;
    }}

    .cabinet-controls {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 12px;
    }}
    .coin-slot {{
      width: 78px;
      height: 78px;
      background: linear-gradient(180deg, #334155, #0f172a);
      border-radius: 10px;
      border: 2px solid #64748b;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 6px;
      box-shadow: inset 0 4px 10px rgba(0,0,0,0.6);
    }}
    .coin-slot-hole {{
      width: 34px;
      height: 6px;
      background: #020617;
      border-radius: 3px;
      border: 1px solid #475569;
      box-shadow: inset 0 2px 4px rgba(0,0,0,0.8);
    }}
    .coin-slot span {{
      font-size: 11px;
      font-weight: 800;
      color: #fbbf24;
      letter-spacing: 1px;
    }}

    .crank-assembly {{
      flex: 1;
      height: 78px;
      background: linear-gradient(180deg, #1e293b, #0f172a);
      border-radius: 12px;
      border: 2px solid #64748b;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: inset 0 4px 12px rgba(0,0,0,0.65);
      position: relative;
    }}
    .crank-dial {{
      width: 58px;
      height: 58px;
      border-radius: 50%;
      background:
        radial-gradient(circle at 35% 30%, #f8fafc 0%, #94a3b8 40%, #475569 75%, #1e293b 100%);
      border: 3px solid #cbd5e1;
      box-shadow:
        0 4px 10px rgba(0,0,0,0.55),
        inset 0 2px 4px rgba(255,255,255,0.45);
      position: relative;
      transform-origin: center center;
    }}
    .crank-dial::before {{
      content: "";
      position: absolute;
      inset: 16px;
      border-radius: 50%;
      background: radial-gradient(circle at 40% 35%, #e2e8f0, #64748b);
      border: 2px solid #94a3b8;
    }}
    .crank-handle {{
      position: absolute;
      top: 50%;
      left: 50%;
      width: 34px;
      height: 10px;
      background: linear-gradient(180deg, #f1f5f9, #64748b);
      border-radius: 5px;
      transform-origin: 0 50%;
      transform: translate(0, -50%);
      box-shadow: 0 2px 4px rgba(0,0,0,0.45);
      border: 1px solid #cbd5e1;
    }}
    .crank-handle::after {{
      content: "";
      position: absolute;
      right: -8px;
      top: 50%;
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: radial-gradient(circle at 35% 30%, #f8fafc, #64748b);
      transform: translateY(-50%);
      border: 1px solid #94a3b8;
      box-shadow: 0 2px 4px rgba(0,0,0,0.4);
    }}
    /* crank rotation driven by JS ratchet physics (no CSS spin) */

    /* 出貨口 */
    .dispense-bay {{
      position: relative;
      height: 70px;
      background: linear-gradient(180deg, #0f172a 0%, #020617 100%);
      border-radius: 10px;
      border: 2px solid #334155;
      box-shadow: inset 0 10px 18px rgba(0,0,0,0.85);
      overflow: hidden;
    }}
    .dispense-flap {{
      position: absolute;
      top: 0;
      left: 18%;
      width: 64%;
      height: 10px;
      background: linear-gradient(180deg, #64748b, #334155);
      border-radius: 0 0 6px 6px;
      z-index: 2;
    }}
    .dispense-label {{
      position: absolute;
      bottom: 6px;
      left: 0;
      right: 0;
      text-align: center;
      font-size: 10px;
      font-weight: 800;
      letter-spacing: 3px;
      color: #475569;
      z-index: 1;
    }}
    .chute-capsule {{
      position: absolute;
      left: 50%;
      top: -50px;
      width: 46px;
      height: 46px;
      margin-left: -23px;
      border-radius: 50%;
      overflow: hidden;
      border: 2px solid rgba(255,255,255,0.7);
      box-shadow: 0 6px 12px rgba(0,0,0,0.5);
      opacity: 0;
      z-index: 3;
    }}
    .chute-capsule::before,
    .chute-capsule::after {{
      content: "";
      position: absolute;
      left: 0;
      width: 100%;
      height: 50%;
    }}
    .chute-capsule::before {{
      top: 0;
      background: #38bdf8;
    }}
    .chute-capsule::after {{
      bottom: 0;
      background: #fbbf24;
    }}
    .chute-capsule.dropping {{
      animation: capsule-drop 0.85s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
    }}
    @keyframes capsule-drop {{
      0% {{ top: -48px; opacity: 0; transform: rotate(0deg); }}
      20% {{ opacity: 1; }}
      70% {{ top: 14px; transform: rotate(220deg); }}
      85% {{ top: 8px; transform: rotate(250deg); }}
      100% {{ top: 12px; opacity: 1; transform: rotate(270deg); }}
    }}
    .chute-capsule.rare::before {{ background: #fbbf24; }}
    .chute-capsule.rare::after {{ background: #ffffff; }}

    .gashapon-base {{
      width: 320px;
      height: 18px;
      margin: 4px auto 0;
      background: linear-gradient(180deg, #334155, #0f172a);
      border-radius: 0 0 10px 10px;
      border: 2px solid #1e293b;
      box-shadow: 0 8px 16px rgba(0,0,0,0.45);
    }}

    .capsule-pop-stage {{
      position: absolute;
      bottom: 8%;
      display: flex;
      flex-direction: column;
      align-items: center;
      opacity: 0;
      transform: translateY(24px) scale(0.86);
      transition: opacity 0.45s ease, transform 0.55s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      pointer-events: none;
      z-index: 20;
    }}
    .capsule-pop-stage.active {{
      opacity: 1;
      transform: translateY(0) scale(1);
    }}
    .capsule-split-container {{
      position: relative;
      width: 100px;
      height: 100px;
      margin-bottom: -12px;
      z-index: 2;
      pointer-events: none;
    }}
    .capsule-half {{
      position: absolute;
      width: 88px;
      height: 44px;
      left: 6px;
      transition: transform 0.65s cubic-bezier(0.2, 0.8, 0.2, 1), opacity 0.65s ease;
      border: 2px solid rgba(255,255,255,0.75);
      box-shadow: 0 6px 14px rgba(0,0,0,0.4);
    }}
    .capsule-half-top {{
      top: 6px;
      border-radius: 44px 44px 8px 8px;
      background: radial-gradient(circle at 35% 30%, rgba(255,255,255,0.95), #38bdf8 55%, #0284c7 100%);
    }}
    .capsule-half-bottom {{
      bottom: 6px;
      border-radius: 8px 8px 44px 44px;
      background: radial-gradient(circle at 40% 70%, #fde68a 0%, #f59e0b 55%, #b45309 100%);
    }}
    .capsule-pop-stage.active .capsule-half-top {{
      transform: translate(-36px, -42px) rotate(-28deg);
      opacity: 0.15;
    }}
    .capsule-pop-stage.active .capsule-half-bottom {{
      transform: translate(36px, 38px) rotate(24deg);
      opacity: 0.15;
    }}
    .toy-bubble {{
      background: rgba(15, 23, 42, 0.94);
      border: 3px solid var(--gold);
      border-radius: 18px;
      padding: 16px 26px;
      box-shadow: 0 15px 45px rgba(0, 0, 0, 0.85), 0 0 24px rgba(245, 158, 11, 0.3);
      text-align: center;
      color: #ffffff;
      display: flex;
      flex-direction: column;
      align-items: center;
      position: relative;
      z-index: 5;
      min-width: 220px;
    }}
    .toy-art-container {{
      width: 140px;
      height: 120px;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .toy-pop-img {{
      max-width: 100%;
      max-height: 110px;
      object-fit: contain;
      filter: drop-shadow(0 10px 18px rgba(0,0,0,0.85));
      animation: toy-pop-bounce 0.65s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }}
    @keyframes toy-pop-bounce {{
      0% {{ transform: scale(0.3) rotate(-10deg); opacity: 0; }}
      70% {{ transform: scale(1.12) rotate(3deg); opacity: 1; }}
      100% {{ transform: scale(1) rotate(0deg); }}
    }}
    .toy-title-text {{
      font-weight: 800;
      font-size: 18px;
      margin-top: 8px;
      background: linear-gradient(90deg, #fef08a, #fbbf24, #f59e0b);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      letter-spacing: 1px;
    }}
    .toy-rarity-badge {{
      font-size: 12px;
      color: #94a3b8;
      margin-top: 4px;
      font-weight: 700;
      letter-spacing: 1px;
    }}

    /* =========================================================================
       4. 二次元星空抽卡 (Card Gacha / 10-Pull 召喚展示)
       ========================================================================= */
    .card-gacha-stage {{
      position: absolute;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transform: scale(0.9);
      /* 禁止 transition: all，避免與子層 3D preserve-3d 衝突導致翻面後正面消失 */
      transition: opacity 0.45s ease, transform 0.45s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      pointer-events: none;
      z-index: 100;
      width: 100vw;
      height: 100vh;
    }}
    .card-gacha-stage.active {{ opacity: 1; transform: scale(1); }}
    /* 震動改由 #overlay-root.screen-shake 負責，勿對本層做 transform animation（會壓扁 3D 卡牌） */

    /* 召喚星空魔法陣 (Summoning Portal) */
    .gacha-summon-portal {{
      position: absolute;
      width: 600px;
      height: 600px;
      display: flex;
      align-items: center;
      justify-content: center;
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.4s ease;
      z-index: 10;
    }}
    .gacha-summon-portal.active {{ opacity: 1; }}
    .summon-magic-circle {{
      position: absolute;
      width: 480px;
      height: 480px;
      filter: drop-shadow(0 0 30px #f59e0b);
      animation: spin-portal 16s linear infinite;
    }}
    @keyframes spin-portal {{
      0% {{ transform: rotate(0deg); }}
      100% {{ transform: rotate(360deg); }}
    }}
    .summon-star-canvas {{
      position: absolute;
      width: 100%;
      height: 100%;
      top: 0;
      left: 0;
      pointer-events: none;
    }}

    /* 單抽卡牌：OBS 友善 2D 翻牌（無 3D backface／無 settle 跳變） */
    .single-card-scene {{
      width: 360px;
      height: 520px;
      z-index: 20;
      position: relative;
      opacity: 0;
      transform: translateY(28px) scale(0.88);
      transition: opacity 0.45s ease, transform 0.55s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }}
    .single-card-scene.visible {{
      opacity: 1;
      transform: translateY(0) scale(1);
    }}
    .card-3d-flipper {{
      width: 100%;
      height: 100%;
      position: relative;
    }}
    .card-3d-flipper.flipped .card-back-side {{
      transform: scaleX(0);
      opacity: 0;
      z-index: 1;
      pointer-events: none;
    }}
    .card-3d-flipper.flipped .card-front-side {{
      transform: scaleX(1);
      opacity: 1;
      z-index: 3;
    }}
    .card-face {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      border-radius: 24px;
      box-shadow: 0 25px 60px rgba(0, 0, 0, 0.9);
      overflow: hidden;
      box-sizing: border-box;
      transition: transform 0.55s cubic-bezier(0.4, 0.0, 0.2, 1), opacity 0.25s ease;
      transform-origin: center center;
    }}
    .card-back-side {{
      background: #0f172a;
      border: 4px solid var(--gold);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 35px rgba(245, 158, 11, 0.6);
      transform: scaleX(1);
      opacity: 1;
      z-index: 2;
    }}
    .card-back-full-img {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
      border-radius: 20px;
    }}
    .card-back-brand {{
      position: absolute;
      bottom: 24px;
      font-weight: 900;
      font-size: 16px;
      color: #fef08a;
      letter-spacing: 5px;
      text-shadow: 0 2px 10px rgba(0, 0, 0, 0.9);
      background: rgba(15, 23, 42, 0.85);
      padding: 6px 18px;
      border-radius: 20px;
      border: 1px solid rgba(245, 158, 11, 0.5);
    }}

    .card-front-side {{
      background: radial-gradient(circle at 50% 30%, #1e1b4b 0%, #090d16 65%, #020617 100%);
      border: 4px solid var(--gold);
      padding: 16px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: space-between;
      position: relative;
      box-shadow: 0 0 40px rgba(245, 158, 11, 0.7);
      transform: scaleX(0);
      opacity: 0;
      z-index: 1;
    }}
    .card-front-side::after {{
      content: "";
      position: absolute;
      inset: 9px;
      border: 1px solid rgba(255,255,255,0.16);
      border-radius: 17px;
      background: linear-gradient(112deg, rgba(255,255,255,0.12), transparent 20%, transparent 78%, rgba(255,255,255,0.04));
      pointer-events: none;
      z-index: 14;
    }}
    .card-front-side.rarity-ssr {{
      border-color: #fbbf24;
      box-shadow: 0 0 45px rgba(251, 191, 36, 0.8), inset 0 0 20px rgba(251, 191, 36, 0.3);
    }}
    .card-front-side.rarity-sr {{
      border-color: #c084fc;
      box-shadow: 0 0 35px rgba(192, 132, 252, 0.7);
    }}
    .card-front-side.rarity-r {{
      border-color: #38bdf8;
      box-shadow: 0 0 30px rgba(56, 189, 248, 0.6);
    }}

    .card-front-side.rarity-ssr::before {{
      content: "";
      position: absolute;
      top: -40%;
      left: -60%;
      width: 40%;
      height: 180%;
      background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.35), transparent);
      transform: skewX(-20deg);
      animation: holo-sheen 2.8s ease-in-out infinite;
      pointer-events: none;
      z-index: 15;
    }}
    @keyframes holo-sheen {{
      0% {{ left: -60%; opacity: 0; }}
      30% {{ opacity: 1; }}
      100% {{ left: 120%; opacity: 0; }}
    }}

    .rarity-badge {{
      font-size: 24px;
      font-weight: 900;
      letter-spacing: 4px;
      text-shadow: 0 2px 10px rgba(0,0,0,0.8);
      z-index: 10;
    }}
    .rarity-badge.ssr {{
      color: #fbbf24;
      background: linear-gradient(90deg, #fef08a, #fbbf24, #f59e0b);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      filter: drop-shadow(0 0 12px rgba(251, 191, 36, 0.8));
    }}
    .rarity-badge.sr {{
      color: #c084fc;
      filter: drop-shadow(0 0 10px rgba(192, 132, 252, 0.7));
    }}
    .rarity-badge.r {{
      color: #38bdf8;
      filter: drop-shadow(0 0 8px rgba(56, 189, 248, 0.6));
    }}

    .card-art-box {{
      width: 100%;
      height: 340px;
      background: radial-gradient(circle at 50% 35%, #2e1065 0%, #0f172a 75%, #020617 100%);
      border-radius: 16px;
      border: 1px solid rgba(251, 191, 36, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      overflow: hidden;
      box-shadow: inset 0 0 25px rgba(0, 0, 0, 0.9);
    }}
    .card-art-box::before {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(135deg, rgba(255,255,255,0.12), transparent 28%),
        radial-gradient(circle at 50% 110%, rgba(245,158,11,0.22), transparent 45%);
      pointer-events: none;
      z-index: 9;
    }}
    .card-character-art {{
      max-width: 96%;
      max-height: 330px;
      object-fit: contain;
      filter: drop-shadow(0 12px 24px rgba(0, 0, 0, 0.9));
      position: relative;
      z-index: 8;
      transform: scale(1.02);
      transition: transform 0.4s ease;
    }}
    .card-character-art:hover {{
      transform: scale(1.08);
    }}

    .card-info-plaque {{
      text-align: center;
      width: 100%;
      background: rgba(15, 23, 42, 0.85);
      border: 1px solid rgba(245, 158, 11, 0.4);
      border-radius: 12px;
      padding: 8px 12px;
      z-index: 10;
    }}
    .card-name-title {{
      font-size: 21px;
      font-weight: 900;
      color: #ffffff;
      letter-spacing: 1px;
    }}
    .card-quote-text {{
      font-size: 13px;
      color: #94a3b8;
      font-style: italic;
      margin-top: 3px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}

    /* 十連抽 5x2 陣列 */
    .ten-pull-stage {{
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      z-index: 25;
    }}
    .ten-pull-header {{
      font-size: 24px;
      font-weight: 900;
      color: #fbbf24;
      letter-spacing: 4px;
      text-shadow: 0 0 15px rgba(251, 191, 36, 0.8);
      margin-bottom: 16px;
      background: rgba(15, 23, 42, 0.85);
      padding: 6px 24px;
      border-radius: 30px;
      border: 2px solid var(--gold);
    }}
    .ten-pull-grid {{
      display: grid;
      grid-template-columns: repeat(5, 126px);
      grid-gap: 14px;
    }}
    .ten-card-flipper {{
      width: 126px;
      height: 180px;
      position: relative;
    }}
    .ten-card-flipper.flipped .ten-card-back {{
      transform: scaleX(0);
      opacity: 0;
      z-index: 1;
    }}
    .ten-card-flipper.flipped .ten-card-front {{
      transform: scaleX(1);
      opacity: 1;
      z-index: 3;
    }}
    .ten-card-face {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      border-radius: 14px;
      overflow: hidden;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.8);
      box-sizing: border-box;
      transition: transform 0.45s cubic-bezier(0.4, 0.0, 0.2, 1), opacity 0.2s ease;
      transform-origin: center center;
    }}
    .ten-card-back {{
      background: #0f172a;
      border: 2px solid #38bdf8;
      display: flex;
      align-items: center;
      justify-content: center;
      transform: scaleX(1);
      opacity: 1;
      z-index: 2;
    }}
    .ten-card-back-img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}
    .ten-card-front {{
      background: radial-gradient(circle at 50% 30%, #1e1b4b 0%, #0f172a 100%);
      border: 2px solid #475569;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: space-between;
      padding: 6px;
      position: relative;
      transform: scaleX(0);
      opacity: 0;
      z-index: 1;
    }}
    .ten-card-front.rarity-ssr {{
      border-color: var(--gold);
      box-shadow: 0 0 20px rgba(245, 158, 11, 0.8);
    }}
    .ten-card-front.rarity-sr {{
      border-color: #c084fc;
      box-shadow: 0 0 15px rgba(192, 132, 252, 0.6);
    }}
    .ten-card-front.rarity-r {{
      border-color: #38bdf8;
    }}
    .ten-rarity-pill {{
      font-size: 13px;
      font-weight: 900;
      letter-spacing: 1px;
    }}
    .ten-rarity-pill.ssr {{ color: #fbbf24; }}
    .ten-rarity-pill.sr {{ color: #c084fc; }}
    .ten-rarity-pill.r {{ color: #38bdf8; }}
    .ten-img-wrap {{
      width: 100%;
      height: 115px;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }}
    .ten-avatar-img {{
      max-width: 90%;
      max-height: 110px;
      object-fit: contain;
      filter: drop-shadow(0 6px 12px rgba(0,0,0,0.8));
    }}
    .ten-name-pill {{
      font-size: 10px;
      color: #f8fafc;
      font-weight: 700;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 100%;
      text-align: center;
    }}
    .ten-ssr-burst {{
      animation: ssr-burst-glow 1s infinite alternate;
    }}
    @keyframes ssr-burst-glow {{
      /* ten-card-flipper already uses scaleX for the reveal.  Rotating the
         whole SSR node here mirrored its artwork after the reveal. */
      0% {{ transform: scale(1); box-shadow: 0 0 15px #f59e0b; }}
      100% {{ transform: scale(1.08); box-shadow: 0 0 35px #fef08a, 0 0 50px #fbbf24; }}
    }}

    /* =========================================================================
       5. 幸運大轉盤 (Lucky Wheel)
       ========================================================================= */
    .wheel-stage {{
      position: absolute;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transform: scale(0.85);
      transition: opacity 0.35s ease, transform 0.45s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      pointer-events: none;
      z-index: 100;
    }}
    .wheel-stage.active {{ opacity: 1; transform: scale(1); }}

    .wheel-container {{
      position: relative;
      width: 360px;
      height: 360px;
      display: flex;
      align-items: center;
      justify-content: center;
      perspective: 900px;
      transform-style: preserve-3d;
      filter: drop-shadow(0 26px 28px rgba(0,0,0,0.55));
    }}
    .wheel-container::before {{
      content: "";
      position: absolute;
      width: 340px;
      height: 340px;
      border-radius: 50%;
      background: linear-gradient(145deg, #7c2d12, #1c1917 72%);
      border: 8px solid #92400e;
      box-shadow: 0 22px 18px rgba(0, 0, 0, 0.55);
      transform: translateY(13px) rotateX(12deg) translateZ(-12px);
    }}
    .wheel-disc {{
      width: 340px;
      height: 340px;
      border-radius: 50%;
      border: 8px solid var(--gold);
      box-shadow: 0 15px 40px rgba(0, 0, 0, 0.8), 0 0 25px rgba(245, 158, 11, 0.5), inset 0 0 0 5px rgba(255,255,255,0.14), inset 0 -18px 24px rgba(0,0,0,0.26);
      transform: rotateX(12deg) rotateZ(0deg) translateZ(2px);
      transform-style: preserve-3d;
    }}
    .wheel-pointer {{
      position: absolute;
      top: -16px;
      left: 50%;
      transform: translateX(-50%);
      width: 0;
      height: 0;
      border-left: 16px solid transparent;
      border-right: 16px solid transparent;
      border-top: 32px solid #ef4444;
      filter: drop-shadow(0 4px 6px rgba(0, 0, 0, 0.6));
      z-index: 20;
      transform-origin: top center;
      transform-style: preserve-3d;
    }}
    .wheel-pointer.flicking {{
      animation: pointer-flick 0.15s ease-in-out infinite alternate;
    }}
    @keyframes pointer-flick {{
      0% {{ transform: translateX(-50%) rotate(-12deg); }}
      100% {{ transform: translateX(-50%) rotate(12deg); }}
    }}

    /* =========================================================================
       6. 3D 物理擲硬幣 (Coin Flip 3D Physics & Euler Wobble)
       ========================================================================= */
    .coin-stage {{
      position: absolute;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transform: scale(0.85);
      transition: all 0.35s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      pointer-events: none;
      z-index: 100;
    }}
    .coin-stage.active {{ opacity: 1; transform: scale(1); }}

    .coin-physics-arena {{
      width: 500px;
      height: 240px;
    }}
    .coin-3d-disc {{
      position: relative;
      width: 120px;
      height: 120px;
      transform-style: preserve-3d;
      transform-origin: center center;
      will-change: transform;
      z-index: 2;
    }}
    /* CSS fallback 也保留圓柱厚度；WebGL 可用時會由 CylinderGeometry 呈現同一個剛體。 */
    .coin-thickness-layer {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      border-radius: 50%;
      box-sizing: border-box;
      background: linear-gradient(145deg, #fbbf24 0%, #b45309 52%, #78350f 100%);
      border: 5px solid #92400e;
      box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.45);
      pointer-events: none;
      z-index: 0;
    }}
    .coin-face {{
      position: absolute;
      width: 100%;
      height: 100%;
      border-radius: 50%;
      backface-visibility: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: inset 0 0 12px rgba(0,0,0,0.5), 0 8px 25px rgba(0,0,0,0.6);
      box-sizing: border-box;
      z-index: 2;
    }}
    .coin-face-heads {{
      background: radial-gradient(circle at 35% 35%, #fef08a 0%, #fbbf24 45%, #d97706 75%, #78350f 100%);
      border: 4px solid #fef08a;
      transform: rotateY(0deg) translateZ(8px);
    }}
    .coin-face-tails {{
      background: radial-gradient(circle at 35% 35%, #f8fafc 0%, #e2e8f0 45%, #94a3b8 75%, #475569 100%);
      border: 4px solid #f8fafc;
      transform: rotateY(180deg) translateZ(8px);
    }}
    .coin-relief-ring {{
      width: 100px;
      height: 100px;
      border-radius: 50%;
      border: 2px dashed rgba(255, 255, 255, 0.45);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      box-shadow: inset 0 0 8px rgba(0, 0, 0, 0.35);
    }}
    .coin-emblem {{
      font-size: 34px;
      filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.6));
    }}
    .coin-text-top {{
      font-size: 8px;
      font-weight: 900;
      letter-spacing: 2px;
      color: rgba(255, 255, 255, 0.95);
      text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
    }}
    .coin-text-bottom {{
      font-size: 8px;
      font-weight: 800;
      letter-spacing: 1.5px;
      color: rgba(255, 255, 255, 0.9);
      text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
      margin-top: 1px;
    }}
    .coin-edge-rim {{
      position: absolute;
      width: 100%;
      height: 100%;
      border-radius: 50%;
      border: 5px solid #d97706;
      box-sizing: border-box;
      pointer-events: none;
      transform: translateZ(8px);
      z-index: 3;
    }}
    .coin-3d-disc[data-face="?"] .coin-edge-rim::after {{
      content: "?";
      position: absolute;
      inset: 34% 34%;
      display: grid;
      place-items: center;
      border-radius: 50%;
      background: rgba(15, 23, 42, 0.82);
      color: #fef08a;
      font: 900 26px/1 monospace;
      text-shadow: 0 0 12px #f59e0b;
    }}
    .coin-shadow {{
      position: absolute;
      left: 50%;
      top: 50%;
      width: 90px;
      height: 32px;
      margin-left: -45px;
      margin-top: -16px;
      background: radial-gradient(ellipse at center, rgba(0, 0, 0, 0.7) 0%, rgba(0, 0, 0, 0.1) 60%, transparent 80%);
      border-radius: 50%;
      pointer-events: none;
      transform-origin: center center;
      will-change: transform, opacity;
      z-index: 1;
    }}

    .coin-physics-arena canvas,
    .dice-physics-arena canvas,
    .gamble-physics-arena canvas {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 5;
      border-radius: 26px;
    }}

    /* =========================================================================
       7. 3D 物理擲骰子 (3D Physics Dice with Multi-Die Collisions)
       ========================================================================= */
    .dice-stage {{
      position: absolute;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transform: scale(0.85);
      transition: all 0.35s ease;
      pointer-events: none;
      z-index: 100;
    }}
    .dice-stage.active {{ opacity: 1; transform: scale(1); }}

    .dice-physics-arena {{
      width: 500px;
      height: 240px;
    }}

    /* 共用 throw-plane 已取代各模組自行繪製的地面陰影。 */
    .dice-physics-arena::before {{
      display: none;
    }}
    .dice-physics-arena.uses-webgl::before {{
      display: none;
    }}

    .dice-webgl-canvas {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 10;
      display: none;
    }}
    .die-wrapper {{
      position: absolute;
      width: 68px;
      height: 68px;
      transform-style: preserve-3d;
      transform-origin: 34px 34px 0;
      will-change: transform;
      z-index: 2;
    }}
    .die-wrapper::after {{
      /* A seventh, always-front-facing panel used to sit here.  At oblique
         quaternions it looked like a detached face, so the six physical cube
         faces now provide all visible volume. */
      content: none;
    }}
    .die-shadow {{
      position: absolute;
      width: 76px;
      height: 32px;
      background: radial-gradient(ellipse at center, rgba(0, 0, 0, 0.65) 0%, rgba(0, 0, 0, 0.15) 60%, transparent 80%);
      border-radius: 50%;
      pointer-events: none;
      transform-origin: center center;
      will-change: transform, opacity;
      z-index: 1;
    }}
    .die-cube {{
      position: absolute;
      width: 68px;
      height: 68px;
      transform-style: preserve-3d;
    }}
    .die-face {{
      position: absolute;
      inset: 0;
      width: 68px;
      height: 68px;
      background:
        radial-gradient(circle at 30% 24%, rgba(255,255,255,0.98) 0%, rgba(255,255,255,0.0) 32%),
        linear-gradient(145deg, #ffffff 0%, #f8fafc 46%, #e2e8f0 82%, #94a3b8 100%);
      border: 1px solid rgba(100, 116, 139, 0.70);
      border-radius: 9px;
      box-shadow:
        inset 3px 3px 7px rgba(255,255,255,0.82),
        inset -5px -6px 10px rgba(15,23,42,0.14);
      box-sizing: border-box;
      backface-visibility: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    /* Reference die convention: +Z=1, +X=2, -Z=3, -X=4, -Y=5, +Y=6. */
    .face-1 {{ transform: rotateY(0deg) translateZ(34px); }}
    .face-2 {{ transform: rotateY(90deg) translateZ(34px); }}
    .face-3 {{ transform: rotateY(180deg) translateZ(34px); }}
    .face-4 {{ transform: rotateY(-90deg) translateZ(34px); }}
    .face-5 {{ transform: rotateX(90deg) translateZ(34px); }}
    .face-6 {{ transform: rotateX(-90deg) translateZ(34px); }}

    .pip {{
      width: 13px;
      height: 13px;
      border-radius: 50%;
      background:
        radial-gradient(circle at 31% 25%, rgba(255,255,255,0.22) 0%, rgba(255,255,255,0) 24%),
        radial-gradient(circle at 40% 38%, #475569 0%, #1e293b 48%, #020617 100%);
      box-shadow: inset 2px 3px 4px rgba(0,0,0,0.82), inset -1px -1px 2px rgba(255,255,255,0.12), 0 1px 1px rgba(255,255,255,0.75);
    }}
    .pip-red {{
      background:
        radial-gradient(circle at 31% 25%, rgba(255,255,255,0.34) 0%, rgba(255,255,255,0) 24%),
        radial-gradient(circle at 40% 38%, #fb7185 0%, #dc2626 48%, #7f1d1d 100%);
      box-shadow: inset 2px 3px 4px rgba(0,0,0,0.68), inset -1px -1px 2px rgba(255,255,255,0.20), 0 1px 1px rgba(255,255,255,0.75);
    }}
    .pip-center-big {{
      width: 25px;
      height: 25px;
    }}
    .face-layout-1 {{ display: flex; align-items: center; justify-content: center; }}
    .face-layout-2 {{ display: flex; justify-content: space-between; width: 100%; height: 100%; padding: 10px; }}
    .face-layout-2 .pip:nth-child(2) {{ align-self: flex-end; }}
    .face-layout-3 {{ display: flex; justify-content: space-between; width: 100%; height: 100%; padding: 8px; }}
    .face-layout-3 .pip:nth-child(2) {{ align-self: center; }}
    .face-layout-3 .pip:nth-child(3) {{ align-self: flex-end; }}
    .face-layout-4 {{ display: grid; grid-template: 1fr 1fr / 1fr 1fr; width: 100%; height: 100%; padding: 10px; place-items: center; }}
    .face-layout-5 {{ position: relative; width: 100%; height: 100%; }}
    .face-layout-5 .pip:nth-child(1) {{ position: absolute; top: 10px; left: 10px; }}
    .face-layout-5 .pip:nth-child(2) {{ position: absolute; top: 10px; right: 10px; }}
    .face-layout-5 .pip:nth-child(3) {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); }}
    .face-layout-5 .pip:nth-child(4) {{ position: absolute; bottom: 10px; left: 10px; }}
    .face-layout-5 .pip:nth-child(5) {{ position: absolute; bottom: 10px; right: 10px; }}
    .face-layout-6 {{ display: grid; grid-template: repeat(3, 1fr) / 1fr 1fr; width: 100%; height: 100%; padding: 8px 12px; place-items: center; }}

    .game-float-bubble {{
      margin-top: 14px;
      padding: 10px 24px;
      background: rgba(255, 255, 255, 0.96);
      border: 1px solid #cfc9e8;
      border-radius: 30px;
      box-shadow: 0 8px 25px rgba(26, 26, 31, 0.18);
      text-align: center;
      color: #2d2944;
      font-size: 15px;
      font-weight: 600;
    }}

    /* =========================================================================
       8. 猜大小骰寶 (Gamble Big/Small / Sic Bo 3D Physics)
       ========================================================================= */
    .gamble-stage {{
      position: absolute;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transform: scale(0.85);
      transition: all 0.35s ease;
      pointer-events: none;
      z-index: 100;
    }}
    .gamble-stage.active {{ opacity: 1; transform: scale(1); }}

    .gamble-arena {{
      width: 500px;
      height: 240px;
    }}

    .gamble-physics-arena {{
      position: absolute;
      inset: 0;
      width: 500px;
      height: 240px;
      pointer-events: none;
      z-index: 6;
    }}

    .gamble-webgl-canvas {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 10;
      display: none;
    }}

    .gamble-cup {{
      position: absolute;
      width: 140px;
      height: 150px;
      bottom: 20px;
      z-index: 12;
      transform-origin: bottom center;
      filter: drop-shadow(0 15px 25px rgba(0, 0, 0, 0.8));
    }}
    .gamble-cup.shaking {{
      animation: cup-shake 1.3s cubic-bezier(0.36, 0.07, 0.19, 0.97) both;
    }}
    @keyframes cup-shake {{
      10%, 90% {{ transform: translate3d(-6px, -2px, 0) rotate(-7deg); }}
      20%, 80% {{ transform: translate3d(8px, 3px, 0) rotate(9deg); }}
      30%, 50%, 70% {{ transform: translate3d(-10px, -4px, 0) rotate(-11deg); }}
      40%, 60% {{ transform: translate3d(10px, 4px, 0) rotate(11deg); }}
    }}
    .gamble-cup.lifted {{
      animation: cup-lift 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
    }}
    @keyframes cup-lift {{
      0% {{ transform: translateY(0) rotateX(0deg); opacity: 1; }}
      100% {{ transform: translateY(-150px) rotateX(30deg) scale(0.85); opacity: 0; pointer-events: none; }}
    }}

    .gamble-tag {{
      position: relative;
      z-index: 20;
      font-size: 26px;
      font-weight: 900;
      letter-spacing: 3px;
      padding: 4px 20px;
      border-radius: 20px;
      margin-top: 10px;
      text-shadow: 0 0 12px currentColor;
    }}
    .gamble-tag.tag-big {{ color: #fbbf24; background: rgba(2, 6, 23, 0.86); border: 2px solid #f59e0b; box-shadow: 0 8px 22px rgba(0,0,0,0.45), inset 0 0 16px rgba(245,158,11,0.12); }}
    .gamble-tag.tag-small {{ color: #7dd3fc; background: rgba(2, 6, 23, 0.86); border: 2px solid #38bdf8; box-shadow: 0 8px 22px rgba(0,0,0,0.45), inset 0 0 16px rgba(56,189,248,0.12); }}
    .gamble-tag.tag-triple {{ color: #f9a8d4; background: rgba(2, 6, 23, 0.90); border: 2px solid #ec4899; box-shadow: 0 8px 22px rgba(0,0,0,0.45), inset 0 0 16px rgba(236,72,153,0.14); }}

    .gamble-res-badge {{
      position: relative;
      z-index: 20;
      font-size: 17px;
      font-weight: 800;
      margin-top: 6px;
      padding: 5px 20px;
      border-radius: 24px;
    }}
    .gamble-res-badge.win {{ color: #fde047; background: rgba(2, 6, 23, 0.86); border: 1px solid #10b981; box-shadow: 0 6px 18px rgba(0,0,0,0.35); }}
    .gamble-res-badge.lose {{ color: #cbd5e1; background: rgba(2, 6, 23, 0.86); border: 1px solid #475569; box-shadow: 0 6px 18px rgba(0,0,0,0.35); }}

    /* =========================================================================
       9. 浮動自訂計數器 HUD (Counter Widget)
       ========================================================================= */
    #counter-hud-widget {{
      position: absolute;
      top: 32px;
      left: 32px;
      display: flex;
      align-items: center;
      gap: 12px;
      background: rgba(15, 23, 42, 0.88);
      backdrop-filter: blur(8px);
      border: 1px solid rgba(56, 189, 248, 0.4);
      border-radius: 40px;
      padding: 8px 20px 8px 12px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.6);
      opacity: 0;
      transform: translateY(-20px);
      transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      z-index: 200;
    }}
    #counter-hud-widget.active {{ opacity: 1; transform: translateY(0); }}

    .counter-icon-wrap {{
      width: 42px;
      height: 42px;
      border-radius: 50%;
      background: linear-gradient(135deg, #0284c7, #0f172a);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      border: 1px solid #38bdf8;
    }}
    .counter-num-box {{
      font-size: 28px;
      font-weight: 900;
      font-family: monospace;
      color: #38bdf8;
      text-shadow: 0 0 10px rgba(56, 189, 248, 0.6);
      min-width: 48px;
    }}
    .counter-delta-float {{
      position: absolute;
      right: -20px;
      top: -10px;
      font-size: 20px;
      font-weight: 900;
      padding: 2px 8px;
      border-radius: 12px;
      animation: float-delta 1.2s ease-out forwards;
      pointer-events: none;
    }}
    @keyframes float-delta {{
      0% {{ transform: translateY(0) scale(0.6); opacity: 0; }}
      20% {{ transform: translateY(-8px) scale(1.2); opacity: 1; }}
      100% {{ transform: translateY(-30px) scale(1); opacity: 0; }}
    }}

    /* =========================================================================
       10. 馬拉松倒數計時器 HUD (Subathon Timer Widget)
       ========================================================================= */
    #subathon-hud-widget {{
      position: absolute;
      top: 32px;
      right: 32px;
      display: flex;
      align-items: center;
      gap: 12px;
      background: rgba(15, 23, 42, 0.9);
      backdrop-filter: blur(10px);
      border: 2px solid rgba(16, 185, 129, 0.6);
      border-radius: 18px;
      padding: 10px 22px;
      box-shadow: 0 12px 30px rgba(0,0,0,0.7), 0 0 20px rgba(16, 185, 129, 0.3);
      opacity: 0;
      transform: translateY(-20px);
      transition: all 0.4s ease;
      z-index: 200;
    }}
    #subathon-hud-widget.active {{ opacity: 1; transform: translateY(0); }}
    .subathon-pulse-dot {{
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 8px #10b981;
      animation: subathon-blink 1.2s infinite ease-in-out;
    }}
    @keyframes subathon-blink {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.3; transform: scale(0.7); }}
    }}
    .subathon-digits {{
      font-size: 32px;
      font-weight: 900;
      font-family: monospace;
      letter-spacing: 2px;
      color: #f8fafc;
      text-shadow: 0 0 12px rgba(16, 185, 129, 0.8);
    }}

    /* =========================================================================
       11. 翻唱歌單 / 正在演唱 HUD (Cover / Now Playing Widget)
       ========================================================================= */
    #cover-hud-widget {{
      position: absolute;
      bottom: 32px;
      left: 32px;
      display: flex;
      align-items: center;
      gap: 14px;
      background: rgba(15, 23, 42, 0.92);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(236, 72, 153, 0.5);
      border-radius: 50px;
      padding: 8px 24px 8px 10px;
      box-shadow: 0 12px 30px rgba(0,0,0,0.7);
      opacity: 0;
      transform: translateY(20px);
      transition: all 0.4s ease;
      z-index: 200;
    }}
    #cover-hud-widget.active {{ opacity: 1; transform: translateY(0); }}
    .cover-vinyl {{
      width: 48px;
      height: 48px;
      border-radius: 50%;
      background: radial-gradient(circle at center, #ec4899 0%, #1e1b4b 40%, #020617 100%);
      border: 2px solid #f472b6;
      box-shadow: 0 0 12px rgba(236, 72, 153, 0.6);
      display: flex;
      align-items: center;
      justify-content: center;
      animation: spin-vinyl 4s linear infinite;
    }}
    @keyframes spin-vinyl {{
      0% {{ transform: rotate(0deg); }}
      100% {{ transform: rotate(360deg); }}
    }}
    .equalizer-bars {{
      display: flex;
      align-items: flex-end;
      gap: 2px;
      height: 18px;
    }}
    .eq-bar {{
      width: 3px;
      background: #ec4899;
      border-radius: 2px;
      animation: eq-bounce 0.6s ease-in-out infinite alternate;
    }}
    @keyframes eq-bounce {{
      0% {{ height: 4px; }}
      100% {{ height: 18px; }}
    }}

    /* =========================================================================
       12. 活躍觀眾抽籤獲獎彈窗 (Picker Jackpot Modal)
       ========================================================================= */
    .picker-stage {{
      position: absolute;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transform: scale(0.85);
      transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      pointer-events: none;
      z-index: 150;
      background: rgba(15, 23, 42, 0.95);
      border: 3px solid var(--gold);
      border-radius: 28px;
      padding: 32px 48px;
      box-shadow: 0 25px 60px rgba(0,0,0,0.9), 0 0 35px rgba(245, 158, 11, 0.5);
    }}
    .picker-stage.active {{ opacity: 1; transform: scale(1); }}

    /* =========================================================================
       13. 活動排隊叫號廣播 (Queue Call Alert)
       ========================================================================= */
    #queue-call-alert {{
      position: absolute;
      top: 40px;
      left: 50%;
      transform: translateX(-50%) translateY(-40px);
      background: linear-gradient(90deg, rgba(30, 58, 138, 0.95), rgba(15, 23, 42, 0.95));
      border: 2px solid #38bdf8;
      border-radius: 40px;
      padding: 12px 36px;
      display: flex;
      align-items: center;
      gap: 16px;
      box-shadow: 0 15px 40px rgba(0,0,0,0.8), 0 0 25px rgba(56, 189, 248, 0.5);
      opacity: 0;
      transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      z-index: 300;
      pointer-events: none;
    }}
    #queue-call-alert.active {{
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }}
    #queue-list-panel {{
      position: absolute;
      top: 116px;
      right: 32px;
      width: 280px;
      max-height: 310px;
      overflow: hidden;
      padding: 14px 16px;
      border: 1px solid rgba(56, 189, 248, 0.5);
      border-radius: 16px;
      background: rgba(8, 15, 31, 0.92);
      box-shadow: 0 16px 34px rgba(0, 0, 0, 0.65), 0 0 22px rgba(56, 189, 248, 0.18);
      backdrop-filter: blur(10px);
      opacity: 0;
      transform: translateY(-12px);
      transition: opacity 0.35s ease, transform 0.35s ease;
      z-index: 295;
      pointer-events: none;
    }}
    #queue-list-panel.active {{ opacity: 1; transform: translateY(0); }}
    .queue-list-heading {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      color: #e0f2fe;
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 1px;
      margin-bottom: 8px;
    }}
    #queue-list-items {{
      display: flex;
      flex-direction: column;
      gap: 5px;
      max-height: 250px;
      overflow-y: auto;
      color: #cbd5e1;
      font-size: 12px;
    }}
    .queue-list-row {{
      display: grid;
      grid-template-columns: 24px 1fr auto;
      align-items: center;
      gap: 6px;
      padding: 6px 8px;
      border-radius: 8px;
      background: rgba(30, 58, 138, 0.28);
    }}
    .queue-list-row:first-child {{
      color: #fef08a;
      background: rgba(245, 158, 11, 0.18);
    }}

    /* =========================================================================
       14. 社群下注預測 HUD (Community Betting Widget)
       ========================================================================= */
    #bet-hud-widget {{
      position: absolute;
      top: 32px;
      left: 50%;
      transform: translateX(-50%) translateY(-20px);
      width: 460px;
      background: rgba(15, 23, 42, 0.94);
      backdrop-filter: blur(12px);
      border: 2px solid rgba(245, 158, 11, 0.6);
      border-radius: 20px;
      padding: 14px 22px;
      box-shadow: 0 16px 36px rgba(0,0,0,0.8), 0 0 25px rgba(245, 158, 11, 0.25);
      opacity: 0;
      transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      z-index: 250;
      pointer-events: none;
    }}
    #bet-hud-widget.active {{
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }}
    .bet-header-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }}
    .bet-badge {{
      font-size: 11px;
      font-weight: 800;
      padding: 2px 10px;
      border-radius: 12px;
      letter-spacing: 1px;
    }}
    .bet-badge.open {{ background: rgba(16, 185, 129, 0.25); color: #34d399; border: 1px solid #10b981; }}
    .bet-badge.locked {{ background: rgba(239, 68, 68, 0.25); color: #f87171; border: 1px solid #ef4444; }}
    .bet-badge.resolved {{ background: rgba(245, 158, 11, 0.25); color: #fbbf24; border: 1px solid #f59e0b; }}
    .bet-bar-wrap {{
      width: 100%;
      height: 18px;
      background: #1e293b;
      border-radius: 10px;
      overflow: hidden;
      display: flex;
      position: relative;
      margin: 8px 0;
      border: 1px solid rgba(255,255,255,0.1);
    }}
    .bet-bar-a {{
      height: 100%;
      background: linear-gradient(90deg, #0284c7, #38bdf8);
      transition: width 0.4s ease;
    }}
    .bet-bar-b {{
      height: 100%;
      background: linear-gradient(90deg, #ec4899, #f43f5e);
      transition: width 0.4s ease;
    }}
    .bet-vs-pill {{
      position: absolute;
      left: 50%;
      top: 50%;
      transform: translate(-50%, -50%);
      font-size: 10px;
      font-weight: 900;
      background: #0f172a;
      border: 1px solid #64748b;
      padding: 1px 6px;
      border-radius: 8px;
      color: #f8fafc;
      z-index: 2;
    }}
    .bet-odds-row {{
      display: flex;
      justify-content: space-between;
      font-size: 13px;
    }}
    .bet-opt-box {{
      display: flex;
      flex-direction: column;
    }}
    .bet-opt-a {{ color: #38bdf8; text-align: left; }}
    .bet-opt-b {{ color: #f43f5e; text-align: right; }}
    .bet-winner-glow-a {{ border-color: #38bdf8 !important; box-shadow: 0 0 30px rgba(56,189,248,0.7) !important; }}
    .bet-winner-glow-b {{ border-color: #f43f5e !important; box-shadow: 0 0 30px rgba(244,63,94,0.7) !important; }}

    /* =========================================================================
       15. 點歌播放器 HUD (Song Request & Music Player Widget)
       ========================================================================= */
    #music-hud-widget {{
      position: absolute;
      bottom: 36px;
      right: 36px;
      width: 420px;
      background: rgba(15, 23, 42, 0.94);
      backdrop-filter: blur(14px);
      border: 2px solid rgba(168, 85, 247, 0.5);
      border-radius: 20px;
      padding: 16px 20px;
      box-shadow: 0 16px 36px rgba(0,0,0,0.8), 0 0 25px rgba(168, 85, 247, 0.25);
      opacity: 0;
      transform: translateY(20px);
      transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      z-index: 240;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    #music-hud-widget.active {{
      opacity: 1;
      transform: translateY(0);
    }}
    .music-top-row {{
      display: flex;
      align-items: center;
      gap: 14px;
    }}
    .music-vinyl-disc {{
      width: 50px;
      height: 50px;
      border-radius: 50%;
      background: radial-gradient(circle, #38bdf8 0%, #1e1b4b 35%, #09090b 70%, #18181b 100%);
      border: 2px solid rgba(255, 255, 255, 0.25);
      box-shadow: 0 0 15px rgba(168, 85, 247, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      animation: spin-vinyl 4s linear infinite;
      flex-shrink: 0;
      font-size: 20px;
    }}
    .music-info-col {{
      flex: 1;
      min-width: 0;
    }}
    .music-title-text {{
      font-size: 15px;
      font-weight: 800;
      color: #ffffff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .music-artist-text {{
      font-size: 12px;
      color: #c084fc;
      font-weight: 600;
      margin-top: 2px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .music-user-tag {{
      font-size: 11px;
      color: #94a3b8;
    }}
    .music-progress-wrap {{
      width: 100%;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .music-bar-bg {{
      width: 100%;
      height: 6px;
      background: #334155;
      border-radius: 4px;
      overflow: hidden;
    }}
    .music-bar-fill {{
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, #a855f7, #ec4899);
      border-radius: 4px;
      transition: width 1s linear;
    }}
    .music-time-row {{
      display: flex;
      justify-content: space-between;
      font-size: 10px;
      color: #94a3b8;
      font-weight: 700;
      letter-spacing: 0.5px;
    }}

    /* =========================================================================
       16. 雙語字幕即時翻譯 HUD (Subtitle & Translation Widget)
       ========================================================================= */
    #trans-hud-widget {{
      position: absolute;
      bottom: 40px;
      left: 50%;
      transform: translateX(-50%) translateY(20px);
      max-width: 780px;
      min-width: 460px;
      background: rgba(15, 23, 42, 0.94);
      backdrop-filter: blur(14px);
      border: 2px solid rgba(6, 182, 212, 0.5);
      border-radius: 24px;
      padding: 14px 24px;
      box-shadow: 0 16px 36px rgba(0,0,0,0.8), 0 0 25px rgba(6, 182, 212, 0.25);
      opacity: 0;
      transition: all 0.35s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      z-index: 260;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    #trans-hud-widget.active {{
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }}
    .trans-meta-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }}
    .trans-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      font-weight: 800;
      background: rgba(6, 182, 212, 0.15);
      color: #22d3ee;
      border: 1px solid rgba(6, 182, 212, 0.4);
      border-radius: 12px;
      padding: 2px 10px;
      letter-spacing: 0.5px;
    }}
    .trans-user {{
      font-size: 12px;
      color: #94a3b8;
      font-weight: 700;
    }}
    .trans-orig-text {{
      font-size: 13px;
      color: #94a3b8;
      font-style: italic;
      line-height: 1.4;
    }}
    .trans-main-text {{
      font-size: 18px;
      font-weight: 900;
      color: #ffffff;
      line-height: 1.4;
      text-shadow: 0 0 10px rgba(6, 182, 212, 0.5);
    }}

    /* =========================================================================
       17. 贊助通知彈窗 HUD (Donation & Sponsor Alert)
       ========================================================================= */
    #donation-alert-widget {{
      position: absolute;
      top: 50px;
      left: 50%;
      transform: translateX(-50%) translateY(-30px);
      width: 480px;
      background: rgba(15, 23, 42, 0.96);
      backdrop-filter: blur(16px);
      border: 2px solid rgba(245, 158, 11, 0.8);
      border-radius: 24px;
      padding: 18px 24px;
      box-shadow: 0 20px 45px rgba(0,0,0,0.85), 0 0 35px rgba(245, 158, 11, 0.5);
      opacity: 0;
      transition: all 0.45s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      z-index: 280;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      text-align: center;
    }}
    #donation-alert-widget.active {{
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }}
    .donation-badge-row {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      font-weight: 900;
      background: linear-gradient(90deg, #d97706, #f59e0b);
      color: #0f172a;
      border-radius: 12px;
      padding: 2px 12px;
      letter-spacing: 1px;
    }}
    .donation-amount-text {{
      font-size: 32px;
      font-weight: 900;
      color: #fbbf24;
      text-shadow: 0 0 20px rgba(245, 158, 11, 0.8);
      letter-spacing: 1px;
    }}
    .donation-donor-text {{
      font-size: 16px;
      font-weight: 800;
      color: #ffffff;
    }}
    .donation-msg-bubble {{
      width: 100%;
      background: rgba(30, 41, 59, 0.7);
      border: 1px solid rgba(245, 158, 11, 0.3);
      border-radius: 12px;
      padding: 8px 14px;
      font-size: 14px;
      color: #f1f5f9;
      line-height: 1.4;
      word-break: break-word;
    }}
    .donation-bonus-row {{
      display: flex;
      gap: 10px;
      font-size: 11px;
      font-weight: 700;
      color: #10b981;
    }}
  </style>
</head>
<body>
  <!-- Canvas VFX: Sparks, Confetti, Coin Rain -->
  <canvas id="vfx-canvas"></canvas>

  <!-- Cinema VFX Elements -->
  <div id="spotlight-vignette"></div>
  <div id="god-rays"></div>
  <div id="shockwave-ring"></div>

  <div id="status-indicator">WS 待命</div>

  <div id="overlay-root">
    <!-- 1. 擲筊舞台 -->
    <div id="bwei-stage" class="bwei-stage">
      <div class="bwei-arena">
        <div class="bwei-cup-wrap">
          <div id="shadow-left" class="bwei-shadow"></div>
          <svg id="cup-left" class="bwei-cup-svg" viewBox="0 0 140 90">
            <defs>
              <linearGradient id="grad-curved-left" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#7f1d1d" /><stop offset="45%" stop-color="#b91c1c" /><stop offset="100%" stop-color="#450a0a" />
              </linearGradient>
              <linearGradient id="grad-flat-left" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#d97706" /><stop offset="60%" stop-color="#b45309" /><stop offset="100%" stop-color="#78350f" />
              </linearGradient>
            </defs>
            <path class="cup-base-edge" d="M 13,70 C 34,78 106,78 127,70 L 125,81 C 101,89 39,89 15,81 Z" fill="#2a0707"/>
            <path class="cup-depth" d="M 15,75 C 25,10 115,10 125,75 C 85,55 55,55 15,75 Z" fill="#3b0a0a" transform="translate(0 8)"/>
            <path id="cup-left-path" d="M 15,75 C 25,10 115,10 125,75 C 85,55 55,55 15,75 Z" fill="url(#grad-curved-left)" stroke="#450a0a" stroke-width="3"/>
            <path class="cup-highlight" d="M 28,59 C 38,25 101,22 113,58" fill="none" stroke="#fca5a5" stroke-width="3" stroke-linecap="round" opacity="0.48"/>
            <ellipse id="cup-left-ridge" cx="70" cy="50" rx="42" ry="14" fill="#ef4444" opacity="0.6"/>
            <path class="cup-rim-glint" d="M 20,70 C 42,61 98,61 120,70" fill="none" stroke="rgba(255,255,255,0.55)" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
        <div class="bwei-cup-wrap">
          <div id="shadow-right" class="bwei-shadow"></div>
          <svg id="cup-right" class="bwei-cup-svg" viewBox="0 0 140 90">
            <defs>
              <linearGradient id="grad-curved-right" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#7f1d1d" /><stop offset="50%" stop-color="#b91c1c" /><stop offset="100%" stop-color="#450a0a" />
              </linearGradient>
              <linearGradient id="grad-flat-right" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#d97706" /><stop offset="55%" stop-color="#b45309" /><stop offset="100%" stop-color="#78350f" />
              </linearGradient>
            </defs>
            <path class="cup-base-edge" d="M 13,70 C 34,78 106,78 127,70 L 125,81 C 101,89 39,89 15,81 Z" fill="#2a0707"/>
            <path class="cup-depth" d="M 15,75 C 25,10 115,10 125,75 C 85,55 55,55 15,75 Z" fill="#3b0a0a" transform="translate(0 8)"/>
            <path id="cup-right-path" d="M 15,75 C 25,10 115,10 125,75 C 85,55 55,55 15,75 Z" fill="url(#grad-curved-right)" stroke="#450a0a" stroke-width="3"/>
            <path class="cup-highlight" d="M 28,59 C 38,25 101,22 113,58" fill="none" stroke="#fca5a5" stroke-width="3" stroke-linecap="round" opacity="0.48"/>
            <ellipse id="cup-right-ridge" cx="70" cy="50" rx="42" ry="14" fill="#ef4444" opacity="0.6"/>
            <path class="cup-rim-glint" d="M 20,70 C 42,61 98,61 120,70" fill="none" stroke="rgba(255,255,255,0.55)" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
      </div>
      <div class="bwei-banner">
        <div id="bwei-user" class="bwei-user">@觀眾 擲出了</div>
        <div id="bwei-title" class="bwei-title res-sheng">【 聖 筊 】</div>
        <div id="bwei-desc" class="bwei-desc">神明贊同，大吉大利！</div>
      </div>
    </div>

    <!-- 2. 拉霸老虎機 -->
    <div id="slot-stage" class="slot-stage">
      <div class="slot-cabinet">
        <div class="slot-title">★ 777 STREAM CASINO ★</div>
        <div class="slot-reels-frame">
          <div class="slot-payline" id="slot-payline"></div>
          <div class="slot-reel-viewport"><div id="strip-0" class="slot-reel-strip"><div class="reel-item">7️⃣</div><div class="reel-item">🎰</div><div class="reel-item">🔔</div><div class="reel-item">🍒</div></div></div>
          <div class="slot-reel-viewport"><div id="strip-1" class="slot-reel-strip"><div class="reel-item">7️⃣</div><div class="reel-item">🎰</div><div class="reel-item">🔔</div><div class="reel-item">🍒</div></div></div>
          <div class="slot-reel-viewport"><div id="strip-2" class="slot-reel-strip"><div class="reel-item">7️⃣</div><div class="reel-item">🎰</div><div class="reel-item">🔔</div><div class="reel-item">🍒</div></div></div>
        </div>
        <div class="slot-footer">
          <div id="slot-user" style="font-size: 13px; color: #94a3b8; margin-bottom: 2px;">@觀眾 投注 50 點</div>
          <div id="slot-result-text" class="slot-result-text">中獎 500 點！</div>
          <div id="slot-jackpot-badge" class="slot-jackpot-badge" style="display: none;">JACKPOT 10x!</div>
        </div>
        <div id="slot-lever" class="slot-lever"><div class="slot-lever-knob"></div></div>
      </div>
    </div>

    <!-- 3. 實體日式扭蛋機 (Realistic Bandai-style Gashapon) -->
    <div id="gashapon-stage" class="gashapon-machine-stage">
      <div class="gashapon-machine">
        <div class="gashapon-sign">GASHAPON</div>
        <div class="gashapon-dome">
          <div class="dome-glass">
            <div class="dome-shine"></div>
            <div class="dome-capsules" id="dome-capsules">
              <div class="mini-capsule c1"></div>
              <div class="mini-capsule c2"></div>
              <div class="mini-capsule c3"></div>
              <div class="mini-capsule c4"></div>
              <div class="mini-capsule c5"></div>
              <div class="mini-capsule c6"></div>
              <div class="mini-capsule c7"></div>
              <div class="mini-capsule c8"></div>
              <div class="mini-capsule c9"></div>
              <div class="mini-capsule c10"></div>
            </div>
          </div>
          <div class="dome-rim"></div>
        </div>
        <div class="gashapon-cabinet">
          <div class="cabinet-chrome"></div>
          <div class="cabinet-sticker">INTERACTIVE LAB<small>CAPSULE TOYS</small></div>
          <div class="cabinet-controls">
            <div class="coin-slot">
              <div class="coin-slot-hole"></div>
              <span>100¥</span>
            </div>
            <div class="crank-assembly">
              <div id="gashapon-crank" class="crank-dial">
                <div class="crank-handle"></div>
              </div>
            </div>
          </div>
          <div class="dispense-bay">
            <div class="dispense-flap"></div>
            <div id="chute-capsule" class="chute-capsule"></div>
            <div class="dispense-label">OUT</div>
          </div>
        </div>
        <div class="gashapon-base"></div>
      </div>
      <div id="capsule-pop" class="capsule-pop-stage">
        <div class="capsule-split-container">
          <div class="capsule-half capsule-half-top" id="capsule-top"></div>
          <div class="capsule-half capsule-half-bottom" id="capsule-bottom"></div>
        </div>
        <div class="toy-bubble" id="toy-bubble">
          <div id="toy-art-container" class="toy-art-container">
            <img id="toy-character-img" src="/assets/toys/toy_robot.png" alt="toy" class="toy-pop-img" />
            <img id="toy-custom-img" src="" alt="toy" style="display: none;" class="toy-pop-img" />
          </div>
          <div class="toy-title-text" id="toy-name">機甲守衛 Q 版公仔</div>
          <div class="toy-rarity-badge" id="toy-desc">★ 扭蛋限定收藏 ★</div>
        </div>
      </div>
    </div>

    <!-- 4. 二次元星空抽卡 (Card Gacha) -->
    <div id="card-gacha-stage" class="card-gacha-stage">
      <!-- 召喚星空法陣過場 (Summoning Portal & Cosmic Vortex) -->
      <div id="gacha-summon-portal" class="gacha-summon-portal">
        <img src="/assets/vfx/magic_circle.png" class="summon-magic-circle" alt="portal" />
        <canvas id="summon-star-canvas" width="600" height="600" class="summon-star-canvas"></canvas>
      </div>

      <!-- 單抽展示 -->
      <div id="single-card-wrap" class="single-card-scene">
        <div id="card-flipper" class="card-3d-flipper">
          <div class="card-face card-back-side">
            <img id="card-back-img" src="/assets/ui/card_back_gold.png" class="card-back-full-img" alt="card-back" />
            <div class="card-back-brand">✦ INTERACTIVE ✦</div>
          </div>
          <div id="card-front" class="card-face card-front-side rarity-ssr">
            <div id="gacha-rarity-badge" class="rarity-badge ssr">✦ SSR ✦</div>
            <!-- 卡面主要立繪窗口 -->
            <div id="card-art-box" class="card-art-box">
              <img id="card-character-img" src="/assets/characters/ssr_shion.png" alt="character" class="card-character-art" />
              <img id="card-custom-img" src="" alt="card" style="display: none; max-width: 95%; max-height: 320px; object-fit: contain; filter: drop-shadow(0 8px 18px rgba(0,0,0,0.8)); position: relative; z-index: 10;" />
            </div>
            <div class="card-info-plaque">
              <div id="gacha-card-name" class="card-name-title">星海夏日 · 詩音</div>
              <div id="gacha-card-quote" class="card-quote-text">「載波信號已鎖定，今晚由我伴飛。」</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 十連抽 5x2 陣列矩陣 -->
      <div id="ten-pull-stage" class="ten-pull-stage" style="display: none;">
        <div class="ten-pull-header" id="ten-pull-header">✦ 召喚結果 · 獲得 SSR ✦</div>
        <div id="ten-pull-grid" class="ten-pull-grid">
          <!-- 10 張卡牌節點 -->
        </div>
      </div>
    </div>

    <!-- 5. 幸運大轉盤 (Lucky Wheel) -->
    <div id="wheel-stage" class="wheel-stage">
      <div class="wheel-container">
        <div id="wheel-pointer" class="wheel-pointer"></div>
        <svg id="wheel-disc" class="wheel-disc" viewBox="0 0 400 400">
          <circle cx="200" cy="200" r="190" fill="#0f172a" />
          <g id="wheel-sectors"></g>
          <circle cx="200" cy="200" r="35" fill="#f59e0b" stroke="#ffffff" stroke-width="4" />
          <text x="200" y="206" text-anchor="middle" font-size="16" font-weight="900" fill="#000000">SPIN</text>
        </svg>
      </div>
      <div id="wheel-bubble" class="game-float-bubble">@觀眾 轉到了：【頭獎】</div>
    </div>

    <!-- 6. 3D 物理擲硬幣 (Coin Flip) -->
    <div id="coin-stage" class="coin-stage">
      <div class="coin-physics-arena throw-physics-arena" id="coin-physics-arena">
        <div class="throw-plane" data-throw-plane="shared-y0" aria-hidden="true"></div>
        <div id="coin-shadow" class="coin-shadow"></div>
        <canvas id="coin-webgl-canvas" class="coin-webgl-canvas" width="500" height="240"></canvas>
        <div id="coin-3d-disc" class="coin-3d-disc">
          <div class="coin-thickness-layer" style="transform: translateZ(-7px);"></div>
          <div class="coin-thickness-layer" style="transform: translateZ(-5px);"></div>
          <div class="coin-thickness-layer" style="transform: translateZ(-3px);"></div>
          <div class="coin-thickness-layer" style="transform: translateZ(-1px);"></div>
          <div class="coin-thickness-layer" style="transform: translateZ(1px);"></div>
          <div class="coin-thickness-layer" style="transform: translateZ(3px);"></div>
          <div class="coin-thickness-layer" style="transform: translateZ(5px);"></div>
          <div class="coin-thickness-layer" style="transform: translateZ(7px);"></div>
          <div class="coin-face coin-face-heads">
            <div class="coin-relief-ring">
              <div class="coin-emblem">👑</div>
              <div class="coin-text-top">INTERACTIVE</div>
              <div class="coin-text-bottom">★ 2026 ★</div>
            </div>
          </div>
          <div class="coin-face coin-face-tails">
            <div class="coin-relief-ring">
              <div class="coin-emblem">🪙</div>
              <div class="coin-text-top">FORTUNE</div>
              <div class="coin-text-bottom">★ 1 GOLD ★</div>
            </div>
          </div>
          <div class="coin-edge-rim"></div>
        </div>
      </div>
      <div id="coin-bubble" class="game-float-bubble">@觀眾 擲出了【正面】！</div>
    </div>

    <!-- 7. 3D 物理擲骰子 (Dice Roll with Multi-Die Physics) -->
    <div id="dice-stage" class="dice-stage">
      <div class="dice-physics-arena throw-physics-arena" id="dice-physics-arena">
        <div class="throw-plane" data-throw-plane="shared-y0" aria-hidden="true"></div>
        <canvas id="dice-webgl-canvas" class="dice-webgl-canvas" width="500" height="240"></canvas>
      </div>
      <div id="dice-bubble" class="game-float-bubble">@觀眾 擲出了 6 點！</div>
    </div>

    <!-- 8. 猜大小骰寶 (Gamble Big/Small 3D Sic Bo) -->
    <div id="gamble-stage" class="gamble-stage">
      <div class="gamble-arena">
        <div class="gamble-physics-arena throw-physics-arena" id="gamble-physics-arena">
          <div class="throw-plane" data-throw-plane="shared-y0" aria-hidden="true"></div>
          <canvas id="gamble-webgl-canvas" class="gamble-webgl-canvas" width="500" height="240"></canvas>
        </div>
        <!-- 3D 骰盅 (Dice Cup) -->
        <svg id="gamble-cup" class="gamble-cup" viewBox="0 0 140 150">
          <defs>
            <linearGradient id="cup-grad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#451a03"/><stop offset="50%" stop-color="#78350f"/><stop offset="100%" stop-color="#1c1917"/>
            </linearGradient>
            <linearGradient id="cup-rim-gold" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#fef08a"/><stop offset="50%" stop-color="#f59e0b"/><stop offset="100%" stop-color="#b45309"/>
            </linearGradient>
          </defs>
          <ellipse cx="70" cy="140" rx="58" ry="9" fill="#1c1917" opacity="0.9"/>
          <path d="M 22,28 Q 18,135 58,138 L 82,138 Q 122,135 118,28 Z" fill="url(#cup-grad)" stroke="#92400e" stroke-width="2"/>
          <ellipse cx="70" cy="28" rx="48" ry="11" fill="url(#cup-rim-gold)" stroke="#d97706" stroke-width="2"/>
          <path d="M 30,75 Q 70,82 110,75" fill="none" stroke="url(#cup-rim-gold)" stroke-width="5"/>
          <circle cx="70" cy="105" r="13" fill="none" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="3 2"/>
          <text x="70" y="110" font-size="11" font-weight="900" fill="#fbbf24" text-anchor="middle">骰</text>
        </svg>
      </div>
      <div id="gamble-tag" class="gamble-tag tag-big">【大 · 5 點】</div>
      <div id="gamble-res-badge" class="gamble-res-badge win">✨ 押對獲勝 +100 點！</div>
      <div id="gamble-bubble" class="game-float-bubble">@賭徒 押【大】勝出！</div>
    </div>

    <!-- 9. 浮動自訂計數器 HUD -->
    <div id="counter-hud-widget">
      <div class="counter-icon-wrap" id="counter-hud-icon">📊</div>
      <div>
        <div style="font-size: 11px; color: #94a3b8; font-weight: 700;" id="counter-hud-name">計數器</div>
        <div class="counter-num-box" id="counter-hud-count">0</div>
      </div>
      <div id="counter-delta-tag" class="counter-delta-float" style="display: none;">+1</div>
    </div>

    <!-- 10. 馬拉松倒數計時 HUD -->
    <div id="subathon-hud-widget">
      <div class="subathon-pulse-dot" id="subathon-dot"></div>
      <div>
        <div style="font-size: 11px; color: #34d399; font-weight: 800; letter-spacing: 1px;">SUBATHON COUNTDOWN</div>
        <div class="subathon-digits" id="subathon-digits">02:00:00</div>
      </div>
    </div>

    <!-- 11. 翻唱歌單 / 正在演唱 HUD -->
    <div id="cover-hud-widget">
      <div class="cover-vinyl">🎵</div>
      <div>
        <div style="font-size: 11px; color: #f472b6; font-weight: 700;" id="cover-hud-status">NOW SINGING</div>
        <div style="font-size: 15px; font-weight: 800; color: #f8fafc;" id="cover-hud-title">Lemon - 米津玄師</div>
        <div style="font-size: 11px; color: #94a3b8;" id="cover-hud-user">點播：@歌迷</div>
      </div>
      <div class="equalizer-bars">
        <div class="eq-bar" style="animation-delay: 0.1s;"></div>
        <div class="eq-bar" style="animation-delay: 0.3s;"></div>
        <div class="eq-bar" style="animation-delay: 0.2s;"></div>
        <div class="eq-bar" style="animation-delay: 0.4s;"></div>
      </div>
    </div>

    <!-- 12. 活躍觀眾抽籤獲獎彈窗 -->
    <div id="picker-stage" class="picker-stage">
      <div style="font-size: 48px; margin-bottom: 6px;">🏆</div>
      <div style="font-size: 15px; color: var(--gold-bright); font-weight: 800; letter-spacing: 2px;">AUDIENCE LUCKY DRAW</div>
      <div style="font-size: 32px; font-weight: 900; color: #ffffff; margin: 8px 0;" id="picker-winner-name">@幸運觀眾</div>
      <div style="font-size: 13px; color: #94a3b8;" id="picker-pool-info">從過去 10 分鐘聊天活躍者中抽出</div>
    </div>

    <!-- 13. 活動排隊叫號廣播 -->
    <div id="queue-call-alert">
      <span style="font-size: 26px;">🔔</span>
      <div>
        <div style="font-size: 11px; color: #38bdf8; font-weight: 800; letter-spacing: 1px;">QUEUE CALLED · 請出列！</div>
        <div style="font-size: 16px; font-weight: 800; color: #ffffff;" id="queue-called-names">下一輪玩家：@玩家1、@玩家2</div>
      </div>
    </div>
    <div id="queue-list-panel">
      <div class="queue-list-heading">
        <span>QUEUE LIST · 排隊清單</span>
        <span id="queue-list-status">—</span>
      </div>
      <div id="queue-list-items"><div class="queue-list-row"><span>—</span><span>等待排隊資料</span><span></span></div></div>
    </div>

    <!-- 14. 社群下注預測 HUD -->
    <div id="bet-hud-widget">
      <div class="bet-header-row">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 18px;">🎯</span>
          <span style="font-weight: 900; font-size: 14px; color: #f8fafc;" id="bet-hud-title">這把遊戲能成功吃雞嗎？</span>
        </div>
        <span class="bet-badge open" id="bet-hud-badge">開放投注</span>
      </div>
      <div class="bet-bar-wrap">
        <div class="bet-bar-a" id="bet-hud-bar-a" style="width: 50%;"></div>
        <div class="bet-bar-b" id="bet-hud-bar-b" style="width: 50%;"></div>
        <div class="bet-vs-pill">VS</div>
      </div>
      <div class="bet-odds-row">
        <div class="bet-opt-box bet-opt-a">
          <span style="font-weight: 800;" id="bet-hud-name-a">🅰️ 能</span>
          <span style="font-size: 11px; opacity: 0.85;" id="bet-hud-info-a">1.85x ｜ 500 點</span>
        </div>
        <div style="text-align: center;">
          <span style="font-size: 11px; color: #94a3b8;">總彩池</span>
          <div style="font-size: 14px; font-weight: 900; color: var(--gold-bright);" id="bet-hud-total-pool">1000 點</div>
        </div>
        <div class="bet-opt-box bet-opt-b">
          <span style="font-weight: 800;" id="bet-hud-name-b">不能 🅱️</span>
          <span style="font-size: 11px; opacity: 0.85;" id="bet-hud-info-b">500 點 ｜ 1.85x</span>
        </div>
      </div>
    </div>

    <!-- 15. 點歌播放器 HUD -->
    <div id="music-hud-widget">
      <div class="music-top-row">
        <div class="music-vinyl-disc" id="music-vinyl">🎵</div>
        <div class="music-info-col">
          <div style="font-size: 10px; color: #a855f7; font-weight: 800; letter-spacing: 1px;" id="music-status-tag">NOW PLAYING</div>
          <div class="music-title-text" id="music-song-title">夜に駆ける</div>
          <div class="music-artist-text" id="music-song-artist">YOASOBI</div>
          <div class="music-user-tag" id="music-song-user">點播：@音樂愛好者</div>
        </div>
      </div>
      <div class="music-progress-wrap">
        <div class="music-bar-bg">
          <div class="music-bar-fill" id="music-progress-fill"></div>
        </div>
        <div class="music-time-row">
          <span id="music-time-curr">00:00</span>
          <span id="music-time-total">03:30</span>
        </div>
      </div>
    </div>

    <!-- 16. 即時雙語翻譯字幕條 HUD -->
    <div id="trans-hud-widget">
      <div class="trans-meta-row">
        <span class="trans-badge" id="trans-badge">🌐 EN ➔ ZH-TW</span>
        <span class="trans-user" id="trans-user">@OverseasFan</span>
      </div>
      <div class="trans-orig-text" id="trans-orig">"Hello everyone! Loving the stream today!"</div>
      <div class="trans-main-text" id="trans-main">大家好！今天的實況太棒了！</div>
    </div>

    <!-- 17. 贊助通知彈窗 HUD -->
    <div id="donation-alert-widget">
      <div class="donation-badge-row">
        <span id="donation-icon">💖</span>
        <span id="donation-badge-title">NEW DONATION</span>
      </div>
      <div class="donation-amount-text" id="donation-amount">TWD $500</div>
      <div class="donation-donor-text" id="donation-donor">感謝 @乾爹大老 的熱情贊助！</div>
      <div class="donation-msg-bubble" id="donation-msg">"主播今天開台辛苦了！這把必吃雞！加油！"</div>
      <div class="donation-bonus-row" id="donation-bonus">
        <span id="donation-points-tag">🎁 +5,000 點數</span>
        <span id="donation-time-tag">⏱️ +2,500s 馬拉松延長</span>
      </div>
    </div>
  </div>

  <script src="{asset_prefix}/vendor/three.min.js"></script>
  <script>
    const WS_PATH = "{ws_path}";
    const MODE = "{mode}";
    const STATIC_DEMO = {str(static_demo).lower()};

    // =========================================================================
    // 全局計時器與動畫狀態重置管理器 (Frame-1 Clean Reset)
    // =========================================================================
    let activeTimers = [];
    let activeIntervals = [];

    function clearAllTimers() {{
      activeTimers.forEach(id => clearTimeout(id));
      activeTimers = [];
      activeIntervals.forEach(id => clearInterval(id));
      activeIntervals = [];
    }}

    function safeTimeout(fn, ms) {{
      const id = setTimeout(() => {{
        const idx = activeTimers.indexOf(id);
        if (idx !== -1) activeTimers.splice(idx, 1);
        fn();
      }}, ms);
      activeTimers.push(id);
      return id;
    }}

    function safeInterval(fn, ms) {{
      const id = setInterval(fn, ms);
      activeIntervals.push(id);
      return id;
    }}

    // =========================================================================
    // Web Audio Synthesizer + In-repo Foley Audio Engine
    // =========================================================================
    class CinemaSoundEngine {{
      constructor() {{
        this.ctx = null;
      }}
      init() {{
        if (!this.ctx) {{
          const AudioContext = window.AudioContext || window.webkitAudioContext;
          if (AudioContext) this.ctx = new AudioContext();
        }}
        if (this.ctx && this.ctx.state === "suspended") {{
          this.ctx.resume();
        }}
      }}
      playFile(url, fallbackFn) {{
        try {{
          const audio = new Audio(url);
          audio.volume = 0.85;
          const p = audio.play();
          if (p && p.catch) {{
            p.catch(() => {{ if (fallbackFn) fallbackFn(); }});
          }}
        }} catch (e) {{
          if (fallbackFn) fallbackFn();
        }}
      }}
      // 重低音震撼衝擊 (Sub-bass boom)
      playSubBoom() {{
        this.init();
        if (!this.ctx) return;
        const now = this.ctx.currentTime;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(150, now);
        osc.frequency.exponentialRampToValueAtTime(30, now + 0.6);
        gain.gain.setValueAtTime(0.9, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.6);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(now);
        osc.stop(now + 0.65);
      }}
      // 木頭敲擊 (擲筊)
      playWoodClack(vol = 0.8) {{
        this.init();
        if (!this.ctx) return;
        const now = this.ctx.currentTime;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(320, now);
        osc.frequency.exponentialRampToValueAtTime(80, now + 0.08);
        gain.gain.setValueAtTime(vol, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.08);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(now);
        osc.stop(now + 0.09);
      }}
      // 機械齒輪咔噠 (扭蛋/拉霸)
      playRatchet() {{
        this.init();
        if (!this.ctx) return;
        const now = this.ctx.currentTime;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = "square";
        osc.frequency.setValueAtTime(280, now);
        osc.frequency.exponentialRampToValueAtTime(60, now + 0.05);
        gain.gain.setValueAtTime(0.4, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.05);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(now);
        osc.stop(now + 0.06);
      }}
      // 轉盤指針彈撥 (Tick)
      playPegTick() {{
        this.playFile("/assets/sound/ui/tick_001.ogg", () => {{
          this.init();
          if (!this.ctx) return;
          const now = this.ctx.currentTime;
          const osc = this.ctx.createOscillator();
          const gain = this.ctx.createGain();
          osc.type = "triangle";
          osc.frequency.setValueAtTime(800, now);
          osc.frequency.exponentialRampToValueAtTime(200, now + 0.03);
          gain.gain.setValueAtTime(0.35, now);
          gain.gain.exponentialRampToValueAtTime(0.01, now + 0.03);
          osc.connect(gain);
          gain.connect(this.ctx.destination);
          osc.start(now);
          osc.stop(now + 0.04);
        }});
      }}
      // 金幣連續落盤 / 籌碼撞擊
      playCoinShower() {{
        this.playFile("/assets/sound/casino/chips-collide-1.ogg", () => {{
          this.init();
          if (!this.ctx) return;
          const freqs = [1975, 2349, 2637, 3135];
          for (let i = 0; i < 6; i++) {{
            const t = this.ctx.currentTime + i * 0.07;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = "sine";
            osc.frequency.value = freqs[i % freqs.length];
            gain.gain.setValueAtTime(0.3, t);
            gain.gain.exponentialRampToValueAtTime(0.01, t + 0.16);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(t);
            osc.stop(t + 0.17);
          }}
        }});
      }}
      // 盛典琶音 (Fanfare)
      playFanfare() {{
        this.playFile("/assets/sound/ui/confirmation_001.ogg", () => {{
          this.init();
          if (!this.ctx) return;
          const now = this.ctx.currentTime;
          const notes = [523.25, 659.25, 783.99, 1046.50];
          notes.forEach((freq, idx) => {{
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = "triangle";
            osc.frequency.value = freq;
            const t = now + idx * 0.12;
            gain.gain.setValueAtTime(0.5, t);
            gain.gain.exponentialRampToValueAtTime(0.01, t + 0.4);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(t);
            osc.stop(t + 0.41);
          }});
        }});
      }}
      // 骰盅搖骰碰撞聲 (Dice Rattle in Cup)
      playDiceRattle() {{
        this.playFile("/assets/sound/casino/dice-throw-1.ogg", () => {{
          this.init();
          if (!this.ctx) return;
          for (let i = 0; i < 6; i++) {{
            const t = this.ctx.currentTime + i * 0.09;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = "sine";
            osc.frequency.setValueAtTime(260 + i * 25, t);
            osc.frequency.exponentialRampToValueAtTime(80, t + 0.05);
            gain.gain.setValueAtTime(0.35, t);
            gain.gain.exponentialRampToValueAtTime(0.01, t + 0.05);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(t);
            osc.stop(t + 0.06);
          }}
        }});
      }}
      // 提示風鈴鐘聲 (Alert Chime)
      playChime() {{
        this.playFile("/assets/sound/ui/confirmation_001.ogg", () => {{
          this.init();
          if (!this.ctx) return;
          const freqs = [587.33, 880.00];
          freqs.forEach((f, idx) => {{
            const t = this.ctx.currentTime + idx * 0.15;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = "sine";
            osc.frequency.value = f;
            gain.gain.setValueAtTime(0.4, t);
            gain.gain.exponentialRampToValueAtTime(0.01, t + 0.35);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(t);
            osc.stop(t + 0.36);
          }});
        }});
      }}
      // 輕微木質敲打 / 骰子撞擊 (Wood Tap)
      playWoodTap(vol = 0.5) {{
        this.init();
        if (!this.ctx) return;
        const now = this.ctx.currentTime;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(420, now);
        osc.frequency.exponentialRampToValueAtTime(110, now + 0.04);
        gain.gain.setValueAtTime(vol, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.04);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(now);
        osc.stop(now + 0.05);
      }}
      // 揭盅/破空呼嘯 (Whoosh / Swipe)
      playWhoosh() {{
        this.playFile("/assets/sound/casino/cards-pack-open-1.ogg", () => {{
          this.init();
          if (!this.ctx) return;
          const now = this.ctx.currentTime;
          const osc = this.ctx.createOscillator();
          const gain = this.ctx.createGain();
          osc.type = "sine";
          osc.frequency.setValueAtTime(360, now);
          osc.frequency.exponentialRampToValueAtTime(90, now + 0.18);
          gain.gain.setValueAtTime(0.45, now);
          gain.gain.exponentialRampToValueAtTime(0.01, now + 0.18);
          osc.connect(gain);
          gain.connect(this.ctx.destination);
          osc.start(now);
          osc.stop(now + 0.2);
        }});
      }}
      // 沉悶失落重擊 (Thud / Failure)
      playThud() {{
        this.init();
        if (!this.ctx) return;
        const now = this.ctx.currentTime;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(130, now);
        osc.frequency.exponentialRampToValueAtTime(35, now + 0.28);
        gain.gain.setValueAtTime(0.65, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.28);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(now);
        osc.stop(now + 0.3);
      }}
    }}
    const rawSound = new CinemaSoundEngine();
    const sound = new Proxy(rawSound, {{
      get(target, prop) {{
        if (prop in target) return target[prop];
        return () => {{}};
      }}
    }});

    // =========================================================================
    // Canvas Multi-layer VFX (Sparks, Confetti & Stardust)
    // =========================================================================
    const canvas = document.getElementById("vfx-canvas");
    const ctx = canvas.getContext("2d");
    let particles = [];

    function resizeCanvas() {{
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }}
    window.addEventListener("resize", resizeCanvas);
    resizeCanvas();

    function triggerScreenEffects(isGrand = false) {{
      const root = document.getElementById("overlay-root");
      const vignette = document.getElementById("spotlight-vignette");
      const rays = document.getElementById("god-rays");
      const shockwave = document.getElementById("shockwave-ring");

      // 立即重置相機震動
      root.classList.remove("screen-shake");
      void root.offsetWidth;
      root.classList.add("screen-shake");

      // 向量光環衝擊波
      shockwave.className = "";
      void shockwave.offsetWidth;
      shockwave.className = "blast-active";

      if (isGrand) {{
        vignette.classList.add("active");
        rays.classList.add("active");
        sound.playSubBoom();
      }}
    }}

    function spawnVFX(type = "gold", count = 90) {{
      for (let i = 0; i < count; i++) {{
        particles.push({{
          type,
          x: canvas.width / 2 + (Math.random() - 0.5) * 180,
          y: canvas.height / 2 + (Math.random() - 0.5) * 60,
          vx: (Math.random() - 0.5) * 18,
          vy: (Math.random() - 0.95) * 22,
          size: Math.random() * 8 + 4,
          color: type === "gold"
            ? ["#fbbf24", "#f59e0b", "#fde047", "#ffffff"][Math.floor(Math.random() * 4)]
            : ["#f59e0b", "#ec4899", "#8b5cf6", "#38bdf8", "#10b981"][Math.floor(Math.random() * 5)],
          rotation: Math.random() * 360,
          vrot: (Math.random() - 0.5) * 14,
          alpha: 1,
          decay: Math.random() * 0.012 + 0.007
        }});
      }}
    }}

    function animateParticles() {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (let i = particles.length - 1; i >= 0; i--) {{
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.44;
        p.rotation += p.vrot;
        p.alpha -= p.decay;

        if (p.alpha <= 0) {{
          particles.splice(i, 1);
          continue;
        }}

        ctx.save();
        ctx.globalAlpha = p.alpha;
        ctx.translate(p.x, p.y);
        ctx.rotate((p.rotation * Math.PI) / 180);
        ctx.fillStyle = p.color;
        ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
        ctx.restore();
      }}
      requestAnimationFrame(animateParticles);
    }}
    animateParticles();

    // 安全操作輔助函式 (防止任何單一子路由或缺失元素拋出 TypeError 中斷全域清空)
    function safeRemove(id, ...cls) {{
      const el = document.getElementById(id);
      if (el) el.classList.remove(...cls);
    }}
    function safeSetClass(id, cls) {{
      const el = document.getElementById(id);
      if (el) {{
        el.className = cls;
        if (typeof el.setAttribute === "function") el.setAttribute("class", cls);
        void (el.offsetWidth || (el.getBoundingClientRect && el.getBoundingClientRect().width));
      }}
    }}
    function safeStyle(id, prop, val) {{
      const el = document.getElementById(id);
      if (el) el.style[prop] = val;
    }}

    // =========================================================================
    // 完全重置所有舞台狀態 (徹底解決連續點擊不重置與清除無反應問題)
    // =========================================================================
    function hideAllStages(msg = null) {{
      clearAllTimers();
      particles = [];
      try {{
        if (ctx && canvas) ctx.clearRect(0, 0, canvas.width, canvas.height);
      }} catch (e) {{}}

      const target = (msg && (msg.target || msg.stage)) || "all";

      // 0. 重置全局視覺特效 (全境暗角、神聖光芒、震波光環、震動)
      safeRemove("overlay-root", "screen-shake");
      safeRemove("spotlight-vignette", "active");
      safeRemove("god-rays", "active");
      safeSetClass("shockwave-ring", "");

      // 1. 重置 擲筊
      if (target === "all" || target === "bwei") {{
        safeRemove("bwei-stage", "active");
        safeSetClass("cup-left", "bwei-cup-svg");
        safeSetClass("cup-right", "bwei-cup-svg");
        safeSetClass("shadow-left", "bwei-shadow");
        safeSetClass("shadow-right", "bwei-shadow");
      }}

      // 2. 重置 拉霸機
      if (target === "all" || target === "slot") {{
        safeRemove("slot-stage", "active");
        safeRemove("slot-payline", "active");
        safeRemove("slot-lever", "pulled");
        safeStyle("slot-jackpot-badge", "display", "none");
        [0, 1, 2].forEach(i => safeSetClass(`strip-${{i}}`, "slot-reel-strip"));
      }}

      // 3. 重置 扭蛋機
      if (target === "all" || target === "gashapon") {{
        safeRemove("gashapon-stage", "active");
        safeSetClass("gashapon-crank", "crank-dial");
        const crankEl = document.getElementById("gashapon-crank");
        if (crankEl) crankEl.style.transform = "rotate(0deg)";
        safeRemove("capsule-pop", "active");
        stopGashaponPhysics();
        const chute = document.getElementById("chute-capsule");
        if (chute) {{
          chute.className = "chute-capsule";
        }}
      }}

      // 4. 重置 抽卡
      if (target === "all" || target === "card" || target === "gacha") {{
        safeRemove("card-gacha-stage", "active");
        safeRemove("gacha-summon-portal", "active");
        safeSetClass("card-flipper", "card-3d-flipper");
        safeRemove("single-card-wrap", "visible");
        const tenGrid = document.getElementById("ten-pull-grid");
        if (tenGrid) {{
          tenGrid.innerHTML = "";
          tenGrid.style.display = "none";
        }}
        safeStyle("single-card-wrap", "display", "block");
        const tenStage = document.getElementById("ten-pull-stage");
        if (tenStage) tenStage.style.display = "none";
      }}

      // 5. 重置 幸運大轉盤
      if (target === "all" || target === "wheel") {{
        safeRemove("wheel-stage", "active");
        safeSetClass("wheel-pointer", "wheel-pointer");
        const disc = document.getElementById("wheel-disc");
        if (disc) {{
          disc.style.transition = "none";
          disc.style.transform = "rotate(0deg)";
          void disc.offsetWidth;
        }}
      }}

      // 6. 重置 硬幣
      if (target === "all" || target === "coin") {{
        safeRemove("coin-stage", "active");
        if (coinPhysicsWorld) {{
          coinPhysicsWorld.stop();
          coinPhysicsWorld = null;
        }}
        if (window.__coinWebGL) {{
          window.__coinWebGL.clearDice();
        }}
        const disc = document.getElementById("coin-3d-disc");
        if (disc) {{
          disc.style.display = "block";
          disc.style.transform = "none";
        }}
        const shadow = document.getElementById("coin-shadow");
        if (shadow) {{
          shadow.style.display = "block";
          shadow.style.opacity = "0";
        }}
        safeStyle("coin-webgl-canvas", "display", "none");
        const arena = document.getElementById("coin-physics-arena");
        if (arena) arena.classList.remove("uses-webgl");
      }}

      // 7. 重置 骰子
      if (target === "all" || target === "dice") {{
        safeRemove("dice-stage", "active");
        if (dicePhysicsWorld) {{
          dicePhysicsWorld.stop();
          dicePhysicsWorld = null;
        }}
        if (window.__diceWebGL) {{
          window.__diceWebGL.clearDice();
        }}
        safeStyle("dice-webgl-canvas", "display", "none");
        const arena = document.getElementById("dice-physics-arena");
        if (arena) {{
          arena.classList.remove("uses-webgl");
          arena.querySelectorAll(".die-wrapper, .die-shadow").forEach(el => el.remove());
        }}
      }}

      // 8. 重置 猜大小骰寶
      if (target === "all" || target === "gamble") {{
        safeRemove("gamble-stage", "active");
        if (gamblePhysicsWorld) {{
          gamblePhysicsWorld.stop();
          gamblePhysicsWorld = null;
        }}
        if (window.__gambleWebGL) {{
          window.__gambleWebGL.clearDice();
        }}
        safeStyle("gamble-webgl-canvas", "display", "none");
        safeSetClass("gamble-cup", "gamble-cup");
        const arena = document.getElementById("gamble-physics-arena");
        if (arena) {{
          arena.classList.remove("uses-webgl");
          arena.querySelectorAll(".die-wrapper, .die-shadow").forEach(el => el.remove());
        }}
      }}

      // 9. 重置 抽籤彈窗
      if (target === "all" || target === "picker") {{
        safeRemove("picker-stage", "active");
      }}

      // 10. 重置 排隊叫號廣播
      if (target === "all" || target === "queue") {{
        safeRemove("queue-call-alert", "active");
        safeRemove("queue-list-panel", "active");
      }}

      // 11. 重置 社群下注預測 HUD (無條件強制關閉)
      if (target === "all" || target === "bet") {{
        safeRemove("bet-hud-widget", "active", "bet-winner-glow-a", "bet-winner-glow-b");
      }}

      // 12. 重置 點歌播放器 HUD (停止計時器並無條件強制關閉)
      if (target === "all" || target === "music") {{
        if (typeof musicProgressTimer !== "undefined" && musicProgressTimer) {{
          clearInterval(musicProgressTimer);
          musicProgressTimer = null;
        }}
        safeRemove("music-hud-widget", "active");
      }}

      // 13. 重置 即時翻譯字幕條 HUD (無條件強制關閉)
      if (target === "all" || target === "trans") {{
        safeRemove("trans-hud-widget", "active");
      }}

      // 14. 重置 贊助與 Twitch EventSub 彈窗 HUD (無條件強制關閉)
      if (target === "all" || target === "donation" || target === "twitch") {{
        safeRemove("donation-alert-widget", "active");
      }}

      // 15. 重置 主播歌單 HUD
      if (target === "all" || target === "cover") {{
        if (MODE === "all" || target === "cover") {{
          safeRemove("cover-hud-widget", "active");
        }}
      }}

      // 16. 重置 自訂計數器 HUD (僅在全合一或指定時關閉)
      if (target === "all" || target === "counter") {{
        if (MODE === "all" || target === "counter") {{
          safeRemove("counter-hud-widget", "active");
        }}
      }}

      // 17. 重置 馬拉松倒數 HUD (僅在全合一或指定時關閉)
      if (target === "all" || target === "subathon") {{
        if (MODE === "all" || target === "subathon") {{
          safeRemove("subathon-hud-widget", "active");
        }}
      }}
    }}

    // =========================================================================
    // 各遊戲動畫啟動流程
    // =========================================================================

    // 1. 擲筊 (BwaBwei)
    function playBweiAnimation(data) {{
      if (MODE !== "all" && MODE !== "bwei") return;
      hideAllStages();

      const stage = document.getElementById("bwei-stage");
      const cupL = document.getElementById("cup-left");
      const cupR = document.getElementById("cup-right");
      const shadowL = document.getElementById("shadow-left");
      const shadowR = document.getElementById("shadow-right");
      const title = document.getElementById("bwei-title");
      const user = document.getElementById("bwei-user");
      const desc = document.getElementById("bwei-desc");

      const resType = data.result || "sheng";
      const resName = data.name || (resType === "sheng" ? "聖筊" : resType === "xiao" ? "笑筊" : resType === "yin" ? "陰筊" : "立筊");
      const q = data.question ? ` 問：「${{data.question}}」` : "";

      user.innerText = `@${{data.user_name || "觀眾"}}${{q}} 誠心擲出：`;
      title.innerText = `【 ${{resName}} 】`;
      desc.innerText = data.desc || (resType === "sheng" ? "神明應允，大吉大利！" : resType === "xiao" ? "神明微笑，若有所思。" : resType === "yin" ? "神明不允，另擇良時。" : "神蹟降臨！直立不倒！");
      title.className = `bwei-title res-${{resType}}`;

      const isLeftCurved = data.left === "curved";
      const isRightCurved = data.right === "curved";
      document.getElementById("cup-left-path").setAttribute("fill", isLeftCurved ? "url(#grad-curved-left)" : "url(#grad-flat-left)");
      document.getElementById("cup-right-path").setAttribute("fill", isRightCurved ? "url(#grad-curved-right)" : "url(#grad-flat-right)");
      document.getElementById("cup-left-ridge").style.display = isLeftCurved ? "block" : "none";
      document.getElementById("cup-right-ridge").style.display = isRightCurved ? "block" : "none";

      stage.classList.add("active");
      void cupL.offsetWidth;
      cupL.classList.add("toss-active-left");
      cupR.classList.add("toss-active-right");
      shadowL.classList.add("shadow-active-left");
      shadowR.classList.add("shadow-active-right");

      if (resType === "standing") {{
        safeTimeout(() => cupR.classList.add("standing-wobble"), 850);
      }}

      safeTimeout(() => sound.playWoodClack(0.9), 620);
      safeTimeout(() => sound.playWoodClack(0.5), 880);

      if (resType === "sheng" || resType === "standing") {{
        safeTimeout(() => {{
          triggerScreenEffects(resType === "standing");
          sound.playFanfare();
          spawnVFX(resType === "standing" ? "confetti" : "gold", resType === "standing" ? 140 : 70);
        }}, 980);
      }}

      safeTimeout(() => hideAllStages(), 7500);
    }}

    // 2. 拉霸機 (Slot)
    function playSlotAnimation(data) {{
      if (MODE !== "all" && MODE !== "slot") return;
      hideAllStages();

      const stage = document.getElementById("slot-stage");
      const lever = document.getElementById("slot-lever");
      const user = document.getElementById("slot-user");
      const resText = document.getElementById("slot-result-text");
      const jackpotBadge = document.getElementById("slot-jackpot-badge");
      const payline = document.getElementById("slot-payline");

      const reels = data.reels || ["7", "7", "7"];
      const win = Number(data.win || 0);
      const mult = Number(data.multiplier || 0);

      user.innerText = `@${{data.user_name || "觀眾"}} 投注 ${{data.bet || 50}} 點`;
      resText.innerText = win > 0 ? `獲得 ${{win}} 點獎勵！` : "差一點就中獎了，再接再厲！";

      jackpotBadge.style.display = mult >= 5 ? "inline-block" : "none";
      if (mult >= 5) jackpotBadge.innerText = `JACKPOT ${{mult}}x!`;

      stage.classList.add("active");
      lever.classList.add("pulled");
      sound.playRatchet();
      safeTimeout(() => lever.classList.remove("pulled"), 320);

      const strips = [document.getElementById("strip-0"), document.getElementById("strip-1"), document.getElementById("strip-2")];
      strips.forEach(strip => {{
        strip.classList.remove("stopping-elastic");
        strip.classList.add("spinning-blur");
      }});

      const symbolMap = {{ "7": "7️⃣", "BAR": "🎰", "BELL": "🔔", "CHERRY": "🍒", "LEMON": "🍋" }};

      strips.forEach((strip, idx) => {{
        safeTimeout(() => {{
          strip.classList.remove("spinning-blur");
          const targetSym = symbolMap[reels[idx]] || reels[idx] || "7️⃣";
          strip.children[0].innerText = targetSym;
          strip.classList.add("stopping-elastic");
          sound.playFile("/assets/sound/ui/tick_001.ogg", () => sound.playRatchet());
        }}, 900 + idx * 400);
      }});

      if (win > 0) {{
        safeTimeout(() => {{
          payline.classList.add("active");
          triggerScreenEffects(mult >= 5);
          sound.playFanfare();
          sound.playCoinShower();
          spawnVFX("gold", mult >= 5 ? 130 : 60);
        }}, 2200);
      }}

      safeTimeout(() => hideAllStages(), 8000);
    }}

    // 3. 實體日式扭蛋機 (Gashapon - Realistic Bandai Capsule Machine)
    // SSOT：須與 minigame.GASHAPON_TOYS 名稱／圖路徑一致
    const GASHAPON_TOY_POOL = [
      {{ name: "機甲守衛 Q 版公仔", desc: "★ 機甲先鋒限定收藏 ★", image: "/assets/toys/toy_robot.png" }},
      {{ name: "熱血冒險家 探險公仔", desc: "★ 遺跡探索限定收藏 ★", image: "/assets/toys/toy_adventurer.png" }},
      {{ name: "呆萌小殭屍 萬聖公仔", desc: "★ 夜行狂歡限定收藏 ★", image: "/assets/toys/toy_zombie.png" }},
      {{ name: "弗芬頓紳士 絨毛布偶", desc: "★ 療癒毛球限定收藏 ★", image: "/assets/toys/toy_fuff.png" }}
    ];

    function resolveGashaponToy(raw) {{
      if (!raw || !raw.name) {{
        const randToy = GASHAPON_TOY_POOL[Math.floor(Math.random() * GASHAPON_TOY_POOL.length)];
        return Object.assign({{}}, randToy, raw || {{}});
      }}
      const byName = GASHAPON_TOY_POOL.find(t => t.name === raw.name);
      if (byName) return Object.assign({{}}, byName, raw);
      return Object.assign({{ image: "/assets/toys/toy_robot.png", desc: "★ 扭蛋限定收藏 ★" }}, raw);
    }}

    let gashaponPhysics = null;
    let gashaponCrankRaf = null;

    class GashaponDomePhysics {{
      constructor(container) {{
        this.el = container;
        this.balls = [];
        this.raf = null;
        this.running = false;
        this.agitateUntil = 0;
        this.stirPhase = 0;
        this.r = 17;
        this.g = 2100;
        this.measure();
        this.bindBalls();
        this.packBottom();
        for (let i = 0; i < 120; i++) this.step(1 / 60);
        this.render();
      }}

      measure() {{
        const w = this.el.clientWidth || 204;
        const h = this.el.clientHeight || 204;
        this.size = Math.min(w, h);
        this.cx = w / 2;
        this.cy = h / 2;
        this.wallR = this.size * 0.48;
      }}

      bindBalls() {{
        const nodes = Array.from(this.el.querySelectorAll(".mini-capsule"));
        this.balls = nodes.map((node) => ({{
          el: node,
          x: this.cx,
          y: this.cy,
          vx: 0,
          vy: 0,
          spin: Math.random() * 360,
          spinV: (Math.random() - 0.5) * 40
        }}));
      }}

      packBottom() {{
        const n = this.balls.length;
        const packR = this.wallR - this.r - 1;
        for (let i = 0; i < n; i++) {{
          const layer = i < 6 ? 0 : 1;
          const inLayer = layer === 0 ? i : i - 6;
          const count = layer === 0 ? Math.min(6, n) : Math.max(1, n - 6);
          const t = (inLayer + 0.5) / count;
          const ang = Math.PI * (0.22 + t * 0.56);
          const rr = packR - layer * this.r * 1.75;
          this.balls[i].x = this.cx + Math.cos(ang) * rr;
          this.balls[i].y = this.cy + Math.sin(ang) * rr;
          this.balls[i].vx = 0;
          this.balls[i].vy = 0;
          this.balls[i].spin = ang * 57.3 + (Math.random() - 0.5) * 40;
          this.balls[i].spinV = 0;
        }}
      }}

      agitate(ms) {{
        this.agitateUntil = performance.now() + ms;
      }}

      start() {{
        if (this.running) return;
        this.running = true;
        this.measure();
        let last = performance.now();
        const loop = (now) => {{
          if (!this.running) return;
          const dt = Math.min(0.032, (now - last) / 1000);
          last = now;
          // substeps for stable collisions
          const steps = 2;
          const h = dt / steps;
          for (let s = 0; s < steps; s++) this.step(h);
          this.render();
          this.raf = requestAnimationFrame(loop);
        }};
        this.raf = requestAnimationFrame(loop);
      }}

      stop() {{
        this.running = false;
        if (this.raf) cancelAnimationFrame(this.raf);
        this.raf = null;
      }}

      step(dt) {{
        const now = performance.now();
        const agitating = now < this.agitateUntil;
        if (agitating) this.stirPhase += dt * 9.5;

        for (const b of this.balls) {{
          b.vy += this.g * dt;

          if (agitating) {{
            const dx = b.x - this.cx;
            const dy = b.y - this.cy;
            const dist = Math.hypot(dx, dy) || 1;
            const tx = -dy / dist;
            const ty = dx / dist;
            // 內部攪拌臂：底部用力更大（真實扭蛋機轉盤感）
            const depth = Math.max(0, (b.y - (this.cy - this.wallR * 0.2)) / (this.wallR * 1.2));
            const swirl = (520 + Math.sin(this.stirPhase + dist * 0.08) * 220) * (0.45 + depth);
            b.vx += tx * swirl * dt;
            b.vy += ty * swirl * dt * 0.4 - (380 + depth * 220) * dt;
            // 偶發碰撞彈起
            if (Math.random() < 0.04) {{
              b.vx += (Math.random() - 0.5) * 280;
              b.vy -= Math.random() * 320;
            }}
            b.spinV += swirl * 0.55 * dt;
          }}

          // 摩擦：靜止時重、翻滾時輕
          const damp = agitating ? 0.992 : 0.90;
          const spinDamp = agitating ? 0.985 : 0.88;
          b.vx *= Math.pow(damp, dt * 60);
          b.vy *= Math.pow(agitating ? 0.997 : 0.94, dt * 60);
          b.spinV *= Math.pow(spinDamp, dt * 60);

          b.x += b.vx * dt;
          b.y += b.vy * dt;
          b.spin += b.spinV * dt;

          // 圓形壁面碰撞 + 滾動
          const dx = b.x - this.cx;
          const dy = b.y - this.cy;
          const dist = Math.hypot(dx, dy);
          const maxD = this.wallR - this.r;
          if (dist > maxD && dist > 0.0001) {{
            const nx = dx / dist;
            const ny = dy / dist;
            b.x = this.cx + nx * maxD;
            b.y = this.cy + ny * maxD;
            const vn = b.vx * nx + b.vy * ny;
            if (vn > 0) {{
              const e = agitating ? 0.42 : 0.22;
              b.vx -= (1 + e) * vn * nx;
              b.vy -= (1 + e) * vn * ny;
              // 切線速度轉為自旋
              const tx = -ny;
              const ty = nx;
              const vt = b.vx * tx + b.vy * ty;
              b.spinV += -vt * 1.8;
              // 壁面摩擦吃掉一點切線速度
              b.vx -= tx * vt * 0.18;
              b.vy -= ty * vt * 0.18;
            }}
          }}
        }}

        // 球-球碰撞
        const minD = this.r * 2;
        for (let i = 0; i < this.balls.length; i++) {{
          for (let j = i + 1; j < this.balls.length; j++) {{
            const a = this.balls[i];
            const b = this.balls[j];
            let dx = b.x - a.x;
            let dy = b.y - a.y;
            let dist = Math.hypot(dx, dy);
            if (dist < 0.0001) {{
              dx = 0.01;
              dy = 0;
              dist = 0.01;
            }}
            if (dist < minD) {{
              const nx = dx / dist;
              const ny = dy / dist;
              const overlap = (minD - dist) * 0.5;
              a.x -= nx * overlap;
              a.y -= ny * overlap;
              b.x += nx * overlap;
              b.y += ny * overlap;
              const rvx = b.vx - a.vx;
              const rvy = b.vy - a.vy;
              const vn = rvx * nx + rvy * ny;
              if (vn < 0) {{
                const e = agitating ? 0.5 : 0.28;
                const impulse = -(1 + e) * vn * 0.5;
                a.vx -= impulse * nx;
                a.vy -= impulse * ny;
                b.vx += impulse * nx;
                b.vy += impulse * ny;
                a.spinV -= impulse * 3.2;
                b.spinV += impulse * 3.2;
              }}
            }}
          }}
        }}
      }}

      render() {{
        for (const b of this.balls) {{
          b.el.style.transform =
            `translate(${{b.x - this.r}}px, ${{b.y - this.r}}px) rotate(${{b.spin}}deg)`;
        }}
      }}
    }}

    function ensureGashaponPhysics() {{
      const dome = document.getElementById("dome-capsules");
      if (!dome) return null;
      if (!gashaponPhysics || gashaponPhysics.el !== dome) {{
        if (gashaponPhysics) gashaponPhysics.stop();
        gashaponPhysics = new GashaponDomePhysics(dome);
      }}
      gashaponPhysics.start();
      return gashaponPhysics;
    }}

    function stopGashaponPhysics() {{
      if (gashaponPhysics) {{
        gashaponPhysics.stop();
        gashaponPhysics = null;
      }}
      if (gashaponCrankRaf) {{
        cancelAnimationFrame(gashaponCrankRaf);
        gashaponCrankRaf = null;
      }}
    }}

    function spinGashaponCrank(crank, durationMs, totalDegrees = 155) {{
      if (gashaponCrankRaf) {{
        cancelAnimationFrame(gashaponCrankRaf);
        gashaponCrankRaf = null;
      }}
      // A real capsule machine needs one short ratchet movement to release a
      // capsule.  A full 360° animation reads as an arcade spinner, not a
      // hand turning the crank once.
      const clicks = 4;
      const start = performance.now();
      let lastClick = -1;
      crank.style.transform = "rotate(0deg)";

      return new Promise((resolve) => {{
        const tick = (now) => {{
          const t = Math.min(1, (now - start) / durationMs);
          // 機械手感：起步費力 → 中段順暢 → 末端咬住
          const eased = t < 0.18
            ? (t / 0.18) * (t / 0.18) * 0.12
            : t > 0.82
              ? 0.88 + (1 - Math.pow(1 - (t - 0.82) / 0.18, 2)) * 0.12
              : 0.12 + ((t - 0.18) / 0.64) * 0.76;

          const clickIdx = Math.min(clicks - 1, Math.floor(eased * clicks));
          if (clickIdx !== lastClick) {{
            lastClick = clickIdx;
            sound.playFile("/assets/sound/ui/tick_001.ogg", () => sound.playPegTick());
          }}

          const seg = 1 / clicks;
          const local = Math.min(1, Math.max(0, (eased - clickIdx * seg) / seg));
          // 每格棘輪：先卡住再突然跟上
          const tooth = local < 0.35
            ? local * local * 0.45
            : 0.055 + Math.pow((local - 0.35) / 0.65, 1.35) * 0.945;
          const deg = (clickIdx + tooth) * (totalDegrees / clicks);
          crank.style.transform = `rotate(${{deg}}deg)`;

          if (t < 1) {{
            gashaponCrankRaf = requestAnimationFrame(tick);
          }} else {{
            crank.style.transform = `rotate(${{totalDegrees}}deg)`;
            gashaponCrankRaf = null;
            resolve();
          }}
        }};
        gashaponCrankRaf = requestAnimationFrame(tick);
      }});
    }}

    function playGashaponAnimation(data) {{
      if (MODE !== "all" && MODE !== "gashapon") return;
      hideAllStages();

      const stage = document.getElementById("gashapon-stage");
      const crank = document.getElementById("gashapon-crank");
      const popStage = document.getElementById("capsule-pop");
      const chute = document.getElementById("chute-capsule");
      const toy = resolveGashaponToy(data.toy);

      document.getElementById("toy-name").innerText = toy.name || "神秘扭蛋玩具";
      document.getElementById("toy-desc").innerText = toy.desc || `恭喜 @${{data.user_name || "觀眾"}} 扭中！`;

      const charImg = document.getElementById("toy-character-img");
      const customImg = document.getElementById("toy-custom-img");
      const imgPath = toy.image || "/assets/toys/toy_robot.png";
      const isRare = /機甲|弗芬|限定/.test(toy.name || "") || /超稀有|機甲先鋒|療癒/.test(toy.desc || "");

      if (toy.image && typeof toy.image === "string" && (toy.image.startsWith("http") || toy.image.startsWith("data:"))) {{
        customImg.src = toy.image;
        customImg.style.display = "block";
        if (charImg) charImg.style.display = "none";
        customImg.onerror = () => {{
          customImg.style.display = "none";
          if (charImg) {{
            charImg.src = "/assets/toys/toy_robot.png";
            charImg.style.display = "block";
          }}
        }};
      }} else {{
        if (customImg) customImg.style.display = "none";
        if (charImg) {{
          charImg.src = imgPath;
          charImg.style.display = "block";
        }}
      }}

      stage.classList.add("active");
      popStage.classList.remove("active");
      if (chute) {{
        chute.className = "chute-capsule" + (isRare ? " rare" : "");
      }}

      // 等 layout 後啟動重力沉降物理
      safeTimeout(() => {{
        const phys = ensureGashaponPhysics();
        if (phys) {{
          phys.measure();
          phys.packBottom();
          for (let i = 0; i < 40; i++) phys.step(1 / 60);
          phys.render();
          // Short, low-energy capsule shuffle: the crank gives one small
          // kick, then the capsules settle back into the dome.
          phys.agitate(720);
        }}
        spinGashaponCrank(crank, 780, 155);
        sound.playRatchet();
      }}, 40);

      // 膠囊落入出貨口（攪拌中段）
      safeTimeout(() => {{
        if (chute) {{
          chute.classList.remove("dropping");
          void chute.offsetWidth;
          chute.classList.add("dropping");
        }}
        sound.playFile("/assets/sound/ui/drop_001.ogg", () => sound.playWoodClack(0.7));
      }}, 980);

      // 裂開露出公仔；球倉繼續重力回落堆疊
      safeTimeout(() => {{
        if (chute) chute.className = "chute-capsule";
        popStage.classList.add("active");
        sound.playFanfare();
        spawnVFX("gold", isRare ? 90 : 55);
      }}, 1880);

      safeTimeout(() => hideAllStages(), 8200);
    }}

    // 4. 二次元星空抽卡 (Card Gacha / 10-Pull 5x2 召喚矩陣)
    // SSOT：須與 minigame.GACHA_CARD_POOL 卡名／立繪路徑一致
    const GACHA_CARD_DATABASE = {{
      ssr: [
        {{ name: "星海夏日 · 詩音", rarity: "SSR", image: "/assets/characters/ssr_shion.png", back: "/assets/ui/card_back_gold.png", quote: "載波信號已鎖定，今晚由我伴飛。", title: "SSR 星海夏日", color: "#fbbf24" }},
        {{ name: "熾天星輝 · 艾莉亞", rarity: "SSR", image: "/assets/characters/ssr_aria.png", back: "/assets/ui/card_back_gold.png", quote: "星輝與你同在，願命運為你降下奇蹟。", title: "SSR 熾天星輝", color: "#fbbf24" }}
      ],
      sr: [
        {{ name: "疾風守護 · 大樹", rarity: "SR", image: "/assets/characters/sr_daiki.png", back: "/assets/ui/card_back_blue.png", quote: "交給我吧，前方的道路由我來守護！", title: "SR 疾風守護", color: "#c084fc" }},
        {{ name: "漫步日常 · 詩音", rarity: "SR", image: "/assets/characters/sr_shion.png", back: "/assets/ui/card_back_blue.png", quote: "今天直播很開心呢，一起加油吧～", title: "SR 漫步日常", color: "#c084fc" }}
      ],
      r: [
        {{ name: "冒險茸茸 · 弗芬頓紳士", rarity: "R", image: "/assets/characters/r_fuffington.png", back: "/assets/ui/card_back_blue.png", quote: "雖然在下身材嬌小，但冒險的心可是無與倫比！", title: "R 冒險茸茸", color: "#38bdf8" }},
        {{ name: "晨曦見習 · 莉莉安", rarity: "R", image: "/assets/characters/r_dennis.png", back: "/assets/ui/card_back_blue.png", quote: "初次見面，請多指教！", title: "R 晨曦見習", color: "#38bdf8" }}
      ]
    }};

    function resolveGachaCard(raw, fallbackIndex) {{
      const c = raw || {{}};
      let rarity = String(c.rarity || "R").toUpperCase();
      if (rarity === "UR") rarity = "SSR";
      const poolKey = rarity.toLowerCase();
      const pool = GACHA_CARD_DATABASE[poolKey] || GACHA_CARD_DATABASE.r;
      let template = null;
      if (c.name) {{
        const all = [
          ...GACHA_CARD_DATABASE.ssr,
          ...GACHA_CARD_DATABASE.sr,
          ...GACHA_CARD_DATABASE.r,
        ];
        template = all.find((t) => t.name === c.name) || null;
        if (template) rarity = template.rarity;
      }}
      if (!template) {{
        const idx = typeof fallbackIndex === "number" ? fallbackIndex % pool.length : Math.floor(Math.random() * pool.length);
        template = pool[idx];
      }}
      return {{
        name: c.name || template.name,
        rarity: rarity,
        image: c.image || template.image,
        quote: c.quote || template.quote,
        back: c.back || template.back,
      }};
    }}

    function playCardGachaAnimation(data) {{
      if (MODE !== "all" && MODE !== "card-gacha" && MODE !== "gacha") return;
      hideAllStages();

      const stage = document.getElementById("card-gacha-stage");
      const portal = document.getElementById("gacha-summon-portal");
      const singleWrap = document.getElementById("single-card-wrap");
      const flipper = document.getElementById("card-flipper");
      const tenStage = document.getElementById("ten-pull-stage");
      const tenGrid = document.getElementById("ten-pull-grid");
      const tenHeader = document.getElementById("ten-pull-header");
      if (!stage) return;

      const isTenPull = Boolean(data.is_ten_pull || (data.cards && data.cards.length === 10));
      stage.classList.add("active");

      if (isTenPull) {{
        if (singleWrap) singleWrap.style.display = "none";
        if (tenStage) tenStage.style.display = "flex";
        if (tenGrid) {{
          tenGrid.style.display = "grid";
          tenGrid.innerHTML = "";
        }}

        const incomingCards = data.cards || [];
        const fullCards = [];
        let ssrCount = 0;

        for (let i = 0; i < 10; i++) {{
          const resolved = resolveGachaCard(incomingCards[i] || {{}}, i);
          if (resolved.rarity === "SSR" || resolved.rarity === "UR") ssrCount++;
          fullCards.push(resolved);
        }}

        if (tenHeader) {{
          tenHeader.innerText = ssrCount > 0 ? `✦ 召喚結果 · 獲得 ${{ssrCount}} 張 SSR ✦` : "✦ 召喚結果 · 十連達成 ✦";
        }}
        sound.playFile("/assets/sound/casino/cards-pack-open-1.ogg", () => sound.playRatchet());

        fullCards.forEach((card, idx) => {{
          const flipperDiv = document.createElement("div");
          const rLow = card.rarity.toLowerCase();
          const isSSR = card.rarity === "SSR" || card.rarity === "UR";
          flipperDiv.className = "ten-card-flipper";
          flipperDiv.id = `ten-card-${{idx}}`;

          flipperDiv.innerHTML = `
            <div class="ten-card-face ten-card-back">
              <img src="${{card.back || "/assets/ui/card_back_blue.png"}}" class="ten-card-back-img" alt="back" />
            </div>
            <div class="ten-card-face ten-card-front rarity-${{rLow}} ${{isSSR ? 'ssr' : ''}}">
              <div class="ten-rarity-pill ${{rLow}}">${{card.rarity}}</div>
              <div class="ten-img-wrap">
                <img src="${{card.image}}" class="ten-avatar-img" alt="${{card.name}}" />
              </div>
              <div class="ten-name-pill">${{card.name}}</div>
            </div>
          `;
          if (tenGrid) tenGrid.appendChild(flipperDiv);

          safeTimeout(() => {{
            flipperDiv.classList.add("flipped");
            sound.playFile("/assets/sound/casino/card-place-1.ogg", () => sound.playPegTick());
            if (isSSR) {{
              flipperDiv.classList.add("ten-ssr-burst");
              triggerScreenEffects(true);
              sound.playFanfare();
              spawnVFX("gold", 100);
            }}
          }}, 450 + idx * 180);
        }});

      }} else {{
        if (singleWrap) singleWrap.style.display = "block";
        if (tenStage) tenStage.style.display = "none";
        if (tenGrid) tenGrid.style.display = "none";

        let card = data.card || (data.cards && data.cards[0]) || {{}};
        const finalCard = resolveGachaCard(card);
        const rarity = finalCard.rarity;

        const rBadge = document.getElementById("gacha-rarity-badge");
        if (rBadge) {{
          rBadge.innerText = `✦ ${{rarity}} ✦`;
          rBadge.className = `rarity-badge ${{rarity.toLowerCase()}}`;
        }}

        const nameEl = document.getElementById("gacha-card-name");
        if (nameEl) nameEl.innerText = finalCard.name;
        const quoteEl = document.getElementById("gacha-card-quote");
        if (quoteEl) quoteEl.innerText = finalCard.quote || `「感謝 @${{data.user_name || "觀眾"}} 的召喚！」`;

        const cardFront = document.getElementById("card-front");
        if (cardFront) cardFront.className = `card-face card-front-side rarity-${{rarity.toLowerCase()}}`;

        const charImg = document.getElementById("card-character-img");
        const customImg = document.getElementById("card-custom-img");
        const backImg = document.getElementById("card-back-img");
        if (backImg) backImg.src = finalCard.back;

        if (card && card.image && typeof card.image === "string" && (card.image.startsWith("http") || card.image.startsWith("data:"))) {{
          if (customImg) {{
            customImg.src = card.image;
            customImg.style.display = "block";
            customImg.onerror = () => {{
              customImg.style.display = "none";
              if (charImg) charImg.style.display = "block";
            }};
          }}
          if (charImg) charImg.style.display = "none";
        }} else {{
          if (customImg) customImg.style.display = "none";
          if (charImg) {{
            charImg.src = finalCard.image;
            charImg.style.display = "block";
            charImg.onerror = () => {{ charImg.style.opacity = "0.35"; }};
          }}
        }}

        if (flipper) {{
          flipper.classList.remove("flipped", "is-settled");
          void flipper.offsetWidth;
        }}
        if (singleWrap) {{
          singleWrap.classList.remove("visible");
          void singleWrap.offsetWidth;
        }}

        // 節奏：法陣 → 卡背登場 → 翻開正面 → 停留展示 → 淡出
        if (portal) portal.classList.add("active");
        sound.playFile("/assets/sound/casino/cards-pack-open-1.ogg", () => sound.playRatchet());

        safeTimeout(() => {{
          if (portal) portal.classList.remove("active");
          if (singleWrap) singleWrap.classList.add("visible");
        }}, 700);

        safeTimeout(() => {{
          if (flipper) flipper.classList.add("flipped");
          sound.playFile("/assets/sound/casino/card-place-1.ogg", () => sound.playPegTick());

          const isGrand = rarity === "SSR" || rarity === "UR";
          triggerScreenEffects(isGrand);
          if (isGrand) {{
            sound.playFanfare();
            spawnVFX("gold", 120);
          }} else if (rarity === "SR") {{
            sound.playChime();
            spawnVFX("spark", 70);
          }} else {{
            spawnVFX("spark", 28);
          }}
        }}, 1450);
      }}

      // 單抽約 7.5 秒、十連約 9 秒後收起
      safeTimeout(() => hideAllStages(), isTenPull ? 9200 : 7500);
    }}

    // 5. 幸運大轉盤 (Lucky Wheel)
    function playWheelAnimation(data) {{
      if (MODE !== "all" && MODE !== "wheel") return;
      hideAllStages();

      const stage = document.getElementById("wheel-stage");
      const disc = document.getElementById("wheel-disc");
      const pointer = document.getElementById("wheel-pointer");
      const bubble = document.getElementById("wheel-bubble");

      const items = data.items || ["頭獎 1000 點", "銘謝惠顧", "二獎 500 點", "再來一次", "三獎 200 點", "專屬稱號", "點數 50", "點數 100"];
      const targetIdx = Number(data.target_index || 0);
      const targetItem = items[targetIdx] || "大獎";

      bubble.innerText = `@${{data.user_name || "觀眾"}} 轉動轉盤中...`;
      stage.classList.add("active");

      // 旋轉度數 (多轉 5 圈後停在目標格)
      const sliceAngle = 360 / items.length;
      const targetAngle = 360 * 5 + (items.length - targetIdx) * sliceAngle;
      const sectorGroup = document.getElementById("wheel-sectors");
      if (sectorGroup) {{
        while (sectorGroup.firstChild) sectorGroup.removeChild(sectorGroup.firstChild);
        const colors = ["#0f766e", "#7c3aed", "#b45309", "#be123c", "#0369a1", "#4d7c0f", "#9f1239", "#4338ca"];
        const polar = (angle, radius) => {{
          const radians = angle * Math.PI / 180;
          return {{ x: 200 + Math.cos(radians) * radius, y: 200 + Math.sin(radians) * radius }};
        }};
        items.forEach((item, index) => {{
          const startAngle = -90 + index * sliceAngle;
          const endAngle = startAngle + sliceAngle;
          const start = polar(startAngle, 188);
          const end = polar(endAngle, 188);
          const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
          path.setAttribute("d", `M 200 200 L ${{start.x}} ${{start.y}} A 188 188 0 ${{sliceAngle > 180 ? 1 : 0}} 1 ${{end.x}} ${{end.y}} Z`);
          path.setAttribute("fill", colors[index % colors.length]);
          path.setAttribute("fill-opacity", "0.92");
          path.setAttribute("stroke", "rgba(255,255,255,0.28)");
          path.setAttribute("stroke-width", "2");
          const labelPoint = polar((startAngle + endAngle) / 2, items.length > 8 ? 132 : 124);
          const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
          label.setAttribute("x", String(labelPoint.x));
          label.setAttribute("y", String(labelPoint.y));
          label.setAttribute("text-anchor", "middle");
          label.setAttribute("dominant-baseline", "middle");
          label.setAttribute("font-size", String(Math.max(10, Math.min(16, 170 / items.length))));
          label.setAttribute("font-weight", "800");
          label.setAttribute("fill", "#f8fafc");
          label.setAttribute("stroke", "rgba(2,6,23,0.45)");
          label.setAttribute("stroke-width", "2");
          label.setAttribute("paint-order", "stroke");
          label.setAttribute("transform", `rotate(${{(startAngle + endAngle) / 2 + 90}} ${{labelPoint.x}} ${{labelPoint.y}})`);
          label.textContent = String(item).slice(0, 10);
          sectorGroup.appendChild(path);
          sectorGroup.appendChild(label);
        }});
      }}

      // 確保從 0 度重新開始平滑過渡
      disc.style.transition = "none";
      disc.style.transform = "rotateX(12deg) rotateZ(0deg) translateZ(2px)";
      void disc.offsetWidth;
      disc.style.transition = "transform 4s cubic-bezier(0.15, 0.9, 0.25, 1)";
      void disc.offsetWidth;
      disc.style.transform = `rotateX(12deg) rotateZ(${{targetAngle}}deg) translateZ(2px)`;

      pointer.classList.add("flicking");

      // 指針連續彈動音
      let tickCount = 0;
      const tickInterval = safeInterval(() => {{
        sound.playFile("/assets/sound/ui/tick_001.ogg", () => sound.playPegTick());
        tickCount++;
        if (tickCount > 24) clearInterval(tickInterval);
      }}, 120);

      safeTimeout(() => {{
        pointer.classList.remove("flicking");
        bubble.innerText = `🎉 @${{data.user_name || "觀眾"}} 轉到了：【${{targetItem}}】！`;
        triggerScreenEffects(true);
        sound.playFanfare();
        spawnVFX("gold", 90);
      }}, 4000);

      safeTimeout(() => hideAllStages(), 8500);
    }}

    // =========================================================================
    // 3D 物理引擎 (reusable 3D Rigid Body Physics Engine with WebGL Three.js)
    // =========================================================================
    let dicePhysicsWorld = null;
    let gamblePhysicsWorld = null;
    let coinPhysicsWorld = null;

    // 所有投擲類展示的唯一接觸面：CSS、WebGL 與剛體 solver 都以此為基準。
    // 模組可以有不同的物件大小與碰撞邊界，但不能再有不同的地面高度、
    // WebGL 平面尺寸或畫布構圖，避免物件看起來各自漂在不同的世界裡。
    const THROW_PLANE_CONFIG = Object.freeze({{
      id: "shared-y0",
      worldY: 0,
      webglWidth: 80,
      webglDepth: 50,
      canvasWidth: 500,
      canvasHeight: 240,
      cameraPosition: [0, 18, 26],
      cameraLookAtY: 0.5,
      cssRestOffsetY: 0
    }});

    // 與 D:\\skymiku\\dice/config/dice-config.json 對齊的可覆寫基準。
    // 事件可帶 physics 物件覆寫；未提供時使用參考專案的預設值。
    const DICE_REFERENCE_DEFAULTS = Object.freeze({{
      diceSize: 60,
      sceneWidth: 800,
      sceneHeight: 600,
      perspective: 2000,
      sceneRotationX: 30,
      initialVelocity: 300,
      throwDistance: 400,
      gravity: 1200,
      pullHeightMin: 200,
      pullHeightMax: 300,
      pullTimeMin: 150,
      pullTimeMax: 250,
      spinDurationMin: 1600,
      spinDurationMax: 2400,
      moveDurationMin: 1400,
      moveDurationMax: 2000,
      bounceFrequencyMin: 2.2,
      bounceFrequencyMax: 3.2,
      tiltAngleMin: -60,
      tiltAngleMax: 60,
      spinRotation: 1080,
      shadowOpacity: 0.7
    }});

    // WebGL 3D 物理骰子渲染引擎 (Three.js PBR Ivory Rounded Dice & Soft Contact Shadow)
    class WebGLDiceEngine {{
      constructor(canvasId, width, height, cameraPos = THROW_PLANE_CONFIG.cameraPosition) {{
        this.canvasId = canvasId;
        this.canvas = document.getElementById(canvasId);
        this.width = width;
        this.height = height;
        this.cameraPos = cameraPos;
        this.planeY = THROW_PLANE_CONFIG.worldY;
        this.isSupported = Boolean(window.THREE && this.canvas);
        this.renderer = null;
        this.scene = null;
        this.camera = null;
        this.diceMeshes = [];
        this.diceMaterials = null;
        this.faceMaterialsByValue = {{}};
        if (this.isSupported) {{
          try {{
            this.init();
          }} catch (err) {{
            console.warn("WebGL initialization failed:", err);
            this.isSupported = false;
          }}
        }}
      }}

      init() {{
        this.renderer = new THREE.WebGLRenderer({{
          canvas: this.canvas,
          alpha: true,
          antialias: true,
          powerPreference: "high-performance"
        }});
        this.renderer.setSize(this.width, this.height, false);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        // Keep the WebGL path visually aligned with the dark CSS felt plane;
        // headless browsers can otherwise composite an alpha render target
        // against white and wash the tabletop into pale blue.
        if (this.renderer.setClearColor) this.renderer.setClearColor(0x081b2a, 1);
        // 參考骰子場景採用長焦＋ACES，避免 OBS 小畫布上的透視膨脹與高光爆白。
        if ("outputEncoding" in this.renderer && THREE.sRGBEncoding) {{
          this.renderer.outputEncoding = THREE.sRGBEncoding;
        }}
        if ("toneMapping" in this.renderer && THREE.ACESFilmicToneMapping) {{
          this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
          this.renderer.toneMappingExposure = 1.05;
        }}
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(20, this.width / this.height, 0.1, 100);
        this.camera.position.set(this.cameraPos[0], this.cameraPos[1], this.cameraPos[2]);
        this.camera.lookAt(0, THROW_PLANE_CONFIG.cameraLookAtY, 0);

        const ambientLight = new THREE.AmbientLight(0xffffff, 0.50);
        this.scene.add(ambientLight);

        const dirLight = new THREE.DirectionalLight(0xfff5e6, 1.40);
        dirLight.position.set(-10, 24, 14);
        dirLight.castShadow = true;
        dirLight.shadow.mapSize.width = 1024;
        dirLight.shadow.mapSize.height = 1024;
        dirLight.shadow.camera.near = 0.5;
        dirLight.shadow.camera.far = 60;
        const d = 16;
        dirLight.shadow.camera.left = -d;
        dirLight.shadow.camera.right = d;
        dirLight.shadow.camera.top = d;
        dirLight.shadow.camera.bottom = -d;
        dirLight.shadow.bias = -0.00025;
        dirLight.shadow.radius = 4.0;
        this.scene.add(dirLight);
        this.scene.add(dirLight.target);
        dirLight.target.position.set(0, THROW_PLANE_CONFIG.cameraLookAtY, 0);

        const fillLight = new THREE.DirectionalLight(0xdbeafe, 0.45);
        fillLight.position.set(12, 14, 10);
        this.scene.add(fillLight);

        const rimLight = new THREE.DirectionalLight(0xfef08a, 0.65);
        rimLight.position.set(0, 18, -14);
        this.scene.add(rimLight);

        // Transparent receiving plane: its y=0 is the exact shared contact
        // plane used by every throwing solver, so shadows cannot float below.
        const floorMaterial = THREE.ShadowMaterial
          ? new THREE.ShadowMaterial({{
              color: 0x0f172a,
              opacity: 0.28,
              transparent: true,
              depthWrite: false
            }})
          : new THREE.MeshBasicMaterial({{
              transparent: true,
              opacity: 0,
              depthWrite: false
            }});
        const floorGeometry = new THREE.PlaneGeometry(
          THROW_PLANE_CONFIG.webglWidth,
          THROW_PLANE_CONFIG.webglDepth
        );
        const floor = new THREE.Mesh(floorGeometry, floorMaterial);
        floor.name = "shared-horizontal-throw-plane";
        floor.rotation.x = -Math.PI / 2;
        floor.position.y = this.planeY;
        floor.receiveShadow = true;
        floor.renderOrder = -1;
        this.scene.add(floor);
        this.floorMesh = floor;

        // A visible, strictly horizontal surface uses the same geometry and
        // y=0 as the shadow receiver.  The CSS rectangle is hidden whenever
        // this WebGL surface is active, so there is only one rendered plane.
        // A lit PBR plane is overexposed by the combined key/fill/rim setup
        // on transparent OBS canvases. Use a stable dark base for the table;
        // the separate shadow receiver and the dice materials still provide
        // the physical lighting cues without washing the stage out.
        const surfaceMaterial = new THREE.MeshBasicMaterial({{
          color: 0x081b2a,
          transparent: false,
          opacity: 1.0,
          depthWrite: true,
          side: THREE.DoubleSide
        }});
        const surface = new THREE.Mesh(
          new THREE.PlaneGeometry(THROW_PLANE_CONFIG.webglWidth, THROW_PLANE_CONFIG.webglDepth),
          surfaceMaterial
        );
        surface.name = "shared-horizontal-throw-plane-surface";
        surface.rotation.x = -Math.PI / 2;
        surface.position.y = this.planeY + 0.006;
        surface.receiveShadow = true;
        surface.renderOrder = -2;
        this.scene.add(surface);
        this.floorSurface = surface;

        this.initFaceTextures();
      }}

      initFaceTextures() {{
        const createFaceCanvas = (faceNum) => {{
          const c = document.createElement("canvas");
          const size = 512;
          c.width = size;
          c.height = size;
          const ctx = c.getContext("2d");

          const center = size / 2;
          const bgGrad = ctx.createRadialGradient(center, center, 50, center, center, 340);
          bgGrad.addColorStop(0, "#ffffff");
          bgGrad.addColorStop(0.72, "#fbf9f5");
          bgGrad.addColorStop(0.92, "#f0e9df");
          bgGrad.addColorStop(1, "#dfd5c5");
          ctx.fillStyle = bgGrad;
          ctx.fillRect(0, 0, size, size);

          // 貼圖內縮邊界：配合真正的圓角幾何，讓面與邊緣有清晰分界。
          const roundedRectPath = (x, y, width, height, radius) => {{
            const r = Math.min(radius, width / 2, height / 2);
            ctx.beginPath();
            ctx.moveTo(x + r, y);
            ctx.lineTo(x + width - r, y);
            ctx.quadraticCurveTo(x + width, y, x + width, y + r);
            ctx.lineTo(x + width, y + height - r);
            ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
            ctx.lineTo(x + r, y + height);
            ctx.quadraticCurveTo(x, y + height, x, y + height - r);
            ctx.lineTo(x, y + r);
            ctx.quadraticCurveTo(x, y, x + r, y);
            ctx.closePath();
          }};

          ctx.strokeStyle = "rgba(120, 100, 78, 0.32)";
          ctx.lineWidth = 22;
          roundedRectPath(10, 10, size - 20, size - 20, 84);
          ctx.stroke();

          ctx.strokeStyle = "rgba(255, 255, 255, 0.72)";
          ctx.lineWidth = 6;
          roundedRectPath(30, 30, size - 60, size - 60, 70);
          ctx.stroke();

          const drawPip = (x, y, r, isRed = false) => {{
            ctx.save();
            ctx.beginPath();
            ctx.arc(x, y, r, 0, Math.PI * 2);
            const pipGrad = ctx.createRadialGradient(x - r * 0.28, y - r * 0.28, r * 0.05, x, y, r);
            if (isRed) {{
              pipGrad.addColorStop(0, "#ef4444");
              pipGrad.addColorStop(0.5, "#d00000");
              pipGrad.addColorStop(0.88, "#7f1d1d");
              pipGrad.addColorStop(1, "#450a0a");
            }} else {{
              pipGrad.addColorStop(0, "#334155");
              pipGrad.addColorStop(0.58, "#111827");
              pipGrad.addColorStop(1, "#020617");
            }}
            ctx.fillStyle = pipGrad;
            ctx.shadowColor = "rgba(0,0,0,0.44)";
            ctx.shadowBlur = 10;
            ctx.shadowOffsetY = 3;
            ctx.fill();

            ctx.beginPath();
            ctx.arc(x, y + 2, r + 2, 0, Math.PI * 2);
            ctx.lineWidth = 3;
            ctx.strokeStyle = isRed ? "rgba(120, 0, 0, 0.36)" : "rgba(0, 0, 0, 0.42)";
            ctx.stroke();
            ctx.shadowColor = "transparent";
            ctx.restore();
          }};

          const R = 48;
          const C = 256;
          const L = 152;
          const U = 360;

          if (faceNum === 1) {{
            drawPip(C, C, 82, true);
          }} else if (faceNum === 2) {{
            drawPip(L, L, R, false);
            drawPip(U, U, R, false);
          }} else if (faceNum === 3) {{
            drawPip(L, L, R, false);
            drawPip(C, C, R, false);
            drawPip(U, U, R, false);
          }} else if (faceNum === 4) {{
            drawPip(L, L, R, true);
            drawPip(U, L, R, true);
            drawPip(L, U, R, true);
            drawPip(U, U, R, true);
          }} else if (faceNum === 5) {{
            drawPip(L, L, R, false);
            drawPip(U, L, R, false);
            drawPip(C, C, R, false);
            drawPip(L, U, R, false);
            drawPip(U, U, R, false);
          }} else if (faceNum === 6) {{
            drawPip(166, 138, R, false);
            drawPip(166, 256, R, false);
            drawPip(166, 374, R, false);
            drawPip(346, 138, R, false);
            drawPip(346, 256, R, false);
            drawPip(346, 374, R, false);
          }}

          return c;
        }};

        // Reference face order around the cube: +Z=1, +X=2, -Z=3,
        // -X=4, -Y=5, +Y=6. Opposite faces still sum to 7.
        const faceOrder = [1, 2, 3, 4, 5, 6];
        this.diceMaterials = faceOrder.map(fNum => {{
          const canvas = createFaceCanvas(fNum);
          const texture = new THREE.CanvasTexture(canvas);
          if ("encoding" in texture && THREE.sRGBEncoding) texture.encoding = THREE.sRGBEncoding;
          texture.generateMipmaps = true;
          texture.anisotropy = 8;
          const FaceMaterial = THREE.MeshPhysicalMaterial || THREE.MeshStandardMaterial;
          const material = new FaceMaterial({{
            map: texture,
            roughness: 0.18,
            metalness: 0.03,
            clearcoat: 0.34,
            clearcoatRoughness: 0.20,
            side: THREE.DoubleSide
          }});
          this.faceMaterialsByValue[fNum] = material;
          return material;
        }});

        const createCoinCanvas = (heads) => {{
          const c = document.createElement("canvas");
          c.width = 512;
          c.height = 512;
          const ctx = c.getContext("2d");
          const center = 256;
          const gradient = ctx.createRadialGradient(160, 140, 24, center, center, 300);
          if (heads) {{
            gradient.addColorStop(0, "#fff7a8");
            gradient.addColorStop(0.45, "#fbbf24");
            gradient.addColorStop(0.82, "#d97706");
            gradient.addColorStop(1, "#78350f");
          }} else {{
            gradient.addColorStop(0, "#ffffff");
            gradient.addColorStop(0.45, "#e2e8f0");
            gradient.addColorStop(0.82, "#94a3b8");
            gradient.addColorStop(1, "#334155");
          }}
          ctx.fillStyle = gradient;
          ctx.fillRect(0, 0, 512, 512);
          ctx.strokeStyle = heads ? "#fef08a" : "#f8fafc";
          ctx.lineWidth = 18;
          ctx.beginPath();
          ctx.arc(center, center, 220, 0, Math.PI * 2);
          ctx.stroke();
          ctx.strokeStyle = heads ? "rgba(120, 53, 15, 0.7)" : "rgba(51, 65, 85, 0.7)";
          ctx.lineWidth = 5;
          ctx.setLineDash([10, 9]);
          ctx.beginPath();
          ctx.arc(center, center, 178, 0, Math.PI * 2);
          ctx.stroke();
          ctx.setLineDash([]);
          ctx.fillStyle = heads ? "rgba(255, 255, 255, 0.78)" : "rgba(15, 23, 42, 0.68)";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.font = "900 128px serif";
          ctx.fillText(heads ? "♛" : "★", center, 238);
          ctx.font = "900 27px sans-serif";
          ctx.letterSpacing = "6px";
          ctx.fillText(heads ? "INTERACTIVE" : "FORTUNE", center, 365);
          ctx.font = "800 21px sans-serif";
          ctx.fillText(heads ? "★ 2026 ★" : "★ 1 GOLD ★", center, 405);
          return c;
        }};
        const CoinMaterial = THREE.MeshPhysicalMaterial || THREE.MeshStandardMaterial;
        const coinTexture = (heads) => {{
          const texture = new THREE.CanvasTexture(createCoinCanvas(heads));
          if ("encoding" in texture && THREE.sRGBEncoding) texture.encoding = THREE.sRGBEncoding;
          texture.anisotropy = 8;
          return texture;
        }};
        this.coinMaterials = {{
          edge: new CoinMaterial({{
            color: 0xb45309,
            roughness: 0.24,
            metalness: 0.78,
            clearcoat: 0.45,
            clearcoatRoughness: 0.18
          }}),
          heads: new CoinMaterial({{
            map: coinTexture(true),
            roughness: 0.22,
            metalness: 0.62,
            clearcoat: 0.42,
            clearcoatRoughness: 0.18,
            side: THREE.DoubleSide
          }}),
          tails: new CoinMaterial({{
            map: coinTexture(false),
            roughness: 0.22,
            metalness: 0.54,
            clearcoat: 0.35,
            clearcoatRoughness: 0.18,
            side: THREE.DoubleSide
          }})
        }};
      }}

      clearDice() {{
        if (!this.isSupported) return;
        this.diceMeshes.forEach(m => {{
          this.scene.remove(m);
        }});
        this.diceMeshes = [];
        this.renderer.render(this.scene, this.camera);
      }}

      createDieMesh(size = 3.6) {{
        if (!this.isSupported) return null;
        const half = size / 2;
        const edgeRadius = size * 0.105;
        const faceSize = size - edgeRadius * 1.35;
        const group = new THREE.Group();
        group.name = "rounded-casino-die";
        group.userData.halfSize = half;

        const EdgeMaterial = THREE.MeshPhysicalMaterial || THREE.MeshStandardMaterial;
        const edgeMaterial = new EdgeMaterial({{
          color: 0xe7dac8,
          roughness: 0.19,
          metalness: 0.025,
          clearcoat: 0.42,
          clearcoatRoughness: 0.18
        }});
        const coreSize = size - edgeRadius * 1.35;
        const core = new THREE.Mesh(new THREE.BoxGeometry(coreSize, coreSize, coreSize), edgeMaterial);
        core.castShadow = true;
        core.receiveShadow = true;
        group.add(core);

        // 以高解析平面承載圓角貼圖；實體圓角由邊柱與角球補齊，避免
        // ShapeGeometry 三角剖分在 OBS 縮放時產生不自然的面內色帶。
        const faceGeometry = new THREE.PlaneGeometry(faceSize, faceSize, 4, 4);

        const addFace = (value, x, y, z, rx, ry, rz) => {{
          const face = new THREE.Mesh(
            faceGeometry,
            this.faceMaterialsByValue[value]
          );
          face.position.set(x, y, z);
          face.rotation.set(rx, ry, rz);
          face.castShadow = true;
          face.receiveShadow = true;
          group.add(face);
        }};
        const faceOffset = half + 0.018;
        // Match the reference die convention used by the CSS fallback:
        // +Z=1, +X=2, -Z=3, -X=4, -Y=5, +Y=6.
        addFace(1, 0, 0, faceOffset, 0, 0, 0);
        addFace(2, faceOffset, 0, 0, 0, Math.PI / 2, 0);
        addFace(3, 0, 0, -faceOffset, 0, Math.PI, 0);
        addFace(4, -faceOffset, 0, 0, 0, -Math.PI / 2, 0);
        addFace(5, 0, -faceOffset, 0, Math.PI / 2, 0, 0);
        addFace(6, 0, faceOffset, 0, -Math.PI / 2, 0, 0);

        const edgeGeometry = new THREE.CylinderGeometry(edgeRadius, edgeRadius, size - edgeRadius * 2, 24, 1, false);
        const addEdge = (x, y, z, rx, ry, rz) => {{
          const edge = new THREE.Mesh(edgeGeometry, edgeMaterial);
          edge.position.set(x, y, z);
          edge.rotation.set(rx, ry, rz);
          edge.castShadow = true;
          edge.receiveShadow = true;
          group.add(edge);
        }};
        const edgeOffset = half - edgeRadius;
        // 三組互相垂直的圓角長邊。
        [-1, 1].forEach(a => {{
          [-1, 1].forEach(b => {{
            addEdge(0, a * edgeOffset, b * edgeOffset, 0, 0, Math.PI / 2);
            addEdge(a * edgeOffset, 0, b * edgeOffset, 0, 0, 0);
            addEdge(a * edgeOffset, b * edgeOffset, 0, Math.PI / 2, 0, 0);
          }});
        }});

        const cornerGeometry = new THREE.SphereGeometry(edgeRadius * 1.04, 20, 16);
        [-1, 1].forEach(xSign => {{
          [-1, 1].forEach(ySign => {{
            [-1, 1].forEach(zSign => {{
              const corner = new THREE.Mesh(cornerGeometry, edgeMaterial);
              corner.position.set(xSign * edgeOffset, ySign * edgeOffset, zSign * edgeOffset);
              corner.castShadow = true;
              corner.receiveShadow = true;
              group.add(corner);
            }});
          }});
        }});

        this.scene.add(group);
        this.diceMeshes.push(group);
        return group;
      }}

      createCoinMesh(radius = 3.02, thickness = 0.36) {{
        if (!this.isSupported) return null;
        const group = new THREE.Group();
        group.name = "solid-coin-cylinder";
        group.userData.coinRadius = radius;
        group.userData.coinHalfThickness = thickness / 2;
        // Do not rely on CylinderGeometry's implicit material-group ordering
        // for the two caps.  The physics contract uses local +Z=正面 and
        // local -Z=反面, so build the side wall and both caps explicitly.
        const sideGeometry = new THREE.CylinderGeometry(radius, radius, thickness, 64, 1, true);
        const side = new THREE.Mesh(sideGeometry, this.coinMaterials.edge);
        // CylinderGeometry's axis is +Y; rotate it to the body's local +Z.
        side.rotation.x = Math.PI / 2;
        side.castShadow = true;
        side.receiveShadow = true;

        const capGeometry = new THREE.CircleGeometry(radius, 64);
        const heads = new THREE.Mesh(capGeometry, this.coinMaterials.heads);
        heads.position.z = thickness / 2;
        heads.castShadow = true;
        heads.receiveShadow = true;
        const tails = new THREE.Mesh(capGeometry, this.coinMaterials.tails);
        tails.position.z = -thickness / 2;
        tails.rotation.y = Math.PI;
        tails.castShadow = true;
        tails.receiveShadow = true;
        group.add(side, heads, tails);
        this.scene.add(group);
        this.diceMeshes.push(group);
        return group;
      }}

      render() {{
        if (!this.isSupported) return;
        this.renderer.render(this.scene, this.camera);
      }}
    }}

    // Dice-only rigid-body helpers.  The previous implementation treated the
    // rendered cube as a sphere and corrected its Euler angles at the end.
    // These helpers keep the existing lightweight overlay architecture, but
    // use a box support point, quaternion orientation, contact impulses and
    // angular friction for the dice path.
    const DICE_DEG2RAD = Math.PI / 180;

    function diceQuatNormalize(q) {{
      const len = Math.hypot(q.x, q.y, q.z, q.w);
      if (len < 1e-9) return {{ x: 0, y: 0, z: 0, w: 1 }};
      return {{ x: q.x / len, y: q.y / len, z: q.z / len, w: q.w / len }};
    }}

    function diceQuatMultiply(a, b) {{
      return {{
        x: a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y,
        y: a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x,
        z: a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w,
        w: a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z
      }};
    }}

    function diceQuatConjugate(q) {{
      return {{ x: -q.x, y: -q.y, z: -q.z, w: q.w }};
    }}

    function diceQuatFromEulerXYZ(rx, ry, rz) {{
      const cx = Math.cos(rx * 0.5);
      const sx = Math.sin(rx * 0.5);
      const cy = Math.cos(ry * 0.5);
      const sy = Math.sin(ry * 0.5);
      const cz = Math.cos(rz * 0.5);
      const sz = Math.sin(rz * 0.5);
      return diceQuatNormalize({{
        x: sx * cy * cz - cx * sy * sz,
        y: cx * sy * cz + sx * cy * sz,
        z: cx * cy * sz - sx * sy * cz,
        w: cx * cy * cz + sx * sy * sz
      }});
    }}

    function diceQuatToEulerXYZ(q) {{
      const sinr = 2 * (q.w * q.x + q.y * q.z);
      const cosr = 1 - 2 * (q.x * q.x + q.y * q.y);
      const rx = Math.atan2(sinr, cosr);
      const sinp = Math.max(-1, Math.min(1, 2 * (q.w * q.y - q.z * q.x)));
      const ry = Math.asin(sinp);
      const siny = 2 * (q.w * q.z + q.x * q.y);
      const cosy = 1 - 2 * (q.y * q.y + q.z * q.z);
      const rz = Math.atan2(siny, cosy);
      return {{
        rx: rx / DICE_DEG2RAD,
        ry: ry / DICE_DEG2RAD,
        rz: rz / DICE_DEG2RAD
      }};
    }}

    function diceQuatToCssMatrix3d(q) {{
      // Map the physics world into the same 64deg camera tilt as the CSS
      // tabletop, without an Euler conversion (and therefore without
      // gimbal-lock jumps or a different CSS rotation order near settlement).
      const xx = q.x * q.x;
      const yy = q.y * q.y;
      const zz = q.z * q.z;
      const xy = q.x * q.y;
      const xz = q.x * q.z;
      const yz = q.y * q.z;
      const xw = q.x * q.w;
      const yw = q.y * q.w;
      const zw = q.z * q.w;
      const r00 = 1 - 2 * (yy + zz);
      const r01 = 2 * (xy - zw);
      const r02 = 2 * (xz + yw);
      const r10 = 2 * (xy + zw);
      const r11 = 1 - 2 * (xx + zz);
      const r12 = 2 * (yz - xw);
      const r20 = 2 * (xz - yw);
      const r21 = 2 * (yz + xw);
      const r22 = 1 - 2 * (xx + yy);
      const cameraSin = Math.sin(64 * DICE_DEG2RAD);
      const cameraCos = Math.cos(64 * DICE_DEG2RAD);
      // M = cameraBasis * quaternionRotation. CSS matrix3d is column-major;
      // the camera basis itself accounts for the screen's downward-positive Y.
      const m00 = r00;
      const m01 = r01;
      const m02 = r02;
      const m10 = -cameraSin * r10 + cameraCos * r20;
      const m11 = -cameraSin * r11 + cameraCos * r21;
      const m12 = -cameraSin * r12 + cameraCos * r22;
      const m20 = cameraCos * r10 + cameraSin * r20;
      const m21 = cameraCos * r11 + cameraSin * r21;
      const m22 = cameraCos * r12 + cameraSin * r22;
      return `matrix3d(${{m00}},${{m10}},${{m20}},0,${{m01}},${{m11}},${{m21}},0,${{m02}},${{m12}},${{m22}},0,0,0,0,1)`;
    }}

    function diceQuatIntegrateWorld(q, wx, wy, wz, dt) {{
      const omega = {{ x: wx, y: wy, z: wz, w: 0 }};
      const derivative = diceQuatMultiply(omega, q);
      return diceQuatNormalize({{
        x: q.x + derivative.x * 0.5 * dt,
        y: q.y + derivative.y * 0.5 * dt,
        z: q.z + derivative.z * 0.5 * dt,
        w: q.w + derivative.w * 0.5 * dt
      }});
    }}

    function diceRotateVector(q, v) {{
      const rotated = diceQuatMultiply(
        diceQuatMultiply(q, {{ x: v.x, y: v.y, z: v.z, w: 0 }}),
        diceQuatConjugate(q)
      );
      return {{ x: rotated.x, y: rotated.y, z: rotated.z }};
    }}

    function diceDot(a, b) {{
      return a.x * b.x + a.y * b.y + a.z * b.z;
    }}

    function diceCross(a, b) {{
      return {{
        x: a.y * b.z - a.z * b.y,
        y: a.z * b.x - a.x * b.z,
        z: a.x * b.y - a.y * b.x
      }};
    }}

    function diceQuatFromAxisAngle(axis, angle) {{
      const half = angle * 0.5;
      const sine = Math.sin(half);
      return diceQuatNormalize({{
        x: axis.x * sine,
        y: axis.y * sine,
        z: axis.z * sine,
        w: Math.cos(half)
      }});
    }}

    function diceQuatSlerp(a, b, amount) {{
      let bx = b.x;
      let by = b.y;
      let bz = b.z;
      let bw = b.w;
      let cosine = a.x * bx + a.y * by + a.z * bz + a.w * bw;
      if (cosine < 0) {{
        cosine = -cosine;
        bx = -bx;
        by = -by;
        bz = -bz;
        bw = -bw;
      }}
      if (cosine > 0.9995) {{
        return diceQuatNormalize({{
          x: a.x + (bx - a.x) * amount,
          y: a.y + (by - a.y) * amount,
          z: a.z + (bz - a.z) * amount,
          w: a.w + (bw - a.w) * amount
        }});
      }}
      const angle = Math.acos(Math.max(-1, Math.min(1, cosine)));
      const sine = Math.sin(angle);
      const fromWeight = Math.sin((1 - amount) * angle) / sine;
      const toWeight = Math.sin(amount * angle) / sine;
      return diceQuatNormalize({{
        x: a.x * fromWeight + bx * toWeight,
        y: a.y * fromWeight + by * toWeight,
        z: a.z * fromWeight + bz * toWeight,
        w: a.w * fromWeight + bw * toWeight
      }});
    }}

    function diceQuatAlignLocalNormal(q, localNormal) {{
      const current = diceRotateVector(q, localNormal);
      const up = {{ x: 0, y: 1, z: 0 }};
      const dot = Math.max(-1, Math.min(1, diceDot(current, up)));
      let axis = diceCross(current, up);
      let axisLength = Math.hypot(axis.x, axis.y, axis.z);
      if (axisLength < 1e-5) {{
        axis = Math.abs(current.x) < 0.7
          ? {{ x: 1, y: 0, z: 0 }}
          : {{ x: 0, y: 0, z: 1 }};
        axisLength = 1;
      }}
      axis = {{ x: axis.x / axisLength, y: axis.y / axisLength, z: axis.z / axisLength }};
      return diceQuatMultiply(diceQuatFromAxisAngle(axis, Math.acos(dot)), q);
    }}

    function diceSupportPoint(body, direction) {{
      const localDirection = diceRotateVector(diceQuatConjugate(body.q), direction);
      const h = body.halfExtent;
      const localPoint = {{
        x: localDirection.x >= 0 ? h : -h,
        y: localDirection.y >= 0 ? h : -h,
        z: localDirection.z >= 0 ? h : -h
      }};
      const worldOffset = diceRotateVector(body.q, localPoint);
      return {{
        x: body.x + worldOffset.x,
        y: body.y + worldOffset.y,
        z: body.z + worldOffset.z
      }};
    }}

    function coinSupportPoint(body, direction) {{
      // Coin local +/-Z are the two faces; X/Y form the circular rim.
      const localDirection = diceRotateVector(diceQuatConjugate(body.q), direction);
      const radial = Math.hypot(localDirection.x, localDirection.y);
      const radialScale = radial > 1e-9 ? body.radius / radial : 0;
      const localPoint = {{
        x: localDirection.x * radialScale,
        y: localDirection.y * radialScale,
        z: localDirection.z >= 0 ? body.halfThickness : -body.halfThickness
      }};
      const worldOffset = diceRotateVector(body.q, localPoint);
      return {{
        x: body.x + worldOffset.x,
        y: body.y + worldOffset.y,
        z: body.z + worldOffset.z
      }};
    }}

    function physicsSupportPoint(body, direction) {{
      return body.shape === "coin"
        ? coinSupportPoint(body, direction)
        : diceSupportPoint(body, direction);
    }}

    function diceBottomContacts(body) {{
      const h = body.halfExtent;
      const points = [];
      let minY = Infinity;
      for (const sx of [-1, 1]) {{
        for (const sy of [-1, 1]) {{
          for (const sz of [-1, 1]) {{
            const offset = diceRotateVector(body.q, {{ x: sx * h, y: sy * h, z: sz * h }});
            const point = {{
              x: body.x + offset.x,
              y: body.y + offset.y,
              z: body.z + offset.z
            }};
            if (point.y < minY - 0.18) {{
              minY = point.y;
              points.length = 0;
              points.push(point);
            }} else if (Math.abs(point.y - minY) <= 0.18) {{
              points.push(point);
            }}
          }}
        }}
      }}
      return {{ minY, points }};
    }}

    function diceFloorContact(body) {{
      // 平放的方骰有一整個底面，不應用單一角點代表接觸。
      // 取所有最低頂點的平均位置，平放時支撐力會穿過重心，
      // 只有真正傾斜／滾動時才會產生回正力矩。
      if (body.shape === "box") {{
        const contacts = diceBottomContacts(body);
        if (contacts.points.length > 0) {{
          const point = contacts.points.reduce((sum, value) => ({{
            x: sum.x + value.x,
            y: sum.y + value.y,
            z: sum.z + value.z
          }}), {{ x: 0, y: 0, z: 0 }});
          const count = contacts.points.length;
          return {{
            minY: contacts.minY,
            point: {{ x: point.x / count, y: point.y / count, z: point.z / count }}
          }};
        }}
      }}
      const point = physicsSupportPoint(body, {{ x: 0, y: -1, z: 0 }});
      return {{ minY: point.y, point }};
    }}

    function diceBoxBoxContact(a, b) {{
      // Full OBB separating-axis test (3 face axes per box plus 9 edge
      // cross-products).  The previous centre-line overlap test produced
      // false contacts between nearby but separated dice, which could hold a
      // die in mid-air or keep pushing an already-flat die forever.
      const axesA = [
        diceRotateVector(a.q, {{ x: 1, y: 0, z: 0 }}),
        diceRotateVector(a.q, {{ x: 0, y: 1, z: 0 }}),
        diceRotateVector(a.q, {{ x: 0, y: 0, z: 1 }})
      ];
      const axesB = [
        diceRotateVector(b.q, {{ x: 1, y: 0, z: 0 }}),
        diceRotateVector(b.q, {{ x: 0, y: 1, z: 0 }}),
        diceRotateVector(b.q, {{ x: 0, y: 0, z: 1 }})
      ];
      const delta = {{ x: b.x - a.x, y: b.y - a.y, z: b.z - a.z }};
      let bestNormal = null;
      let bestPenetration = Infinity;

      const testAxis = (rawAxis) => {{
        const length = Math.hypot(rawAxis.x, rawAxis.y, rawAxis.z);
        if (length < 1e-6) return true;
        let axis = {{ x: rawAxis.x / length, y: rawAxis.y / length, z: rawAxis.z / length }};
        const distanceSigned = diceDot(delta, axis);
        // Match the visibly rounded dice more closely than a sharp-cornered
        // cube.  A rounded box is a smaller core box swept by a bevel sphere:
        // face-to-face extent stays exact, while diagonal/corner extent is
        // reduced so three dice cannot form an unrealistically perfect wedge.
        const bevelA = a.halfExtent * 0.14;
        const bevelB = b.halfExtent * 0.14;
        const radiusA = (a.halfExtent - bevelA) * axesA.reduce((sum, basis) => sum + Math.abs(diceDot(axis, basis)), 0) + bevelA;
        const radiusB = (b.halfExtent - bevelB) * axesB.reduce((sum, basis) => sum + Math.abs(diceDot(axis, basis)), 0) + bevelB;
        const penetration = radiusA + radiusB - Math.abs(distanceSigned);
        if (penetration <= 0) return false;
        if (penetration < bestPenetration) {{
          if (distanceSigned < 0) axis = {{ x: -axis.x, y: -axis.y, z: -axis.z }};
          bestNormal = axis;
          bestPenetration = penetration;
        }}
        return true;
      }};

      for (const axis of axesA) if (!testAxis(axis)) return null;
      for (const axis of axesB) if (!testAxis(axis)) return null;
      for (const axisA of axesA) {{
        for (const axisB of axesB) {{
          if (!testAxis(diceCross(axisA, axisB))) return null;
        }}
      }}
      return bestNormal ? {{ normal: bestNormal, penetration: bestPenetration }} : null;
    }}

    function diceFaceUpFromQuaternion(q) {{
      // This is the same face layout used by the CSS and WebGL dice:
      // +Z=1, +X=2, -Z=3, -X=4, -Y=5, +Y=6.
      const faces = [
        {{ value: 1, normal: {{ x: 0, y: 0, z: 1 }} }},
        {{ value: 2, normal: {{ x: 1, y: 0, z: 0 }} }},
        {{ value: 3, normal: {{ x: 0, y: 0, z: -1 }} }},
        {{ value: 4, normal: {{ x: -1, y: 0, z: 0 }} }},
        {{ value: 5, normal: {{ x: 0, y: -1, z: 0 }} }},
        {{ value: 6, normal: {{ x: 0, y: 1, z: 0 }} }}
      ];
      let best = {{ value: 1, alignment: -Infinity }};
      for (const face of faces) {{
        const normal = diceRotateVector(q, face.normal);
        if (normal.y > best.alignment) {{
          best = {{ value: face.value, alignment: normal.y, normal }};
        }}
      }}
      return best;
    }}

    function diceLocalNormalForFace(value) {{
      // Keep one authoritative face-to-normal table for CSS, WebGL and the
      // low-energy result assist.  A result assist may guide the last part of
      // a landing, but it must never replace the physical face geometry.
      const normals = {{
        1: {{ x: 0, y: 0, z: 1 }},
        2: {{ x: 1, y: 0, z: 0 }},
        3: {{ x: 0, y: 0, z: -1 }},
        4: {{ x: -1, y: 0, z: 0 }},
        5: {{ x: 0, y: -1, z: 0 }},
        6: {{ x: 0, y: 1, z: 0 }}
      }};
      return normals[Number(value)] || null;
    }}

    function coinFaceUpFromQuaternion(q) {{
      const headsNormal = diceRotateVector(q, {{ x: 0, y: 0, z: 1 }});
      const tailsNormal = {{ x: -headsNormal.x, y: -headsNormal.y, z: -headsNormal.z }};
      // 硬幣不是只有正／反兩種可見狀態；若最後是以邊緣接觸桌面，
      // 保留第三種結果，避免把一個明顯的側立姿態硬判成正面或反面。
      const faceAlignment = Math.abs(headsNormal.y);
      if (faceAlignment < 0.28) {{
        return {{ value: "?", alignment: faceAlignment, edge: true }};
      }}
      return headsNormal.y >= tailsNormal.y
        ? {{ value: "正面", alignment: headsNormal.y }}
        : {{ value: "反面", alignment: tailsNormal.y }};
    }}

    function normalizeCoinSide(data) {{
      const raw = data && data.side !== undefined
        ? data.side
        : (data && data.is_heads !== undefined
          ? data.is_heads
          : (data && data.artifacts ? data.artifacts.side : null));
      if (raw === true || raw === 1) return "正面";
      if (raw === false || raw === 0) return "反面";
      const normalized = String(raw == null ? "" : raw).trim().toLowerCase();
      if (["正面", "正", "heads", "head", "front", "up"].includes(normalized)) return "正面";
      if (["反面", "反", "tails", "tail", "back", "down"].includes(normalized)) return "反面";
      return null;
    }}

    function physicsApplyInvInertia(body, impulse) {{
      if (!body.q || !body.invInertiaLocal) {{
        const scalar = body.invInertia || 0;
        return {{ x: impulse.x * scalar, y: impulse.y * scalar, z: impulse.z * scalar }};
      }}
      const local = diceRotateVector(diceQuatConjugate(body.q), impulse);
      const localResult = {{
        x: local.x * body.invInertiaLocal.x,
        y: local.y * body.invInertiaLocal.y,
        z: local.z * body.invInertiaLocal.z
      }};
      return diceRotateVector(body.q, localResult);
    }}

    function diceVelocityAtPoint(body, point) {{
      const r = {{ x: point.x - body.x, y: point.y - body.y, z: point.z - body.z }};
      const angularVelocity = body.angularVelocity;
      const spinVelocity = diceCross(angularVelocity, r);
      return {{
        x: body.vx + spinVelocity.x,
        y: body.vy + spinVelocity.y,
        z: body.vz + spinVelocity.z
      }};
    }}

    function diceImpulseDenominator(body, r, direction) {{
      const angularArm = diceCross(r, direction);
      const inverseMass = body.settled ? 0 : (1 / Math.max(0.001, body.mass));
      if (body.settled) return 0;
      const angularResponse = physicsApplyInvInertia(body, angularArm);
      return inverseMass + diceDot(angularArm, angularResponse);
    }}

    function diceApplyImpulse(body, impulse, point) {{
      // 已睡眠的骰子視為靜態接觸體；只有足夠強的撞擊才會在
      // resolveBoxPair() 中先喚醒它，避免低速數值誤差讓骰子反覆晃動。
      if (body.settled) return;
      const invMass = 1 / Math.max(0.001, body.mass);
      body.vx += impulse.x * invMass;
      body.vy += impulse.y * invMass;
      body.vz += impulse.z * invMass;
      const r = {{ x: point.x - body.x, y: point.y - body.y, z: point.z - body.z }};
      const torque = diceCross(r, impulse);
      const angularResponse = physicsApplyInvInertia(body, torque);
      body.angularVelocity.x += angularResponse.x;
      body.angularVelocity.y += angularResponse.y;
      body.angularVelocity.z += angularResponse.z;
    }}

    function diceResolveContact(body, normal, point, restitution, friction, normalLoad) {{
      let normalImpulse = 0;
      let contactVelocity = diceVelocityAtPoint(body, point);
      const velocityAlongNormal = diceDot(contactVelocity, normal);
      const r = {{ x: point.x - body.x, y: point.y - body.y, z: point.z - body.z }};

      if (velocityAlongNormal < -0.01) {{
        const denominator = diceImpulseDenominator(body, r, normal);
        // 接觸速度很低時使用完全非彈性接觸，吸收重力造成的微小
        // 反覆彈跳；只有真正的撞擊才保留骰子的彈性。
        const effectiveRestitution = Math.abs(velocityAlongNormal) < 48 ? 0 : restitution;
        normalImpulse = -(1 + effectiveRestitution) * velocityAlongNormal / denominator;
        diceApplyImpulse(body, {{
          x: normal.x * normalImpulse,
          y: normal.y * normalImpulse,
          z: normal.z * normalImpulse
        }}, point);
      }}

      contactVelocity = diceVelocityAtPoint(body, point);
      const normalComponent = diceDot(contactVelocity, normal);
      const tangentVelocity = {{
        x: contactVelocity.x - normal.x * normalComponent,
        y: contactVelocity.y - normal.y * normalComponent,
        z: contactVelocity.z - normal.z * normalComponent
      }};
      const tangentSpeed = Math.hypot(tangentVelocity.x, tangentVelocity.y, tangentVelocity.z);
      if (tangentSpeed > 0.01) {{
        const tangent = {{
          x: tangentVelocity.x / tangentSpeed,
          y: tangentVelocity.y / tangentSpeed,
          z: tangentVelocity.z / tangentSpeed
        }};
        const denominator = diceImpulseDenominator(body, r, tangent);
        const requested = -tangentSpeed / denominator;
        const maxFriction = Math.max(normalImpulse, normalLoad || 0) * friction;
        const tangentImpulse = Math.max(-maxFriction, Math.min(maxFriction, requested));
        diceApplyImpulse(body, {{
          x: tangent.x * tangentImpulse,
          y: tangent.y * tangentImpulse,
          z: tangent.z * tangentImpulse
        }}, point);
      }}

      return Math.max(0, -velocityAlongNormal);
    }}

    function diceResolvePlaneContact(body, normal, planeOffset, restitution, friction, normalLoad) {{
      const oppositeNormal = {{ x: -normal.x, y: -normal.y, z: -normal.z }};
      const isFloor = normal.y > 0.99;
      let floorContact = isFloor ? diceFloorContact(body) : null;
      let point = floorContact ? floorContact.point : physicsSupportPoint(body, oppositeNormal);
      const gap = floorContact ? floorContact.minY - planeOffset : diceDot(point, normal) - planeOffset;
      if (gap >= 0) return null;

      body.x += normal.x * -gap;
      body.y += normal.y * -gap;
      body.z += normal.z * -gap;
      floorContact = isFloor ? diceFloorContact(body) : null;
      point = floorContact ? floorContact.point : physicsSupportPoint(body, oppositeNormal);
      const impactSpeed = diceResolveContact(body, normal, point, restitution, friction, normalLoad);
      return {{ impactSpeed }};
    }}

    class RigidBody3D {{
      constructor(opts) {{
        this.element = opts.element || null;
        this.shadowElement = opts.shadowElement || null;
        this.threeMesh = opts.threeMesh || null;
        this.shape = opts.shape || "sphere";
        this.radius = opts.radius || 34;
        this.halfThickness = opts.halfThickness || 7;
        this.halfExtent = opts.halfExtent || this.radius;
        this.mass = opts.mass || 1.0;
        this.restitution = opts.restitution !== undefined ? opts.restitution : 0.54;
        this.friction = opts.friction !== undefined ? opts.friction : 0.76;
        this.surfaceFriction = opts.surfaceFriction !== undefined ? opts.surfaceFriction : 0.82;
        this.airDrag = opts.airDrag || 0.994;
        this.rotDamping = opts.rotDamping || 0.985;

        this.x = opts.x || 0;
        this.y = opts.y !== undefined ? opts.y : 200;
        this.z = opts.z || 0;

        this.vx = opts.vx || 0;
        this.vy = opts.vy || 0;
        this.vz = opts.vz || 0;

        this.rx = opts.rx || 0;
        this.ry = opts.ry || 0;
        this.rz = opts.rz || 0;

        this.wx = opts.wx || 0;
        this.wy = opts.wy || 0;
        this.wz = opts.wz || 0;

        this.boundingRadius = this.shape === "box"
          ? this.halfExtent * Math.sqrt(3)
          : (this.shape === "coin" ? Math.hypot(this.radius, this.halfThickness) : this.radius);
        this.q = (this.shape === "box" || this.shape === "coin")
          ? diceQuatFromEulerXYZ(
              -(this.rx || 0) * DICE_DEG2RAD,
              (this.ry || 0) * DICE_DEG2RAD,
              (this.rz || 0) * DICE_DEG2RAD
            )
          : null;
        // The cube is isotropic, but a coin is not: rotating around its face
        // normal is much easier than rotating it over its rim.  Keeping this
        // tensor in body-local space makes contact impulses physically
        // consistent without introducing a second physics dependency.
        this.invInertia = this.shape === "box"
          ? 6 / (Math.max(0.001, this.mass) * Math.pow(this.halfExtent * 2, 2))
          : (this.shape === "coin"
            ? 2 / (Math.max(0.001, this.mass) * Math.pow(this.radius, 2))
            : 0);
        if (this.shape === "box") {{
          this.invInertiaLocal = {{ x: this.invInertia, y: this.invInertia, z: this.invInertia }};
        }} else if (this.shape === "coin") {{
          const coinMass = Math.max(0.001, this.mass);
          const coinDiameter = this.halfThickness * 2;
          const radialInertia = (coinMass / 12) * (3 * this.radius * this.radius + coinDiameter * coinDiameter);
          const axialInertia = 0.5 * coinMass * this.radius * this.radius;
          this.invInertiaLocal = {{
            x: 1 / Math.max(0.001, radialInertia),
            y: 1 / Math.max(0.001, radialInertia),
            z: 1 / Math.max(0.001, axialInertia)
          }};
        }} else {{
          this.invInertiaLocal = {{ x: 0, y: 0, z: 0 }};
        }}
        this.angularVelocity = (this.shape === "box" || this.shape === "coin")
          ? {{
              x: (this.wx || 0) * DICE_DEG2RAD,
              y: (this.wy || 0) * DICE_DEG2RAD,
              z: (this.wz || 0) * DICE_DEG2RAD
            }}
          : null;
        this.shadowOpacity = opts.shadowOpacity !== undefined ? opts.shadowOpacity : 0.75;
        this.targetFace = this.shape === "box" && Number.isInteger(Number(opts.targetFace)) &&
          Number(opts.targetFace) >= 1 && Number(opts.targetFace) <= 6
          ? Number(opts.targetFace)
          : null;
        this.targetCoinSide = this.shape === "coin" &&
          (opts.targetCoinSide === "正面" || opts.targetCoinSide === "反面")
          ? opts.targetCoinSide
          : null;
        this.restTime = 0;
        this.unstableContactTime = 0;
        this.lastBounceAt = 0;
        this.settled = false;
        // 上層骰子可能是落在另一顆骰子上，而不是直接接觸桌面。
        // 這個接觸只保存碰撞 solver 上一個 fixed step 找到的支撐點，
        // 下一步再由重力與支撐力矩自然消耗傾斜，不把姿態指定成某個結果。
        this.supportContact = null;
        this.onBounce = opts.onBounce || null;
        this.onWallHit = opts.onWallHit || null;
      }}
    }}

    class StreamPhysicsWorld {{
      constructor(arenaElement, webglEngine = null, tuning = DICE_REFERENCE_DEFAULTS) {{
        this.arena = arenaElement;
        this.webglEngine = webglEngine;
        this.tuning = tuning;
        this.planeY = THROW_PLANE_CONFIG.worldY;
        this.bodies = [];
        this.gravity = -Math.abs(Number(tuning.gravity) || DICE_REFERENCE_DEFAULTS.gravity);
        this.bounds = {{ minX: -200, maxX: 200, minZ: -100, maxZ: 100 }};
        this.isRunning = false;
        this.lastTime = 0;
        this.rafId = null;
        // 固定時間步進避免掉幀時穿透地面／骰子，畫面仍以 RAF 速度更新。
        this.fixedDt = 1 / 120;
        this.accumulator = 0;
        this.maxSubSteps = 8;
        this.onSettled = null;
      }}

      addBody(b) {{
        this.bodies.push(b);
      }}

      start() {{
        this.stop();
        this.isRunning = true;
        this.lastTime = performance.now();
        this.accumulator = 0;
        const loop = (now) => {{
          if (!this.isRunning) return;
          let dt = (now - this.lastTime) / 1000;
          this.lastTime = now;
          // 暫停／切窗回來時最多追趕 50ms，避免一次大步驟把物體打穿碰撞面。
          dt = Math.min(0.05, Math.max(0, dt));
          this.accumulator += dt;

          let subSteps = 0;
          while (this.accumulator >= this.fixedDt && subSteps < this.maxSubSteps) {{
            this.step(this.fixedDt);
            this.accumulator -= this.fixedDt;
            subSteps++;
          }}
          if (subSteps === this.maxSubSteps && this.accumulator > this.fixedDt * 2) {{
            this.accumulator = 0;
          }}
          this.render();

          const allSettled = this.bodies.every(b => b.settled);
          if (allSettled) {{
            this.isRunning = false;
            if (this.onSettled) this.onSettled(this.bodies.map(body => body.finalFace));
            this.render();
            return;
          }}

          this.rafId = requestAnimationFrame(loop);
        }};
        this.render();
        this.rafId = requestAnimationFrame(loop);
      }}

      stop() {{
        this.isRunning = false;
        if (this.rafId) {{
          cancelAnimationFrame(this.rafId);
          this.rafId = null;
        }}
      }}

      stepBoxBody(b, dt) {{
        const angular = b.angularVelocity;
        b.vy += this.gravity * dt;
        b.vx *= Math.pow(b.airDrag, dt * 60);
        b.vy *= Math.pow(b.airDrag, dt * 60);
        b.vz *= Math.pow(b.airDrag, dt * 60);
        const angularDamping = Math.pow(b.rotDamping, dt * 60);
        angular.x *= angularDamping;
        angular.y *= angularDamping;
        angular.z *= angularDamping;

        b.x += b.vx * dt;
        b.y += b.vy * dt;
        b.z += b.vz * dt;
        b.q = diceQuatIntegrateWorld(b.q, angular.x, angular.y, angular.z, dt);

        const now = performance.now();
        const floorHit = diceResolvePlaneContact(
          b,
          {{ x: 0, y: 1, z: 0 }},
          this.planeY,
          b.restitution,
          b.friction,
          Math.abs(this.gravity) * b.mass * dt
        );
        diceResolvePlaneContact(
          b,
          {{ x: 1, y: 0, z: 0 }},
          this.bounds.minX,
          b.restitution * 0.82,
          b.friction,
          0
        );
        diceResolvePlaneContact(
          b,
          {{ x: -1, y: 0, z: 0 }},
          -this.bounds.maxX,
          b.restitution * 0.82,
          b.friction,
          0
        );
        diceResolvePlaneContact(
          b,
          {{ x: 0, y: 0, z: 1 }},
          this.bounds.minZ,
          b.restitution * 0.82,
          b.friction,
          0
        );
        diceResolvePlaneContact(
          b,
          {{ x: 0, y: 0, z: -1 }},
          -this.bounds.maxZ,
          b.restitution * 0.82,
          b.friction,
          0
        );

        if (floorHit && floorHit.impactSpeed > 70 && now - b.lastBounceAt > 75) {{
          b.lastBounceAt = now;
          if (b.onBounce) b.onBounce(floorHit.impactSpeed);
        }}

        const horizontalSpeed = Math.hypot(b.vx, b.vz);
        const angularSpeed = Math.hypot(angular.x, angular.y, angular.z);
        let faceState = b.shape === "coin"
          ? coinFaceUpFromQuaternion(b.q)
          : diceFaceUpFromQuaternion(b.q);
        let floorContact = diceFloorContact(b);
        let supportY = floorContact.minY;
        // Keep the contact tolerance sub-pixel.  A broad 0.45px band could
        // classify a corner hovering just above the plane as grounded, then
        // apply damping before gravity had actually made contact.
        // A cylinder's curved rim needs a slightly wider persistent-contact
        // band than a cube corner, otherwise it repeatedly drops a fraction
        // of a pixel and re-bounces instead of dissipating its last spin.
        const floorTolerance = b.shape === "coin" ? 0.45 : 0.10;
        const touchingFloor = Boolean(floorHit) || Math.abs(supportY) < floorTolerance;
        if (!floorHit && touchingFloor && supportY >= 0 && b.vy <= 0) {{
          // Persistent resting-contact constraint: consume the sub-pixel gap
          // instead of letting gravity create an endless drop/impact cycle.
          // This translates the centre to the plane and clears only vertical
          // velocity; orientation and the eventual face remain untouched.
          b.y -= supportY;
          b.vy = 0;
        }}
        const targetLocalNormal = b.shape === "box"
          ? diceLocalNormalForFace(b.targetFace)
          : (b.targetCoinSide
            ? {{ x: 0, y: 0, z: b.targetCoinSide === "正面" ? 1 : -1 }}
            : null);
        const targetNormal = targetLocalNormal
          ? diceRotateVector(b.q, targetLocalNormal)
          : null;
        const targetAlignment = targetNormal ? targetNormal.y : null;
        if (targetNormal && touchingFloor && Math.abs(b.vy) < 90 &&
            horizontalSpeed < 260 && angularSpeed < 7.0) {{
          // The event result is allowed to influence only the final, already
          // supported part of the landing. This is a bounded torque, not a
          // quaternion snap: gravity, contact correction, friction and the
          // visible face geometry still determine the actual pose.
          let targetTorque = diceCross(targetNormal, {{ x: 0, y: 1, z: 0 }});
          let targetTorqueLength = Math.hypot(targetTorque.x, targetTorque.y, targetTorque.z);
          if (targetTorqueLength < 0.05 && targetAlignment < 0) {{
            // A face pointing exactly down is the one singular case where
            // cross(targetNormal, up) has no direction. Pick a stable axis so
            // the body can leave that unstable upside-down pose.
            const seed = b.shape === "coin"
              ? 1
              : (Number(b.targetFace) % 2 === 0 ? -1 : 1);
            targetTorque = {{ x: 0, y: 0, z: seed }};
            targetTorqueLength = 1;
          }}
          if (targetTorqueLength > 0.05) {{
            const targetForceArm = b.shape === "coin"
              ? b.radius * 0.42
              : b.halfExtent * 1.05;
            const approach = Math.max(0.22, Math.min(1.0, (0.94 - targetAlignment) / 1.35));
            const targetForce = Math.abs(this.gravity) * b.mass * targetForceArm * approach;
            const targetResponse = physicsApplyInvInertia(b, {{
              x: targetTorque.x * targetForce,
              y: targetTorque.y * targetForce,
              z: targetTorque.z * targetForce
            }});
            angular.x += targetResponse.x * dt;
            angular.y += targetResponse.y * dt;
            angular.z += targetResponse.z * dt;
          }}
        }}
        if (touchingFloor && (floorHit || supportY <= floorTolerance)) {{
          // 桌面不是把物體「吸」到某個角度；它提供向上的接觸力，
          // 接觸點偏離重心時自然產生回正力矩，讓傾斜骰子／硬幣滾到
          // 真正穩定的面；硬幣靠邊時仍受接觸力矩影響，只有幾乎精確
          // 平衡在邊緣才會保留 ?，不把普通斜靠誤當成第三面。
          if (b.shape === "box" || b.shape === "coin") {{
            const support = floorContact.point;
            const lever = {{ x: support.x - b.x, y: support.y - b.y, z: support.z - b.z }};
            const normalForce = {{ x: 0, y: -this.gravity * b.mass, z: 0 }};
            const restoringTorque = diceCross(lever, normalForce);
            const response = physicsApplyInvInertia(b, restoringTorque);
            const torqueScale = b.shape === "coin" ? 0.72 : 0.92;
            angular.x += response.x * torqueScale * dt;
            angular.y += response.y * torqueScale * dt;
            angular.z += response.z * torqueScale * dt;
            if (b.shape === "coin") {{
              // A thin cylinder can lose its single rim contact before the
              // normal-force torque has visibly rotated it.  This is the
              // equivalent of the broad tabletop contact patch: a gentle
              // gravity-aligned spring, based only on the current normal,
              // never on the requested/event result.
              const headsNormal = diceRotateVector(b.q, {{ x: 0, y: 0, z: 1 }});
              const desiredNormal = {{ x: 0, y: headsNormal.y >= 0 ? 1 : -1, z: 0 }};
              const alignmentTorque = diceCross(headsNormal, desiredNormal);
              const alignmentForce = Math.abs(this.gravity) * b.mass * b.radius * 0.42;
              const alignmentResponse = physicsApplyInvInertia(b, {{
                x: alignmentTorque.x * alignmentForce,
                y: alignmentTorque.y * alignmentForce,
                z: alignmentTorque.z * alignmentForce
              }});
              angular.x += alignmentResponse.x * dt;
              angular.y += alignmentResponse.y * dt;
              angular.z += alignmentResponse.z * dt;
            }}
          }}
        }}
        if (!floorHit && b.supportContact && b.shape === "box") {{
          // 骰子落在另一顆骰子上時，接觸面的向上反作用力同樣會在
          // 偏離重心的位置產生回正力矩；否則骰子可能停在半空堆疊，
          // 永遠進不了 settled 狀態。
          const support = b.supportContact.point;
          const lever = {{ x: support.x - b.x, y: support.y - b.y, z: support.z - b.z }};
          const normalForce = {{ x: 0, y: -this.gravity * b.mass, z: 0 }};
          const restoringTorque = diceCross(lever, normalForce);
          const response = physicsApplyInvInertia(b, restoringTorque);
          angular.x += response.x * 0.72 * dt;
          angular.y += response.y * 0.72 * dt;
          angular.z += response.z * 0.72 * dt;
        }}
        // 硬幣不能像方骰一樣在大角度斜靠時進入尾段煞車；
        // 先要求它接近平躺，才能避免「還沒翻平就被煞停」。
        const restAlignment = b.shape === "coin" ? 0.985 : 0.86;
        const settleAlignment = b.shape === "coin" ? 0.995 : 0.965;
        // 判斷「有沒有安靜地躺在某一面」先看接觸、水平滑動、角速度
        // 與頂面法線；事件目標只會在低能量接觸尾段透過阻尼收斂，
        // 不在空中改寫投擲，也不在結算瞬間硬擺角度。
        // A coin that is merely leaning on its rim is still unstable.  Keep
        // the third-face result only for an almost exact edge balance; the
        // normal tilted cases must continue to tip until heads or tails is
        // actually supported by the tabletop.
        const edgeRest = b.shape === "coin" && faceState.edge && faceState.alignment < 0.06;
        const supportedBySurface = touchingFloor || Boolean(b.supportContact);
        if (supportedBySurface && horizontalSpeed < 28 && angularSpeed < 1.4 && (faceState.alignment > restAlignment || edgeRest)) {{
          b.restTime += dt;
        }} else {{
          b.restTime = 0;
        }}

        // Rounded physical dice do not remain perfectly wedged between sharp
        // mathematical corners.  If a low-energy die is suspended above the
        // table without a near-horizontal support manifold, model that small
        // geometric imperfection as a downhill rolling impulse.  Its direction
        // comes only from the current quaternion; it neither selects a face nor
        // edits the quaternion, and normal face-on-face stacks are untouched.
        const unstableSuspendedGeometry = !touchingFloor && floorContact.minY > 0.5 &&
          faceState.alignment < settleAlignment;
        if (unstableSuspendedGeometry) {{
          b.unstableContactTime += dt;
        }} else {{
          b.unstableContactTime = 0;
        }}
        if (b.shape === "box" && b.unstableContactTime > 0.22 && faceState.normal &&
            Math.abs(b.vy) < 50 && angularSpeed < 1.2) {{
          // Pick the least obstructed horizontal downhill path around nearby
          // dice.  This approximates a rounded corner deflecting out of a
          // multi-die pinch instead of repeatedly resolving into both boxes.
          let escapeX = -faceState.normal.x;
          let escapeZ = -faceState.normal.z;
          let bestClearance = -Infinity;
          for (let directionIndex = 0; directionIndex < 8; directionIndex++) {{
            const angle = directionIndex * Math.PI / 4;
            const candidateX = Math.cos(angle);
            const candidateZ = Math.sin(angle);
            let clearance = Infinity;
            for (const other of this.bodies) {{
              if (other === b) continue;
              clearance = Math.min(clearance, Math.hypot(
                b.x + candidateX * 54 - other.x,
                b.z + candidateZ * 54 - other.z
              ));
            }}
            if (clearance > bestClearance) {{
              bestClearance = clearance;
              escapeX = candidateX;
              escapeZ = candidateZ;
            }}
          }}
          const escapeLength = Math.hypot(escapeX, escapeZ);
          if (escapeLength > 1e-5) {{
            escapeX /= escapeLength;
            escapeZ /= escapeLength;
            b.vx += escapeX * 600 * dt;
            b.vz += escapeZ * 600 * dt;
            angular.x += escapeZ * 12 * dt;
            angular.z -= escapeX * 12 * dt;
          }}
        }}

        if (touchingFloor) {{
          // 真正的桌面接觸會有滾動阻力；越接近平面，耗能越明顯，
          // 但不改變姿態，讓最後面向仍然由碰撞結果自然決定。
          // Do not overdamp an edge/corner contact.  That creates a false
          // static equilibrium where gravity torque and damping cancel while
          // the body is visibly tilted.  Strong braking starts only once a
          // broad face is already close to the tabletop.
          const isCoin = b.shape === "coin";
          const brakeStart = isCoin ? 0.60 : 0.86;
          const contactLevel = Math.max(0, Math.min(1,
            (faceState.alignment - brakeStart) / Math.max(0.001, 1 - brakeStart)
          ));
          const surfaceBrake = isCoin
            ? 0.92 - contactLevel * 0.14
            : 0.975 - contactLevel * 0.195;
          const contactSpinBrake = isCoin
            ? 0.94 - contactLevel * 0.16
            : 0.992 - contactLevel * 0.212;
          b.vx *= Math.pow(surfaceBrake, dt * 60);
          b.vz *= Math.pow(surfaceBrake, dt * 60);
          angular.x *= Math.pow(contactSpinBrake, dt * 60);
          angular.y *= Math.pow(contactSpinBrake, dt * 60);
          angular.z *= Math.pow(contactSpinBrake, dt * 60);
        }}
        if (b.supportContact && !touchingFloor) {{
          const broadSupport = faceState.alignment > settleAlignment;
          const supportLinearBrake = broadSupport ? 0.88 : 0.97;
          const supportSpinBrake = broadSupport ? 0.90 : 0.992;
          b.vx *= Math.pow(supportLinearBrake, dt * 60);
          b.vz *= Math.pow(supportLinearBrake, dt * 60);
          angular.x *= Math.pow(supportSpinBrake, dt * 60);
          angular.y *= Math.pow(supportSpinBrake, dt * 60);
          angular.z *= Math.pow(supportSpinBrake, dt * 60);
        }}

        if (b.restTime > 0.18) {{
          // 接觸面的動摩擦在 solver 中逐步消耗平移與角動能；這裡只
          // 加強已經接近靜止的尾段煞車，完全不改變骰子的姿態。
          const groundBrake = Math.pow(0.62, dt * 60);
          const spinBrake = Math.pow(0.56, dt * 60);
          b.vx *= groundBrake;
          b.vz *= groundBrake;
          angular.x *= spinBrake;
          angular.y *= spinBrake;
          angular.z *= spinBrake;
        }}

        if (targetLocalNormal && (touchingFloor || Boolean(b.supportContact)) &&
            Math.abs(b.vy) < 42 && Math.hypot(b.vx, b.vz) < 34 &&
            Math.hypot(angular.x, angular.y, angular.z) < 1.8 &&
            targetAlignment < settleAlignment) {{
          // Once motion is genuinely low-energy, close the remaining contact
          // error with a critically damped incremental orientation step. It
          // is intentionally gradual (never a last-frame snap), and the
          // support point is re-evaluated immediately so a corrected die
          // remains seated on the same horizontal plane.
          const targetQuaternion = diceQuatAlignLocalNormal(b.q, targetLocalNormal);
          const correctionAmount = 1 - Math.exp(-8.5 * dt);
          b.q = diceQuatSlerp(b.q, targetQuaternion, correctionAmount);
          const correctedContact = diceFloorContact(b);
          if (correctedContact.minY < 0) b.y -= correctedContact.minY;
          b.vy = 0;
          angular.x *= 0.72;
          angular.y *= 0.72;
          angular.z *= 0.72;
          faceState = b.shape === "coin"
            ? coinFaceUpFromQuaternion(b.q)
            : diceFaceUpFromQuaternion(b.q);
          floorContact = correctedContact;
          supportY = correctedContact.minY;
        }}

        const cooledHorizontalSpeed = Math.hypot(b.vx, b.vz);
        const cooledAngularSpeed = Math.hypot(angular.x, angular.y, angular.z);
        let cooledTiltSpeed = cooledAngularSpeed;
        if (b.shape === "coin") {{
          const faceAxis = diceRotateVector(b.q, {{ x: 0, y: 0, z: 1 }});
          const axialSpeed = diceDot(angular, faceAxis);
          cooledTiltSpeed = Math.sqrt(Math.max(0, cooledAngularSpeed * cooledAngularSpeed - axialSpeed * axialSpeed));
        }}
        const edgeSettled = b.shape === "coin" && faceState.edge && faceState.alignment < 0.06;
        const targetSettled = targetNormal
          ? targetAlignment > settleAlignment
          : true;
        const faceSettled = faceState.alignment > settleAlignment && targetSettled;
        const angularSettled = b.shape === "coin"
          ? cooledTiltSpeed < 0.50 && cooledAngularSpeed < 1.0
          : cooledAngularSpeed < 0.50;
        if (b.restTime > (edgeSettled ? 0.52 : 0.30) && cooledHorizontalSpeed < 9 && angularSettled && (faceSettled || edgeSettled)) {{
          // 自然姿態已經達到平面接觸，讀取頂面並進入睡眠；只清零
          // 速度，不改 quaternion，因此不會出現最後硬擺到定位點。
          b.vx = 0;
          b.vy = 0;
          b.vz = 0;
          angular.x = 0;
          angular.y = 0;
          angular.z = 0;
          b.finalFace = faceState.value;
          b.settled = true;
          if (b.onSettle) b.onSettle(faceState.value);
        }}
      }}

      resolveBoxPair(b1, b2) {{
        if (!b1.q || !b2.q) return;
        const dx = b2.x - b1.x;
        const dy = b2.y - b1.y;
        const dz = b2.z - b1.z;
        const distSq = dx * dx + dy * dy + dz * dz;
        const broadRadius = (b1.boundingRadius || b1.radius) + (b2.boundingRadius || b2.radius);
        if (distSq >= broadRadius * broadRadius) return;

        const contact = diceBoxBoxContact(b1, b2);
        if (!contact) return;
        const normal = contact.normal;
        let pointA = diceSupportPoint(b1, normal);
        let pointB = diceSupportPoint(b2, {{
          x: -normal.x,
          y: -normal.y,
          z: -normal.z
        }});
        const penetration = contact.penetration;

        const sleepingA = Boolean(b1.settled);
        const sleepingB = Boolean(b2.settled);
        // 兩顆都已停穩時不再修正近似 OBB 的微小重疊，否則每個
        // fixed step 都會把它們推開，畫面就會出現落地後的抖動。
        if (sleepingA && sleepingB) return;
        const invMassA = sleepingA ? 0 : 1 / Math.max(0.001, b1.mass);
        const invMassB = sleepingB ? 0 : 1 / Math.max(0.001, b2.mass);
        const invMassSum = invMassA + invMassB;
        if (invMassSum <= 0) return;
        const correction = penetration * 0.82 / invMassSum;
        b1.x -= normal.x * correction * invMassA;
        b1.y -= normal.y * correction * invMassA;
        b1.z -= normal.z * correction * invMassA;
        b2.x += normal.x * correction * invMassB;
        b2.y += normal.y * correction * invMassB;
        b2.z += normal.z * correction * invMassB;

        pointA = diceSupportPoint(b1, normal);
        pointB = diceSupportPoint(b2, {{
          x: -normal.x,
          y: -normal.y,
          z: -normal.z
        }});
        const contactPoint = {{
          x: (pointA.x + pointB.x) * 0.5,
          y: (pointA.y + pointB.y) * 0.5,
          z: (pointA.z + pointB.z) * 0.5
        }};
        // Only a nearly upward manifold is structural support.  Treating a
        // steep edge/side contact as a shelf lets friction hold the upper die
        // at an implausible angle instead of letting it slide to the table.
        if (normal.y > 0.97 && !b2.settled) {{
          if (!b2.supportContact || normal.y > b2.supportContact.normalY) {{
            // For a die supported from below, the useful torque arm is the
            // lowest contact patch on that die.  The old midpoint between two
            // OBB support corners could pass almost through its centre and
            // leave a tilted upper die balanced forever.  Reuse the same
            // averaged bottom patch as the tabletop solver; only its height
            // comes from the die/die contact manifold.
            const supportedPatch = diceFloorContact(b2).point;
            b2.supportContact = {{
              point: {{ x: supportedPatch.x, y: contactPoint.y, z: supportedPatch.z }},
              normalY: normal.y
            }};
          }}
        }} else if (normal.y < -0.97 && !b1.settled) {{
          if (!b1.supportContact || -normal.y > b1.supportContact.normalY) {{
            const supportedPatch = diceFloorContact(b1).point;
            b1.supportContact = {{
              point: {{ x: supportedPatch.x, y: contactPoint.y, z: supportedPatch.z }},
              normalY: -normal.y
            }};
          }}
        }}
        const va = diceVelocityAtPoint(b1, contactPoint);
        const vb = diceVelocityAtPoint(b2, contactPoint);
        const relative = {{ x: vb.x - va.x, y: vb.y - va.y, z: vb.z - va.z }};
        const velocityAlongNormal = diceDot(relative, normal);
        if (velocityAlongNormal >= 0) return;

        // 已停穩的骰子只會被明顯撞擊喚醒；一般的接觸修正把它當成
        // 靜態物體，讓另一顆骰子自己吸收剩餘速度。
        const impactSpeed = -velocityAlongNormal;
        const wakeSleepingBody = impactSpeed > 85;
        if (sleepingA && wakeSleepingBody) b1.settled = false;
        if (sleepingB && wakeSleepingBody) b2.settled = false;
        const activeInvMassA = b1.settled ? 0 : 1 / Math.max(0.001, b1.mass);
        const activeInvMassB = b2.settled ? 0 : 1 / Math.max(0.001, b2.mass);
        if (activeInvMassA + activeInvMassB <= 0) return;

        const ra = {{
          x: contactPoint.x - b1.x,
          y: contactPoint.y - b1.y,
          z: contactPoint.z - b1.z
        }};
        const rb = {{
          x: contactPoint.x - b2.x,
          y: contactPoint.y - b2.y,
          z: contactPoint.z - b2.z
        }};
        const denominator =
          diceImpulseDenominator(b1, ra, normal) +
          diceImpulseDenominator(b2, rb, normal);
        const pairRestitution = impactSpeed < 48 ? 0 : Math.min(b1.restitution, b2.restitution);
        const impulseMagnitude =
          -(1 + pairRestitution) *
          velocityAlongNormal / denominator;
        const normalImpulse = {{
          x: normal.x * impulseMagnitude,
          y: normal.y * impulseMagnitude,
          z: normal.z * impulseMagnitude
        }};
        diceApplyImpulse(b1, {{
          x: -normalImpulse.x,
          y: -normalImpulse.y,
          z: -normalImpulse.z
        }}, contactPoint);
        diceApplyImpulse(b2, normalImpulse, contactPoint);
        const postA = diceVelocityAtPoint(b1, contactPoint);
        const postB = diceVelocityAtPoint(b2, contactPoint);
        const postRelative = {{
          x: postB.x - postA.x,
          y: postB.y - postA.y,
          z: postB.z - postA.z
        }};
        const normalVelocity = diceDot(postRelative, normal);
        const tangentVelocity = {{
          x: postRelative.x - normal.x * normalVelocity,
          y: postRelative.y - normal.y * normalVelocity,
          z: postRelative.z - normal.z * normalVelocity
        }};
        const tangentSpeed = Math.hypot(tangentVelocity.x, tangentVelocity.y, tangentVelocity.z);
        if (tangentSpeed > 0.01) {{
          const tangent = {{
            x: tangentVelocity.x / tangentSpeed,
            y: tangentVelocity.y / tangentSpeed,
            z: tangentVelocity.z / tangentSpeed
          }};
          const tangentDenominator =
            diceImpulseDenominator(b1, ra, tangent) +
            diceImpulseDenominator(b2, rb, tangent);
          const requested = -tangentSpeed / tangentDenominator;
          const supportSlope = Math.abs(normal.y);
          const pairFriction = supportSlope > 0.97 ? Math.min(b1.friction, b2.friction) : 0;
          const maxFriction = impulseMagnitude * pairFriction;
          const tangentMagnitude = Math.max(-maxFriction, Math.min(maxFriction, requested));
          const tangentImpulse = {{
            x: tangent.x * tangentMagnitude,
            y: tangent.y * tangentMagnitude,
            z: tangent.z * tangentMagnitude
          }};
          diceApplyImpulse(b1, {{
            x: -tangentImpulse.x,
            y: -tangentImpulse.y,
            z: -tangentImpulse.z
          }}, contactPoint);
          diceApplyImpulse(b2, tangentImpulse, contactPoint);
        }}

        if (Math.abs(velocityAlongNormal) > 45) {{
          sound.playFile("/assets/sound/casino/chips-collide-1.ogg", () => sound.playWoodClack(0.7));
        }}
      }}

      step(dt) {{
        // Pair contacts discovered in the previous fixed step are consumed
        // while integrating the bodies below.  They are cleared only after
        // that integration, before this step's pair solver writes fresh
        // contacts; clearing them here would make support never reach the
        // body that needs the restoring torque.
        for (let i = 0; i < this.bodies.length; i++) {{
          const b = this.bodies[i];
          if (b.settled) continue;
          if (b.shape === "box" || b.shape === "coin") {{
            this.stepBoxBody(b, dt);
            continue;
          }}

          b.vy += this.gravity * dt;
          b.vx *= Math.pow(b.airDrag, dt * 60);
          b.vy *= Math.pow(b.airDrag, dt * 60);
          b.vz *= Math.pow(b.airDrag, dt * 60);
          b.wx *= Math.pow(b.rotDamping, dt * 60);
          b.wy *= Math.pow(b.rotDamping, dt * 60);
          b.wz *= Math.pow(b.rotDamping, dt * 60);

          b.x += b.vx * dt;
          b.y += b.vy * dt;
          b.z += b.vz * dt;
          b.rx += b.wx * dt;
          b.ry += b.wy * dt;
          b.rz += b.wz * dt;

          if (b.y <= this.planeY) {{
            b.y = this.planeY;
            const impactSpeed = Math.abs(b.vy);
            if (impactSpeed > 45) {{
              b.vy = -b.vy * b.restitution;
              b.vx *= b.friction;
              b.vz *= b.friction;

              const kick = Math.min(1600, impactSpeed * 2.8);
              b.wx = b.wx * 0.45 + (Math.random() - 0.5) * kick;
              b.wy = b.wy * 0.55 + (Math.random() - 0.5) * kick * 0.7;
              b.wz = b.wz * 0.45 + (Math.random() - 0.5) * kick;

              if (b.onBounce) b.onBounce(impactSpeed);
            }} else {{
              b.vy = 0;
              const grip = Math.max(0.58, Math.min(0.94, b.surfaceFriction));
              const linearDamp = Math.pow(1 - grip * 0.10, dt * 60);
              const angularDamp = Math.pow(1 - grip * 0.14, dt * 60);
              b.vx *= linearDamp;
              b.vz *= linearDamp;
              b.wx *= angularDamp;
              b.wy *= angularDamp;
              b.wz *= angularDamp;

              // 地面滾動阻力把水平速度逐步轉成角速度，避免骰子像滑鼠游標一樣平移停住。
              b.wx += b.vz * grip * 0.012 * dt;
              b.wz -= b.vx * grip * 0.012 * dt;

              const vSq = b.vx * b.vx + b.vz * b.vz;
              const wSq = b.wx * b.wx + b.wy * b.wy + b.wz * b.wz;
              if (vSq < 50 && wSq < 500) {{
                // Legacy spherical bodies may still be used by non-throwing
                // callers.  They can sleep on low velocity, but never rotate
                // toward an event-provided result during settlement.
                if (vSq < 8 && wSq < 80) b.settled = true;
              }}
            }}
          }}

          if (b.x < this.bounds.minX) {{
            b.x = this.bounds.minX;
            b.vx = -b.vx * 0.65;
            b.wz += (Math.random() - 0.5) * 500;
            if (b.onWallHit) b.onWallHit();
          }} else if (b.x > this.bounds.maxX) {{
            b.x = this.bounds.maxX;
            b.vx = -b.vx * 0.65;
            b.wz += (Math.random() - 0.5) * 500;
            if (b.onWallHit) b.onWallHit();
          }}

          if (b.z < this.bounds.minZ) {{
            b.z = this.bounds.minZ;
            b.vz = -b.vz * 0.65;
            b.wx += (Math.random() - 0.5) * 500;
            if (b.onWallHit) b.onWallHit();
          }} else if (b.z > this.bounds.maxZ) {{
            b.z = this.bounds.maxZ;
            b.vz = -b.vz * 0.65;
            b.wx += (Math.random() - 0.5) * 500;
            if (b.onWallHit) b.onWallHit();
          }}
        }}

        for (const body of this.bodies) body.supportContact = null;
        for (let i = 0; i < this.bodies.length; i++) {{
          for (let j = i + 1; j < this.bodies.length; j++) {{
            const b1 = this.bodies[i];
            const b2 = this.bodies[j];
            if (b1.shape === "box" && b2.shape === "box") {{
              this.resolveBoxPair(b1, b2);
              continue;
            }}
            const dx = b2.x - b1.x;
            const dy = b2.y - b1.y;
            const dz = b2.z - b1.z;
            const distSq = dx * dx + dy * dy + dz * dz;
            const minDist = (b1.boundingRadius || b1.radius) + (b2.boundingRadius || b2.radius);

            if (distSq < minDist * minDist && distSq > 0.001) {{
              const dist = Math.sqrt(distSq);
              const nx = dx / dist;
              const ny = dy / dist;
              const nz = dz / dist;

              const overlap = (minDist - dist) * 0.5;
              b1.x -= nx * overlap;
              b1.y -= ny * overlap;
              b1.z -= nz * overlap;
              b2.x += nx * overlap;
              b2.y += ny * overlap;
              b2.z += nz * overlap;

              const rvx = b2.vx - b1.vx;
              const rvy = b2.vy - b1.vy;
              const rvz = b2.vz - b1.vz;
              const velAlongNormal = rvx * nx + rvy * ny + rvz * nz;

              if (velAlongNormal < 0) {{
                const rest = Math.min(b1.restitution, b2.restitution);
                const invMass1 = 1 / Math.max(0.001, b1.mass);
                const invMass2 = 1 / Math.max(0.001, b2.mass);
                const invMassSum = invMass1 + invMass2;
                const impulse = -(1 + rest) * velAlongNormal / invMassSum;

                b1.vx -= impulse * nx * invMass1;
                b1.vy -= impulse * ny * invMass1;
                b1.vz -= impulse * nz * invMass1;
                b2.vx += impulse * nx * invMass2;
                b2.vy += impulse * ny * invMass2;
                b2.vz += impulse * nz * invMass2;

                // 庫倫式切向摩擦：碰撞不只交換法向速度，也會消耗擦過彼此的速度。
                let tx = -nz;
                let ty = 0;
                let tz = nx;
                const tangentLen = Math.hypot(tx, ty, tz);
                if (tangentLen < 0.0001) {{
                  tx = 1;
                  ty = 0;
                  tz = 0;
                }} else {{
                  tx /= tangentLen;
                  ty /= tangentLen;
                  tz /= tangentLen;
                }}
                const tangentVelocity = rvx * tx + rvy * ty + rvz * tz;
                const frictionImpulse = Math.max(
                  -impulse * 0.72,
                  Math.min(impulse * 0.72, -tangentVelocity / invMassSum)
                );
                b1.vx -= frictionImpulse * tx * invMass1;
                b1.vy -= frictionImpulse * ty * invMass1;
                b1.vz -= frictionImpulse * tz * invMass1;
                b2.vx += frictionImpulse * tx * invMass2;
                b2.vy += frictionImpulse * ty * invMass2;
                b2.vz += frictionImpulse * tz * invMass2;

                b1.wx += frictionImpulse * tz * 0.9;
                b1.wz -= frictionImpulse * tx * 0.9;
                b2.wx -= frictionImpulse * tz * 0.9;
                b2.wz += frictionImpulse * tx * 0.9;

                if (Math.abs(velAlongNormal) > 40) {{
                  sound.playFile("/assets/sound/casino/chips-collide-1.ogg", () => sound.playWoodClack(0.7));
                }}
              }}
            }}
          }}
        }}
        // Sequential impulse solvers need more than one pass for a three-body
        // contact graph.  Two quiet correction passes prevent the last pair
        // from undoing the first pair's separation and leaving a die pinched
        // between neighbours until the watchdog.  Single dice/coin paths pay
        // no extra work.
        for (let solverPass = 0; solverPass < 2; solverPass++) {{
          for (let i = 0; i < this.bodies.length; i++) {{
            for (let j = i + 1; j < this.bodies.length; j++) {{
              const b1 = this.bodies[i];
              const b2 = this.bodies[j];
              if (b1.shape === "box" && b2.shape === "box") this.resolveBoxPair(b1, b2);
            }}
          }}
        }}
      }}

      render() {{
        const deg2rad = Math.PI / 180;
        const scaleFactor = 0.052;
        const hasWebGL = Boolean(this.webglEngine && this.webglEngine.isSupported);
        const planeY = this.planeY;

        for (let i = 0; i < this.bodies.length; i++) {{
          const b = this.bodies[i];
          const isOrientedBody = (b.shape === "box" || b.shape === "coin") && b.q;
          const bodyEuler = isOrientedBody ? diceQuatToEulerXYZ(b.q) : null;
          if (b.threeMesh) {{
            const halfSize = b.threeMesh.userData && b.threeMesh.userData.halfSize
              ? b.threeMesh.userData.halfSize
              : ((b.threeMesh.geometry && b.threeMesh.geometry.parameters) ? (b.threeMesh.geometry.parameters.height / 2) : 1.4);
            const planeRenderY = this.webglEngine
              ? this.webglEngine.planeY * scaleFactor
              : 0;
            const bodyY = (b.y - planeY) * scaleFactor + planeRenderY;
            // The solver's support point, not the axis-aligned half-size, is
            // the source of truth for contact. Clamping a tilted die's
            // centre to halfSize lifts a legitimate corner/edge contact and
            // makes the die visibly hover before it settles.
            b.threeMesh.position.set(b.x * scaleFactor, bodyY, b.z * scaleFactor);
            if (isOrientedBody) {{
              b.threeMesh.quaternion.set(b.q.x, b.q.y, b.q.z, b.q.w);
            }} else {{
              b.threeMesh.rotation.set(-b.rx * deg2rad, b.ry * deg2rad, b.rz * deg2rad);
            }}
          }}
          if (b.element) {{
            if (isOrientedBody) {{
              const cameraSin = Math.sin(64 * DICE_DEG2RAD);
              const cameraCos = Math.cos(64 * DICE_DEG2RAD);
              const height = b.y - planeY;
              const cssY = -cameraSin * height + cameraCos * b.z;
              const cssZ = cameraCos * height + cameraSin * b.z;
              b.element.style.transform = `translate3d(${{b.x}}px, ${{cssY}}px, ${{cssZ}}px) ${{diceQuatToCssMatrix3d(b.q)}}`;
            }} else {{
              b.element.style.transform = `translate3d(${{b.x}}px, ${{-(b.y - planeY)}}px, ${{b.z}}px) rotateX(${{b.rx}}deg) rotateY(${{b.ry}}deg) rotateZ(${{b.rz}}deg)`;
            }}
          }}
          if (b.shadowElement) {{
            const heightAbovePlane = Math.max(0, b.y - planeY);
            const scale = Math.max(0.2, 1 - heightAbovePlane / 420);
            const op = Math.max(0.04, b.shadowOpacity - heightAbovePlane / 360);
            const cameraSin = Math.sin(64 * DICE_DEG2RAD);
            const cameraCos = Math.cos(64 * DICE_DEG2RAD);
            b.shadowElement.style.transform = `translate3d(${{b.x}}px, ${{cameraCos * b.z}}px, ${{cameraSin * b.z}}px) scale(${{scale}})`;
            b.shadowElement.style.opacity = op;
          }}
        }}

        if (hasWebGL) {{
          this.webglEngine.render();
        }}
      }}
    }}

    function create3DDieDOM(size = 68) {{
      const wrap = document.createElement("div");
      wrap.className = "die-wrapper";
      wrap.style.width = `${{size}}px`;
      wrap.style.height = `${{size}}px`;
      wrap.style.transformOrigin = `${{size / 2}}px ${{size / 2}}px 0px`;

      const shadow = document.createElement("div");
      shadow.className = "die-shadow";
      shadow.style.width = `${{size + 8}}px`;
      shadow.style.height = `${{Math.round(size * 0.45)}}px`;

      const cube = document.createElement("div");
      cube.className = "die-cube";
      cube.style.width = `${{size}}px`;
      cube.style.height = `${{size}}px`;

      const half = size / 2;
      const makeFace = (num, cls, pipsHtml, transformStyle) => {{
        const f = document.createElement("div");
        f.className = `die-face face-${{num}} ${{cls}}`;
        f.style.width = `${{size}}px`;
        f.style.height = `${{size}}px`;
        f.style.transform = transformStyle;
        f.innerHTML = pipsHtml;
        return f;
      }};

      cube.appendChild(makeFace(1, "face-layout-1", '<div class="pip pip-red pip-center-big"></div>', `rotateY(0deg) translateZ(${{half}}px)`));
      cube.appendChild(makeFace(6, "face-layout-6", '<div class="pip"></div><div class="pip"></div><div class="pip"></div><div class="pip"></div><div class="pip"></div><div class="pip"></div>', `rotateY(180deg) translateZ(${{half}}px)`));
      cube.appendChild(makeFace(2, "face-layout-2", '<div class="pip"></div><div class="pip"></div>', `rotateX(90deg) translateZ(${{half}}px)`));
      cube.appendChild(makeFace(5, "face-layout-5", '<div class="pip"></div><div class="pip"></div><div class="pip"></div><div class="pip"></div><div class="pip"></div>', `rotateX(-90deg) translateZ(${{half}}px)`));
      cube.appendChild(makeFace(3, "face-layout-3", '<div class="pip"></div><div class="pip"></div><div class="pip"></div>', `rotateY(90deg) translateZ(${{half}}px)`));
      cube.appendChild(makeFace(4, "face-layout-4", '<div class="pip pip-red"></div><div class="pip pip-red"></div><div class="pip pip-red"></div><div class="pip pip-red"></div>', `rotateY(-90deg) translateZ(${{half}}px)`));

      wrap.appendChild(cube);
      return {{ wrap, shadow, cube }};
    }}

    // 6. 3D 物理擲硬幣 (solid cylinder + shared horizontal plane)
    function playCoinAnimation(data) {{
      if (MODE !== "all" && MODE !== "coin") return;
      hideAllStages();

      const stage = document.getElementById("coin-stage");
      const arena = document.getElementById("coin-physics-arena");
      const disc = document.getElementById("coin-3d-disc");
      const shadow = document.getElementById("coin-shadow");
      const bubble = document.getElementById("coin-bubble");
      const requestedSide = normalizeCoinSide(data);

      bubble.innerText = `@${{data.user_name || "觀眾"}} 拋出硬幣，等待硬幣自然落桌……`;

      stage.classList.add("active");
      sound.playRatchet();

      let webglEngine = null;
      const canvasEl = document.getElementById("coin-webgl-canvas");
      if (window.THREE && canvasEl) {{
        if (!window.__coinWebGL) {{
          window.__coinWebGL = new WebGLDiceEngine(
            "coin-webgl-canvas",
            THROW_PLANE_CONFIG.canvasWidth,
            THROW_PLANE_CONFIG.canvasHeight,
            THROW_PLANE_CONFIG.cameraPosition
          );
        }}
        webglEngine = window.__coinWebGL;
        if (webglEngine.isSupported) {{
          webglEngine.clearDice();
          canvasEl.style.display = "block";
          if (arena) arena.classList.add("uses-webgl");
        }}
      }} else if (arena) {{
        arena.classList.remove("uses-webgl");
      }}

      if (coinPhysicsWorld) coinPhysicsWorld.stop();
      coinPhysicsWorld = new StreamPhysicsWorld(arena, webglEngine, DICE_REFERENCE_DEFAULTS);
      coinPhysicsWorld.bounds = {{ minX: -190, maxX: 190, minZ: -90, maxZ: 90 }};

      let bouncePlayed = false;
      let coinMesh = null;
      if (webglEngine && webglEngine.isSupported) {{
        try {{
          coinMesh = webglEngine.createCoinMesh(3.02, 0.36);
        }} catch (e) {{
          console.warn("WebGL createCoinMesh error:", e);
        }}
      }}
      const body = new RigidBody3D({{
        element: disc,
        shadowElement: shadow,
        threeMesh: coinMesh,
        shape: "coin",
        radius: 58,
        halfThickness: 7,
        mass: 1.0,
        restitution: 0.42,
        friction: 0.84,
        surfaceFriction: 0.90,
        airDrag: 0.997,
        rotDamping: 0.987,
        x: -38,
        // Keep the full first toss inside the shared camera frustum.  At 250px
        // the coin entered above the viewport in both WebGL and CSS fallback,
        // making the opening frame look like a clipped asset instead of a toss.
        y: 115,
        z: -20,
        vx: 118 + Math.random() * 58,
        vy: 36 + Math.random() * 38,
        vz: 34 + (Math.random() - 0.5) * 34,
        rx: 18 + Math.random() * 34,
        ry: Math.random() * 360,
        rz: 12 + Math.random() * 30,
        wx: 1100 + Math.random() * 560,
        wy: (Math.random() - 0.5) * 900,
        wz: 700 + Math.random() * 500,
        targetCoinSide: requestedSide,
        shadowOpacity: 0.82,
        onBounce: (impactSpeed) => {{
          if (!bouncePlayed) bouncePlayed = true;
          sound.playFile("/assets/sound/casino/chips-collide-1.ogg", () => sound.playWoodClack(Math.min(1.0, impactSpeed / 420)));
        }}
      }});
      if (disc) disc.dataset.face = "rolling";
      if (body.threeMesh) {{
        if (disc) disc.style.display = "none";
        if (shadow) shadow.style.display = "none";
      }} else {{
        if (disc) disc.style.display = "block";
        if (shadow) shadow.style.display = "block";
      }}

      let resultAnnounced = false;
      body.onSettle = (physicalSide) => {{
        if (resultAnnounced) return;
        resultAnnounced = true;
        const eventSide = requestedSide || physicalSide;
        // The physics pose is guided toward the requested side; use the same
        // resolved side for the CSS fallback so its face artwork cannot drift
        // away from the WebGL mesh or the result bubble.
        if (disc) disc.dataset.face = eventSide;
        bubble.innerText = `@${{data.user_name || "觀眾"}} 拋出了【${{eventSide}}】！`;
        sound.playFile("/assets/sound/casino/chips-collide-1.ogg", () => sound.playCoinShower());
        spawnVFX("gold", 45);
      }};
      coinPhysicsWorld.onSettled = () => safeTimeout(() => hideAllStages(), 2800);
      coinPhysicsWorld.addBody(body);
      coinPhysicsWorld.start();
      // A watchdog may update copy, but it must never erase an unresolved
      // physical result.  The stage is cleared only after onSettled above.
      safeTimeout(() => {{
        if (coinPhysicsWorld && coinPhysicsWorld.isRunning) {{
          bubble.innerText = `@${{data.user_name || "觀眾"}} 硬幣仍在桌面滾動，等待自然停止……`;
        }}
      }}, 9000);
    }}

    // 7. 3D 物理擲骰子 (Dice Roll with Multi-Die 3D Rigid Body Collisions)
    function playDiceAnimation(data) {{
      if (MODE !== "all" && MODE !== "dice") return;
      hideAllStages();

      const stage = document.getElementById("dice-stage");
      const arena = document.getElementById("dice-physics-arena");
      const bubble = document.getElementById("dice-bubble");
      if (arena) arena.querySelectorAll(".die-wrapper, .die-shadow").forEach(el => el.remove());

      let rolls = [];
      if (Array.isArray(data.rolls) && data.rolls.length > 0) {{
        rolls = data.rolls.map(Number);
      }} else if (data.detail && typeof data.detail === "string") {{
        const match = data.detail.match(/\\(([^)]+)\\)/) || data.detail.match(/=\\s*([0-9\\s+]+)/);
        if (match) {{
          const parts = match[1].split("+").map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n));
          if (parts.length > 0) rolls = parts;
        }}
      }}

      const total = Number(data.total || 6);
      const physicsInput = data.physics && typeof data.physics === "object" ? data.physics : {{}};
      const finiteOr = (value, fallback) => Number.isFinite(Number(value)) ? Number(value) : fallback;
      const rangeOr = (value, fallbackMin, fallbackMax) => {{
        if (value && typeof value === "object") {{
          return {{
            min: finiteOr(value.min, fallbackMin),
            max: finiteOr(value.max, fallbackMax)
          }};
        }}
        return {{ min: finiteOr(value, fallbackMin), max: fallbackMax }};
      }};
      const physicsConfig = {{
        ...DICE_REFERENCE_DEFAULTS,
        initialVelocity: finiteOr(physicsInput.initialVelocity, DICE_REFERENCE_DEFAULTS.initialVelocity),
        throwDistance: finiteOr(physicsInput.throwDistance, DICE_REFERENCE_DEFAULTS.throwDistance),
        gravity: finiteOr(physicsInput.gravity, DICE_REFERENCE_DEFAULTS.gravity),
        pullHeight: rangeOr(physicsInput.pullHeight, DICE_REFERENCE_DEFAULTS.pullHeightMin, DICE_REFERENCE_DEFAULTS.pullHeightMax),
        pullTime: rangeOr(physicsInput.pullTime, DICE_REFERENCE_DEFAULTS.pullTimeMin, DICE_REFERENCE_DEFAULTS.pullTimeMax),
        spinDuration: rangeOr(physicsInput.spinDuration, DICE_REFERENCE_DEFAULTS.spinDurationMin, DICE_REFERENCE_DEFAULTS.spinDurationMax),
        moveDuration: rangeOr(physicsInput.moveDuration, DICE_REFERENCE_DEFAULTS.moveDurationMin, DICE_REFERENCE_DEFAULTS.moveDurationMax),
        bounceFrequency: rangeOr(physicsInput.bounceFrequency, DICE_REFERENCE_DEFAULTS.bounceFrequencyMin, DICE_REFERENCE_DEFAULTS.bounceFrequencyMax),
        tiltAngle: rangeOr(physicsInput.tiltAngle, DICE_REFERENCE_DEFAULTS.tiltAngleMin, DICE_REFERENCE_DEFAULTS.tiltAngleMax),
        spinRotation: finiteOr(physicsInput.spinRotation, DICE_REFERENCE_DEFAULTS.spinRotation),
        shadowOpacity: finiteOr(physicsInput.shadowOpacity, DICE_REFERENCE_DEFAULTS.shadowOpacity)
      }};
      if (rolls.length === 0) {{
        if (total <= 6) {{
          rolls = [total];
        }} else if (total <= 12) {{
          const d1 = Math.min(6, Math.max(1, Math.floor(total / 2)));
          const d2 = total - d1;
          rolls = [d1, d2];
        }} else {{
          const d1 = Math.min(6, Math.max(1, Math.floor(total / 3)));
          const d2 = Math.min(6, Math.max(1, Math.floor((total - d1) / 2)));
          const d3 = total - d1 - d2;
          rolls = [d1, d2, d3];
        }}
      }}
      rolls = rolls
        .map(value => Math.round(Number(value)))
        .filter(value => Number.isFinite(value))
        .map(value => Math.max(1, Math.min(6, value)));
      if (rolls.length === 0) rolls = [1];

      stage.classList.add("active");
      bubble.innerText = `@${{data.user_name || "觀眾"}} 正在擲骰，等待骰子自然落地……`;

      let webglEngine = null;
      const canvasEl = document.getElementById("dice-webgl-canvas");
      if (window.THREE && canvasEl) {{
        if (!window.__diceWebGL) {{
            window.__diceWebGL = new WebGLDiceEngine(
              "dice-webgl-canvas",
              THROW_PLANE_CONFIG.canvasWidth,
              THROW_PLANE_CONFIG.canvasHeight,
              THROW_PLANE_CONFIG.cameraPosition
            );
        }}
        webglEngine = window.__diceWebGL;
        if (webglEngine.isSupported) {{
          webglEngine.clearDice();
          canvasEl.style.display = "block";
          if (arena) arena.classList.add("uses-webgl");
        }}
      }} else if (arena) {{
        arena.classList.remove("uses-webgl");
      }}

      if (dicePhysicsWorld) dicePhysicsWorld.stop();
      dicePhysicsWorld = new StreamPhysicsWorld(arena, webglEngine, physicsConfig);
      dicePhysicsWorld.bounds = {{ minX: -190, maxX: 190, minZ: -90, maxZ: 90 }};

      const numDice = rolls.length;
      let physicalFanfarePlayed = false;
      const eventRolls = rolls.slice();
      const eventTotal = Number.isFinite(Number(data.total))
        ? Number(data.total)
        : eventRolls.reduce((sum, value) => sum + value, 0);
      const eventDetail = typeof data.detail === "string" && data.detail.trim()
        ? data.detail.trim()
        : (eventRolls.length === 1
          ? `1d6 = ${{eventRolls[0]}}`
          : `${{eventRolls.length}}d6 (${{eventRolls.join(" + ")}}) = ${{eventTotal}}`);
      const announceSettledResult = (settledRolls = null) => {{
        // The event is the settlement authority.  The rigid bodies still land
        // naturally, but the overlay must never contradict the chat reply or
        // point ledger just because the visual physics took another face.
        const finalRolls = settledRolls || dicePhysicsWorld.bodies.map(body => body.finalFace);
        if (finalRolls.length !== numDice || finalRolls.some(value => !Number.isInteger(value))) return;
        bubble.innerText = `@${{data.user_name || "觀眾"}} 擲出了 ${{eventDetail}}！`;
        if (!physicalFanfarePlayed &&
            (eventTotal === 6 || eventTotal === 12 || eventRolls.every(value => value === eventRolls[0]))) {{
          physicalFanfarePlayed = true;
          sound.playFanfare();
          spawnVFX("gold", 80);
        }}
        safeTimeout(() => hideAllStages(), 2800);
      }};
      dicePhysicsWorld.onSettled = announceSettledResult;
      const direction = String(data.direction || "top").toLowerCase();
      const entryVector = ({{
        top: {{ x: 0, z: -1 }},
        bottom: {{ x: 0, z: 1 }},
        left: {{ x: -1, z: 0 }},
        right: {{ x: 1, z: 0 }}
      }})[direction] || {{ x: 0, z: -1 }};
      rolls.forEach((val, idx) => {{
        const {{ wrap, shadow }} = create3DDieDOM(68);
        if (arena) {{
          arena.appendChild(shadow);
          arena.appendChild(wrap);
        }}

        let mesh = null;
        if (webglEngine && webglEngine.isSupported) {{
          try {{
            mesh = webglEngine.createDieMesh(3.8);
          }} catch (e) {{
            console.warn("WebGL createDieMesh error:", e);
            mesh = null;
          }}
        }}

        if (mesh) {{
          wrap.style.display = "none";
          shadow.style.display = "none";
        }} else {{
          wrap.style.display = "block";
          shadow.style.display = "block";
        }}

        // Spawn on a non-overlapping grid.  Starting three 72px collision
        // boxes only 55px apart created an artificial pile before the throw
        // had even begun, greatly increasing three-body wedges.
        const layoutColumns = Math.min(4, numDice);
        const layoutRows = Math.ceil(numDice / layoutColumns);
        const layoutColumn = idx % layoutColumns;
        const layoutRow = Math.floor(idx / layoutColumns);
        const startX = (layoutColumn - (layoutColumns - 1) / 2) * 78;
        const startZ = (layoutRow - (layoutRows - 1) / 2) * 70;
        // 參考專案的 distance 是舞台像素；WebGL 舞台較小，映射成可見的入場距離，
        // 避免骰子一開始被物理邊界立即彈回。
        const entryDistance = Math.max(70, Math.min(130, physicsConfig.throwDistance * 0.25));
        const spawnX = startX + entryVector.x * entryDistance;
        const spawnZ = startZ + entryVector.z * entryDistance + (Math.random() - 0.5) * 12;
        const moveDuration = physicsConfig.moveDuration.min + Math.random() * Math.max(0, physicsConfig.moveDuration.max - physicsConfig.moveDuration.min);
        const movementScale = Math.max(0.78, Math.min(1.22, 1800 / Math.max(900, moveDuration)));
        const travelSpeed = physicsConfig.initialVelocity * 0.55 * movementScale + Math.random() * physicsConfig.initialVelocity * 0.25;
        const initVx = -entryVector.x * travelSpeed + (Math.random() - 0.5) * 70;
        const initVz = -entryVector.z * travelSpeed + (Math.random() - 0.5) * 70;
        const pullHeight = physicsConfig.pullHeight.min + Math.random() * Math.max(0, physicsConfig.pullHeight.max - physicsConfig.pullHeight.min);
        const pullTime = physicsConfig.pullTime.min + Math.random() * Math.max(0, physicsConfig.pullTime.max - physicsConfig.pullTime.min);
        const bounceFrequency = physicsConfig.bounceFrequency.min + Math.random() * Math.max(0, physicsConfig.bounceFrequency.max - physicsConfig.bounceFrequency.min);
        const bounceSpan = Math.max(0.001, DICE_REFERENCE_DEFAULTS.bounceFrequencyMax - DICE_REFERENCE_DEFAULTS.bounceFrequencyMin);
        const restitution = Math.max(0.30, Math.min(0.52, 0.30 + ((bounceFrequency - DICE_REFERENCE_DEFAULTS.bounceFrequencyMin) / bounceSpan) * 0.22));
        const spinDuration = physicsConfig.spinDuration.min + Math.random() * Math.max(0, physicsConfig.spinDuration.max - physicsConfig.spinDuration.min);
        const spinRate = physicsConfig.spinRotation * 1000 / Math.max(800, spinDuration);
        const pullVelocity = -(physicsConfig.gravity * Math.max(0.12, pullTime / 1000) * 0.45);
        const initialRx = Math.random() * 360;
        const initialRy = Math.random() * 360;
        const initialRz = Math.random() * 360;
        const body = new RigidBody3D({{
          element: wrap,
          shadowElement: shadow,
          threeMesh: mesh,
          shape: "box",
          radius: 36,
          halfExtent: 36,
          mass: 1.0,
          restitution,
          friction: 0.76,
          airDrag: 0.998,
          // Continuous angular damping: fast in-air tumble, then a believable
          // energy loss after the first contacts instead of spinning forever.
          rotDamping: 0.965,
          x: spawnX,
          y: pullHeight,
          z: spawnZ,
          vx: initVx,
          vy: pullVelocity - Math.random() * 35,
          vz: initVz,
          rx: initialRx,
          ry: initialRy,
          rz: initialRz,
          wx: (Math.random() - 0.5) * spinRate * 2.2,
          wy: (Math.random() - 0.5) * spinRate * 1.8,
          wz: (Math.random() - 0.5) * spinRate * 2.2,
          targetFace: val,
          shadowOpacity: physicsConfig.shadowOpacity,
          onBounce: (impactSpeed) => {{
            sound.playFile("/assets/sound/casino/dice-throw-1.ogg", () => sound.playWoodClack(Math.min(1.0, impactSpeed / 500)));
          }}
        }});

        dicePhysicsWorld.addBody(body);
      }});

      dicePhysicsWorld.start();
      safeTimeout(() => {{
        if (dicePhysicsWorld && dicePhysicsWorld.isRunning) {{
          bubble.innerText = `@${{data.user_name || "觀眾"}} 骰子仍在桌面滾動，等待自然停止……`;
        }}
      }}, 9000);
    }}

    // =========================================================================
    // 8. 猜大小骰寶 (Gamble Big/Small / 3D Sic Bo Physics)
    // =========================================================================
    function playGambleAnimation(data) {{
      if (MODE !== "all" && MODE !== "gamble") return;
      hideAllStages();

      const stage = document.getElementById("gamble-stage");
      const cup = document.getElementById("gamble-cup");
      const arena = document.getElementById("gamble-physics-arena");
      const tag = document.getElementById("gamble-tag");
      const badge = document.getElementById("gamble-res-badge");
      const bubble = document.getElementById("gamble-bubble");
      if (arena) arena.querySelectorAll(".die-wrapper, .die-shadow").forEach(el => el.remove());

      const roll = Number.isFinite(Number(data.dice_roll)) ? Number(data.dice_roll) : 3;
      const bet = data.bet || 10;
      const sideChosen = data.side_chosen || "大";
      const eventSide = String(data.winning_side || (roll >= 11 ? "大" : "小"));
      const eventTriple = eventSide === "圍骰" || data.triple === true;
      const suppliedDice = Array.isArray(data.rolls) && data.rolls.length === 3
        ? data.rolls.map(Number)
        : null;
      const diceVals = (() => {{
        const total = Math.max(3, Math.min(18, Math.round(roll)));
        if (suppliedDice && suppliedDice.every(value => Number.isInteger(value) && value >= 1 && value <= 6) &&
            suppliedDice.reduce((sum, value) => sum + value, 0) === total) {{
          return suppliedDice;
        }}
        if (eventTriple && total % 3 === 0) {{
          const face = total / 3;
          if (face >= 1 && face <= 6) return [face, face, face];
        }}
        // Reconstruct a valid Sic Bo triple whose visible faces always sum to
        // the event total.  The old hand-written table mapped 4 to 2+3+3,
        // 5 to 2+4+5, etc., so the animation contradicted the announced roll.
        const values = [1, 1, 1];
        let remaining = total - 3;
        for (let index = 0; index < values.length; index++) {{
          const slotsAfter = values.length - index - 1;
          const maxAdd = Math.min(5, remaining - slotsAfter);
          const add = Math.max(0, Math.min(maxAdd, Math.floor(remaining / (values.length - index))));
          values[index] += add;
          remaining -= add;
        }}
        return values;
      }})();
      let physicalResultShown = false;

      stage.classList.add("active");
      tag.innerText = "【骰盅搖動 · 尚未判定】";
      tag.className = "gamble-tag tag-big";
      badge.className = "gamble-res-badge";
      badge.innerText = `下注【${{sideChosen}}】${{bet}} 點｜等待骰子自然落地`;
      bubble.innerText = `@${{data.user_name || "觀眾"}} 正在擲骰，結果尚未判定……`;
      safeSetClass("gamble-cup", "gamble-cup shaking");

      sound.playRatchet();
      let rattleCount = 0;
      const rattleTimer = safeInterval(() => {{
        sound.playWoodTap();
        rattleCount++;
        if (rattleCount > 8) clearInterval(rattleTimer);
      }}, 120);

      safeTimeout(() => {{
        safeSetClass("gamble-cup", "gamble-cup lifted");
        sound.playWhoosh();

        let webglEngine = null;
        const canvasEl = document.getElementById("gamble-webgl-canvas");
        if (window.THREE && canvasEl) {{
          if (!window.__gambleWebGL) {{
            window.__gambleWebGL = new WebGLDiceEngine(
              "gamble-webgl-canvas",
              THROW_PLANE_CONFIG.canvasWidth,
              THROW_PLANE_CONFIG.canvasHeight,
              THROW_PLANE_CONFIG.cameraPosition
            );
          }}
          webglEngine = window.__gambleWebGL;
          if (webglEngine.isSupported) {{
            webglEngine.clearDice();
            canvasEl.style.display = "block";
            if (arena) arena.classList.add("uses-webgl");
          }} else if (arena) {{
            arena.classList.remove("uses-webgl");
          }}
        }}

        if (gamblePhysicsWorld) gamblePhysicsWorld.stop();
        gamblePhysicsWorld = new StreamPhysicsWorld(arena, webglEngine);
        // Sic Bo uses the same usable tabletop footprint as Dice/Coin.  The
        // former tiny tray was narrower than three 52px dice plus collision
        // clearance, so wall contacts could keep one die wedged indefinitely.
        gamblePhysicsWorld.bounds = {{ minX: -190, maxX: 190, minZ: -90, maxZ: 90 }};

        diceVals.forEach((val, idx) => {{
          const {{ wrap, shadow }} = create3DDieDOM(48);
          if (arena) {{
            arena.appendChild(shadow);
            arena.appendChild(wrap);
          }}

          let mesh = null;
          if (webglEngine && webglEngine.isSupported) {{
            try {{
              mesh = webglEngine.createDieMesh(2.8);
            }} catch (e) {{
              mesh = null;
            }}
          }}

          if (mesh) {{
            wrap.style.display = "none";
            shadow.style.display = "none";
          }} else {{
            wrap.style.display = "block";
            shadow.style.display = "block";
          }}

          const angle = (idx / 3) * Math.PI * 2;
          const body = new RigidBody3D({{
            element: wrap,
            shadowElement: shadow,
            threeMesh: mesh,
            shape: "box",
            radius: 26,
            halfExtent: 26,
            mass: 1.0,
            restitution: 0.58,
            friction: 0.74,
            x: Math.cos(angle) * 42,
            y: 110 + Math.random() * 40,
            z: Math.sin(angle) * 32,
            vx: Math.cos(angle) * (130 + Math.random() * 70),
            vy: -110 - Math.random() * 70,
            vz: Math.sin(angle) * (90 + Math.random() * 50),
            rx: Math.random() * 360,
            ry: Math.random() * 360,
            rz: Math.random() * 360,
            wx: (Math.random() - 0.5) * 2400,
            wy: (Math.random() - 0.5) * 1800,
            wz: (Math.random() - 0.5) * 2400,
            targetFace: val,
            onBounce: (impactSpeed) => {{
              sound.playFile("/assets/sound/casino/dice-throw-1.ogg", () => sound.playWoodClack(Math.min(1.0, impactSpeed / 450)));
            }}
          }});
          gamblePhysicsWorld.addBody(body);
        }});

        gamblePhysicsWorld.onSettled = (settledFaces = []) => {{
          const physicalFaces = settledFaces.filter(value => Number.isInteger(value));
          if (physicalFaces.length !== 3 || physicalResultShown) return;
          physicalResultShown = true;
          const eventRoll = Number.isFinite(Number(data.dice_roll)) ? Number(data.dice_roll) : null;
          const visualWon = typeof data.won === "boolean"
            ? data.won
            : (!eventTriple && eventSide === sideChosen);
          tag.innerText = eventRoll === null
            ? `【${{eventSide}} · 結果已落定】`
            : `【${{eventSide}} · 開出 ${{eventRoll}} 點】`;
          tag.className = `gamble-tag ${{eventTriple ? "tag-triple" : (eventSide === "大" ? "tag-big" : "tag-small")}}`;
          badge.className = `gamble-res-badge ${{visualWon ? "win" : "lose"}}`;
          badge.innerText = visualWon
            ? `✨ 事件結果：押中【${{sideChosen}}】｜帳務餘額：${{data.balance || 0}} 點`
            : `💨 事件結果：押【${{sideChosen}}】落空｜帳務餘額：${{data.balance || 0}} 點`;
          bubble.innerText = visualWon
            ? `🎉 @${{data.user_name || "觀眾"}} 押中事件結果【${{eventSide}}】！`
            : `@${{data.user_name || "觀眾"}} 事件結果是【${{eventSide}}】。`;
          if (visualWon) {{
            triggerScreenEffects(true);
            sound.playFanfare();
            sound.playCoinShower();
            spawnVFX("gold", 100);
          }} else {{
            sound.playThud();
          }}
          safeTimeout(() => hideAllStages(), 3000);
        }};
        gamblePhysicsWorld.start();

        safeTimeout(() => {{
          if (!physicalResultShown) {{
            tag.innerText = "【骰盅揭開 · 等待自然落地】";
            tag.className = "gamble-tag tag-big";
          }}
          badge.className = "gamble-res-badge";
          badge.innerText = `下注【${{sideChosen}}】${{bet}} 點｜等待骰子自然落地`;
          bubble.innerText = `@${{data.user_name || "觀眾"}} 的骰子仍在碰撞、滾動與收斂……`;
        }}, 1800);
      }}, 1250);

      safeTimeout(() => {{
        if (gamblePhysicsWorld && gamblePhysicsWorld.isRunning) {{
          tag.innerText = "【仍在桌面滾動 · 不提前清場】";
          tag.className = "gamble-tag tag-big";
        }}
      }}, 9000);
    }}

    // =========================================================================
    // 9. 浮動自訂計數器 HUD
    // =========================================================================
    function updateCounterHud(data) {{
      if (MODE !== "all" && MODE !== "counter") return;
      const widget = document.getElementById("counter-hud-widget");
      const nameEl = document.getElementById("counter-hud-name");
      const countEl = document.getElementById("counter-hud-count");
      const deltaEl = document.getElementById("counter-delta-tag");

      nameEl.innerText = data.name || data.counter_id || "計數器";
      countEl.innerText = data.count !== undefined ? data.count : 0;

      const delta = data.delta || 0;
      if (delta !== 0) {{
        deltaEl.innerText = delta > 0 ? `+${{delta}}` : `${{delta}}`;
        deltaEl.style.background = delta > 0 ? "rgba(16, 185, 129, 0.9)" : "rgba(239, 68, 68, 0.9)";
        deltaEl.style.color = "#ffffff";
        deltaEl.style.display = "block";
        sound.playPegTick();
        safeTimeout(() => {{ deltaEl.style.display = "none"; }}, 1200);
      }}

      widget.classList.add("active");
      if (MODE !== "counter") {{
        safeTimeout(() => widget.classList.remove("active"), 8000);
      }}
    }}

    // =========================================================================
    // 10. 馬拉松倒數計時器 HUD
    // =========================================================================
    let subathonInterval = null;
    let subathonSec = 7200;
    let subathonRunning = false;

    function formatTimeStr(sec) {{
      const s = Math.max(0, sec);
      const h = Math.floor(s / 3600);
      const m = Math.floor((s % 3600) / 60);
      const sc = s % 60;
      return `${{String(h).padStart(2, "0")}}:${{String(m).padStart(2, "0")}}:${{String(sc).padStart(2, "0")}}`;
    }}

    function updateSubathonHud(data) {{
      if (MODE !== "all" && MODE !== "subathon") return;
      const widget = document.getElementById("subathon-hud-widget");
      const digits = document.getElementById("subathon-digits");
      const dot = document.getElementById("subathon-dot");

      if (data.remaining_seconds !== undefined) {{
        subathonSec = Number(data.remaining_seconds);
      }}
      subathonRunning = Boolean(data.is_running);
      digits.innerText = data.formatted || formatTimeStr(subathonSec);
      dot.style.background = subathonRunning ? "#10b981" : "#f59e0b";

      const deltaValue = data.delta !== undefined ? data.delta : data.delta_seconds;
      if (deltaValue !== undefined && Number(deltaValue) !== 0) {{
        const delta = Number(deltaValue);
        sound.playPegTick();
        digits.style.color = delta > 0 ? "#34d399" : "#fb7185";
        safeTimeout(() => {{ digits.style.color = "#f8fafc"; }}, 1500);
      }}

      if (data.hidden === true || data.visible === false) {{
        widget.classList.remove("active");
      }} else {{
        widget.classList.add("active");
      }}

      if (!subathonInterval) {{
        subathonInterval = setInterval(() => {{
          if (subathonRunning && subathonSec > 0) {{
            subathonSec--;
            digits.innerText = formatTimeStr(subathonSec);
          }}
        }}, 1000);
      }}

    }}

    function setSubathonVisibility(data) {{
      if (MODE !== "all" && MODE !== "subathon") return;
      const widget = document.getElementById("subathon-hud-widget");
      if (!widget) return;
      if (data.hidden === true || data.visible === false || data.action === "hide") {{
        widget.classList.remove("active");
      }} else {{
        widget.classList.add("active");
      }}
    }}

    // =========================================================================
    // 11. 翻唱歌單 / 正在演唱 HUD
    // =========================================================================
    function updateCoverHud(data) {{
      if (MODE !== "all" && MODE !== "cover") return;
      if (data.status === "idle" || data.status === "cleared" || data.clear === true) {{
        clearCoverHud();
        return;
      }}
      const widget = document.getElementById("cover-hud-widget");
      const titleEl = document.getElementById("cover-hud-title");
      const userEl = document.getElementById("cover-hud-user");
      const statusEl = document.getElementById("cover-hud-status");

      statusEl.innerText = "NOW SINGING";
      const art = data.artist ? ` - ${{data.artist}}` : "";
      titleEl.innerText = `${{data.song_title || "演唱中曲目"}}${{art}}`;
      userEl.innerText = data.user_name && data.user_name !== "主播" ? `點播：@${{data.user_name}}` : "主播精選曲目";

      sound.playChime();
      widget.classList.add("active");

      if (MODE !== "cover") {{
        safeTimeout(() => widget.classList.remove("active"), 14000);
      }}
    }}

    function toastCoverRequested(data) {{
      if (MODE !== "all" && MODE !== "cover") return;
      const widget = document.getElementById("cover-hud-widget");
      const titleEl = document.getElementById("cover-hud-title");
      const userEl = document.getElementById("cover-hud-user");
      const statusEl = document.getElementById("cover-hud-status");

      statusEl.innerText = `NEW REQUEST (順位 #${{data.queue_position || 1}})`;
      titleEl.innerText = `《${{data.title || "點播歌曲"}}》`;
      userEl.innerText = `來自 @${{data.user_name || "觀眾"}} 的點歌`;

      sound.playChime();
      widget.classList.add("active");
      safeTimeout(() => {{
        if (MODE !== "cover") widget.classList.remove("active");
      }}, 8000);
    }}

    function clearCoverHud() {{
      const widget = document.getElementById("cover-hud-widget");
      const statusEl = document.getElementById("cover-hud-status");
      const titleEl = document.getElementById("cover-hud-title");
      const userEl = document.getElementById("cover-hud-user");
      if (statusEl) statusEl.innerText = "IDLE";
      if (titleEl) titleEl.innerText = "目前沒有演唱歌曲";
      if (userEl) userEl.innerText = "點唱清單已清空";
      if (widget) widget.classList.remove("active");
    }}

    // =========================================================================
    // 12. 活躍觀眾抽籤獲獎彈窗
    // =========================================================================
    function showPickerWinner(data) {{
      if (MODE !== "all" && MODE !== "picker") return;
      hideAllStages();

      const stage = document.getElementById("picker-stage");
      const nameEl = document.getElementById("picker-winner-name");
      const infoEl = document.getElementById("picker-pool-info");

      nameEl.innerText = `@${{data.user_name || "幸運觀眾"}}`;
      infoEl.innerText = `從過去 ${{data.minutes || 10}} 分鐘活躍的 ${{data.pool_size || 1}} 位聊天者中抽中！`;

      stage.classList.add("active");
      triggerScreenEffects(true);
      sound.playFanfare();
      sound.playCoinShower();
      spawnVFX("confetti", 120);

      safeTimeout(() => hideAllStages(), 9000);
    }}

    // =========================================================================
    // 13. 活動排隊叫號廣播
    // =========================================================================
    function updateQueueHud(data) {{
      if (MODE !== "all" && MODE !== "queue") return;
      const panel = document.getElementById("queue-list-panel");
      const itemsEl = document.getElementById("queue-list-items");
      const statusEl = document.getElementById("queue-list-status");
      if (!panel || !itemsEl) return;

      const entries = Array.isArray(data.entries)
        ? data.entries
        : (Array.isArray(data.remaining_entries) ? data.remaining_entries : (Array.isArray(data.queue) ? data.queue : null));
      if (statusEl) {{
        const status = data.status === "closed" ? "已截止" : "開放中";
        const count = data.waiting_count !== undefined ? data.waiting_count : (entries ? entries.length : 0);
        statusEl.innerText = `${{status}} · ${{count}} 人`;
      }}
      if (entries) {{
        itemsEl.innerHTML = "";
        if (entries.length === 0) {{
          itemsEl.innerHTML = '<div class="queue-list-row"><span>—</span><span>目前沒有等待者</span><span></span></div>';
        }} else {{
          entries.slice(0, 24).forEach((entry, index) => {{
            const row = document.createElement("div");
            row.className = "queue-list-row";
            const pos = document.createElement("span");
            const name = document.createElement("span");
            const note = document.createElement("span");
            pos.innerText = `${{index + 1}}.`;
            name.innerText = `@${{entry.user_name || entry.name || "觀眾"}}`;
            note.innerText = entry.note || "";
            note.style.color = "#94a3b8";
            row.append(pos, name, note);
            itemsEl.appendChild(row);
          }});
        }}
      }} else if (Number(data.waiting_count || 0) === 0) {{
        itemsEl.innerHTML = '<div class="queue-list-row"><span>—</span><span>目前沒有等待者</span><span></span></div>';
      }}
      panel.classList.add("active");
    }}

    function showQueueCalled(data) {{
      if (MODE !== "all" && MODE !== "queue") return;
      const alert = document.getElementById("queue-call-alert");
      const namesEl = document.getElementById("queue-called-names");

      const called = data.called_users || [];
      const nameList = called.map(c => `@${{c.user_name}}`).join("、") || "玩家出列";
      const rem = data.remaining_count !== undefined ? `（剩餘排隊：${{data.remaining_count}} 人）` : "";
      namesEl.innerText = `下一輪玩家：${{nameList}} ${{rem}}`;
      updateQueueHud({{
        ...data,
        waiting_count: data.remaining_count,
        entries: data.remaining_entries || data.entries || []
      }});

      sound.playChime();
      alert.classList.add("active");
      safeTimeout(() => alert.classList.remove("active"), 7000);
    }}

    // =========================================================================
    // 14. 社群下注預測 HUD
    // =========================================================================
    function updateBetHud(data) {{
      if (MODE !== "all" && MODE !== "bet") return;
      const widget = document.getElementById("bet-hud-widget");
      const titleEl = document.getElementById("bet-hud-title");
      const badgeEl = document.getElementById("bet-hud-badge");
      const barA = document.getElementById("bet-hud-bar-a");
      const barB = document.getElementById("bet-hud-bar-b");
      const nameA = document.getElementById("bet-hud-name-a");
      const nameB = document.getElementById("bet-hud-name-b");
      const infoA = document.getElementById("bet-hud-info-a");
      const infoB = document.getElementById("bet-hud-info-b");
      const totalPool = document.getElementById("bet-hud-total-pool");

      widget.classList.remove("bet-winner-glow-a", "bet-winner-glow-b");

      if (data.title) titleEl.innerText = data.title;
      const optA = data.option_a || "能";
      const optB = data.option_b || "不能";
      nameA.innerText = `🅰️ ${{optA}}`;
      nameB.innerText = `${{optB}} 🅱️`;

      const poolA = Number(data.pool_a || 0);
      const poolB = Number(data.pool_b || 0);
      const oddsA = data.odds_a || 1.0;
      const oddsB = data.odds_b || 1.0;
      const tot = Number(data.total_pool || 0);

      infoA.innerText = `${{oddsA}}x ｜ ${{poolA}} 點`;
      infoB.innerText = `${{poolB}} 點 ｜ ${{oddsB}}x`;
      totalPool.innerText = `${{tot}} 點`;

      const ratioA = tot > 0 ? Math.round(poolA / tot * 100) : 50;
      const ratioB = 100 - ratioA;
      barA.style.width = `${{ratioA}}%`;
      barB.style.width = `${{ratioB}}%`;

      const isLocked = data.type === "bet.locked" || data.status === "locked";
      badgeEl.className = `bet-badge ${{isLocked ? "locked" : "open"}}`;
      badgeEl.innerText = isLocked ? "已封盤" : "開放投注";

      if (data.type === "bet.placed") {{
        sound.playPegTick();
      }} else if (data.type === "bet.opened") {{
        sound.playChime();
      }}

      widget.classList.add("active");
      if (MODE !== "bet") {{
        safeTimeout(() => {{
          if (MODE !== "bet") widget.classList.remove("active");
        }}, 14000);
      }}
    }}

    function resolveBetHud(data) {{
      if (MODE !== "all" && MODE !== "bet") return;
      const widget = document.getElementById("bet-hud-widget");
      const badgeEl = document.getElementById("bet-hud-badge");
      const winOpt = (data.winning_option || "A").toUpperCase();

      badgeEl.className = "bet-badge resolved";
      badgeEl.innerText = `🏆 【${{winOpt}}】獲勝`;

      if (winOpt === "A") {{
        widget.classList.add("bet-winner-glow-a");
      }} else {{
        widget.classList.add("bet-winner-glow-b");
      }}

      sound.playFanfare();
      sound.playCoinShower();
      spawnVFX("gold", 100);

      widget.classList.add("active");
      safeTimeout(() => {{
        if (MODE !== "bet") widget.classList.remove("active");
      }}, 16000);
    }}

    function cancelBetHud(data) {{
      if (MODE !== "all" && MODE !== "bet") return;
      const widget = document.getElementById("bet-hud-widget");
      const badgeEl = document.getElementById("bet-hud-badge");
      badgeEl.className = "bet-badge locked";
      badgeEl.innerText = "🛑 已流盤退款";
      sound.playChime();
      safeTimeout(() => {{
        if (MODE !== "bet") widget.classList.remove("active");
      }}, 8000);
    }}

    // =========================================================================
    // 15. 點歌播放器 HUD
    // =========================================================================
    let musicProgressTimer = null;
    let musicElapsedSecs = 0;

    function updateMusicHud(data) {{
      if (MODE !== "all" && MODE !== "music") return;
      const widget = document.getElementById("music-hud-widget");
      const titleEl = document.getElementById("music-song-title");
      const artistEl = document.getElementById("music-song-artist");
      const userEl = document.getElementById("music-song-user");
      const fillEl = document.getElementById("music-progress-fill");
      const currEl = document.getElementById("music-time-curr");
      const totalEl = document.getElementById("music-time-total");
      const disc = document.getElementById("music-vinyl");
      const statusEl = document.getElementById("music-status-tag");

      titleEl.innerText = data.title || "未知歌曲";
      artistEl.innerText = data.artist || "未知歌手";
      userEl.innerText = `點播：@${{data.user_name || "觀眾"}}`;
      statusEl.innerText = "NOW PLAYING";
      statusEl.style.color = "#a855f7";

      const totalSecs = data.duration_seconds || 210;
      totalEl.innerText = data.duration_formatted || "03:30";
      currEl.innerText = "00:00";
      fillEl.style.width = "0%";
      disc.style.animationPlayState = "running";

      musicElapsedSecs = 0;
      if (musicProgressTimer) clearInterval(musicProgressTimer);
      musicProgressTimer = safeInterval(() => {{
        musicElapsedSecs += 1;
        if (musicElapsedSecs > totalSecs) {{
          clearInterval(musicProgressTimer);
          return;
        }}
        const pct = Math.min(100, (musicElapsedSecs / totalSecs) * 100);
        fillEl.style.width = `${{pct}}%`;
        const m = Math.floor(musicElapsedSecs / 60);
        const s = musicElapsedSecs % 60;
        currEl.innerText = `${{m < 10 ? '0' : ''}}${{m}}:${{s < 10 ? '0' : ''}}${{s}}`;
      }}, 1000);

      sound.playChime();
      widget.classList.add("active");
      if (MODE !== "music") {{
        safeTimeout(() => {{
          if (MODE !== "music") widget.classList.remove("active");
        }}, 14000);
      }}
    }}

    function toastMusicRequested(data) {{
      sound.playPegTick();
      if (MODE === "music") {{
        const widget = document.getElementById("music-hud-widget");
        widget.classList.add("active");
      }}
    }}

    function skipMusicHud(data) {{
      sound.playWoodTap();
      const statusEl = document.getElementById("music-status-tag");
      if (statusEl) {{
        statusEl.innerText = "SKIPPED";
        statusEl.style.color = "#f43f5e";
      }}
    }}

    function clearMusicHud(data) {{
      const widget = document.getElementById("music-hud-widget");
      if (musicProgressTimer) {{
        clearInterval(musicProgressTimer);
        musicProgressTimer = null;
      }}
      if (widget) widget.classList.remove("active");
    }}

    // =========================================================================
    // 16. 雙語字幕即時翻譯 HUD
    // =========================================================================
    let transHideTimer = null;

    function showTransHud(data) {{
      if (MODE !== "all" && MODE !== "trans") return;
      const widget = document.getElementById("trans-hud-widget");
      const badgeEl = document.getElementById("trans-badge");
      const userEl = document.getElementById("trans-user");
      const origEl = document.getElementById("trans-orig");
      const mainEl = document.getElementById("trans-main");

      const sLang = (data.src_lang || "auto").toUpperCase();
      const tLang = (data.target_lang || "zh-tw").toUpperCase();
      badgeEl.innerText = `🌐 ${{sLang}} ➔ ${{tLang}}`;
      userEl.innerText = `@${{data.user_name || "觀眾"}}`;
      origEl.innerText = `"${{data.orig_text || ""}}"`;
      mainEl.innerText = data.trans_text || "";

      sound.playPegTick();
      widget.classList.add("active");

      if (transHideTimer) clearTimeout(transHideTimer);
      if (MODE !== "trans") {{
        transHideTimer = safeTimeout(() => {{
          if (MODE !== "trans") widget.classList.remove("active");
        }}, 8000);
      }}
    }}

    // =========================================================================
    // 17. 贊助通知彈窗 HUD
    // =========================================================================
    let donationHideTimer = null;
    const recentDonationEventIds = new Set();

    function showDonationAlert(data) {{
      if (MODE !== "all" && MODE !== "donation") return;
      const eventId = data.message_id || data.event_id;
      if (eventId) {{
        if (recentDonationEventIds.has(eventId)) return;
        recentDonationEventIds.add(eventId);
        window.setTimeout(() => recentDonationEventIds.delete(eventId), 12000);
      }}
      const widget = document.getElementById("donation-alert-widget");
      const iconEl = document.getElementById("donation-icon");
      const badgeTitle = document.getElementById("donation-badge-title");
      const amtEl = document.getElementById("donation-amount");
      const donorEl = document.getElementById("donation-donor");
      const msgEl = document.getElementById("donation-msg");
      const ptsTag = document.getElementById("donation-points-tag");
      const timeTag = document.getElementById("donation-time-tag");

      if (iconEl) iconEl.innerText = data.icon || "💖";
      if (badgeTitle) badgeTitle.innerText = data.badge_title || "NEW DONATION";
      const name = data.donor_name || data.user_name || "熱心觀眾";
      const amtStr = data.amount_formatted || (data.amount ? `TWD $${{data.amount}}` : "贊助支持");
      const msg = data.message || "謝謝主播！";

      amtEl.innerText = amtStr;
      donorEl.innerText = data.donor_title || `感謝 @${{name}} 的熱情贊助！`;
      msgEl.innerText = `"${{msg}}"`;

      const pts = data.points_awarded || 0;
      ptsTag.innerText = pts > 0 ? `🎁 +${{pts}} 點數` : "";
      ptsTag.style.display = pts > 0 ? "inline" : "none";

      const secs = data.seconds_added || 0;
      timeTag.innerText = secs > 0 ? `⏱️ +${{secs}}s 馬拉松延長` : "";
      timeTag.style.display = secs > 0 ? "inline" : "none";

      sound.playFanfare();
      sound.playCoinShower();
      spawnVFX("gold", 120);

      widget.classList.add("active");

      if (donationHideTimer) clearTimeout(donationHideTimer);
      if (MODE !== "donation") {{
        donationHideTimer = safeTimeout(() => {{
          if (MODE !== "donation") widget.classList.remove("active");
        }}, 9000);
      }}
    }}

    function showOverlayStatusToast(icon, title, detail, accent = "#38bdf8") {{
      let toast = document.getElementById("overlay-status-toast");
      if (!toast) {{
        toast = document.createElement("div");
        toast.id = "overlay-status-toast";
        document.body.appendChild(toast);
      }}
      toast.style.cssText = `position:fixed;left:50%;bottom:34px;transform:translateX(-50%) translateY(16px);opacity:0;z-index:99999;min-width:280px;max-width:640px;padding:12px 18px;border:1px solid ${{accent}}99;border-radius:14px;background:rgba(8,15,31,.94);box-shadow:0 14px 32px rgba(0,0,0,.6),0 0 20px ${{accent}}33;color:#f8fafc;font:700 14px/1.45 system-ui,sans-serif;text-align:center;transition:opacity .22s ease,transform .22s ease;pointer-events:none;`;
      toast.replaceChildren();
      const heading = document.createElement("div");
      heading.style.cssText = `color:${{accent}};font-size:11px;letter-spacing:1px`;
      heading.textContent = `${{icon}} ${{title}}`;
      const body = document.createElement("div");
      body.textContent = String(detail || "");
      toast.append(heading, body);
      requestAnimationFrame(() => {{ toast.style.opacity = "1"; toast.style.transform = "translateX(-50%) translateY(0)"; }});
      if (toast._hideTimer) window.clearTimeout(toast._hideTimer);
      toast._hideTimer = window.setTimeout(() => {{
        toast.style.opacity = "0";
        toast.style.transform = "translateX(-50%) translateY(16px)";
      }}, 3600);
    }}

    function showCustomCommandChange(data) {{
      const name = String(data.cmd_name || "command").replace(/^!+/, "");
      const removed = data.action === "delete" || data.action === "del" || data.action === "rm";
      showOverlayStatusToast("⚡", removed ? "CUSTOM COMMAND REMOVED" : "CUSTOM COMMAND READY", removed
        ? `已停用 <b>!${{name}}</b>`
        : `已啟用 <b>!${{name}}</b>：${{data.response || "聊天室輸入後會回覆"}}`, removed ? "#fb7185" : "#38bdf8");
    }}

    function showCustomCommandReply(data) {{
      showOverlayStatusToast("💬", "CUSTOM COMMAND", data.text || "自訂指令已回覆", "#a78bfa");
    }}

    function showTwitchCheerAlert(data) {{
      const bits = Number(data.bits || 0);
      showDonationAlert({{
        ...data,
        donor_name: data.user_name,
        badge_title: "TWITCH BITS CHEER",
        amount_formatted: `${{bits}} Bits`,
        message: data.message || `Cheer ${{bits}}`,
        points_awarded: bits,
        seconds_added: bits * 5,
      }});
    }}

    function showTwitchSubAlert(data) {{
      const isGift = data.type === "twitch.subgift" || Boolean(data.is_gift);
      showDonationAlert({{
        icon: isGift ? "🎁" : "⭐",
        badge_title: isGift ? "TWITCH GIFT SUB" : "NEW TWITCH SUB",
        user_name: data.user_name,
        donor_title: isGift ? `狂賀！感謝 @${{data.user_name}} 狂送訂閱！` : `感謝 @${{data.user_name}} 訂閱了頻道！`,
        amount_formatted: isGift ? `贈送 ${{data.total || 1}} 份訂閱` : `Tier ${{data.tier || "1"}} 訂閱`,
        message: data.message || (isGift ? "大家快謝謝乾爹！" : "感謝訂閱支持！"),
        points_awarded: isGift ? 0 : 500,
        seconds_added: (data.total || 1) * 300,
      }});
    }}

    function showTwitchFollowAlert(data) {{
      showDonationAlert({{
        icon: "🌟",
        badge_title: "NEW TWITCH FOLLOWER",
        user_name: data.user_name,
        donor_title: `歡迎 @${{data.user_name}} 追隨本頻道！`,
        amount_formatted: "新追隨者",
        message: "感謝加入實況大家庭～",
        points_awarded: 0,
        seconds_added: 0,
      }});
    }}

    function showTwitchRedeemAlert(data) {{
      const title = data.title || "";
      if (/拉霸|slot|抽卡|召喚|gacha|擲筊|bwei|請示|神明|轉盤|wheel|扭蛋|gashapon|硬幣|coin|拋幣|骰子|dice|擲骰|骰寶|gamble|猜大小/i.test(title)) {{
        return;
      }}
      let icon = "🎯";
      let badgeTitle = "TWITCH CHANNEL POINTS";
      let donorTitle = `@${{data.user_name}} 兌換了忠誠點數獎勵！`;

      if (/冷卻|喝水/i.test(title)) {{
        icon = "💧";
        badgeTitle = "HYDRATION ALERT";
        donorTitle = `💧 @${{data.user_name}} 提醒主播補充水分降溫！`;
      }} else if (/骨架|姿態|坐姿/i.test(title)) {{
        icon = "🦾";
        badgeTitle = "POSTURE CHECK";
        donorTitle = `🦾 @${{data.user_name}} 提醒主播挺直坐姿伸展！`;
      }} else if (/簽到|登錄|訊號/i.test(title)) {{
        icon = "📡";
        badgeTitle = "CHECK-IN SIGNAL";
        donorTitle = `📡 @${{data.user_name}} 成功登錄每日連線！`;
      }} else if (/回歸|重新同步/i.test(title)) {{
        icon = "🔄";
        badgeTitle = "STREAM RESYNC";
        donorTitle = `🔄 @${{data.user_name}} 重新同步回到實況間！`;
      }} else if (/先退|離線/i.test(title)) {{
        icon = "🔌";
        badgeTitle = "OFFLINE LOGOUT";
        donorTitle = `🔌 @${{data.user_name}} 申請離線告退～辛苦了！`;
      }} else if (/晚安|休眠/i.test(title)) {{
        icon = "🌙";
        badgeTitle = "SLEEP PROTOCOL";
        donorTitle = `🌙 @${{data.user_name}} 進入待機休眠，祝好夢晚安！`;
      }} else if (/掛台|背景/i.test(title)) {{
        icon = "🤖";
        badgeTitle = "LURK MODE";
        donorTitle = `🤖 @${{data.user_name}} 啟動背景自動掛台守護！`;
      }} else if (/排隊|艦隊|同樂|報名/i.test(title)) {{
        icon = "🎟️";
        badgeTitle = "QUEUE JOINED";
        donorTitle = `🎟️ @${{data.user_name}} 成功加入觀眾場活動排隊！`;
      }}

      showDonationAlert({{
        icon: icon,
        badge_title: badgeTitle,
        user_name: data.user_name,
        donor_title: donorTitle,
        amount_formatted: `${{data.cost || 10}} 忠誠點數`,
        message: `【${{data.title || "獎勵"}}】${{data.user_input ? "：「" + data.user_input + "」" : ""}}`,
        points_awarded: 0,
        seconds_added: 0,
      }});
    }}

    // =========================================================================
    // WebSocket Client
    // =========================================================================
    const statusPill = document.getElementById("status-indicator");

    function handleOverlayMessage(msg) {{
      const type = msg && msg.type || "";
      if (type === "overlay.reset" || type === "game.reset" || type === "overlay.clear" || type === "stage.reset") hideAllStages(msg);
      else if (type === "game.bwei.tossed") playBweiAnimation(msg);
      else if (type === "game.slot.rolled") playSlotAnimation(msg);
      else if (type === "game.gashapon.pulled") playGashaponAnimation(msg);
      else if (type === "gacha.card.pulled") playCardGachaAnimation(msg);
      else if (type === "game.wheel.spun") playWheelAnimation(msg);
      else if (type === "game.coin.flipped") playCoinAnimation(msg);
      else if (type === "game.dice.rolled") playDiceAnimation(msg);
      else if (type === "game.gamble.resolved") playGambleAnimation(msg);
      else if (type === "counter.changed") updateCounterHud(msg);
      else if (type === "subathon.timer.updated") updateSubathonHud(msg);
      else if (type === "subathon.visibility" || type === "subathon.display") setSubathonVisibility(msg);
      else if (type === "cover.current") updateCoverHud(msg);
      else if (type === "cover.cleared" || type === "cover.clear") clearCoverHud();
      else if (type === "cover.requested") toastCoverRequested(msg);
      else if (type === "picker.selected") showPickerWinner(msg);
      else if (type === "queue.updated") updateQueueHud(msg);
      else if (type === "queue.called") showQueueCalled(msg);
      else if (type === "bet.opened" || type === "bet.placed" || type === "bet.locked") updateBetHud(msg);
      else if (type === "bet.resolved") resolveBetHud(msg);
      else if (type === "bet.cancelled") cancelBetHud(msg);
      else if (type === "music.playing") updateMusicHud(msg);
      else if (type === "music.requested") toastMusicRequested(msg);
      else if (type === "music.skipped") skipMusicHud(msg);
      else if (type === "music.cleared") clearMusicHud();
      else if (type === "trans.translated") showTransHud(msg);
      else if (type === "custom_cmd.changed") showCustomCommandChange(msg);
      else if (type === "bot.reply" && msg.source === "custom_cmd") showCustomCommandReply(msg);
      else if (type === "donation.received") showDonationAlert(msg);
      else if (type === "twitch.cheer") showTwitchCheerAlert(msg);
      else if (type === "twitch.subscribe" || type === "twitch.subgift") showTwitchSubAlert(msg);
      else if (type === "twitch.follow") showTwitchFollowAlert(msg);
      else if (type === "twitch.channel_points.redeem") showTwitchRedeemAlert(msg);
    }}

    function connectWs() {{
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.host;
      const wsUrl = `${{proto}}//${{host}}${{WS_PATH}}`;

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {{
        statusPill.innerText = "WS 已連線";
        statusPill.classList.add("visible");
        setTimeout(() => statusPill.classList.remove("visible"), 2000);

        // HUD 模式開箱自動啟用
        if (MODE === "subathon") {{
          document.getElementById("subathon-hud-widget").classList.add("active");
        }} else if (MODE === "counter") {{
          document.getElementById("counter-hud-widget").classList.add("active");
        }} else if (MODE === "cover") {{
          document.getElementById("cover-hud-widget").classList.add("active");
        }} else if (MODE === "bet") {{
          document.getElementById("bet-hud-widget").classList.add("active");
        }} else if (MODE === "music") {{
          document.getElementById("music-hud-widget").classList.add("active");
        }} else if (MODE === "trans") {{
          document.getElementById("trans-hud-widget").classList.add("active");
        }} else if (MODE === "donation") {{
          document.getElementById("donation-alert-widget").classList.add("active");
        }}
      }};

      function handleSocketOverlayMessage(msg) {{
        const type = msg && msg.type || "";

          if (type === "overlay.reset" || type === "game.reset" || type === "overlay.clear" || type === "stage.reset") {{
            hideAllStages(msg);
          }}
          else if (type === "game.bwei.tossed") playBweiAnimation(msg);
          else if (type === "game.slot.rolled") playSlotAnimation(msg);
          else if (type === "game.gashapon.pulled") playGashaponAnimation(msg);
          else if (type === "gacha.card.pulled") playCardGachaAnimation(msg);
          else if (type === "game.wheel.spun") playWheelAnimation(msg);
          else if (type === "game.coin.flipped") playCoinAnimation(msg);
          else if (type === "game.dice.rolled") playDiceAnimation(msg);
          else if (type === "game.gamble.resolved") playGambleAnimation(msg);
          else if (type === "counter.changed") updateCounterHud(msg);
          else if (type === "subathon.timer.updated") updateSubathonHud(msg);
          else if (type === "subathon.visibility" || type === "subathon.display") setSubathonVisibility(msg);
          else if (type === "cover.current") updateCoverHud(msg);
          else if (type === "cover.cleared" || type === "cover.clear") clearCoverHud();
          else if (type === "cover.requested") toastCoverRequested(msg);
          else if (type === "picker.selected") showPickerWinner(msg);
          else if (type === "queue.updated") updateQueueHud(msg);
          else if (type === "queue.called") showQueueCalled(msg);
          else if (type === "bet.opened" || type === "bet.placed" || type === "bet.locked") updateBetHud(msg);
          else if (type === "bet.resolved") resolveBetHud(msg);
          else if (type === "bet.cancelled") cancelBetHud(msg);
          else if (type === "music.playing") updateMusicHud(msg);
          else if (type === "music.requested") toastMusicRequested(msg);
          else if (type === "music.skipped") skipMusicHud(msg);
          else if (type === "music.cleared") clearMusicHud(msg);
          else if (type === "trans.translated") showTransHud(msg);
          else if (type === "custom_cmd.changed") showCustomCommandChange(msg);
          else if (type === "bot.reply" && msg.source === "custom_cmd") showCustomCommandReply(msg);
          else if (type === "donation.received") showDonationAlert(msg);
          else if (type === "twitch.cheer") showTwitchCheerAlert(msg);
          else if (type === "twitch.subscribe" || type === "twitch.subgift") showTwitchSubAlert(msg);
          else if (type === "twitch.follow") showTwitchFollowAlert(msg);
          else if (type === "twitch.channel_points.redeem") showTwitchRedeemAlert(msg);
      }}

      ws.onmessage = (event) => {{
        try {{
          handleSocketOverlayMessage(JSON.parse(event.data));
        }} catch (err) {{
          console.error("Game parse error:", err);
        }}
      }};

      ws.onclose = () => {{
        statusPill.innerText = "WS 中斷重連中...";
        statusPill.classList.add("visible");
        setTimeout(connectWs, 2500);
      }};

      ws.onerror = () => ws.close();
    }}

    window.testBwei = playBweiAnimation;
    window.testSlot = playSlotAnimation;
    window.testGashapon = playGashaponAnimation;
    window.testCardGacha = playCardGachaAnimation;
    window.testWheel = playWheelAnimation;
    window.testCoin = playCoinAnimation;
    window.testDice = playDiceAnimation;
    window.testGamble = playGambleAnimation;
    window.testCounter = updateCounterHud;
    window.testSubathon = updateSubathonHud;
    window.testCover = updateCoverHud;
    window.testPicker = showPickerWinner;
    window.testQueue = showQueueCalled;
    window.testBet = updateBetHud;
    window.testBetResolve = resolveBetHud;
    window.testMusic = updateMusicHud;
    window.testTrans = showTransHud;
    window.testDonation = showDonationAlert;
    window.handleOverlayMessage = handleOverlayMessage;
    window.hideAllStages = hideAllStages;
    window.clearOverlay = hideAllStages;
    window.addEventListener("message", (ev) => {{
      if (ev.data && ev.data.type === "interactive.demo.event") {{
        handleOverlayMessage(ev.data.payload || {{}});
      }} else if (ev.data && (ev.data.type === "overlay.reset" || ev.data.type === "game.reset" || ev.data.type === "overlay.clear")) {{
        hideAllStages(ev.data);
      }}
    }});

    if (STATIC_DEMO) {{
      if (statusPill) {{
        statusPill.innerText = "GitHub Pages 展示模式";
        statusPill.classList.add("visible");
      }}
    }} else {{
      connectWs();
    }}
  </script>
</body>
</html>"""


def render_preview_dashboard_html(
    *,
    static_demo: bool = False,
    asset_prefix: str = "/assets",
    overlay_path: str = "/overlay/games",
) -> str:
    """Return the local control dashboard or a static GitHub Pages demo."""
    html = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <title>Stream Interactive Workbench</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    :root {
      --bg: #f7f7f8;
      --card-bg: #ffffff;
      --border: #e0e0e6;
      --primary: #6b5db8;
      --accent: #0ea5b0;
      --pink: #c45c93;
      --purple: #6b5db8;
      --green: #22c55e;
      --text: #1a1a1f;
      --muted: #6b6b80;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft JhengHei UI", sans-serif;
      padding: 28px;
      line-height: 1.5;
    }
    .header {
      margin-bottom: 24px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 16px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
    }
    .header h1 {
      font-size: 26px;
      font-weight: 900;
      color: #2d2944;
    }
    .header p {
      font-size: 14px;
      color: var(--muted);
      margin-top: 4px;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
      gap: 20px;
    }

    .card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 2px 8px rgba(26, 26, 31, 0.10);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;
    }
    .card h2 {
      font-size: 19px;
      font-weight: 800;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .tag {
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 12px;
      font-weight: 700;
    }
    .tag-live { background: #e9f8ef; color: #15803d; border: 1px solid #86efac; }

    .desc { font-size: 13px; color: var(--muted); margin-bottom: 14px; }

    /* 醒目的「正常遊玩一次」大按鈕 */
    .play-hero-btn {
      width: 100%;
      background: var(--primary);
      color: #ffffff;
      border: none;
      padding: 12px;
      border-radius: 10px;
      font-size: 16px;
      font-weight: 800;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      box-shadow: 0 3px 10px rgba(107, 93, 184, 0.22);
      transition: all 0.15s ease;
      margin-bottom: 12px;
    }
    .play-hero-btn:active {
      transform: scale(0.98);
      filter: brightness(1.15);
    }
    .play-hero-btn:hover {
      background: #5a4da8;
      transform: translateY(-2px);
      box-shadow: 0 6px 16px rgba(107, 93, 184, 0.28);
    }
    .play-hero-btn.btn-gold {
      background: #0ea5b0;
      box-shadow: 0 4px 15px rgba(14, 165, 176, 0.22);
    }
    .play-hero-btn.btn-purple {
      background: #806fc7;
      box-shadow: 0 4px 15px rgba(107, 93, 184, 0.22);
    }
    .play-hero-btn.btn-cyan {
      background: #0ea5b0;
      box-shadow: 0 4px 15px rgba(14, 165, 176, 0.22);
    }

    .btn-group {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 14px;
    }
    button.sub-btn {
      background: #ffffff;
      color: #474758;
      border: 1px solid var(--border);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }
    button.sub-btn:hover { background: #f0f0f4; color: #2d2944; border-color: #c6c1dd; }

    .obs-box {
      background: #f3f3f6;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px 12px;
      font-family: monospace;
      font-size: 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: #5a4da8;
    }
    .copy-btn {
      background: #ffffff;
      color: #474758;
      border: 1px solid var(--border);
      padding: 4px 10px;
      font-size: 11px;
      border-radius: 4px;
      cursor: pointer;
    }
    .copy-btn:hover { background: #f0f0f4; }

    /* 全域快捷控制工具列 */
    .global-toolbar {
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 12px 16px;
      margin-bottom: 16px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      box-shadow: 0 2px 8px rgba(26, 26, 31, 0.08);
    }
    .toolbar-group {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .toolbar-label {
      font-size: 12px;
      color: var(--muted);
      font-weight: 700;
      margin-right: 4px;
    }
    .variable-control-row {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      margin: 8px 0;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }
    .variable-control-row input {
      width: 82px;
      padding: 6px 8px;
      border: 1px solid var(--border);
      border-radius: 7px;
      color: #242431;
      background: #fff;
      font: 700 13px/1 system-ui, sans-serif;
    }
    .control-hint { color: #8b88a0; font-weight: 600; }
    .tb-btn {
      background: #ffffff;
      color: #474758;
      border: 1px solid var(--border);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
    }
    .tb-btn:hover { background: #f0f0f4; border-color: #c6c1dd; transform: translateY(-1px); }
    .tb-btn:active { transform: scale(0.97); }
    .tb-btn-danger { background: #fff1f2; border-color: #fda4af; color: #be123c; }
    .tb-btn-danger:hover { background: #ffe4e6; border-color: #fb7185; }
    .tb-btn-active { background: #6b5db8; border-color: #6b5db8; color: #fff; }

    /* 即時置頂預覽窗格 */
    .preview-container {
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: 14px;
      /* Keep the stage in view while the operator scrolls through controls. */
      height: min(72vh, 760px);
      min-height: 520px;
      position: sticky;
      top: 16px;
      z-index: 20;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      margin-bottom: 20px;
      box-shadow: 0 4px 16px rgba(26, 26, 31, 0.10);
    }
    .preview-header {
      background: #ffffff;
      padding: 8px 16px;
      font-size: 13px;
      color: var(--muted);
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .preview-sticky-hint {
      margin-left: 8px;
      color: #6b5db8;
      font-size: 11px;
      font-weight: 800;
      white-space: nowrap;
    }
    .preview-iframe-wrap {
      width: 100%;
      height: 100%;
      min-height: 0;
      flex: 1 1 auto;
      position: relative;
      transition: background 0.2s ease;
    }
    .preview-bg-dark { background: #1a1a1f !important; }
    .preview-bg-checker {
      background-color: #f0f0f4 !important;
      background-image: linear-gradient(45deg, #e0e0e6 25%, transparent 25%),
                        linear-gradient(-45deg, #e0e0e6 25%, transparent 25%),
                        linear-gradient(45deg, transparent 75%, #e0e0e6 75%),
                        linear-gradient(-45deg, transparent 75%, #e0e0e6 75%) !important;
      background-size: 20px 20px !important;
      background-position: 0 0, 0 10px, 10px -10px, -10px 0px !important;
    }
    .preview-bg-green { background: #00ff00 !important; }
    iframe {
      width: 100%;
      height: 100%;
      border: none;
      background: transparent;
    }

    /* 分類導航標籤 Bar */
    .nav-tabs {
      display: flex;
      gap: 8px;
      overflow-x: auto;
      padding-bottom: 8px;
      margin-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }
    .nav-tab {
      background: #ffffff;
      color: #6b6b80;
      border: 1px solid var(--border);
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s ease;
    }
    .nav-tab:hover { background: #f0f0f4; color: #2d2944; }
    .nav-tab.active {
      background: #6b5db8;
      color: #ffffff;
      border-color: #6b5db8;
      box-shadow: 0 4px 12px rgba(107, 93, 184, 0.22);
    }

    @media (max-width: 720px) {
      body { padding: 16px; }
      .header {
        align-items: flex-start;
        flex-direction: column;
        gap: 10px;
      }
      .header h1 {
        font-size: 22px;
        overflow-wrap: anywhere;
      }
      .header > div:last-child { text-align: left !important; }
      .global-toolbar {
        align-items: stretch;
        flex-direction: column;
      }
      .toolbar-group {
        width: 100%;
        min-width: 0;
      }
      .toolbar-group:last-child .tb-btn { width: 100%; justify-content: center; }
      .preview-container {
        top: 8px;
        height: min(68vh, 620px);
        min-height: 420px;
      }
      .preview-header {
        align-items: flex-start;
        flex-direction: column;
        gap: 2px;
      }
      .preview-sticky-hint { margin-left: 0; }
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>Stream Interactive Workbench</h1>
      <p>管理直播互動遊戲、OBS 圖層與觀眾活動。選擇工具後即可即時預覽與測試。</p>
    </div>
    <div style="text-align: right;">
      <span class="tag tag-live">● 系統運作中</span>
    </div>
  </div>

  <!-- 全域快捷控制工具列 -->
  <div class="global-toolbar">
    <div class="toolbar-group">
      <span class="toolbar-label">畫面控制：</span>
      <button class="tb-btn tb-btn-danger" onclick="triggerCleanReset('all', this)">
        <span>清除所有畫面</span>
      </button>
    </div>

    <div class="toolbar-group">
      <span class="toolbar-label">預覽背景：</span>
      <button class="tb-btn tb-btn-active" id="btn-bg-dark" onclick="setPreviewBg('dark')">深色</button>
      <button class="tb-btn" id="btn-bg-checker" onclick="setPreviewBg('checker')">透明棋盤格</button>
      <button class="tb-btn" id="btn-bg-green" onclick="setPreviewBg('green')">綠幕</button>
    </div>

    <div class="toolbar-group">
      <span class="toolbar-label">音效：</span>
      <button class="tb-btn" onclick="testUiSound('coin')">投幣音</button>
      <button class="tb-btn" onclick="testUiSound('chime')">中獎提示</button>
      <button class="tb-btn" onclick="testUiSound('beep')">提示音</button>
    </div>

    <div class="toolbar-group">
      <button class="tb-btn" onclick="copyUrl('url-all')">複製 OBS 網址</button>
    </div>
  </div>

  <!-- 置頂即時預覽視窗 -->
  <div class="preview-container">
    <div class="preview-header">
      <span>即時圖層預覽 <span class="preview-sticky-hint">捲動控制區時保持可見</span></span>
      <span>按下工具卡片的測試按鈕即可觸發動畫</span>
    </div>
    <div class="preview-iframe-wrap preview-bg-dark" id="preview-iframe-wrap">
    <iframe id="preview-iframe" src="__INTERACTIVE_OVERLAY_PATH__"></iframe>
    </div>
  </div>

  <!-- 分類篩選導航標籤 Bar -->
  <div class="nav-tabs">
    <button class="nav-tab active" onclick="switchTab('all')">全部工具</button>
    <button class="nav-tab" onclick="switchTab('cat1')">抽獎與運氣遊戲</button>
    <button class="nav-tab" onclick="switchTab('cat2')">直播互動 HUD</button>
    <button class="nav-tab" onclick="switchTab('cat3')">社群預測與指令</button>
    <button class="nav-tab" onclick="switchTab('cat4')">音樂與點歌</button>
    <button class="nav-tab" onclick="switchTab('cat5')">即時翻譯</button>
    <button class="nav-tab" onclick="switchTab('cat6')">通知與活動</button>
  </div>

  <div class="grid" id="cards-grid">
    <!-- =================================================================== -->
    <!-- CAT-1 抽卡與運氣遊戲 (Minigames) -->
    <!-- =================================================================== -->

    <!-- 1. 二次元星空抽卡 -->
    <div class="card" data-cat="cat1">
      <div class="card-header">
        <h2>✨ 二次元星空抽卡 (Card Gacha)</h2>
        <span class="tag" style="background: rgba(236, 72, 153, 0.2); color: #f472b6;">手遊召喚</span>
      </div>
      <p class="desc">撕開卡包真實錄音、向量衝擊光環、3D 翻牌、天樞星輝羅盤全息閃卡。</p>
      <button class="play-hero-btn btn-purple" onclick="playRandomCardGacha(false)">
        <span>🌟 正常單抽一次 (真實隨機出貨)</span>
      </button>
      <button class="play-hero-btn btn-gold" onclick="playRandomCardGacha(true)">
        <span>👑 正常十連抽一次 (含保底機制)</span>
      </button>
      <div class="btn-group">
        <button class="sub-btn" onclick="triggerEvent({type: 'gacha.card.pulled', user_name: '課長小明', card: {name: '星海夏日 · 詩音', rarity: 'SSR', image: '/assets/characters/ssr_shion.png', quote: '載波信號已鎖定，今晚由我伴飛。'}})">測試【SSR 歐皇金光】</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'gacha.card.pulled', user_name: '觀眾阿華', card: {name: '漫步日常 · 詩音', rarity: 'SR', image: '/assets/characters/sr_shion.png', quote: '今天直播很開心呢，一起加油吧～'}})">測試【SR 紫光脈衝】</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'gacha.card.pulled', user_name: '路人小李', card: {name: '冒險茸茸 · 弗芬頓紳士', rarity: 'R', image: '/assets/characters/r_fuffington.png', quote: '雖然在下身材嬌小，但冒險的心可是無與倫比！'}})">測試【R 卡 普通翻牌】</button>
        <button class="sub-btn" onclick="playRandomCardGacha(true)">測試【十連抽全展開】</button>
        <button class="sub-btn danger" onclick="triggerCleanReset('card', this)">🚨 重置卡牌</button>
      </div>
      <div class="obs-box">
        <span id="url-card-gacha">http://localhost:18767/overlay/game/card-gacha</span>
        <button class="copy-btn" onclick="copyUrl('url-card-gacha')">複製 OBS 網址</button>
      </div>
    </div>

    <!-- 2. 實體日式扭蛋機 -->
    <div class="card" data-cat="cat1">
      <div class="card-header">
        <h2>🎰 實體日式扭蛋機 (Gashapon)</h2>
        <span class="tag" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24;">秋葉原扭蛋</span>
      </div>
      <p class="desc">金屬投幣聲、旋鈕 360 度轉動阻尼、滾落震動、晶球彈開模型亮相。</p>
      <button class="play-hero-btn btn-gold" onclick="playRandomGashapon()">
        <span>🎰 正常投幣扭一下 (隨機出貨)</span>
      </button>
      <div class="btn-group">
        <button class="sub-btn" onclick="triggerEvent({type: 'game.gashapon.pulled', user_name: '扭蛋愛好者', toy: {name: '機甲守衛 Q 版公仔', desc: '★ 機甲先鋒限定收藏 ★', image: '/assets/toys/toy_robot.png'}})">測試【機甲守衛】</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'game.gashapon.pulled', user_name: '散客', toy: {name: '熱血冒險家 探險公仔', desc: '★ 遺跡探索限定收藏 ★', image: '/assets/toys/toy_adventurer.png'}})">測試【冒險家】</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'game.gashapon.pulled', user_name: '路人', toy: {name: '弗芬頓紳士 絨毛布偶', desc: '★ 療癒毛球限定收藏 ★', image: '/assets/toys/toy_fuff.png'}})">測試【弗芬頓】</button>
        <button class="sub-btn danger" onclick="triggerCleanReset('gashapon', this)">🚨 重置扭蛋機</button>
      </div>
      <div class="obs-box">
        <span id="url-gashapon">http://localhost:18767/overlay/game/gashapon</span>
        <button class="copy-btn" onclick="copyUrl('url-gashapon')">複製 OBS 網址</button>
      </div>
    </div>

    <!-- 3. 寺廟靈驗擲筊 -->
    <div class="card" data-cat="cat1">
      <div class="card-header">
        <h2>🙏 寺廟靈驗擲筊 (BwaBwei)</h2>
        <span class="tag" style="background: rgba(239, 68, 68, 0.2); color: #f87171;">台灣民俗</span>
      </div>
      <p class="desc">紅木拋物線自旋翻滾、物理木塊碰撞音效、神明指點吉祥光環。</p>
      <button class="play-hero-btn" onclick="playRandomBwei()">
        <span>🙏 誠心擲筊一次 (隨機機率)</span>
      </button>
      <div class="btn-group">
        <button class="sub-btn" onclick="triggerEvent({type: 'game.bwei.tossed', user_name: '小明', question: '能通關嗎？', result: 'sheng', name: '聖筊', desc: '神明贊同，大吉大利！', left: 'flat', right: 'curved'})">必出【聖筊（一平一凸）】</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'game.bwei.tossed', user_name: '阿華', question: '該睡了嗎？', result: 'xiao', name: '笑筊', desc: '神明微笑，若有所思。', left: 'flat', right: 'flat'})">必出【笑筊（雙平朝上）】</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'game.bwei.tossed', user_name: '大雄', question: '能吃宵夜？', result: 'yin', name: '陰筊', desc: '神明不允，另擇良時。', left: 'curved', right: 'curved'})">必出【陰筊（雙凸朝上）】</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'game.bwei.tossed', user_name: '天選之人', question: '會發財嗎？', result: 'standing', name: '立筊', desc: '神蹟顯靈！彩光籠罩！', left: 'curved', right: 'standing'})">神蹟【立筊（萬分之一）】</button>
        <button class="sub-btn danger" onclick="triggerCleanReset('bwei', this)">🚨 重置擲筊</button>
      </div>
      <div class="obs-box">
        <span id="url-bwei">http://localhost:18767/overlay/game/bwei</span>
        <button class="copy-btn" onclick="copyUrl('url-bwei')">複製 OBS 網址</button>
      </div>
    </div>

    <!-- 4. 復古拉霸機 -->
    <div class="card" data-cat="cat1">
      <div class="card-header">
        <h2>🎰 復古拉霸機 (Classic Slot)</h2>
        <span class="tag" style="background: rgba(16, 185, 129, 0.2); color: #34d399;">拉斯維加斯</span>
      </div>
      <p class="desc">實體拉桿物理下扳、滾輪機械式逐輪急停、777 爆獎警報與金幣雨噴發。</p>
      <button class="play-hero-btn btn-gold" onclick="playRandomSlot()">
        <span>🎰 正常拉桿滾動 (隨機機率)</span>
      </button>
      <div class="btn-group">
        <button class="sub-btn" onclick="triggerEvent({type: 'game.slot.rolled', user_name: '散客', bet: 20, reels: ['LEMON', 'BELL', '7'], win: 0, multiplier: 0})">測試【未中獎落空】</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'game.slot.rolled', user_name: '常客', bet: 50, reels: ['CHERRY', 'CHERRY', 'BELL'], win: 100, multiplier: 2})">測試【櫻桃二連（2x 小獎）】</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'game.slot.rolled', user_name: '老手', bet: 50, reels: ['CHERRY', 'CHERRY', 'CHERRY'], win: 250, multiplier: 5})">測試【櫻桃三連（5x 彩金）】</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'game.slot.rolled', user_name: '大亨', bet: 100, reels: ['BAR', 'BAR', 'BAR'], win: 2000, multiplier: 20})">測試【BAR BAR BAR（20x 高額）】</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'game.slot.rolled', user_name: '幸運星', bet: 100, reels: ['7', '7', '7'], win: 5000, multiplier: 50, desc: '777 爆棚！'})">測試【777 JACKPOT（50x 大獎）】</button>
        <button class="sub-btn danger" onclick="triggerCleanReset('slot', this)">🚨 重置拉霸機</button>
      </div>
      <div class="obs-box">
        <span id="url-slot">http://localhost:18767/overlay/game/slot</span>
        <button class="copy-btn" onclick="copyUrl('url-slot')">複製 OBS 網址</button>
      </div>
    </div>

    <!-- 5. 命運幸運大轉盤 -->
    <div class="card" data-cat="cat1">
      <div class="card-header">
        <h2>🎡 命運幸運大轉盤 (Wheel of Fortune)</h2>
        <span class="tag" style="background: rgba(168, 85, 247, 0.2); color: #c084fc;">電視綜藝</span>
      </div>
      <p class="desc">多色漸層色塊圓盤、真實棘爪撥動卡嗒音效、指針回彈與減速停格。</p>
      <button class="play-hero-btn" onclick="playRandomWheel()">
        <span>🎡 轉動幸運大轉盤 (隨機停止)</span>
      </button>
      <div class="btn-group">
        <button class="sub-btn" onclick="triggerEvent({type: 'game.wheel.spun', user_name: '大胃王', items: ['頭獎 1000 點', '銘謝惠顧', '再來一次', '三獎 200 點', '喝苦茶一杯'], target_index: 0})">測試命中【頭獎 1000 點】</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'game.wheel.spun', user_name: '小衰神', items: ['頭獎 1000 點', '銘謝惠顧', '再來一次', '三獎 200 點', '喝苦茶一杯'], target_index: 1})">測試命中【銘謝惠顧】</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'game.wheel.spun', user_name: '苦主', items: ['頭獎 1000 點', '銘謝惠顧', '再來一次', '三獎 200 點', '喝苦茶一杯'], target_index: 4})">測試命中【喝苦茶一杯】</button>
        <button class="sub-btn danger" onclick="triggerCleanReset('wheel', this)">🚨 重置轉盤</button>
      </div>
      <div class="obs-box">
        <span id="url-wheel">http://localhost:18767/overlay/game/wheel</span>
        <button class="copy-btn" onclick="copyUrl('url-wheel')">複製 OBS 網址</button>
      </div>
    </div>

    <!-- 6. 命運硬幣 -->
    <div class="card" data-cat="cat1">
      <div class="card-header">
        <h2>🪙 命運硬幣</h2>
        <span class="tag" style="background: #e8f7f8; color: #0b7f88;">投擲工具</span>
      </div>
      <p class="desc">單獨的硬幣工具：翻騰、落地、結果鎖定與音效，畫面和骰子工具分開控制。</p>
      <button class="play-hero-btn btn-cyan" onclick="playRandomCoin()">
        <span>拋硬幣</span>
      </button>
      <div class="btn-group">
        <button class="sub-btn" onclick="triggerEvent({type: 'game.coin.flipped', user_name: '決策者', side: '正面'})">硬幣【必出 正面】</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'game.coin.flipped', user_name: '決策者', side: '反面'})">硬幣【必出 反面】</button>
        <button class="sub-btn danger" onclick="triggerCleanReset('coin', this)">重置硬幣</button>
      </div>
      <div class="obs-box">
        <span id="url-coin">http://localhost:18767/overlay/game/coin</span>
        <button class="copy-btn" onclick="copyUrl('url-coin')">複製 OBS 網址</button>
      </div>
    </div>

    <!-- 7. 3D 擲骰 -->
    <div class="card" data-cat="cat1">
      <div class="card-header">
        <h2>🎲 3D 擲骰</h2>
        <span class="tag" style="background: #eeeafd; color: #5a4da8;">骰子工具</span>
      </div>
      <p class="desc">參考 GACHAGO／Skymiku Dice 的單骰、多骰與方向投擲；結果由事件提供，動畫負責呈現投擲過程。</p>
      <div style="display: flex; gap: 8px; margin-bottom: 8px;">
        <button class="play-hero-btn btn-purple" style="flex: 1;" onclick="playRandomDice(1)">
          <span>單骰</span>
        </button>
        <button class="play-hero-btn btn-cyan" style="flex: 1;" onclick="playRandomDice(2)">
          <span>雙骰</span>
        </button>
        <button class="play-hero-btn" style="flex: 1;" onclick="playRandomDice(3)">
          <span>三骰</span>
        </button>
      </div>
      <div class="btn-group" style="align-items: center;">
        <span class="toolbar-label">投擲方向</span>
        <button class="sub-btn" onclick="playRandomDice(1, 'top')">上方</button>
        <button class="sub-btn" onclick="playRandomDice(1, 'bottom')">下方</button>
        <button class="sub-btn" onclick="playRandomDice(1, 'left')">左側</button>
        <button class="sub-btn" onclick="playRandomDice(1, 'right')">右側</button>
      </div>
      <div class="btn-group">
        <button class="sub-btn" onclick="triggerEvent({type: 'game.dice.rolled', user_name: '骰神', total: 1, rolls: [1], direction: 'top', detail: '1d6 = 1'})">結果 1</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'game.dice.rolled', user_name: '骰神', total: 6, rolls: [6], direction: 'left', detail: '1d6 = 6'})">結果 6</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'game.dice.rolled', user_name: '雙骰手', total: 12, rolls: [6, 6], direction: 'right', detail: '2d6 = 6 + 6 (雙六豹子)'})">雙骰 6+6</button>
        <button class="sub-btn danger" onclick="triggerCleanReset('dice', this)">重置骰子</button>
      </div>
      <div class="obs-box">
        <span id="url-dice">http://localhost:18767/overlay/game/dice</span>
        <button class="copy-btn" onclick="copyUrl('url-dice')">複製 OBS 網址</button>
      </div>
    </div>

    <!-- 8. 骰寶比大小賭博 -->
    <div class="card" data-cat="cat1">
      <div class="card-header">
        <h2>🎲 骰寶比大小賭博 (Gamble Minigame 3D Sic Bo)</h2>
        <span class="tag" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24;">3D 碗內碰撞</span>
      </div>
      <p class="desc">!gamble 押大押小、金屬骰盅搖晃、揭盅 3 顆實體 3D 骰子碗內激烈碰撞彈跳與圍骰特寫。</p>
      <div style="display: flex; gap: 8px;">
        <button class="play-hero-btn btn-gold" style="flex: 1;" onclick="triggerEvent({type: 'game.gamble.resolved', user_name: '骰寶王', bet: 50, side_chosen: '大', dice_roll: 5, winning_side: '大', won: true, win_amount: 100, balance: 650})">
          <span>👑 押大 $50 (開 5 點 - 獲勝翻倍)</span>
        </button>
        <button class="play-hero-btn btn-purple" style="flex: 1;" onclick="triggerEvent({type: 'game.gamble.resolved', user_name: '散客', bet: 30, side_chosen: '小', dice_roll: 4, winning_side: '大', won: false, win_amount: 0, balance: 220})">
          <span>💸 押小 $30 (開 4 點 - 落敗扣點)</span>
        </button>
      </div>
      <div class="btn-group">
        <button class="sub-btn" onclick="triggerEvent({type: 'game.gamble.resolved', user_name: '神算子', bet: 100, side_chosen: '大', dice_roll: 6, winning_side: '大', won: true, win_amount: 200, balance: 1200})">測試【押大 $100 獲勝 (開 6 點)】</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'game.gamble.resolved', user_name: '逆轉王', bet: 100, side_chosen: '小', dice_roll: 1, winning_side: '小', won: true, win_amount: 200, balance: 880})">測試【押小 $100 獲勝 (開 1 點)】</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'game.gamble.resolved', user_name: '倒楣鬼', bet: 50, side_chosen: '大', dice_roll: 3, winning_side: '圍骰', won: false, win_amount: 0, balance: 150})">測試【開出 3 點 圍骰通殺】</button>
        <button class="sub-btn danger" onclick="triggerCleanReset('gamble', this)">🚨 重置骰寶</button>
      </div>
      <div class="obs-box">
        <span id="url-gamble">http://localhost:18767/overlay/game/gamble</span>
        <button class="copy-btn" onclick="copyUrl('url-gamble')">複製 OBS 網址</button>
      </div>
    </div>

    <!-- =================================================================== -->
    <!-- CAT-2 實況互動 HUD (Stream HUDs) -->
    <!-- =================================================================== -->

    <!-- 8. 實況自訂計數器 -->
    <div class="card" data-cat="cat2">
      <div class="card-header">
        <h2>📊 實況自訂計數器 (Custom Counter HUD)</h2>
        <span class="tag" style="background: rgba(56, 189, 248, 0.2); color: #38bdf8;">HUD 浮動條</span>
      </div>
      <p class="desc">支援 !counter, !addcounter, !setcounter，數字即時彈跳並持久化儲存。</p>
      <div class="variable-control-row">
        <label for="counter-delta-input">調整量</label>
        <input id="counter-delta-input" type="number" min="1" step="1" value="1" aria-label="計數器調整量" />
        <span id="counter-value-hint" class="control-hint">目前值：12</span>
      </div>
      <div style="display: flex; gap: 8px;">
        <button class="play-hero-btn btn-gold" style="flex: 1;" onclick="sendDemoCounterDelta(1)">
          <span>💀 主播死亡 + 調整量</span>
        </button>
        <button class="play-hero-btn" style="flex: 1;" onclick="sendDemoCounterDelta(-1)">
          <span>↩️ 手誤修正 - 調整量</span>
        </button>
      </div>
      <div class="btn-group">
        <button class="sub-btn" onclick="triggerEvent({type: 'counter.changed', counter_id: 'wins', name: '今日吃雞勝場', count: 5, delta: 1})">👑 今日吃雞勝場 +1</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'counter.changed', counter_id: 'water', name: '喝水打卡', count: 8, delta: 1})">💧 喝水打卡 +1</button>
        <button class="sub-btn danger" onclick="triggerEvent({type: 'counter.changed', counter_id: 'deaths', name: '主播受苦死亡', count: 0, delta: 0})">🔄 計數歸零</button>
      </div>
      <div class="obs-box">
        <span id="url-counter">http://localhost:18767/overlay/hud/counter</span>
        <button class="copy-btn" onclick="copyUrl('url-counter')">複製 OBS 網址</button>
      </div>
    </div>

    <!-- 9. 觀眾互動排隊叫號 -->
    <div class="card" data-cat="cat2">
      <div class="card-header">
        <h2>👥 觀眾互動排隊叫號 (Queue Service)</h2>
        <span class="tag" style="background: rgba(168, 85, 247, 0.2); color: #c084fc;">隊列叫號</span>
      </div>
      <p class="desc">支援 !qjoin, !qleave, !qnext，多名額叫號彈窗閃爍亮起。</p>
      <button class="play-hero-btn btn-purple" onclick="triggerEvent({type: 'queue.called', session_id: 'q_demo', called_users: [{user_name: '忠實觀眾阿明', note: '鑽石段位'}, {user_name: '小美喵喵', note: '輔助位'}], remaining_count: 5, remaining_entries: [{user_name: '玩家C', note: '中路'}, {user_name: '玩家D', note: '坦克'}, {user_name: '玩家E', note: '新加入'}]})">
        <span>🔔 叫號唱名彈窗 (請玩家出列)</span>
      </button>
      <div class="btn-group">
        <button class="sub-btn" onclick="triggerEvent({type: 'queue.updated', session_id: 'q_demo', status: 'open', title: '週五觀眾同樂賽', waiting_count: 8, entries: [{user_name: '忠實觀眾阿明', note: '鑽石段位'}, {user_name: '小美喵喵', note: '輔助位'}, {user_name: '玩家C', note: '中路'}, {user_name: '玩家D', note: '坦克'}, {user_name: '新手小豪', note: '新加入'}], latest_joined: {user_name: '新手小豪', position: 8}})">🟢 開放排隊 / 顯示清單</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'queue.called', session_id: 'q_demo', called_users: [{user_name: '玩家A'}, {user_name: '玩家B'}, {user_name: '玩家C'}, {user_name: '玩家D'}], remaining_count: 2, remaining_entries: [{user_name: '玩家E', note: '候補'}, {user_name: '玩家F', note: '候補'}]})">👥 多名額叫號 (一次叫4人)</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'queue.updated', session_id: 'q_demo', status: 'closed', waiting_count: 8, entries: [{user_name: '玩家A'}, {user_name: '玩家B'}, {user_name: '玩家C'}]})">🔴 截止收單關閉 (!qstop)</button>
        <button class="sub-btn danger" onclick="triggerEvent({type: 'queue.updated', session_id: 'q_demo', status: 'closed', waiting_count: 0, entries: []})">🗑️ 清空排隊清單 (!qclear)</button>
      </div>
      <div class="obs-box">
        <span id="url-queue">http://localhost:18767/overlay/hud/queue</span>
        <button class="copy-btn" onclick="copyUrl('url-queue')">複製 OBS 網址</button>
      </div>
    </div>

    <!-- 10. 活躍觀眾抽籤選人 -->
    <div class="card" data-cat="cat2">
      <div class="card-header">
        <h2>🎁 活躍觀眾抽籤選人 (Audience Picker)</h2>
        <span class="tag" style="background: rgba(16, 185, 129, 0.2); color: #34d399;">幸運抽籤</span>
      </div>
      <p class="desc">支援 !pickuser，從最近 10 分鐘活躍聊天者中抽取並展示金色中獎彈窗。</p>
      <button class="play-hero-btn" onclick="triggerEvent({type: 'picker.selected', user_name: '幸運兒大雄', user_id: 'u_999', pool_size: 42, minutes: 10})">
        <span>🏆 發起抽籤並抽出幸運兒 (@幸運兒大雄)</span>
      </button>
      <div class="btn-group">
        <button class="sub-btn" onclick="triggerEvent({type: 'picker.selected', user_name: '鐵粉阿明', user_id: 'u_101', pool_size: 68, minutes: 15})">測試【抽出超級鐵粉 (@鐵粉阿明)】</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'picker.selected', user_name: '萌新小菜', user_id: 'u_202', pool_size: 25, minutes: 5})">測試【抽出新進觀眾 (@萌新小菜)】</button>
        <button class="sub-btn danger" onclick="triggerCleanReset('picker', this)">🚨 關閉抽籤彈窗</button>
      </div>
      <div class="obs-box">
        <span id="url-picker">http://localhost:18767/overlay/hud/picker</span>
        <button class="copy-btn" onclick="copyUrl('url-picker')">複製 OBS 網址</button>
      </div>
    </div>

    <!-- 11. 主播自訂歌單點唱 -->
    <div class="card" data-cat="cat2">
      <div class="card-header">
        <h2>🎤 主播自訂歌單點唱 (Cover Song Service)</h2>
        <span class="tag" style="background: rgba(236, 72, 153, 0.2); color: #f472b6;">點唱清單</span>
      </div>
      <p class="desc">管理主播拿手曲庫，支援觀眾 !cr 點唱、!cover 查詢與進度推進。</p>
      <div style="display: flex; gap: 8px;">
        <button class="play-hero-btn btn-gold" style="flex: 1;" onclick="triggerEvent({type: 'cover.requested', request_id: 1, song_id: 'lemon', title: 'Lemon', artist: '米津玄師', user_name: '歌迷阿光', queue_position: 1})">
          <span>🎶 觀眾點播《Lemon》</span>
        </button>
        <button class="play-hero-btn btn-purple" style="flex: 1;" onclick="triggerEvent({type: 'cover.current', song_title: 'First Love', artist: '宇多田光', user_name: '主播', status: 'singing'})">
          <span>🎤 演唱中《First Love》</span>
        </button>
      </div>
      <div class="btn-group">
        <button class="sub-btn" onclick="triggerEvent({type: 'cover.requested', request_id: 2, song_id: 'idol', title: 'アイドル', artist: 'YOASOBI', user_name: '追番隊長', queue_position: 2})">點播《アイドル (Idol)》</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'cover.current', song_title: '晴天', artist: '周杰倫', user_name: '主播', status: 'singing'})">演唱完畢切換下一首《晴天》</button>
        <button class="sub-btn danger" onclick="triggerEvent({type: 'cover.cleared', cleared_by: '中控台'})">🗑️ 清空點唱畫面與隊列</button>
      </div>
      <div class="obs-box">
        <span id="url-cover">http://localhost:18767/overlay/hud/cover</span>
        <button class="copy-btn" onclick="copyUrl('url-cover')">複製 OBS 網址</button>
      </div>
    </div>

    <!-- 12. 實況馬拉松倒數計時 -->
    <div class="card" data-cat="cat2">
      <div class="card-header">
        <h2>⏱️ 實況馬拉松倒數計時 (Subathon Timer)</h2>
        <span class="tag" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24;">馬拉松持久戰</span>
      </div>
      <p class="desc">支援 !time, !addtime, 贊助/訂閱自動延長、倒數至零警示與暫停。</p>
      <div class="variable-control-row">
        <label for="subathon-delta-input">調整秒數</label>
        <input id="subathon-delta-input" type="number" min="1" step="1" value="300" aria-label="馬拉松調整秒數" />
        <span id="subathon-value-hint" class="control-hint">目前值：7800 秒</span>
      </div>
      <div style="display: flex; gap: 8px;">
        <button class="play-hero-btn" style="flex: 1;" onclick="triggerEvent({type: 'subathon.timer.updated', timer_id: 'main', remaining_seconds: 7800, formatted: '02:10:00', is_running: true, delta: 600})">
          <span>⏱️ 馬拉松正在倒數 (02:10:00)</span>
        </button>
        <button class="play-hero-btn btn-gold" style="flex: 1;" onclick="triggerEvent({type: 'subathon.timer.updated', timer_id: 'main', remaining_seconds: 7800, formatted: '02:10:00', is_running: false, delta: 0})">
          <span>⏸️ 暫停倒數計時</span>
        </button>
      </div>
      <div class="btn-group">
        <button class="sub-btn" onclick="sendDemoSubathonDelta(1)">➕ 延長 + 調整秒數</button>
        <button class="sub-btn" onclick="sendDemoSubathonDelta(-1)">➖ 扣除 - 調整秒數</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'subathon.visibility', action: 'hide', hidden: true})">🙈 隱藏計時器</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'subathon.visibility', action: 'show', visible: true})">👁️ 顯示計時器</button>
        <button class="sub-btn danger" onclick="triggerEvent({type: 'subathon.timer.updated', timer_id: 'main', remaining_seconds: 30, formatted: '00:00:30', is_running: true, delta: -7000})">🚨 時間告急紅光警示 (剩 30s)</button>
        <button class="sub-btn danger" onclick="triggerCleanReset('subathon', this)">🗑️ 清空計時器畫面</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'subathon.timer.updated', timer_id: 'main', remaining_seconds: 3600, formatted: '01:00:00', is_running: true, delta: 0})">🔄 重置為 1 小時</button>
      </div>
      <div class="obs-box">
        <span id="url-subathon">http://localhost:18767/overlay/hud/subathon</span>
        <button class="copy-btn" onclick="copyUrl('url-subathon')">複製 OBS 網址</button>
      </div>
    </div>

    <!-- =================================================================== -->
    <!-- CAT-3 社群預測與指令 (Betting & Commands) -->
    <!-- =================================================================== -->

    <!-- 13. 社群下注預測盤口 -->
    <div class="card" data-cat="cat3">
      <div class="card-header">
        <h2>🎯 社群下注預測盤口 (Community Betting)</h2>
        <span class="tag" style="background: rgba(239, 68, 68, 0.2); color: #f87171;">同花大順</span>
      </div>
      <p class="desc">!bet open/lock/end/cancel，雙向彩池動態比例條、即時賠率計算與派彩。</p>
      <div class="variable-control-row">
        <label for="bet-pool-a">A 彩池</label>
        <input id="bet-pool-a" type="number" min="0" step="10" value="500" aria-label="A 彩池數值" />
        <label for="bet-pool-b">B 彩池</label>
        <input id="bet-pool-b" type="number" min="0" step="10" value="300" aria-label="B 彩池數值" />
        <button class="sub-btn" onclick="sendDemoBetPools()">套用變數彩池</button>
      </div>
      <div style="display: flex; gap: 8px;">
        <button class="play-hero-btn btn-gold" style="flex: 1;" onclick="triggerEvent({type: 'bet.opened', pool_id: 'demo_pool', title: '這把遊戲能成功吃雞嗎？', option_a: '能', option_b: '不能', status: 'open', pool_a: 500, pool_b: 300, total_pool: 800, odds_a: 1.6, odds_b: 2.67})">
          <span>🎯 開啟吃雞盤口 (能 / 不能)</span>
        </button>
        <button class="play-hero-btn btn-cyan" style="flex: 1;" onclick="triggerEvent({type: 'bet.opened', pool_id: 'demo_pool_2', title: '本關主播受苦死幾次？', option_a: '0~2次', option_b: '3次以上', status: 'open', pool_a: 400, pool_b: 400, total_pool: 800, odds_a: 2.0, odds_b: 2.0})">
          <span>🎯 開啟挑戰盤 (0~2次 / 3次+)</span>
        </button>
      </div>
      <div style="display: flex; gap: 8px;">
        <button class="play-hero-btn" style="flex: 1;" onclick="triggerEvent({type: 'bet.placed', pool_id: 'demo_pool', user_name: '忠實大粉', option: 'A', option_title: '能', amount: 200, total_pool: 1000, pool_a: 700, pool_b: 300, odds_a: 1.43, odds_b: 3.33})">
          <span>觀眾押 A ($200) 賠率浮動</span>
        </button>
        <button class="play-hero-btn btn-purple" style="flex: 1;" onclick="triggerEvent({type: 'bet.placed', pool_id: 'demo_pool', user_name: '反指標阿光', option: 'B', option_title: '不能', amount: 800, total_pool: 1800, pool_a: 700, pool_b: 1100, odds_a: 2.57, odds_b: 1.64})">
          <span>大戶重注 B ($800) 賠率逆轉</span>
        </button>
      </div>
      <div class="btn-group">
        <button class="sub-btn" onclick="triggerEvent({type: 'bet.locked', pool_id: 'demo_pool', title: '這把遊戲能成功吃雞嗎？', option_a: '能', option_b: '不能', total_pool: 1800, pool_a: 700, pool_b: 1100, odds_a: 2.57, odds_b: 1.64})">🔒 MOD 封盤截止下注</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'bet.resolved', pool_id: 'demo_pool', title: '這把遊戲能成功吃雞嗎？', winning_option: 'A', winning_title: '能', total_pool: 1800, winner_count: 5, top_winners: [{user_name: '忠實大粉', payout: 750}]})">🏆 結算【A 獲勝】派彩</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'bet.resolved', pool_id: 'demo_pool', title: '這把遊戲能成功吃雞嗎？', winning_option: 'B', winning_title: '不能', total_pool: 1800, winner_count: 8, top_winners: [{user_name: '反指標阿光', payout: 1312}]})">🏆 結算【B 獲勝】派彩</button>
        <button class="sub-btn danger" onclick="triggerEvent({type: 'bet.cancelled', pool_id: 'demo_pool', title: '這把遊戲能成功吃雞嗎？', reason: '遊戲突發斷線，本局無效', refunded_count: 12, total_refunded: 1800})">⚠️ 突發狀況：流盤退款</button>
        <button class="sub-btn danger" onclick="triggerCleanReset('bet', this)">🚨 關閉盤口 HUD</button>
      </div>
      <div class="obs-box">
        <span id="url-bet">http://localhost:18767/overlay/hud/bet</span>
        <button class="copy-btn" onclick="copyUrl('url-bet')">複製 OBS 網址</button>
      </div>
    </div>

    <!-- 14. 自訂指令動態管理 -->
    <div class="card" data-cat="cat3">
      <div class="card-header">
        <h2>⚡ 自訂指令動態管理 (Custom Commands)</h2>
        <span class="tag" style="background: rgba(14, 165, 233, 0.2); color: #38bdf8;">動態擴充</span>
      </div>
      <p class="desc">主播／MOD 在聊天室輸入 <code>!cmd add dc Discord網址</code> 後，觀眾輸入 <code>!dc</code> 會收到回覆；下方分開測試「設定」與「執行結果」。</p>
      <div style="display: flex; gap: 8px;">
        <button class="play-hero-btn" style="flex: 1;" onclick="triggerEvent({type: 'custom_cmd.changed', action: 'set', cmd_name: 'dc', response: '歡迎加入實況 Discord 群：https://discord.gg/stream'})">
          <span>⚡ 設定／啟用 !dc</span>
        </button>
        <button class="play-hero-btn btn-purple" style="flex: 1;" onclick="triggerEvent({type: 'bot.reply', source: 'custom_cmd', text: '@測試觀眾 歡迎加入實況 Discord 群：https://discord.gg/stream'})">
          <span>💬 執行 !dc 回覆</span>
        </button>
      </div>
      <div class="btn-group">
        <button class="sub-btn" onclick="triggerEvent({type: 'custom_cmd.changed', action: 'add', cmd_name: 'rules', response: '【實況守則】1. 請友善包容 2. 請勿暴雷 3. 開心看台！'})">新增 !rules 規範指令</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'custom_cmd.changed', action: 'set', cmd_name: 'yt', response: '精華剪輯頻道：https://youtube.com/@channel'})">更新 !yt 頻道指令</button>
        <button class="sub-btn danger" onclick="triggerEvent({type: 'custom_cmd.changed', action: 'del', cmd_name: 'oldcmd'})">刪除 !oldcmd 舊指令</button>
      </div>
      <div class="obs-box">
        <span id="url-cmd">http://localhost:18767/overlay/games</span>
        <button class="copy-btn" onclick="copyUrl('url-cmd')">複製 OBS 網址</button>
      </div>
    </div>

    <!-- =================================================================== -->
    <!-- CAT-4 音樂與點歌播放 (Music & Song Request) -->
    <!-- =================================================================== -->

    <!-- 15. 點歌播放系統 -->
    <div class="card" data-cat="cat4">
      <div class="card-header">
        <h2>🎵 點歌播放系統 (Song Request HUD)</h2>
        <span class="tag" style="background: rgba(168, 85, 247, 0.2); color: #c084fc;">動態黑膠</span>
      </div>
      <p class="desc">支援觀眾 !sr 點歌、YouTube 解析、旋轉黑膠唱片、音量頻譜條與 MOD 切歌。</p>
      <div style="display: flex; gap: 8px;">
        <button class="play-hero-btn btn-purple" style="flex: 1;" onclick="triggerEvent({type: 'music.playing', song_id: 1, title: '夜に駆ける (Racing into the Night)', artist: 'YOASOBI', duration_seconds: 260, duration_formatted: '04:20', user_name: '音樂愛好者', queue_length: 3})">
          <span>🎵 播放《夜に駆ける》</span>
        </button>
        <button class="play-hero-btn btn-cyan" style="flex: 1;" onclick="triggerEvent({type: 'music.playing', song_id: 2, title: '晴天 (Sunny Day)', artist: '周杰倫 (Jay Chou)', duration_seconds: 270, duration_formatted: '04:30', user_name: '老歌迷', queue_length: 2})">
          <span>🎵 播放《晴天》</span>
        </button>
      </div>
      <div class="btn-group">
        <button class="sub-btn" onclick="triggerEvent({type: 'music.requested', song_id: 3, title: 'アイドル (Idol)', artist: 'YOASOBI', user_name: '追番小隊長', position: 2})">🎶 模擬點播《アイドル》入隊</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'music.requested', song_id: 4, title: 'Lemon', artist: '米津玄師', user_name: 'J-POP粉', position: 3})">🎶 模擬點播《Lemon》入隊</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'music.skipped', song_id: 1, title: '夜に駆ける', skipped_by: 'MOD_Admin'})">⏭️ MOD 切歌 (下一首)</button>
        <button class="sub-btn danger" onclick="triggerEvent({type: 'music.cleared', cleared_by: 'MOD_Admin', count: 4})">🗑️ MOD 清空待播清單</button>
        <button class="sub-btn danger" onclick="triggerCleanReset('music', this)">🚨 立即隱藏音樂條</button>
      </div>
      <div class="obs-box">
        <span id="url-music">http://localhost:18767/overlay/hud/music</span>
        <button class="copy-btn" onclick="copyUrl('url-music')">複製 OBS 網址</button>
      </div>
    </div>

    <!-- =================================================================== -->
    <!-- CAT-5 即時多語翻譯 (Chat Translation) -->
    <!-- =================================================================== -->

    <!-- 16. 聊天室即時翻譯字幕 -->
    <div class="card" data-cat="cat5">
      <div class="card-header">
        <h2>🌐 聊天室即時翻譯字幕 (Chat Translation)</h2>
        <span class="tag" style="background: rgba(8, 145, 178, 0.2); color: #38bdf8;">多語無國界</span>
      </div>
      <p class="desc">支援 !trans [語言] &lt;文字&gt;、MOD !trans-auto 開關自動翻譯與 OBS 底部浮動字幕條。</p>
      <div style="display: flex; gap: 8px;">
        <button class="play-hero-btn btn-cyan" style="flex: 1;" onclick="triggerEvent({type: 'trans.translated', user_name: 'OverseasFan', orig_text: 'Hello everyone! Loving the stream today!', trans_text: '大家好！今天的實況太棒了！', src_lang: 'en', target_lang: 'zh-tw', auto: true})">
          <span>💬 模擬英文即時翻譯字幕</span>
        </button>
        <button class="play-hero-btn btn-purple" style="flex: 1;" onclick="triggerEvent({type: 'trans.translated', user_name: 'Sakura_JP', orig_text: '配信お疲れ様です！応援してます！', trans_text: '直播辛苦了！為您加油！', src_lang: 'ja', target_lang: 'zh-tw', auto: true})">
          <span>🇯🇵 模擬日文即時翻譯字幕</span>
        </button>
      </div>
      <div class="btn-group">
        <button class="sub-btn" onclick="triggerEvent({type: 'trans.translated', user_name: 'Minho_KR', orig_text: '오늘 방송 너무 재미있어요! 화이팅!', trans_text: '今天的實況太有趣了！加油！', src_lang: 'ko', target_lang: 'zh-tw', auto: true})">🇰🇷 模擬韓文翻譯字幕</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'trans.translated', user_name: 'Carlos_ES', orig_text: 'Hola amigo, ¡buena partida!', trans_text: '你好朋友，精彩的一局！', src_lang: 'es', target_lang: 'zh-tw', auto: true})">🇪🇸 模擬西文翻譯字幕</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'trans.setting', auto_enabled: true, updated_by: 'MOD_Admin'})">⚙️ 自動翻譯已開啟 🟢</button>
        <button class="sub-btn danger" onclick="triggerEvent({type: 'trans.setting', auto_enabled: false, updated_by: 'MOD_Admin'})">⚙️ 自動翻譯已關閉 🔴</button>
        <button class="sub-btn danger" onclick="triggerCleanReset('trans', this)">🚨 立即隱藏字幕條</button>
      </div>
      <div class="obs-box">
        <span id="url-trans">http://localhost:18767/overlay/hud/trans</span>
        <button class="copy-btn" onclick="copyUrl('url-trans')">複製 OBS 網址</button>
      </div>
    </div>

    <!-- =================================================================== -->
    <!-- CAT-6 贊助通知與乾爹 (Donation & Sponsor Alert) -->
    <!-- =================================================================== -->

    <!-- 17. 綠界/歐付寶贊助通知 -->
    <div class="card" data-cat="cat6">
      <div class="card-header">
        <h2>💖 綠界/歐付寶贊助通知 (Donation & Sponsor Alert)</h2>
        <span class="tag" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24;">斗內金幣雨</span>
      </div>
      <p class="desc">接收 ECPay / O'Pay 贊助 Webhook，自動發放點數、延長馬拉松並觸發金色通知。</p>
      <div style="display: flex; gap: 8px;">
        <button class="play-hero-btn btn-gold" style="flex: 1;" onclick="triggerEvent({type: 'donation.received', donor_name: '乾爹大老', amount: 500, amount_formatted: 'TWD $500', currency: 'TWD', message: '主播今天開台辛苦了！這把必吃雞！加油！', points_awarded: 5000, seconds_added: 2500})">
          <span>🎉 模擬贊助 TWD $500 (金幣雨＋音效)</span>
        </button>
        <button class="play-hero-btn btn-purple" style="flex: 1;" onclick="triggerEvent({type: 'donation.received', donor_name: '神秘大乾爹', amount: 3000, amount_formatted: 'TWD $3,000', currency: 'TWD', message: '今晚吃大餐！祝開台長紅！', points_awarded: 30000, seconds_added: 15000})">
          <span>👑 巨額大乾爹 TWD $3,000 (全螢幕爆閃)</span>
        </button>
      </div>
      <div class="btn-group">
        <button class="sub-btn" onclick="triggerEvent({type: 'donation.received', donor_name: '忠實大粉', amount: 100, amount_formatted: 'TWD $100', currency: 'TWD', message: '喝杯咖啡～繼續加油！', points_awarded: 1000, seconds_added: 500})">☕ 模擬小額贊助 $100</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'donation.received', donor_name: '宵夜大隊長', amount: 1000, amount_formatted: 'TWD $1,000', currency: 'TWD', message: '買宵夜給主播補補身子～', points_awarded: 10000, seconds_added: 5000})">🎁 模擬 $1,000 宵夜金</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'donation.received', donor_name: '深情小迷妹', amount: 200, amount_formatted: 'TWD $200', currency: 'TWD', message: '從一年前就開始看主播開台，每次疲憊的時候只要看到主播的笑容就充滿力量，今天也請務必元氣滿滿喔！', points_awarded: 2000, seconds_added: 1000})">💬 模擬超長真情留言</button>
        <button class="sub-btn danger" onclick="triggerCleanReset('donation', this)">🚨 立即淡出贊助彈窗</button>
      </div>
      <div class="obs-box">
        <span id="url-donation">http://localhost:18767/overlay/hud/donation</span>
        <button class="copy-btn" onclick="copyUrl('url-donation')">複製 OBS 網址</button>
      </div>
    </div>

    <!-- 18. Twitch EventSub 原生事件 -->
    <div class="card" data-cat="cat6">
      <div class="card-header">
        <h2>👾 Twitch EventSub 原生事件 (Bits / 訂閱 / 追隨)</h2>
        <span class="tag" style="background: rgba(147, 51, 234, 0.2); color: #c084fc;">Twitch 官方長連線</span>
      </div>
      <p class="desc">透過官方 EventSub WebSocket 監聽 Bits 小奇點、新訂閱/續訂、贈訂、追隨與自訂點數兌換。</p>
      <div style="display: flex; gap: 8px;">
        <button class="play-hero-btn btn-purple" style="flex: 1;" onclick="triggerEvent({type: 'twitch.cheer', bits: 100, user_name: '奇點小霸王', message: 'Cheer100 主播好強！繼續加油！'})">
          <span>💎 模擬 Bits 贊助 100 奇點 (轉贊助通知)</span>
        </button>
        <button class="play-hero-btn btn-gold" style="flex: 1;" onclick="triggerEvent({type: 'twitch.subscribe', user_name: '新晉熱血粉絲', tier: '1000', cumulative_months: 1, message: '第一個月訂閱，主播加油！'})">
          <span>⭐ 模擬 Tier 1 新訂閱 (加時 300s＋贈點)</span>
        </button>
      </div>
      <div class="btn-group">
        <button class="sub-btn" onclick="triggerEvent({type: 'twitch.channel_points.redeem', reward_id: 'rw_slot', title: '🎰 幸運拉霸 ｜ 777 機械拉霸', cost: 1, user_name: '模擬拉霸手'})">🎰 拉霸 (1 點)</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'twitch.channel_points.redeem', reward_id: 'rw_gacha', title: '🔮 星空召喚 ｜ 召喚手遊抽卡', cost: 1, user_name: '模擬召喚師'})">🔮 抽卡 (1 點)</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'twitch.channel_points.redeem', reward_id: 'rw_bwei', title: '🙏 虔誠擲筊 ｜ 寺廟神明請示', cost: 1, user_name: '虔誠信眾', user_input: '開台一切順利嗎？'})">🙏 擲筊 (1 點)</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'twitch.channel_points.redeem', reward_id: 'rw_wheel', title: '🎡 幸運轉盤 ｜ 指針大轉盤', cost: 1, user_name: '轉盤幸運兒'})">🎡 轉盤 (1 點)</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'twitch.channel_points.redeem', reward_id: 'rw_gashapon', title: '💊 實體扭蛋 ｜ 日式膠囊扭蛋', cost: 1, user_name: '模擬扭蛋控'})">💊 扭蛋 (1 點)</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'twitch.channel_points.redeem', reward_id: 'rw_coin', title: '🪙 幸運硬幣 ｜ 3D 拋擲金幣', cost: 1, user_name: '拋幣高手'})">🪙 拋幣 (1 點)</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'twitch.channel_points.redeem', reward_id: 'rw_dice', title: '🎲 命運骰子 ｜ 3D 骰子擲點', cost: 1, user_name: '命運骰客', user_input: '2d6'})">🎲 擲骰 (1 點)</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'twitch.channel_points.redeem', reward_id: 'rw_gamble', title: '🎯 幸運骰寶 ｜ 押大押小猜點數', cost: 1, user_name: '大滿貫賭徒', user_input: '大'})">🎯 骰寶 (1 點)</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'twitch.channel_points.redeem', reward_id: 'rw_checkin', title: '📡 訊號登錄 ｜ 每日連線簽到', cost: 10, user_name: '模擬訪客'})">📡 簽到 (10 點)</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'twitch.channel_points.redeem', reward_id: 'rw_queue', title: '🎟️ 艦隊集結 ｜ 觀眾同樂排隊報名', cost: 10, user_name: '同樂艦長', user_input: '遊戲ID: SkyMikuFan'})">🎟️ 排隊 (10 點)</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'twitch.channel_points.redeem', reward_id: 'rw_resync', title: '🔄 重新同步 ｜ 恢復連線', cost: 10, user_name: '回歸艦長'})">🔄 回歸 (10 點)</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'twitch.channel_points.redeem', reward_id: 'rw_offline', title: '🔌 離線申請 ｜ 斷開連線 (先退)', cost: 10, user_name: '先退探員'})">🔌 先退 (10 點)</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'twitch.channel_points.redeem', reward_id: 'rw_sleep', title: '🌙 休眠協議 ｜ 進入待機充電 (晚安)', cost: 10, user_name: '夜貓艦長'})">🌙 晚安 (10 點)</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'twitch.channel_points.redeem', reward_id: 'rw_lurk', title: '🤖 背景守護 ｜ 自動掛台模式', cost: 10, user_name: '掛台小幫手'})">🤖 掛台 (10 點)</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'twitch.channel_points.redeem', reward_id: 'rw_drink', title: '💧 冷卻循環 ｜ 強制注入冷卻液', cost: 20, user_name: '健康守護者', user_input: '記得喝大口一點！'})">💧 主播喝水 (20 點)</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'twitch.channel_points.redeem', reward_id: 'rw_posture', title: '🦾 骨架校準 ｜ 機體姿態校正', cost: 20, user_name: '健康守護者', user_input: '坐直起來伸展！'})">🦾 姿態校正 (20 點)</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'twitch.cheer', bits: 1000, user_name: '大金主', message: 'Cheer1000 今晚吃雞！'})">💎 模擬 1,000 Bits</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'twitch.subgift', user_name: '慈善大亨', total: 5, tier: '1000'})">🎁 模擬贈送 5 份訂閱</button>
        <button class="sub-btn" onclick="triggerEvent({type: 'twitch.follow', user_name: '路過的小精靈'})">🌟 模擬新觀眾追隨</button>
        <button class="sub-btn danger" onclick="triggerCleanReset('twitch', this)">🚨 立即淡出通知彈窗</button>
      </div>
      <div class="obs-box">
        <span id="url-eventsub">http://localhost:18767/overlay/hud/donation</span>
        <button class="copy-btn" onclick="copyUrl('url-eventsub')">複製 OBS 網址</button>
      </div>
    </div>

    <!-- 19. 全遊戲通用萬能 URL -->
    <div class="card" style="grid-column: 1 / -1;" data-cat="all">
      <div class="card-header">
        <h2>🌐 全遊戲通用 OBS 網址 (All-in-One 萬能圖層)</h2>
        <span class="tag tag-live">推薦主播使用</span>
      </div>
      <p class="desc">只需在 OBS 頂層加入此單一來源，所有遊戲事件、浮動 HUD、下注盤口與贊助彈窗全自動適配呈現！</p>
      <div class="obs-box">
        <span id="url-all">http://localhost:18767/overlay/games</span>
        <button class="copy-btn" onclick="copyUrl('url-all')">複製 OBS 萬能網址</button>
      </div>
    </div>
  </div>

  <script src="__INTERACTIVE_ASSET_PREFIX__/vendor/three.min.js"></script>
  <script>
    const STATIC_DEMO = __INTERACTIVE_STATIC_DEMO__;
    async function triggerEvent(payload) {
      if (STATIC_DEMO) {
        const iframe = document.getElementById("preview-iframe");
        if (iframe && iframe.contentWindow) {
          iframe.contentWindow.postMessage({ type: "interactive.demo.event", payload: payload }, "*");
          return { ok: true, static_demo: true };
        }
        return { ok: false, error: "preview_not_ready" };
      }
      try {
        await fetch("/api/test-event", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
      } catch (err) {
        console.error("Test event failed:", err);
      }
    }

    function showToast(msg, isSuccess = true) {
      let c = document.getElementById("toast-container");
      if (!c) {
        c = document.createElement("div");
        c.id = "toast-container";
        c.style.cssText = "position:fixed;bottom:24px;right:24px;z-index:99999;display:flex;flex-direction:column;gap:8px;pointer-events:none;";
        document.body.appendChild(c);
      }
      const t = document.createElement("div");
      t.style.cssText = "background:" + (isSuccess ? "#064e3b" : "#7f1d1d") + ";color:#f8fafc;padding:12px 20px;border-radius:8px;font-size:14px;font-weight:800;box-shadow:0 10px 25px rgba(0,0,0,0.6);border:1px solid " + (isSuccess ? "#10b981" : "#ef4444") + ";transition:all 0.25s cubic-bezier(0.16, 1, 0.3, 1);transform:translateY(12px);opacity:0;";
      t.innerText = msg;
      c.appendChild(t);
      requestAnimationFrame(() => {
        t.style.transform = "translateY(0)";
        t.style.opacity = "1";
      });
      setTimeout(() => {
        t.style.opacity = "0";
        t.style.transform = "translateY(-10px)";
        setTimeout(() => t.remove(), 300);
      }, 2200);
    }

    async function triggerCleanReset(target = "all", btnEl = null) {
      if (btnEl) {
        const origText = btnEl.innerText;
        btnEl.innerText = "✅ 已清除！";
        btnEl.style.background = "#059669";
        btnEl.style.borderColor = "#10b981";
        setTimeout(() => {
          btnEl.innerText = origText;
          btnEl.style.background = "";
          btnEl.style.borderColor = "";
        }, 800);
      }
      showToast(target === "all" ? "🚨 已清除所有 OBS 畫面與特效！" : ("🚨 已清除【" + target + "】畫面！"));

      // 1. 本地預覽 iframe 立即強制清除 (0 毫秒即刻生效，雙重保險)
      try {
        const iframe = document.getElementById("preview-iframe");
        if (iframe && iframe.contentWindow) {
          if (typeof iframe.contentWindow.hideAllStages === "function") {
            iframe.contentWindow.hideAllStages({ target: target });
          }
          iframe.contentWindow.postMessage({ type: "overlay.reset", target: target }, "*");
        }
      } catch (err) {
        console.warn("Iframe local reset fallback:", err);
      }

      // 2. 廣播推播至後端與遠端連線中的所有 OBS Browser Sources
      await triggerEvent({ type: "overlay.reset", target: target });
    }

    // 預覽面板使用與正式指令相同的「目前值 + 調整量」模型，
    // 讓測試不再把 +1/-1、固定秒數或固定彩池誤當成模組本身的邏輯。
    let demoCounterValue = 12;
    let demoSubathonSeconds = 7800;

    function inputNumber(id, fallback, minimum = null) {
      const el = document.getElementById(id);
      let value = Number(el && el.value);
      if (!Number.isFinite(value)) value = fallback;
      if (minimum !== null) value = Math.max(minimum, value);
      return value;
    }

    function sendDemoCounterDelta(direction) {
      const amount = Math.max(1, Math.abs(Math.trunc(inputNumber("counter-delta-input", 1))));
      const delta = direction < 0 ? -amount : amount;
      demoCounterValue = Math.max(0, demoCounterValue + delta);
      const hint = document.getElementById("counter-value-hint");
      if (hint) hint.innerText = `目前值：${{demoCounterValue}}`;
      triggerEvent({ type: "counter.changed", counter_id: "deaths", name: "主播受苦死亡", count: demoCounterValue, delta: delta });
    }

    function sendDemoSubathonDelta(direction) {
      const amount = Math.max(1, Math.abs(Math.trunc(inputNumber("subathon-delta-input", 300))));
      const delta = direction < 0 ? -amount : amount;
      demoSubathonSeconds = Math.max(0, demoSubathonSeconds + delta);
      const hint = document.getElementById("subathon-value-hint");
      if (hint) hint.innerText = `目前值：${{demoSubathonSeconds}} 秒`;
      triggerEvent({
        type: "subathon.timer.updated",
        timer_id: "main",
        remaining_seconds: demoSubathonSeconds,
        formatted: formatDemoDuration(demoSubathonSeconds),
        is_running: true,
        delta: delta
      });
    }

    function formatDemoDuration(seconds) {
      const total = Math.max(0, Math.trunc(Number(seconds) || 0));
      const h = Math.floor(total / 3600);
      const m = Math.floor((total % 3600) / 60);
      const s = total % 60;
      return [h, m, s].map((v) => String(v).padStart(2, "0")).join(":");
    }

    function sendDemoBetPools() {
      const poolA = Math.max(0, Math.trunc(inputNumber("bet-pool-a", 500)));
      const poolB = Math.max(0, Math.trunc(inputNumber("bet-pool-b", 300)));
      const total = poolA + poolB;
      triggerEvent({
        type: "bet.placed", pool_id: "demo_pool", title: "自訂變數預測盤",
        option_a: "能", option_b: "不能", pool_a: poolA, pool_b: poolB,
        total_pool: total, odds_a: poolA ? Number((total / poolA).toFixed(2)) : 0,
        odds_b: poolB ? Number((total / poolB).toFixed(2)) : 0,
        user_name: "測試玩家", amount: 0
      });
    }

    function setPreviewBg(mode) {
      const wrap = document.getElementById("preview-iframe-wrap");
      wrap.className = "preview-iframe-wrap preview-bg-" + mode;
      document.getElementById("btn-bg-dark").classList.toggle("tb-btn-active", mode === "dark");
      document.getElementById("btn-bg-checker").classList.toggle("tb-btn-active", mode === "checker");
      document.getElementById("btn-bg-green").classList.toggle("tb-btn-active", mode === "green");
    }

    function switchTab(cat) {
      document.querySelectorAll(".nav-tab").forEach(tab => tab.classList.remove("active"));
      if (window.event && window.event.target) {
        window.event.target.classList.add("active");
      }

      const cards = document.querySelectorAll("#cards-grid .card");
      cards.forEach(card => {
        const cardCat = card.getAttribute("data-cat");
        if (cat === "all" || cardCat === cat || cardCat === "all") {
          card.style.display = "flex";
        } else {
          card.style.display = "none";
        }
      });
    }

    function testUiSound(name) {
      try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (!AudioContext) return;
        const ctx = new AudioContext();
        if (name === "coin") {
          const osc = ctx.createOscillator();
          const g = ctx.createGain();
          osc.type = "sine";
          osc.frequency.setValueAtTime(987.77, ctx.currentTime);
          osc.frequency.setValueAtTime(1318.51, ctx.currentTime + 0.08);
          g.gain.setValueAtTime(0.3, ctx.currentTime);
          g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
          osc.connect(g);
          g.connect(ctx.destination);
          osc.start();
          osc.stop(ctx.currentTime + 0.45);
        } else if (name === "chime") {
          [523.25, 659.25, 783.99, 1046.50].forEach((freq, idx) => {
            const osc = ctx.createOscillator();
            const g = ctx.createGain();
            osc.frequency.value = freq;
            g.gain.setValueAtTime(0.2, ctx.currentTime + idx * 0.08);
            g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + idx * 0.08 + 0.5);
            osc.connect(g);
            g.connect(ctx.destination);
            osc.start(ctx.currentTime + idx * 0.08);
            osc.stop(ctx.currentTime + idx * 0.08 + 0.55);
          });
        } else if (name === "beep") {
          const osc = ctx.createOscillator();
          const g = ctx.createGain();
          osc.type = "square";
          osc.frequency.setValueAtTime(440, ctx.currentTime);
          g.gain.setValueAtTime(0.2, ctx.currentTime);
          g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
          osc.connect(g);
          g.connect(ctx.destination);
          osc.start();
          osc.stop(ctx.currentTime + 0.35);
        }
      } catch (err) {
        console.error("Audio test error:", err);
      }
    }

    function copyUrl(elementId) {
      if (STATIC_DEMO) {
        showToast("GitHub Pages 是互動展示版；OBS 網址請使用本機 Surface Bridge", false);
        return;
      }
      const text = document.getElementById(elementId).innerText;
      navigator.clipboard.writeText(text).then(() => {
        showToast("📋 已複製 OBS 網址：" + text);
      });
    }

    // =========================================================================
    // 正常遊玩真實機率隨機產生器 (Live Realistic Play Generators)
    // =========================================================================

    // 1. 正常單抽 / 十連抽 (二次元動漫立繪與保底機制)
    function playRandomCardGacha(isTen = false) {
      const pool = [
        { name: "星海夏日 · 詩音", rarity: "SSR", image: "/assets/characters/ssr_shion.png", quote: "載波信號已鎖定，今晚由我伴飛。", icon: "🌟", weight: 4 },
        { name: "熾天星輝 · 艾莉亞", rarity: "SSR", image: "/assets/characters/ssr_aria.png", quote: "星輝與你同在，願命運為你降下奇蹟。", icon: "✨", weight: 4 },
        { name: "疾風守護 · 大樹", rarity: "SR", image: "/assets/characters/sr_daiki.png", quote: "交給我吧，前方的道路由我來守護！", icon: "🛡️", weight: 16 },
        { name: "漫步日常 · 詩音", rarity: "SR", image: "/assets/characters/sr_shion.png", quote: "今天直播很開心呢，一起加油吧～", icon: "🌸", weight: 16 },
        { name: "冒險茸茸 · 弗芬頓紳士", rarity: "R", image: "/assets/characters/r_fuffington.png", quote: "雖然在下身材嬌小，但冒險的心可是無與倫比！", icon: "🐾", weight: 30 },
        { name: "晨曦見習 · 莉莉安", rarity: "R", image: "/assets/characters/r_dennis.png", quote: "初次見面，請多指教！", icon: "📖", weight: 30 }
      ];

      function pickOne() {
        const totalW = pool.reduce((acc, c) => acc + c.weight, 0);
        let rand = Math.random() * totalW;
        for (const c of pool) {
          if (rand < c.weight) return c;
          rand -= c.weight;
        }
        return pool[0];
      }

      if (isTen) {
        const cards = [];
        let hasSrOrHigher = false;
        for (let i = 0; i < 9; i++) {
          const c = pickOne();
          if (c.rarity === "SR" || c.rarity === "SSR") hasSrOrHigher = true;
          cards.push(c);
        }
        // 十連抽第 10 抽保底 SR 或 SSR
        if (!hasSrOrHigher) {
          cards.push(pool[2]); // 保底 SR
        } else {
          cards.push(pickOne());
        }
        triggerEvent({
          type: "gacha.card.pulled",
          user_name: "現場玩家",
          is_ten_pull: true,
          cards: cards
        });
      } else {
        triggerEvent({
          type: "gacha.card.pulled",
          user_name: "現場玩家",
          is_ten_pull: false,
          card: pickOne()
        });
      }
    }

    // 2. 正常投幣扭蛋 (實體日式公仔隨機出貨)
    function playRandomGashapon() {
      const toys = [
        { name: "機甲守衛 Q 版公仔", image: "/assets/toys/toy_robot.png", icon: "🤖", desc: "★ 機甲先鋒限定收藏 ★" },
        { name: "熱血冒險家 探險公仔", image: "/assets/toys/toy_adventurer.png", icon: "🧭", desc: "★ 遺跡探索限定收藏 ★" },
        { name: "呆萌小殭屍 萬聖公仔", image: "/assets/toys/toy_zombie.png", icon: "🎃", desc: "★ 夜行狂歡限定收藏 ★" },
        { name: "弗芬頓紳士 絨毛布偶", image: "/assets/toys/toy_fuff.png", icon: "🧸", desc: "★ 療癒毛球限定收藏 ★" }
      ];
      const selected = toys[Math.floor(Math.random() * toys.length)];
      triggerEvent({
        type: "game.gashapon.pulled",
        user_name: "幸運觀眾",
        toy: selected
      });
    }

    // 3. 正常擲筊
    function playRandomBwei() {
      const r = Math.random();
      let res = "sheng";
      let name = "聖筊";
      let desc = "神明贊同，大吉大利！";
      let left = "flat";
      let right = "curved";

      if (r < 0.005) {
        res = "standing";
        name = "立筊";
        desc = "萬中選一之神蹟！天地共鑑！";
        left = "curved";
        right = "standing";
      } else if (r < 0.52) {
        res = "sheng";
        name = "聖筊";
        desc = "神明應允，所求皆吉！";
        left = "flat";
        right = "curved";
      } else if (r < 0.77) {
        res = "xiao";
        name = "笑筊";
        desc = "神明微笑，若有所思。";
        left = "flat";
        right = "flat";
      } else {
        res = "yin";
        name = "陰筊";
        desc = "神明不允，此事宜緩。";
        left = "curved";
        right = "curved";
      }

      triggerEvent({
        type: "game.bwei.tossed",
        user_name: "祈福香客",
        question: "今天直播順利嗎？",
        result: res,
        name: name,
        desc: desc,
        left: left,
        right: right
      });
    }

    // 4. 正常拉霸機
    function playRandomSlot() {
      const symbols = ["🍒", "LEMON", "BELL", "BAR", "7"];
      const r1 = symbols[Math.floor(Math.random() * symbols.length)];
      const r2 = symbols[Math.floor(Math.random() * symbols.length)];
      const r3 = symbols[Math.floor(Math.random() * symbols.length)];

      let win = 0;
      let mult = 0;
      if (r1 === r2 && r2 === r3) {
        if (r1 === "7") { win = 5000; mult = 50; }
        else if (r1 === "BAR") { win = 1000; mult = 20; }
        else { win = 500; mult = 10; }
      } else if (r1 === r2 || r2 === r3 || r1 === r3) {
        win = 100; mult = 2;
      }

      triggerEvent({
        type: "game.slot.rolled",
        user_name: "常客阿財",
        bet: 50,
        reels: [r1, r2, r3],
        win: win,
        multiplier: mult
      });
    }

    // 5. 正常轉動幸運輪盤
    function playRandomWheel() {
      const items = ["頭獎 1000 點", "銘謝惠顧", "二獎 500 點", "再來一次", "三獎 200 點", "專屬稱號", "點數 50", "點數 100"];
      const targetIdx = Math.floor(Math.random() * items.length);
      triggerEvent({
        type: "game.wheel.spun",
        user_name: "旋轉達人",
        items: items,
        target_index: targetIdx
      });
    }

    // 6. 正常拋硬幣
    function playRandomCoin() {
      const side = Math.random() > 0.5 ? "正面" : "反面";
      triggerEvent({
        type: "game.coin.flipped",
        user_name: "決策者",
        side: side
      });
    }

    // 7. 正常擲骰子 (支援 1、2、3 顆物理骰子)
    function playRandomDice(count = 1, direction = "top") {
      if (count === 1) {
        const val = Math.floor(Math.random() * 6) + 1;
        triggerEvent({
          type: "game.dice.rolled",
          user_name: "骰神",
          total: val,
          rolls: [val],
          direction: direction,
          detail: `1d6 = ${val}`
        });
      } else if (count === 2) {
        const d1 = Math.floor(Math.random() * 6) + 1;
        const d2 = Math.floor(Math.random() * 6) + 1;
        triggerEvent({
          type: "game.dice.rolled",
          user_name: "雙骰豪客",
          total: d1 + d2,
          rolls: [d1, d2],
          direction: direction,
          detail: `2d6 (${d1} + ${d2}) = ${d1 + d2}`
        });
      } else {
        const d1 = Math.floor(Math.random() * 6) + 1;
        const d2 = Math.floor(Math.random() * 6) + 1;
        const d3 = Math.floor(Math.random() * 6) + 1;
        triggerEvent({
          type: "game.dice.rolled",
          user_name: "三骰至尊",
          total: d1 + d2 + d3,
          rolls: [d1, d2, d3],
          direction: direction,
          detail: `3d6 (${d1} + ${d2} + ${d3}) = ${d1 + d2 + d3}`
        });
      }
    }

    window.addEventListener("DOMContentLoaded", () => {
      const host = window.location.host;
      const setEl = (id, url) => {
        const el = document.getElementById(id);
        if (el) el.innerText = url;
      };
      const obsUrl = (path) => STATIC_DEMO
        ? "GitHub Pages 展示模式（OBS 需本機服務）"
        : `http://${host}${path}`;
      setEl("url-card-gacha", obsUrl("/overlay/game/card-gacha"));
      setEl("url-gashapon", obsUrl("/overlay/game/gashapon"));
      setEl("url-bwei", obsUrl("/overlay/game/bwei"));
      setEl("url-slot", obsUrl("/overlay/game/slot"));
      setEl("url-wheel", obsUrl("/overlay/game/wheel"));
      setEl("url-coin", obsUrl("/overlay/game/coin"));
      setEl("url-dice", obsUrl("/overlay/game/dice"));
      setEl("url-counter", obsUrl("/overlay/hud/counter"));
      setEl("url-queue", obsUrl("/overlay/hud/queue"));
      setEl("url-picker", obsUrl("/overlay/hud/picker"));
      setEl("url-gamble", obsUrl("/overlay/game/gamble"));
      setEl("url-cmd", obsUrl("/overlay/games"));
      setEl("url-cover", obsUrl("/overlay/hud/cover"));
      setEl("url-subathon", obsUrl("/overlay/hud/subathon"));
      setEl("url-bet", obsUrl("/overlay/hud/bet"));
      setEl("url-music", obsUrl("/overlay/hud/music"));
      setEl("url-trans", obsUrl("/overlay/hud/trans"));
      setEl("url-donation", obsUrl("/overlay/hud/donation"));
      setEl("url-eventsub", obsUrl("/overlay/hud/donation"));
      setEl("url-all", obsUrl("/overlay/games"));
    });
  </script>
</body>
</html>"""
    if static_demo:
        html = html.replace("<span class=\"tag tag-live\">● 系統運作中</span>", "<span class=\"tag tag-live\">● GitHub Pages 互動展示</span>")
        html = html.replace(
            "管理直播互動遊戲、OBS 圖層與觀眾活動。選擇工具後即可即時預覽與測試。",
            "公開展示版：可直接試玩互動動畫；正式 Twitch、RabbitMQ 與 OBS 事件服務仍在本機中控台運行。",
        )
    return (
        html.replace("__INTERACTIVE_STATIC_DEMO__", "true" if static_demo else "false")
        .replace("__INTERACTIVE_ASSET_PREFIX__", asset_prefix.rstrip("/"))
        .replace("__INTERACTIVE_OVERLAY_PATH__", overlay_path)
    )
