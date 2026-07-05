import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';

async function loadPlaywright() {
  try {
    return await import('playwright');
  } catch {
    const require = createRequire(import.meta.url);
    return require('../local_archive/playwright-runner/node_modules/playwright');
  }
}

function argValue(name, fallback = '') {
  const index = process.argv.indexOf(name);
  if (index === -1 || index + 1 >= process.argv.length) return fallback;
  return process.argv[index + 1];
}

async function firstExisting(paths) {
  for (const candidate of paths) {
    try {
      await fs.access(candidate);
      return candidate;
    } catch {
      // Try the next known Playwright browser cache path.
    }
  }
  return null;
}

const repoRoot = process.cwd();
const { chromium } = await loadPlaywright();
const topic = argValue('--topic');
if (!topic.trim()) {
  throw new Error('Usage: node tools/run_forge_browser_stress.mjs --topic "<topic>" [--base-url http://127.0.0.1:8000] [--out-dir "..."]');
}

const baseUrl = argValue('--base-url', 'http://127.0.0.1:8000').replace(/\/+$/, '');
const outDir = argValue(
  '--out-dir',
  path.join(repoRoot, 'Troubleshooting Prompts', `forge_browser_stress_${new Date().toISOString().slice(0, 10)}`)
);
const timeoutMs = Number(argValue('--timeout-ms', '720000'));
const pollMs = Number(argValue('--poll-ms', '5000'));

await fs.mkdir(outDir, { recursive: true });
await fs.writeFile(path.join(outDir, '00_user_input.txt'), topic, 'utf8');

const userHome = process.env.USERPROFILE || process.env.HOME || '';
const executablePath = await firstExisting([
  path.join(userHome, 'AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe'),
  path.join(userHome, 'AppData/Local/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-win64/chrome-headless-shell.exe'),
  path.join(userHome, 'AppData/Local/ms-playwright/chromium-1200/chrome-win64/chrome.exe'),
  path.join(userHome, 'AppData/Local/ms-playwright/chromium_headless_shell-1200/chrome-headless-shell-win64/chrome-headless-shell.exe'),
]);

const browser = await chromium.launch({
  headless: true,
  ...(executablePath ? { executablePath } : {}),
});

