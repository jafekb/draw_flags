import { expect, test } from "@playwright/test";

// The grid must render in windows of PAGE_SIZE (60) and reveal more on scroll, rather
// than mounting every flag at once — mounting all ~2700 hotlinks that many images from
// Wikimedia simultaneously and gets the browser 429-throttled (blank flags). We mock
// the API with 300 flags and serve a tiny image for every flag URL, so we can assert
// both the DOM node count and how many image requests actually fire.

const PAGE_SIZE = 60;
const TOTAL = 300;

const FLAGS = Array.from({ length: TOTAL }, (_, i) => ({
  name: `Flag ${i}`,
  wikipedia_url: "https://example.test/wiki",
  wikipedia_image_url: `https://img.test/flag-${i}.png`,
  color_coverage: {},
  score: 0.5,
}));

// 1x1 transparent PNG
const PNG_1x1 = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMBAQAY3Y2wAAAAAElFTkSuQmCC",
  "base64",
);

const gridItemCount = (page) => page.locator(".grid-item").count();

test("Show All windows to 60 items and grows to the full set on scroll", async ({
  page,
}) => {
  let imageRequests = 0;

  await page.route("**/flags/all", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ flags: FLAGS }),
    }),
  );
  await page.route("**/flags/random**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ flags: FLAGS.slice(0, 12) }),
    }),
  );
  await page.route("https://img.test/**", (route) => {
    imageRequests += 1;
    route.fulfill({ status: 200, contentType: "image/png", body: PNG_1x1 });
  });

  await page.goto("/");

  // "Show All" (A-Z sort) loads all 300 flags.
  await page.getByRole("button", { name: "A-Z" }).click();

  // Only the first window mounts, and we haven't requested more images than that.
  await expect(page.locator(".grid-item")).toHaveCount(PAGE_SIZE);
  await expect(page.locator(".grid-sentinel")).toBeVisible();
  expect(imageRequests).toBeLessThanOrEqual(PAGE_SIZE + 5);

  // Scrolling reveals more, in windows, until the whole set is present.
  let guard = 0;
  while ((await gridItemCount(page)) < TOTAL && guard < 20) {
    const before = await gridItemCount(page);
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await expect
      .poll(() => gridItemCount(page), { timeout: 5000 })
      .toBeGreaterThan(before);
    guard += 1;
  }

  // Everything is eventually rendered, the sentinel is gone, and we never requested
  // more images than flags shown (no mass hotlinking).
  await expect(page.locator(".grid-item")).toHaveCount(TOTAL);
  await expect(page.locator(".grid-sentinel")).toHaveCount(0);
  expect(imageRequests).toBeLessThanOrEqual(TOTAL);
});
