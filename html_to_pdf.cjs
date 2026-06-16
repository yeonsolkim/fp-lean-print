const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");

async function main() {
  const [, , inputHtml, outputPdf = "fp-lean.pdf"] = process.argv;
  if (!inputHtml) {
    console.error("usage: node html_to_pdf.cjs input.html [output.pdf]");
    process.exit(2);
  }

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 1800 } });
  await page.goto(pathToFileURL(path.resolve(inputHtml)).href, { waitUntil: "networkidle" });

  const startButton = page.getByRole("button", { name: "조판 시작" });
  if (await startButton.count()) {
    await startButton.click();
    await page.waitForFunction(() => document.body.classList.contains("book-layout-ready"), null, {
      timeout: 180000
    });
  }

  await page.emulateMedia({ media: "screen" });
  await page.pdf({
    path: path.resolve(outputPdf),
    format: "Letter",
    printBackground: true,
    preferCSSPageSize: true,
    margin: { top: "0", right: "0", bottom: "0", left: "0" }
  });
  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
