import { expect, test } from "@playwright/test";

test("example workspace supports cited answers and a human handoff", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Open example" })).toBeVisible();

  await page.getByRole("button", { name: "Open example" }).click();
  await expect(page.getByRole("heading", { name: "acme/payments-service" })).toBeVisible();
  await expect(page.getByText("Payments Service handles authorization, capture, refunds, and settlement through a REST API and publishes domain events for downstream workflows.")).toBeVisible();

  const question = page.getByRole("textbox", { name: "Ask a question" });
  await question.fill("How does the architecture work?");
  await page.getByRole("button", { name: "Ask question" }).click();
  await expect(page.getByText("77% confidence")).toBeVisible();
  await expect(page.getByText("application/PaymentService.java")).toBeVisible();

  await question.fill("What decision should we make next?");
  await page.getByRole("button", { name: "Ask question" }).click();
  await expect(page.getByRole("button", { name: "Get human help →" })).toBeVisible();
  await page.getByRole("button", { name: "Get human help →" }).click();
  await expect(page.getByText("Handoff created for Maya Patel.")).toBeVisible();
  await page.screenshot({ path: "test-results/onboard-repo-copilot-qa.png", fullPage: true });
});

test("workspace remains usable on a mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Open example" }).click();

  await expect(page.getByRole("heading", { name: "acme/payments-service" })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Ask a question" })).toBeVisible();
  const fitsViewport = await page.locator("body").evaluate((body) => body.scrollWidth <= window.innerWidth);
  expect(fitsViewport).toBeTruthy();
  await page.screenshot({ path: "test-results/onboard-repo-copilot-mobile.png", fullPage: true });
});
