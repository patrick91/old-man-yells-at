"""Landing page route."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response

router = APIRouter()


LANDING_PAGE_HTML = """<!doctype html>
<html lang="en" class="antialiased">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Old Man Yells At</title>
    <meta
      name="description"
      content="Generate Old Man Yells At memes from domains, X handles, image URLs, or Slack."
    />
    <link rel="preconnect" href="https://rsms.me" />
    <link rel="stylesheet" href="https://rsms.me/inter/inter.css" />
    <link rel="preload" as="image" href="/assets/template.png" />
    <link rel="stylesheet" href="/static/landing.css" />
  </head>
  <body>
    <div class="page">
      <section class="hero" id="top">
        <header class="site-header">
          <a class="brand" href="/" aria-label="Homepage">Old Man Yells At</a>

          <nav class="desktop-nav" aria-label="Primary navigation">
            <a href="#demo">Demo</a>
            <a href="#slack">Slack</a>
            <a href="#api">API</a>
          </nav>

          <div class="header-actions">
            <a class="header-link" href="/docs">Docs</a>
            <button
              class="menu-button"
              type="button"
              aria-controls="mobile-menu"
              aria-expanded="false"
              data-menu-button
            >
              <span class="menu-lines" aria-hidden="true"></span>
              <span class="sr-only">Open menu</span>
            </button>
          </div>
        </header>

        <nav class="mobile-nav" id="mobile-menu" hidden aria-label="Mobile navigation">
          <a href="#demo">Demo</a>
          <a href="#slack">Slack</a>
          <a href="#api">API</a>
          <a href="/docs">Docs</a>
        </nav>

        <div class="hero-inner">
          <div class="hero-copy">
            <p class="eyebrow">FastAPI meme endpoint</p>
            <h1>Old Man Yells At</h1>
            <p class="hero-subtitle">
              Turn a company domain, X handle, or image URL into the classic shouty meme, then post it straight from Slack.
            </p>
            <div class="hero-actions">
              <a class="button button-primary" href="#demo">Try the demo</a>
              <a class="button button-secondary" href="/docs">API docs</a>
            </div>
            <form class="hero-form" data-target-form>
              <input
                id="target"
                name="target"
                type="text"
                value="python.org"
                aria-label="Target domain or X handle"
                autocomplete="off"
              />
              <button class="button button-quiet" type="submit">Open meme URL</button>
            </form>
            <p class="hero-note">
              The same route accepts domains like python.org and X handles like @patrick91.
            </p>
          </div>
        </div>
      </section>

      <main>
        <section class="section section-tight" id="demo">
          <div class="section-inner">
            <div class="section-heading">
              <p class="eyebrow">One tiny input</p>
              <h2>Pick a target. Get a PNG.</h2>
              <p>
                The app resolves a logo or public profile image, places it where the cloud would be, and streams the finished meme as an image response.
              </p>
            </div>

            <dl class="steps-grid">
              <div>
                <dt>Input</dt>
                <dd>Use a domain, X handle, or direct image URL.</dd>
              </div>
              <div>
                <dt>Compose</dt>
                <dd>The image is trimmed, resized, anchored, and merged with the template.</dd>
              </div>
              <div>
                <dt>Ship</dt>
                <dd>The endpoint returns a PNG that Slack, browsers, and bots can render.</dd>
              </div>
            </dl>
          </div>
        </section>

        <section class="section section-muted" id="slack">
          <div class="section-inner split-layout">
            <div class="section-heading">
              <p class="eyebrow">Slack-ready</p>
              <h2>Make the channel decide if it belongs in public.</h2>
              <p>
                The slash command responds fast, builds the meme in the background, previews it privately, and only posts to the channel when someone confirms it.
              </p>
            </div>

            <div class="preview-panel" aria-label="Preview of a generated meme">
              <div class="preview-bar">Old Man Yells At python.org</div>
              <div class="preview-body">
                <div class="preview-target">
                  <span>Py</span>
                </div>
                <img src="/assets/template.png" alt="" />
              </div>
              <div class="preview-caption">GET /python.org</div>
            </div>
          </div>
        </section>

        <section class="section" id="api">
          <div class="section-inner api-layout">
            <div class="section-heading">
              <p class="eyebrow">HTTP first</p>
              <h2>Useful as a bot, a bookmark, or a joke factory.</h2>
              <p>
                Keep the UI lightweight and call the same routes from scripts, browser links, Slack interactivity, or anything else that can fetch an image.
              </p>
            </div>

            <div class="api-panel" aria-label="API examples">
              <pre><code>GET /python.org
GET /@patrick91
GET /generate-meme?image_url=https://example.com/logo.png</code></pre>
            </div>
          </div>
        </section>
      </main>

      <footer class="site-footer">
        <div class="footer-inner">
          <a class="footer-brand" href="/" aria-label="Homepage">Old Man Yells At</a>
          <div class="footer-links">
            <a href="/docs">Docs</a>
            <a href="#demo">Demo</a>
            <a href="#api">API</a>
          </div>
        </div>
      </footer>
    </div>

    <script>
      const menuButton = document.querySelector("[data-menu-button]");
      const mobileMenu = document.querySelector("#mobile-menu");

      menuButton?.addEventListener("click", () => {
        const isOpen = menuButton.getAttribute("aria-expanded") === "true";
        menuButton.setAttribute("aria-expanded", String(!isOpen));
        mobileMenu.hidden = isOpen;
      });

      document.querySelector("[data-target-form]")?.addEventListener("submit", (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const target = new FormData(form).get("target").toString().trim();

        if (!target) {
          return;
        }

        window.location.href = `/${encodeURIComponent(target)}`;
      });
    </script>
  </body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
async def landing_page() -> HTMLResponse:
    """Render the marketing page for the meme generator."""
    return HTMLResponse(LANDING_PAGE_HTML)


@router.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    """Avoid routing browser favicon requests through the meme catch-all."""
    return Response(status_code=204)
