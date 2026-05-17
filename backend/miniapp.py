"""Small Telegram mini app that lets the user pick a plan and send it to the bot."""

from __future__ import annotations

import json
from textwrap import dedent


DEFAULT_PLANS = [
    {"id": "basic", "title": "Basic", "duration_days": 30, "price_cents": 500, "description": "1 month access"},
    {"id": "pro", "title": "Pro", "duration_days": 90, "price_cents": 1200, "description": "3 months access"},
    {"id": "premium", "title": "Premium", "duration_days": 365, "price_cents": 4000, "description": "12 months access"},
]


def build_miniapp_html() -> str:
    plans_json = json.dumps(DEFAULT_PLANS, ensure_ascii=False)
    return dedent(f"""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>SkullVPN Mini App</title>
      <script src="https://telegram.org/js/telegram-web-app.js"></script>
      <style>
        :root {{ color-scheme: dark; }}
        body {{ margin: 0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif; background: linear-gradient(160deg, #09111f, #0f172a 45%, #111827 100%); color: #e5eefb; }}
        .wrap {{ max-width: 960px; margin: 0 auto; padding: 24px; }}
        .hero {{ padding: 24px; border: 1px solid rgba(255,255,255,0.08); border-radius: 24px; background: rgba(255,255,255,0.04); box-shadow: 0 20px 60px rgba(0,0,0,0.25); }}
        .title {{ font-size: 32px; margin: 0 0 8px; }}
        .subtitle {{ opacity: .8; margin: 0 0 18px; line-height: 1.5; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-top: 18px; }}
        .card {{ border-radius: 20px; padding: 18px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08); }}
        .card h3 {{ margin: 0 0 6px; font-size: 20px; }}
        .muted {{ opacity: .72; font-size: 14px; line-height: 1.45; }}
        .price {{ font-size: 28px; margin: 10px 0 14px; font-weight: 700; }}
        .btn {{ width: 100%; border: 0; border-radius: 14px; padding: 12px 14px; font-weight: 700; cursor: pointer; color: #fff; background: linear-gradient(135deg, #22c55e, #2563eb); }}
        .btn:active {{ transform: translateY(1px); }}
        .pill {{ display:inline-block; padding: 6px 10px; border-radius: 999px; background: rgba(34,197,94,.14); color: #86efac; font-size: 12px; font-weight: 700; }}
        .foot {{ margin-top: 18px; opacity: .65; font-size: 13px; }}
        .note {{ margin-top: 14px; padding: 12px 14px; border-radius: 14px; background: rgba(37,99,235,0.15); border: 1px solid rgba(59,130,246,.25); font-size: 14px; line-height: 1.5; }}
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="hero">
          <div class="pill">SkullVPN</div>
          <h1 class="title">Buy access and get a config instantly</h1>
          <p class="subtitle">Pick a plan, tap <b>Buy</b>, complete payment in Telegram, and the bot will create your access in 3x-ui and send the config back to this chat.</p>
          <div id="plans" class="grid"></div>
          <div class="note">If payment is not configured yet, this page still works as a selector: it will hand the plan choice to the bot, and the bot will tell you what is missing.</div>
          <div class="foot">Open this from Telegram for the best experience.</div>
        </div>
      </div>
      <script>
        const FALLBACK_PLANS = {plans_json};
        const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
        if (tg) {{ tg.ready(); tg.expand(); }}

        function fmtPrice(plan) {{ return new Intl.NumberFormat(undefined, {{ style: 'currency', currency: 'USD' }}).format(plan.price_cents / 100); }}

        function render(plans) {{
          const root = document.getElementById('plans');
          root.innerHTML = plans.map(plan => `
            <div class="card">
              <h3>${{plan.title}}</h3>
              <div class="muted">${{plan.duration_days}} days access</div>
              <div class="price">${{fmtPrice(plan)}}</div>
              <div class="muted">${{plan.description}}</div>
              <button class="btn" onclick='buy("${{plan.id}}")'>Buy</button>
            </div>
          `).join('');
        }}

        async function loadPlans() {{
          try {{
            const res = await fetch('/api/plans', {{ headers: {{ 'Accept': 'application/json' }} }});
            const data = await res.json();
            if (Array.isArray(data) && data.length > 0) return render(data.map((p, idx) => ({{
              id: String(p.id),
              title: p.name || `Plan ${{idx+1}}`,
              duration_days: p.duration_days || 30,
              price_cents: p.price_cents || 0,
              description: `${{p.duration_days || 30}} days access`,
            }})));
          }} catch (e) {{ /* fallback below */ }}
          render(FALLBACK_PLANS);
        }}

        function buy(planId) {{
          if (!tg) {{
            alert('Open this page from Telegram to pay.');
            return;
          }}
          tg.sendData(JSON.stringify({{ action: 'buy', plan_id: planId }}));
          tg.close();
        }}

        loadPlans();
      </script>
    </body>
    </html>
    """)