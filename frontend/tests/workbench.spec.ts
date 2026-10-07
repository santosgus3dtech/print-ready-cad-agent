import { test, expect, type Page } from '@playwright/test';
import { PNG } from 'pngjs';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';

const screenshots = path.resolve('../docs/screenshots');

async function modelReady(page: Page) {
  await expect(page.locator('canvas')).toHaveAttribute('data-loaded', 'true');
  await expect(page.getByRole('button', { name: 'Generate model', exact: true })).toBeEnabled();
}

async function generate(page: Page) {
  const response = page.waitForResponse(r => r.url().endsWith('/api/jobs') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Generate model', exact: true }).click();
  const result = await response;
  expect(result.status()).toBe(201);
  const job = await result.json();
  await expect(page.locator('canvas')).toHaveAttribute('data-model-source', job.artifacts['preview.glb'].url);
  await modelReady(page);
}

function geometryPixels(buffer: Buffer) {
  const image = PNG.sync.read(buffer);
  let count = 0, minX = image.width, minY = image.height, maxX = 0, maxY = 0;
  for (let y = 0; y < image.height; y++) {
    for (let x = 0; x < image.width; x++) {
      const index = (y * image.width + x) * 4;
      const [r, g, b] = image.data.subarray(index, index + 3);
      if (r < 160 && g > r * 1.14 && b > r * 1.14 && g > 65) {
        count++; minX = Math.min(minX, x); maxX = Math.max(maxX, x);
        minY = Math.min(minY, y); maxY = Math.max(maxY, y);
      }
    }
  }
  expect(count / (image.width * image.height)).toBeGreaterThan(.01);
  expect(minX).toBeGreaterThan(2); expect(minY).toBeGreaterThan(2);
  expect(maxX).toBeLessThan(image.width - 2); expect(maxY).toBeLessThan(image.height - 2);
}

test('generate, validate, inspect evidence, export and restore history', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {
    const screenshotDriverWarning = message.type() === 'warning'
      && /^\[\.WebGL-.*GL Driver Message .*GPU stall due to ReadPixels/.test(message.text());
    if (screenshotDriverWarning) {
      test.info().annotations.push({ type: 'capture-driver-warning', description: 'Chromium screenshot ReadPixels stall; not an application error.' });
    } else if (['error', 'warning'].includes(message.type())) errors.push(message.text());
  });
  await page.goto('/');
  await expect(page).toHaveTitle('PrintReady | CAD workbench');
  await expect(page.locator('vite-error-overlay')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Generate model', exact: true })).toBeEnabled();
  await page.getByRole('tab', { name: 'Enclosure', exact: true }).click();
  await page.getByLabel('Width (X)', { exact: true }).fill('80');
  await page.getByLabel('Printer', { exact: true }).selectOption('bambu-a1');
  await page.getByLabel('Material', { exact: true }).selectOption('PLA');
  await generate(page);
  geometryPixels(await page.locator('canvas').screenshot());
  await page.getByRole('tab', { name: 'Evidence', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Design evidence' })).toBeVisible();
  await expect(page.locator('.evidence-item')).not.toHaveCount(0);
  await page.getByRole('tab', { name: 'Validation', exact: true }).click();

  await page.getByLabel('Width (X)', { exact: true }).fill('90');
  await expect(page.getByText('Changes not generated')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Slice locally' })).toBeDisabled();
  await page.locator('.export-menu summary').click();
  await expect(page.locator('.export-options a')).toHaveCount(0);
  await page.locator('.export-menu summary').click();
  await page.getByLabel('Width (X)', { exact: true }).fill('80');

  await page.locator('.export-menu summary').click();
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('link', { name: 'model.step', exact: true }).click();
  expect((await downloadPromise).suggestedFilename()).toBe('model.step');
  await page.locator('.export-menu summary').click();

  await page.getByRole('tab', { name: 'Bracket', exact: true }).click();
  await generate(page);
  await expect(page.getByRole('heading', { name: 'Mounting bracket' })).toBeVisible();
  geometryPixels(await page.locator('canvas').screenshot());
  await page.getByRole('tab', { name: 'Adapter', exact: true }).click();
  await generate(page);
  await expect(page.getByRole('heading', { name: 'Flanged adapter' })).toBeVisible();
  geometryPixels(await page.locator('canvas').screenshot());

  await page.getByRole('tab', { name: 'History', exact: true }).click();
  await page.locator('.history-row').filter({ hasText: 'Electronics enclosure' }).first().click();
  await expect(page.getByRole('heading', { name: 'Electronics enclosure', exact: true })).toBeVisible();
  await page.getByRole('tab', { name: 'Validation', exact: true }).click();
  await modelReady(page);

  await page.getByRole('button', { name: 'Wireframe', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Wireframe', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: 'Wireframe', exact: true }).click();
  const before = await page.locator('canvas').screenshot();
  await page.getByRole('button', { name: 'Auto rotate', exact: true }).click();
  await page.waitForTimeout(700);
  const moving = await page.locator('canvas').screenshot();
  expect(before.equals(moving)).toBe(false);
  await page.getByRole('button', { name: 'Auto rotate', exact: true }).click();
  await page.getByRole('button', { name: 'Fit view', exact: true }).click();

  await mkdir(screenshots, { recursive: true });
  await page.screenshot({ path: path.join(screenshots, 'workbench-desktop.png') });
  for (const [width, height] of [[1024, 768], [390, 844]]) {
    await page.setViewportSize({ width, height });
    await page.getByRole('button', { name: 'Fit view', exact: true }).click();
    geometryPixels(await page.locator('canvas').screenshot());
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await expect(page.getByRole('button', { name: 'Generate model', exact: true })).toBeVisible();
    if (width === 390) await page.screenshot({ path: path.join(screenshots, 'workbench-mobile.png'), fullPage: true });
  }
  expect(errors).toEqual([]);
});

test('invalid dimensions show an actionable error without replacing the model', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Generate model', exact: true })).toBeEnabled();
  await page.getByRole('tab', { name: 'Enclosure', exact: true }).click();
  await page.getByLabel('Width (X)', { exact: true }).fill('20');
  await page.getByRole('button', { name: 'Generate model', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('too small');
  await page.getByRole('button', { name: 'Dismiss error' }).click();
  await expect(page.getByRole('alert')).toHaveCount(0);
});
