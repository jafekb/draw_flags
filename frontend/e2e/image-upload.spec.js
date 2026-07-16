import { expect, test } from "@playwright/test";

// Uploading an image should downscale it client-side, POST it to /image, and render the
// returned flags plus the "Detected: …" caption. The backend (hosted VLM + search) is
// mocked so this test needs no provider key or Python backend.

const RESULT = {
  detected: "a red disc centered on a white field",
  flags: [
    {
      name: "Japan",
      wikipedia_url: "https://example.test/wiki/Japan",
      wikipedia_image_url: "https://img.test/japan.png",
      color_coverage: {},
      score: 0.91,
    },
    {
      name: "Bangladesh",
      wikipedia_url: "https://example.test/wiki/Bangladesh",
      wikipedia_image_url: "https://img.test/bangladesh.png",
      color_coverage: {},
      score: 0.72,
    },
  ],
};

// 1x1 transparent PNG (must be a real image so the client-side canvas resize works).
const PNG_1x1 = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMBAQAY3Y2wAAAAAElFTkSuQmCC",
  "base64",
);

test("uploading an image renders identified flags and the detected caption", async ({
  page,
}) => {
  let imagePostBody = null;

  await page.route("**/flags/random**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ flags: [] }),
    }),
  );
  await page.route("**/image", (route) => {
    imagePostBody = route.request().postDataJSON();
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(RESULT),
    });
  });
  await page.route("https://img.test/**", (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: PNG_1x1 }),
  );

  await page.goto("/");

  await page.locator('input[type="file"]').setInputFiles({
    name: "flag.png",
    mimeType: "image/png",
    buffer: PNG_1x1,
  });

  // Results render and the detected description is shown.
  await expect(page.locator(".grid-item")).toHaveCount(2);
  await expect(page.getByText(/Detected:/)).toContainText(
    "a red disc centered on a white field",
  );

  // We sent a base64 data URI, not a filename (the old broken behavior).
  expect(imagePostBody?.image).toMatch(/^data:image\/jpeg;base64,/);
});
