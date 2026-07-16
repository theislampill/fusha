/* Headless proof protocol for the generated F-D Ṣufahāʾ card. */
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "..");
const htmlPath = path.join(root, "qamus", "examples", "fd", "sufaha-card.html");
const screenshotPath = path.join(root, "qamus", "examples", "fd", "sufaha-card.png");
const proofPath = path.join(root, "qamus", "examples", "fd", "render-proof.json");

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1100 }, deviceScaleFactor: 1 });
    await page.goto(`file:///${htmlPath.replace(/\\/g, "/")}`, { waitUntil: "load" });
    await page.evaluate(async () => {
      await document.fonts.ready;
      const fontPass = document.fonts.check('32px "Kawkab Mono Qamus"');
      if (!fontPass) throw new Error("document.fonts.check failed");
      if (!window.__reconCheck()) throw new Error("exact reconstruction failed");
      if (!window.__fontProof()) throw new Error("visible font proof failed");
    });
    await page.waitForTimeout(250);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    const proof = await page.evaluate(() => ({
      font_check: document.fonts.check('32px "Kawkab Mono Qamus"'),
      exact_reconstruction: window.__reconCheck(),
      compact_present: Boolean(document.querySelector("#compact-view .arabic")),
      expanded_present: Boolean(document.querySelector("#expanded-view .component")),
      same_payload_identity: window.__compactPayload === window.__expandedPayload && JSON.stringify(window.__fdPayload) === document.getElementById("fd-normalized-payload").textContent,
      live_mutation_allowed: window.__fdPayload.live_mutation_allowed,
      viewport: { width: 1440, height: 1100 },
    }));
    fs.writeFileSync(proofPath, JSON.stringify(proof, null, 2) + "\n", "utf8");
    if (!proof.font_check || !proof.exact_reconstruction || !proof.compact_present || !proof.expanded_present || !proof.same_payload_identity || proof.live_mutation_allowed !== false) {
      throw new Error("render proof assertions failed");
    }
    console.log("FD PLAYWRIGHT RENDER PASS");
    console.log(JSON.stringify(proof));
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error("FD PLAYWRIGHT RENDER FAIL");
  console.error(error && error.stack ? error.stack : error);
  process.exitCode = 1;
});
