def dashboard_html() -> str:
    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>VideoDB Console</title>
    <style>
      body {
        background: #0f172a;
        color: #e2e8f0;
        font-family: Inter, system-ui, sans-serif;
        margin: 0;
      }
      main {
        margin: 0 auto;
        max-width: 1120px;
        padding: 32px;
      }
      .grid {
        display: grid;
        gap: 16px;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      }
      .card {
        background: #111827;
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 18px;
      }
      input,
      textarea,
      button {
        border: 0;
        border-radius: 10px;
        box-sizing: border-box;
        font: inherit;
        margin: 6px 0;
        padding: 10px;
        width: 100%;
      }
      button {
        background: #38bdf8;
        color: #082f49;
        cursor: pointer;
        font-weight: 700;
      }
      code {
        color: #93c5fd;
      }
      .flow {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }
      .step {
        background: #1e293b;
        border: 1px solid #475569;
        border-radius: 999px;
        padding: 8px 12px;
      }
      pre {
        background: #020617;
        border-radius: 12px;
        overflow: auto;
        padding: 14px;
      }
    </style>
  </head>
  <body>
    <main>
      <h1>VideoDB Console</h1>
      <p>
        Minimal UI for the current API: create collections/assets, run hybrid
        search, create clips, inspect deletion status, and understand the
        indexing flow.
      </p>

      <section class="card">
        <h2>Workflow</h2>
        <div class="flow">
          <span class="step">Upload / import video</span>
          <span class="step">Normalize media</span>
          <span class="step">Transcript index</span>
          <span class="step">Visual index</span>
          <span class="step">Hybrid search</span>
          <span class="step">Clip / alert / temporal query</span>
        </div>
      </section>

      <section class="grid">
        <form class="card" data-endpoint="/collections">
          <h2>Create collection</h2>
          <input name="name" placeholder="collection name" value="demo" />
          <button type="submit">POST /collections</button>
        </form>

        <form class="card" data-endpoint="/assets">
          <h2>Create asset</h2>
          <input name="collection_id" placeholder="collection id" />
          <input name="source_uri" placeholder="s3://bucket/video.mp4" />
          <input name="source_type" value="object" />
          <button type="submit">POST /assets</button>
        </form>

        <form class="card" data-endpoint="/search">
          <h2>Hybrid search</h2>
          <input name="query" placeholder="goal, replay, speaker..." />
          <button type="submit">POST /search</button>
        </form>

        <form class="card" data-endpoint="/clips">
          <h2>Create clip</h2>
          <input name="name" value="highlight" />
          <textarea name="segments" rows="4">[
  {"asset_id":"asset-id","start_ms":0,"end_ms":1000}
]</textarea>
          <button type="submit">POST /clips</button>
        </form>
      </section>

      <section class="card">
        <h2>Response</h2>
        <pre id="output">Submit a form to call the API.</pre>
      </section>
    </main>
    <script>
      const tenantId = "demo-tenant";
      for (const form of document.querySelectorAll("form[data-endpoint]")) {
        form.addEventListener("submit", async (event) => {
          event.preventDefault();
          const payload = {};
          for (const element of new FormData(form).entries()) {
            const [key, value] = element;
            payload[key] = key === "segments" ? JSON.parse(value) : value;
          }
          const response = await fetch(form.dataset.endpoint, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-Tenant-ID": tenantId
            },
            body: JSON.stringify(payload)
          });
          document.getElementById("output").textContent = JSON.stringify(
            await response.json(),
            null,
            2
          );
        });
      }
    </script>
  </body>
</html>"""
