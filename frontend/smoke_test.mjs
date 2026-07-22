import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const html = fs.readFileSync(new URL('./index.html', import.meta.url), 'utf8');
const script = fs.readFileSync(new URL('./app.js', import.meta.url), 'utf8');

test('frontend exposes the ingestion, status, and explainability surfaces', () => {
  assert.match(html, /id="ingest"/);
  assert.match(html, /id="asset-status"/);
  assert.match(html, /data-tab="json"/);
  assert.match(script, /\/assets\/\$\{assetId\}\/status/);
  assert.match(script, /MiniCPM-V · openbmb\/MiniCPM-V-4\.6/);
  assert.match(script, /source_frame_uris/);
});
