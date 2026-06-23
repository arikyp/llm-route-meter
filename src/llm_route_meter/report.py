from __future__ import annotations

import html
from pathlib import Path
from typing import Any


def render_html_report(summary: dict[str, Any]) -> str:
    rows = []
    for route in summary.get("routes", []):
        metrics = route.get("summary", {})
        waste = ", ".join(item.get("category", "") for item in route.get("ranked_waste", [])) or "none"
        rows.append(f"""
        <tr>
          <td>{html.escape(route.get('route_id', ''))}</td>
          <td><strong>{html.escape(route.get('decision', ''))}</strong></td>
          <td>{html.escape(waste)}</td>
          <td>{metrics.get('estimated_cost_usd', '')}</td>
          <td>{metrics.get('cached_input_share_pct', '')}%</td>
          <td>{metrics.get('batchable_request_share_pct', '')}%</td>
          <td>{metrics.get('accepted_output_rate_pct', '')}</td>
        </tr>""")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LLM Route Meter Report</title>
  <style>
    body {{ margin:0; background:#f5f6f4; color:#15171a; font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
    main {{ max-width:1100px; margin:0 auto; padding:32px; }}
    .panel {{ background:white; border:1px solid #d8dee4; border-radius:8px; padding:18px; box-shadow:0 12px 28px rgba(23,31,38,.07); }}
    h1 {{ margin-top:0; letter-spacing:0; }}
    p {{ color:#34404a; line-height:1.55; }}
    table {{ width:100%; border-collapse:collapse; font-size:.92rem; }}
    th,td {{ border:1px solid #d8dee4; padding:8px 10px; text-align:left; vertical-align:top; }}
    th {{ background:#eef2f5; }}
  </style>
</head>
<body><main><section class="panel">
  <h1>LLM Route Meter Report</h1>
  <p>Metadata-only summary. This report should contain no prompts, responses, transcripts, API keys, or auth headers.</p>
  <table>
    <thead><tr><th>Route</th><th>Decision</th><th>Waste</th><th>Cost</th><th>Cached Share</th><th>Batchable</th><th>Accepted Rate</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</section></main></body></html>"""


def write_html_report(summary: dict[str, Any], output: str | Path) -> None:
    Path(output).write_text(render_html_report(summary), encoding="utf-8")
