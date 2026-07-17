/* Headless render witness for the generated PROOF-N noun card. */
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "..");
const htmlPath = path.join(root, "qamus", "examples", "proof-noun-sufaha", "proofn-card.html");
const screenshotPath = path.join(root, "qamus", "examples", "proof-noun-sufaha", "proofn-card.png");
const proofPath = path.join(root, "qamus", "examples", "proof-noun-sufaha", "render-proof.json");

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1100 }, deviceScaleFactor: 1 });
    const url = "file:///" + htmlPath.replace(/\\/g, "/");
    await page.goto(url, { waitUntil: "load" });
    await page.evaluate(async () => {
      await document.fonts.ready;
      if (!document.fonts.check('32px "Kawkab Mono Qamus"')) {
        throw new Error("document.fonts.check failed");
      }
      if (!window.__reconCheck()) {
        throw new Error("exact reconstruction failed");
      }
      if (!window.__fontProof()) {
        throw new Error("visible font proof failed");
      }
    });
    await page.waitForTimeout(250);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    const proof = await page.evaluate(() => {
      const payload = window.__fdPayload;
      const appearances = payload.appearance_parity && payload.appearance_parity.appearances || [];
      return {
        schema: "qamus.proofn.render_proof.v1",
        status: "measured_local",
        font_check: document.fonts.check('32px "Kawkab Mono Qamus"'),
        exact_reconstruction: window.__reconCheck(),
        compact_present: Boolean(document.querySelector("#compact-view .arabic")),
        expanded_present: Boolean(document.querySelector("#expanded-view .component")),
        same_payload_identity:
          window.__compactPayload === window.__expandedPayload &&
          JSON.stringify(window.__fdPayload) === document.getElementById("fd-normalized-payload").textContent,
        appearance_parity: appearances.length === 2 && appearances.every(item =>
          item.same_payload_id === true && item.payload_id === payload.payload_id),
        live_mutation_allowed: payload.live_mutation_allowed,
        readback_target_status: payload.readback_target && payload.readback_target.status,
        screenshot_path: "local-only: proofn-card.png",
        png_policy: "local-only-not-tracked",
        viewport: { width: 1440, height: 1100 },
      };
    });
    fs.writeFileSync(proofPath, JSON.stringify(proof, null, 2) + "\n", "utf8");
    const required = [
      "font_check", "exact_reconstruction", "compact_present", "expanded_present",
      "same_payload_identity", "appearance_parity",
    ];
    if (required.some(key => proof[key] !== true) ||
        proof.live_mutation_allowed !== false ||
        proof.readback_target_status !== "declared_not_measured") {
      throw new Error("render proof assertions failed");
    }
    console.log("PROOFN PLAYWRIGHT RENDER PASS");
    console.log(JSON.stringify(proof));
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error("PROOFN PLAYWRIGHT RENDER FAIL");
  console.error(error && error.stack ? error.stack : error);
  process.exitCode = 1;
});
