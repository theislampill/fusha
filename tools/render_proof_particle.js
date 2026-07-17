#!/usr/bin/env node
/* Render the local PROOF-P card and write only a durable proof descriptor.
 * The PNG is ignored by the repository and is never a publication artifact. */

const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "..");
const OUT = path.resolve(process.argv[2] || path.join(ROOT, "qamus", "examples", "proof-particle"));
const HTML = path.join(OUT, "particle-card.html");
const PAYLOAD = path.join(OUT, "particle-normalized-public-payload.json");
const PROOF = path.join(OUT, "render-proof.json");
const PNG = path.join(OUT, "particle-card.png");

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

(async () => {
  const payload = readJson(PAYLOAD);
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 });
    await page.goto(pathToFileURL(HTML).href, { waitUntil: "load" });
    await page.evaluate(() => document.fonts.ready);
    const observed = await page.evaluate(() => {
      const root = document.querySelector("#proofp-root");
      const token = document.querySelector("#token");
      const segments = Array.from(token.querySelectorAll(".segment")).map((node) => node.textContent || "");
      return {
        fontCheck: document.fonts.check("16px system-ui"),
        exactReconstruction: segments.join("") === "مَا",
        compactPresent: Boolean(document.querySelector("#compact")),
        expandedPresent: Boolean(document.querySelector("#expanded")),
        samePayloadIdentity: window.__proofpPayloadIdentity === root.dataset.payloadIdentity,
        liveMutationAllowed: window.__proofpPayload.live_mutation_allowed,
        rootIdentity: root.dataset.payloadIdentity,
        tokenText: segments.join(""),
      };
    });
    await page.screenshot({ path: PNG, fullPage: true });
    const proof = {
      schema: "qamus.proof_particle.render_proof.v1",
      status: "measured",
      payload_identity: payload.payload_identity,
      font_check: observed.fontCheck,
      exact_reconstruction: observed.exactReconstruction,
      compact_present: observed.compactPresent,
      expanded_present: observed.expandedPresent,
      same_payload_identity: observed.samePayloadIdentity && observed.rootIdentity === payload.payload_identity,
      live_mutation_allowed: observed.liveMutationAllowed,
      screenshot_path: "particle-card.png",
      screenshot_local_only: true,
      viewport: { width: 1280, height: 900, device_scale_factor: 1 },
      observed_token_surface: observed.tokenText,
    };
    fs.writeFileSync(PROOF, JSON.stringify(proof, null, 2) + "\n", "utf8");
    const failed = [
      ["font_check", proof.font_check],
      ["exact_reconstruction", proof.exact_reconstruction],
      ["compact_present", proof.compact_present],
      ["expanded_present", proof.expanded_present],
      ["same_payload_identity", proof.same_payload_identity],
      ["live_mutation_allowed=false", proof.live_mutation_allowed === false],
    ].filter(([, ok]) => !ok).map(([name]) => name);
    if (failed.length) {
      throw new Error(`render proof failed: ${failed.join(", ")}`);
    }
    console.log(`PROOF-P RENDER ALL PASS ${PROOF}`);
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
