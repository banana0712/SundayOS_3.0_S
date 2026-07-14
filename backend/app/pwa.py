"""PWA manifest + iOS splash screen routes.

Serves the web app manifest at /manifest.json so mobile browsers
offer "Add to Home Screen" with proper icons and colors.
"""
from __future__ import annotations

# Inline manifest — served by main.py at /manifest.json
MANIFEST_JSON = r"""{
  "name": "Sunday OS",
  "short_name": "Sunday",
  "description": "One mind for every task",
  "start_url": "/",
  "display": "standalone",
  "orientation": "portrait-primary",
  "background_color": "#0B0B0C",
  "theme_color": "#0B0B0C",
  "icons": [
    {
      "src": "/api/pwa/icon-192",
      "sizes": "192x192",
      "type": "image/svg+xml",
      "purpose": "any maskable"
    },
    {
      "src": "/api/pwa/icon-512",
      "sizes": "512x512",
      "type": "image/svg+xml",
      "purpose": "any maskable"
    }
  ]
}"""

# SVG icon template — simple Sunday mark, parameterized by size.
# Uses {{size}} placeholders so the icon renders at the exact pixel
# dimensions the PWA manifest declares.
_SVG_ICON_TEMPLATE = (
    '<svg xmlns="http://www.w3.org/2000/svg" '
    'width="{size}" height="{size}" viewBox="0 0 512 512">'
    '<defs>'
    '<linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0%" stop-color="#0a84ff"/>'
    '<stop offset="50%" stop-color="#5e5ce6"/>'
    '<stop offset="100%" stop-color="#30d158"/>'
    '</linearGradient>'
    '</defs>'
    '<rect width="512" height="512" rx="112" fill="url(#g)"/>'
    '<circle cx="256" cy="256" r="100" fill="#0B0B0C" opacity="0.9"/>'
    '<circle cx="256" cy="256" r="40" fill="url(#g)"/>'
    '</svg>'
)


def get_icon_svg(size: int = 512) -> str:
    """Return SVG icon at the requested pixel size."""
    return _SVG_ICON_TEMPLATE.replace("{size}", str(size))