let page;
try {
  page = await browser.newPage({
    viewport: { width: 1440, height: 1200 },
    acceptDownloads: true,
  });

  const consoleLog = [];
  page.on('console', msg => {
    consoleLog.push({ ts: new Date().toISOString(), type: msg.type(), text: msg.text() });
  });
  page.on('pageerror', err => {
    consoleLog.push({ ts: new Date().toISOString(), type: 'pageerror', text: err.message });
  });

  await page.goto(`${baseUrl}/forge`, { waitUntil: 'networkidle', timeout: 60000 });
  await page.fill('#topic', topic);
  await page.evaluate(() => {
    const demo = document.getElementById('demo-mode-toggle');
    if (demo) demo.checked = false;
    const op = document.getElementById('operator-toggle');
    if (op) op.checked = true;
    const chaos = document.getElementById('chaos');
    if (chaos) {
      chaos.value = '7';
      chaos.dispatchEvent(new Event('input', { bubbles: true }));
    }
  });

  await page.screenshot({ path: path.join(outDir, '01_forge_before.png'), fullPage: true });
  await page.click('#forge-btn');

  const started = Date.now();
  let status = {};
  while (Date.now() - started < timeoutMs) {
    await page.waitForTimeout(pollMs);
    status = await page.evaluate(() => ({
      storyStatus: document.getElementById('status-story')?.textContent || '',
      storyDetail: document.getElementById('detail-story')?.textContent || '',
      qualityStatus: document.getElementById('status-quality')?.textContent || '',
      qualityDetail: document.getElementById('detail-quality')?.textContent || '',
      promptStatus: document.getElementById('status-prompt')?.textContent || '',
      promptDetail: document.getElementById('detail-prompt')?.textContent || '',
      debug: document.getElementById('debug-box')?.innerText || '',
      hasStory: !!currentStoryData,
      anchors: currentStoryData?.voLines?.length || 0,
      prompt1Len: document.getElementById('prompt-copy-1')?.value?.length || 0,
      prompt2Len: document.getElementById('prompt-copy-2')?.value?.length || 0,
      forgeBtnDisabled: document.getElementById('forge-btn')?.disabled || false,
    }));
    await fs.writeFile(path.join(outDir, 'live_status.json'), JSON.stringify(status, null, 2), 'utf8');

    const terminalError = /ERROR|[✗]/i.test(`${status.storyStatus} ${status.promptStatus}`);
    if (status.prompt2Len > 1000 || terminalError) break;
  }

  await page.screenshot({ path: path.join(outDir, '02_forge_after.png'), fullPage: true });
  const bundle = await page.evaluate(() => {
    const topic = document.getElementById('topic')?.value?.trim() || '';
    const qualityResultEl = document.getElementById('quality-result');
    const img1 = document.getElementById('gen-img-1-el');
    const img2 = document.getElementById('gen-img-2-el');
    const resultImg = document.getElementById('gen-img-result-el');
    return {
      _format: 'mnemorized-forge-bundle-v1',
      exported_at: new Date().toISOString(),
      topic,
      model: typeof CLAUDE_MODEL !== 'undefined' ? CLAUDE_MODEL : '',
      sketchy_style_prompt: typeof SKETCHY_STYLE !== 'undefined' ? SKETCHY_STYLE : '',
      story: currentStoryData || null,
      image_prompts: {
        prompt1: currentPromptData?.prompt1 || document.getElementById('prompt-copy-1')?.value || '',
        prompt2: currentPromptData?.prompt2 || document.getElementById('prompt-copy-2')?.value || '',
      },
      quality_gate: qualityResultEl?.innerText?.trim() || '',
      generated_images: {
        image_1: (img1?.src && img1.src.startsWith('data:')) ? img1.src : null,
        image_2: (img2?.src && img2.src.startsWith('data:')) ? img2.src : null,
        final: (resultImg?.src && resultImg.src.startsWith('data:')) ? resultImg.src : null,
      },
      guided_video: window.MnemorizedGuided?.getBundleData?.() || null,
      status_snapshot: {
        story: document.getElementById('status-story')?.textContent || '',
        story_detail: document.getElementById('detail-story')?.textContent || '',
        quality: document.getElementById('status-quality')?.textContent || '',
        quality_detail: document.getElementById('detail-quality')?.textContent || '',
        prompt: document.getElementById('status-prompt')?.textContent || '',
        prompt_detail: document.getElementById('detail-prompt')?.textContent || '',
        debug: document.getElementById('debug-box')?.innerText || '',
      },
    };
  });

  await fs.writeFile(path.join(outDir, '03_forge_bundle.json'), JSON.stringify(bundle, null, 2), 'utf8');
  await fs.writeFile(path.join(outDir, '04_browser_console.json'), JSON.stringify(consoleLog, null, 2), 'utf8');
  await fs.writeFile(path.join(outDir, '05_run_meta.json'), JSON.stringify({
    baseUrl,
    outDir,
    executablePath,
    status,
    anchors: bundle.story?.voLines?.length || 0,
    prompt1Len: bundle.image_prompts?.prompt1?.length || 0,
    prompt2Len: bundle.image_prompts?.prompt2?.length || 0,
  }, null, 2), 'utf8');

  console.log(JSON.stringify({
    outDir,
    status,
    anchors: bundle.story?.voLines?.length || 0,
    prompt1Len: bundle.image_prompts?.prompt1?.length || 0,
    prompt2Len: bundle.image_prompts?.prompt2?.length || 0,
  }, null, 2));
} finally {
  await page?.close().catch(() => {});
  await browser.close().catch(() => {});
}
