import { expect, test } from "@playwright/test";

const email = process.env.ROBOOPS_BOOTSTRAP_EMAIL;
const password = process.env.ROBOOPS_BOOTSTRAP_PASSWORD;

test("anonymous users are redirected to sign in", async ({ page }) => {
  await page.goto("/alerts");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});

test("invalid credentials show a useful error without leaving login", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("nobody@example.com");
  await page.getByLabel("Password").fill("incorrect-password");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByRole("alert")).toHaveText("Unable to sign in with those credentials.");
  await expect(page).toHaveURL(/\/login$/);
});

test("admin can sign in, inspect real seeded data, navigate, and log out", async ({ page }) => {
  if (!email || !password) {
    throw new Error("ROBOOPS_BOOTSTRAP_EMAIL and ROBOOPS_BOOTSTRAP_PASSWORD are required.");
  }

  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  const totalRobots = page.locator(".summary-card", { hasText: "Total Robots" });
  await expect(totalRobots.locator(".summary-card-value")).toHaveText("12");
  await expect(page.getByText(`${email} (admin)`)).toBeVisible();

  await page.getByRole("link", { name: "Alerts" }).click();
  await expect(page).toHaveURL(/\/alerts$/);
  await expect(page.getByRole("heading", { name: "Alerts" })).toBeVisible();
  await expect(page.getByText("Alert lifecycle")).toBeVisible();
  await expect(page.getByText("RBT-001").first()).toBeVisible();

  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  const storedToken = await page.evaluate(() => sessionStorage.getItem("roboops.access_token"));
  expect(storedToken).toBeNull();
});
