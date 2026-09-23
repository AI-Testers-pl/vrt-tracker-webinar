import { test, expect } from '@playwright/test';
import { PlaywrightVisualRegressionTracker } from '@visual-regression-tracker/agent-playwright';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FIXTURE = 'file://' + path.join(__dirname, '..', 'fixtures', 'index.html');

/**
 * Minimal, self-contained version of the webinar demo. The baseline lives in the
 * tracker's database, not in this repository — no PNG file is created here, the
 * server computes the diff, and a human approves or rejects it in the panel at
 * http://localhost:8082.
 *
 *   npx playwright test              clean baseline run
 *   DEMO_BUG=1 npx playwright test   the same test, with the logo hidden
 */

const INJECT_BUG = Boolean(process.env.DEMO_BUG);

test.describe('VRT Tracker webinar demo', () => {
  let vrt: PlaywrightVisualRegressionTracker;

  test.beforeAll(async ({ browserName }) => {
    vrt = new PlaywrightVisualRegressionTracker(browserName, {
      apiUrl: process.env.VRT_APIURL ?? 'http://localhost:4200',
      project: process.env.VRT_PROJECT ?? 'VRT Webinar Demo',
      apiKey: process.env.VRT_APIKEY ?? 'DEFAULTUSERAPIKEYTOBECHANGED',
      branchName: process.env.VRT_BRANCHNAME ?? 'main',
      enableSoftAssert: process.env.VRT_ENABLESOFTASSERT !== 'false',
    });
    await vrt.start();
  });

  test.afterAll(async () => {
    await vrt.stop();
  });

  test('header, logo present', async ({ page }) => {
    const url = INJECT_BUG ? `${FIXTURE}?bug=header-logo` : FIXTURE;
    await page.goto(url);

    const header = page.getByTestId('site-header');
    await expect(header).toBeVisible();

    await vrt.trackElementHandle(
      header,
      'Webinar Header',
      {
        screenshotOptions: { animations: 'disabled', caret: 'hide' },
        diffTollerancePercent: 1,
        agent: { os: process.platform, device: 'desktop' },
        comment: INJECT_BUG ? 'feature branch run' : 'baseline run',
      },
      0,
    );
  });
});
