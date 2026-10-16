import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';

async function loadPlaywright() {
  try {
    return await import('playwright');
  } catch {
    // Legacy convenience for the original dev machine's archived runner;
    // local_archive/ is gitignored, so fresh clones will not have it.
    try {
      const require = createRequire(import.meta.url);
      return require('../local_archive/playwright-runner/node_modules/playwright');
    } catch {
      throw new Error(
        'Playwright is not installed. From the repo root run:\n' +
        '  npm install playwright\n' +
        '  npx playwright install chromium\n' +
        'then re-run this script.'
      );
    }
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
const resumeBundlePath = argValue('--resume-bundle');
const redesign = process.argv.includes('--redesign');
const repair = process.argv.includes('--repair');
const expertReview = process.argv.includes('--expert-review');
const feedbackPath = argValue('--feedback-file');
const repairUnitsArg = argValue('--repair-units');
if (process.argv.includes('--repair-units') && !repairUnitsArg.trim()) throw new Error('--repair-units needs a nonempty anchor selection.');
const repairUnits = repairUnitsArg ? repairUnitsArg.split(',').map(Number) : undefined;
if (repairUnits && (!repair || redesign || !/^\d+(?:,\d+)*$/.test(repairUnitsArg))) {
  throw new Error('--repair-units requires --repair and comma-separated existing anchor IDs.');
}
if (redesign && repair) throw new Error('Choose --redesign or --repair, not both.');
if ((redesign || repair) && !resumeBundlePath) throw new Error('Repair/redesign requires a real exported --resume-bundle.');
if ((expertReview || feedbackPath) && !resumeBundlePath) throw new Error('Expert review/audit feedback requires a real exported --resume-bundle.');
const externalFeedback = feedbackPath ? await fs.readFile(feedbackPath, 'utf8') : '';
if (externalFeedback.length > 20000) throw new Error('Audit feedback exceeds the Forge 20,000-character limit.');
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

async function findCachedChromium() {
  const userHome = process.env.USERPROFILE || process.env.HOME || '';
  const cacheDir = path.join(userHome, 'AppData/Local/ms-playwright');
  let entries;
  try {
    entries = await fs.readdir(cacheDir);
  } catch {
    return null;
  }
  // Prefer full chromium builds over headless-shell builds, newest first.
  const full = entries.filter((e) => e.startsWith('chromium-')).sort().reverse();
  const shell = entries.filter((e) => e.startsWith('chromium_headless_shell-')).sort().reverse();
  return firstExisting([
    ...full.map((e) => path.join(cacheDir, e, 'chrome-win64/chrome.exe')),
    ...shell.map((e) => path.join(cacheDir, e, 'chrome-headless-shell-win64/chrome-headless-shell.exe')),
  ]);
}

// If no cached browser is found, chromium.launch() falls back to Playwright's
// own registry resolution (works after `npx playwright install chromium`).
const executablePath = await findCachedChromium();

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
  const networkCaptureTasks = [];
  const providerExchanges = [];
  let qualityGateExchange = null;
  page.on('console', msg => {
    consoleLog.push({ ts: new Date().toISOString(), type: msg.type(), text: msg.text() });
  });
  page.on('pageerror', err => {
    consoleLog.push({ ts: new Date().toISOString(), type: 'pageerror', text: err.message });
  });
  page.on('response', response => {
    if (response.url().endsWith('/api/anthropic/messages')) {
      networkCaptureTasks.push((async () => {
        const request = response.request();
        let requestBody = null;
        let responseBody = null;
        try { requestBody = request.postDataJSON(); } catch { /* no JSON body */ }
        try { responseBody = await response.json(); } catch { /* non-JSON failure */ }
        const exchange = {
          captured_at: new Date().toISOString(),
          status: response.status(),
          request: requestBody,
          response: responseBody,
        };
        providerExchanges.push(exchange);
        await fs.writeFile(path.join(outDir, '07_provider_exchanges.json'), JSON.stringify(providerExchanges, null, 2), 'utf8');
      })());
    }
    if (!response.url().includes('/api/medical-knowledge/quality-check')) return;
    networkCaptureTasks.push((async () => {
      const request = response.request();
      let requestBody = null;
      let responseBody = null;
      try {
        requestBody = request.postDataJSON();
      } catch {
        requestBody = request.postData() || null;
      }
      try {
        responseBody = await response.json();
      } catch {
        responseBody = await response.text().catch(() => null);
      }
      qualityGateExchange = {
        captured_at: new Date().toISOString(),
        status: response.status(),
        request: requestBody,
        response: responseBody,
      };
    })());
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
  if (resumeBundlePath) {
    const source = JSON.parse(await fs.readFile(resumeBundlePath, 'utf8'));
    if (source.topic !== topic || !source.story?.voLines?.length) throw new Error('Recovery requires the exact topic and full saved Forge story.');
    if (repairUnits && (new Set(repairUnits).size !== repairUnits.length ||
        repairUnits.some(n => !source.story.voLines.some(line => line.n === n)))) {
      throw new Error('Repair units must be unique IDs in the saved Forge story.');
    }
    await fs.writeFile(path.join(outDir, 'recovery_provenance.json'), JSON.stringify({
      run_kind: 'development_recovery_not_fresh_first_pass', source_bundle: path.resolve(resumeBundlePath),
      source_exported_at: source.exported_at,
      recovery_action: redesign ? 'forge_evidence_backed_redesign' : repair ? 'forge_evidence_backed_repair' : 'gate_and_preflight_rebuild',
      expert_review: expertReview,
      repair_units: repairUnits || null,
      feedback_file: feedbackPath ? path.resolve(feedbackPath) : null,
      feedback_sha256: externalFeedback ? createHash('sha256').update(externalFeedback).digest('hex') : null,
    }, null, 2));
    await page.evaluate(({story, redesign, repair, expertReview, reviewHistory, externalFeedback, repairUnits}) => {
      document.getElementById('pipeline').classList.add('visible');
      currentStoryData = story;
      renderStoryData(story);
      document.getElementById('forge-btn').disabled = true;
      window.__recovery = (async () => {
        await runMedicalQualityGate(story, story.required_concepts);
        if (redesign || repair) await repairCurrentPalaceWithMedicalEvidence({redesignVisuals: redesign, expertReview, reviewHistory, externalFeedback, repairUnits});
        else await rebuildImagePromptsForStory(story, null, {expertReview, externalFeedback});
      })().finally(() => { document.getElementById('forge-btn').disabled = false; });
    }, {story: source.story, redesign, repair, expertReview, reviewHistory: source.visual_preflight, externalFeedback, repairUnits});
  } else {
    await page.click('#forge-btn');
  }

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

    const terminalError = /ERROR|failed|[✗]/i.test(`${status.storyStatus} ${status.promptStatus}`) ||
      (!status.forgeBtnDisabled && /ERROR|failed|[✗]/i.test(status.qualityStatus));
    if ((status.prompt2Len > 0 && !status.forgeBtnDisabled) || terminalError) break;
  }

  await page.screenshot({ path: path.join(outDir, '02_forge_after.png'), fullPage: true });
  await Promise.allSettled(networkCaptureTasks);
  const bundle = await page.evaluate(() => {
    const topic = document.getElementById('topic')?.value?.trim() || '';
    const qualityResultEl = document.getElementById('quality-result');
    const img1 = document.getElementById('gen-img-1-el');
    const img2 = document.getElementById('gen-img-2-el');
    const resultImg = document.getElementById('gen-img-result-el');
    return {
      _format: 'mnemorized-forge-bundle-v1',
      run_kind: window.__recovery ? 'development_recovery_not_fresh_first_pass' : 'fresh_forge_generation',
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
      quality_gate_data: currentQualityGateData || null,
      visual_preflight: window.MnemorizedVisualPreflight?.getReport() || null,
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
  await fs.writeFile(
    path.join(outDir, '06_quality_gate_exchange.json'),
    JSON.stringify(qualityGateExchange, null, 2),
    'utf8'
  );
  await fs.writeFile(path.join(outDir, '05_run_meta.json'), JSON.stringify({
    baseUrl,
    outDir,
    executablePath,
    status,
    anchors: bundle.story?.voLines?.length || 0,
    prompt1Len: bundle.image_prompts?.prompt1?.length || 0,
    prompt2Len: bundle.image_prompts?.prompt2?.length || 0,
    qualityGateHttpStatus: qualityGateExchange?.status || null,
    qualityGateEvidenceStatus: qualityGateExchange?.response?.evidence_status || null,
    qualityGateEvidenceCount: qualityGateExchange?.response?.evidence_count || 0,
  }, null, 2), 'utf8');

  console.log(JSON.stringify({
    outDir,
    status,
    anchors: bundle.story?.voLines?.length || 0,
    prompt1Len: bundle.image_prompts?.prompt1?.length || 0,
    prompt2Len: bundle.image_prompts?.prompt2?.length || 0,
    qualityGateHttpStatus: qualityGateExchange?.status || null,
    qualityGateEvidenceStatus: qualityGateExchange?.response?.evidence_status || null,
    qualityGateEvidenceCount: qualityGateExchange?.response?.evidence_count || 0,
  }, null, 2));
} finally {
  await page?.close().catch(() => {});
  await browser.close().catch(() => {});
}
