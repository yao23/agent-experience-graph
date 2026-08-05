import * as vscode from 'vscode';
import * as path from 'path';
import {
  ExperienceReceipt,
  RankedPlaybook,
  RecoveryPlaybook,
  classifyFailure,
  estimateTokens,
  failureSignature,
  rankPlaybooks,
  redactSensitiveText
} from './core';
import {
  ExperienceFeedback,
  ExperienceRating,
  VerifiedExperienceMatch,
  appendExperienceFeedback,
  generateRecoveryCapsule,
  loadVerifiedExperienceLibrary,
  rankVerifiedExperiences
} from './verifiedExperience';

const VERIFIED_EXPERIENCE_DEMO = 'Keepalive control fails after active stream ownership moved behind a protocol object; repair the public wrapper so it delegates through the protocol without using its stale socket field.';

interface SkillRecord {
  id: string;
  name: string;
  description: string;
  uri: vscode.Uri;
  tags: string[];
  source: 'SKILL.md' | 'capability.json';
}

interface SkillMetric {
  uses: number;
  totalEstimatedTokens: number;
  ratings: number[];
  lastUsed?: string;
}

type Metrics = Record<string, SkillMetric>;
type DiagnosisSource = 'selection' | 'active-file' | 'artifact' | 'pasted';

interface FailureInput {
  source: DiagnosisSource;
  text: string;
  intent: string;
  artifactUri?: vscode.Uri;
}

class AegTreeItem extends vscode.TreeItem {
  constructor(
    label: string,
    description: string,
    icon: string,
    command?: vscode.Command
  ) {
    super(label, vscode.TreeItemCollapsibleState.None);
    this.description = description;
    this.iconPath = new vscode.ThemeIcon(icon);
    this.command = command;
  }
}

class PlaywrightViewProvider implements vscode.TreeDataProvider<AegTreeItem> {
  private readonly changeEmitter = new vscode.EventEmitter<AegTreeItem | undefined>();
  readonly onDidChangeTreeData = this.changeEmitter.event;

  refresh(): void {
    this.changeEmitter.fire(undefined);
  }

  getTreeItem(element: AegTreeItem): vscode.TreeItem {
    return element;
  }

  async getChildren(): Promise<AegTreeItem[]> {
    const count = await countExperienceReceipts();
    return [
      new AegTreeItem(
        'Try a verified experience',
        'task → match → recovery capsule',
        'library',
        {command: 'aeg.tryVerifiedExperience', title: 'Try verified experience'}
      ),
      new AegTreeItem(
        'Open the transfer challenge',
        'bundled zero-cold-start demo',
        'lightbulb-autofix',
        {command: 'aeg.openVerifiedExperienceDemo', title: 'Open challenge'}
      ),
      new AegTreeItem(
        'Diagnose Playwright failure',
        'selection, artifact, file, or clipboard',
        'debug-alt',
        {command: 'aeg.diagnosePlaywrightFailure', title: 'Diagnose'}
      ),
      new AegTreeItem(
        'Mark latest outcome',
        'resolved or unresolved',
        'pass',
        {command: 'aeg.verifyLatestExperience', title: 'Verify'}
      ),
      new AegTreeItem(
        'Local experience receipts',
        `${count} recorded`,
        'history',
        {command: 'aeg.showExperiences', title: 'Show experiences'}
      ),
      new AegTreeItem(
        'Run public repair lab',
        'baseline vs AEG-assisted',
        'beaker',
        {command: 'aeg.runPublicRepairLab', title: 'Run repair lab'}
      ),
      new AegTreeItem(
        'Privacy',
        'local only · no upload',
        'shield',
        {command: 'aeg.openGettingStarted', title: 'Getting started'}
      )
    ];
  }
}

export function activate(context: vscode.ExtensionContext): void {
  const status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  status.text = '$(library) AEG Experience';
  status.command = 'aeg.tryVerifiedExperience';
  status.tooltip = 'Retrieve verified debugging experience before starting from scratch';
  status.show();

  const viewProvider = new PlaywrightViewProvider();
  const tree = vscode.window.createTreeView('aeg.playwright', {treeDataProvider: viewProvider});
  const notifiedArtifacts = new Set<string>();
  const watcher = vscode.workspace.createFileSystemWatcher('**/test-results/**/*');

  const maybeNotify = async (uri: vscode.Uri): Promise<void> => {
    if (!vscode.workspace.getConfiguration('aeg').get<boolean>('notifyOnPlaywrightArtifacts', true)) return;
    if (notifiedArtifacts.has(uri.toString())) return;
    if (!/\.(md|txt|log|xml|json)$/i.test(uri.path)) return;
    notifiedArtifacts.add(uri.toString());
    const action = await vscode.window.showInformationMessage(
      `AEG detected a Playwright artifact: ${path.basename(uri.fsPath)}`,
      'Diagnose'
    );
    if (action === 'Diagnose') {
      await diagnosePlaywrightFailure(viewProvider, uri);
    }
  };

  watcher.onDidCreate(uri => void maybeNotify(uri));
  watcher.onDidChange(uri => void maybeNotify(uri));

  context.subscriptions.push(
    status,
    tree,
    watcher,
    vscode.commands.registerCommand(
      'aeg.tryVerifiedExperience',
      () => tryVerifiedExperience(context.extensionUri)
    ),
    vscode.commands.registerCommand(
      'aeg.openVerifiedExperienceDemo',
      () => tryVerifiedExperience(context.extensionUri, VERIFIED_EXPERIENCE_DEMO)
    ),
    vscode.commands.registerCommand(
      'aeg.diagnosePlaywrightFailure',
      (uri?: vscode.Uri) => diagnosePlaywrightFailure(viewProvider, uri)
    ),
    vscode.commands.registerCommand(
      'aeg.verifyLatestExperience',
      () => verifyLatestExperience(viewProvider)
    ),
    vscode.commands.registerCommand('aeg.showExperiences', showExperiences),
    vscode.commands.registerCommand('aeg.openGettingStarted', openGettingStarted),
    vscode.commands.registerCommand('aeg.runPublicRepairLab', () => runPublicRepairLab(context.extensionUri)),
    vscode.commands.registerCommand('aeg.discoverSkills', discoverSkills),
    vscode.commands.registerCommand('aeg.recommendSkill', recommendSkill),
    vscode.commands.registerCommand('aeg.rateSkill', rateSkill),
    vscode.commands.registerCommand('aeg.showSkillMetrics', showSkillMetrics)
  );
}

export function deactivate(): void {
  // All resources are registered through the extension context.
}

async function tryVerifiedExperience(extensionUri: vscode.Uri, presetTask?: string): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  const selectedText = editor && !editor.selection.isEmpty
    ? redactSensitiveText(editor.document.getText(editor.selection), 1_000)
    : '';
  const task = presetTask ?? await vscode.window.showInputBox({
    title: 'AEG: Try a Verified Experience',
    prompt: 'Describe the task, error, or issue. AEG ranks only bundled verified records; it does not upload this text.',
    value: selectedText,
    placeHolder: 'A protocol wrapper still uses a stale socket after stream ownership moved'
  });
  if (!task?.trim()) return;

  const libraryUri = vscode.Uri.joinPath(extensionUri, 'verified-experiences', 'verified.json');
  let raw: string;
  try {
    raw = Buffer.from(await vscode.workspace.fs.readFile(libraryUri)).toString('utf8');
  } catch {
    void vscode.window.showErrorMessage('The bundled verified-experience library is missing. Reinstall AEG v0.1.4.');
    return;
  }

  const library = loadVerifiedExperienceLibrary(raw);
  if (library.malformed.length) {
    void vscode.window.showWarningMessage(`AEG excluded ${library.malformed.length} malformed verified-experience record(s).`);
  }
  const matches = rankVerifiedExperiences(task, library.experiences);
  if (!matches.length) {
    void vscode.window.showInformationMessage('AEG found no verified experience above the retrieval threshold. No candidate or fallback guidance was injected.');
    return;
  }

  const picked = await vscode.window.showQuickPick(
    matches.map(match => ({
      label: match.experience.task,
      description: `${Math.round(match.score * 100)}% weighted match · ${match.experience.verification.status}`,
      detail: match.evidence.length
        ? `Why: ${match.evidence.slice(0, 2).map(item => `${item.field} matched “${item.experiencePhrase}”`).join('; ')}`
        : 'No lexical evidence',
      match
    })),
    {
      title: 'Verified experience matches',
      placeHolder: 'Choose a verified record to inspect before your coding agent starts',
      matchOnDescription: true,
      matchOnDetail: true
    }
  );
  if (!picked) return;
  await showVerifiedExperiencePanel(task, picked.match);
}

async function showVerifiedExperiencePanel(task: string, match: VerifiedExperienceMatch): Promise<void> {
  const panel = vscode.window.createWebviewPanel(
    'aegVerifiedExperience',
    'AEG: Verified Experience',
    vscode.ViewColumn.Beside,
    {enableScripts: true}
  );
  const capsule = generateRecoveryCapsule(match);
  panel.webview.html = verifiedExperienceHtml(match, capsule, panel.webview);
  panel.webview.onDidReceiveMessage(async message => {
    if (message?.command === 'copy') {
      await vscode.env.clipboard.writeText(capsule);
      void vscode.window.showInformationMessage('Verified-experience recovery capsule copied. Validate it against the local repository before applying changes.');
      return;
    }
    if (message?.command === 'rate' && isExperienceRating(message.rating)) {
      const saved = await writeVerifiedExperienceFeedback(task, match, message.rating);
      if (saved) void vscode.window.showInformationMessage(`AEG recorded “${message.rating}” feedback locally.`);
    }
  });
}

function isExperienceRating(value: unknown): value is ExperienceRating {
  return value === 'helpful' || value === 'partially-helpful' || value === 'irrelevant' || value === 'harmful';
}

async function writeVerifiedExperienceFeedback(
  task: string,
  match: VerifiedExperienceMatch,
  rating: ExperienceRating
): Promise<boolean> {
  const root = workspaceRoot();
  if (!root) {
    void vscode.window.showWarningMessage('Open a workspace folder to save local AEG feedback.');
    return false;
  }
  const configured = vscode.workspace.getConfiguration('aeg').get<string>(
    'verifiedExperienceFeedbackFile',
    '.aeg/verified-experience-feedback.json'
  );
  const uri = vscode.Uri.joinPath(root, ...configured.split('/'));
  const parent = vscode.Uri.joinPath(uri, '..');
  await vscode.workspace.fs.createDirectory(parent);
  let raw = '';
  try {
    raw = Buffer.from(await vscode.workspace.fs.readFile(uri)).toString('utf8');
  } catch {
    // A missing file is the expected first-use state.
  }
  const feedback: ExperienceFeedback = {
    schemaVersion: '1.0.0',
    recordedAt: new Date().toISOString(),
    experienceId: match.experience.id,
    taskSummary: redactSensitiveText(task, 500),
    rating,
    retrievalScore: match.score,
    localOnly: true
  };
  await vscode.workspace.fs.writeFile(
    uri,
    Buffer.from(JSON.stringify(appendExperienceFeedback(raw, feedback), null, 2), 'utf8')
  );
  return true;
}

function verifiedExperienceHtml(
  match: VerifiedExperienceMatch,
  capsule: string,
  webview: vscode.Webview
): string {
  const nonce = `${Date.now()}`;
  const experience = match.experience;
  const source = experience.provenance.publicSource;
  const list = (items: string[]) => items.map(item => `<li>${escapeHtml(item)}</li>`).join('');
  const evidence = match.evidence.map(item => `<tr><td>${escapeHtml(item.field)}</td><td>${escapeHtml(item.queryPhrase)}</td><td>${escapeHtml(item.experiencePhrase)}</td><td>${item.lexicalScore.toFixed(3)}</td><td>${item.weightedContribution.toFixed(3)}</td></tr>`).join('');
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{padding:28px;max-width:920px;margin:auto;font:14px/1.55 var(--vscode-font-family);color:var(--vscode-foreground)}
.badge{display:inline-block;padding:4px 9px;border-radius:999px;background:var(--vscode-badge-background);color:var(--vscode-badge-foreground)}
.card,.guardrail{margin:18px 0;padding:18px;border:1px solid var(--vscode-widget-border);border-radius:10px;background:var(--vscode-editor-background)}
.guardrail{border-left:4px solid var(--vscode-editorWarning-foreground)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px} h1{line-height:1.15} h2{margin-top:26px} li{margin:6px 0}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:7px;border-bottom:1px solid var(--vscode-widget-border)}
pre{white-space:pre-wrap;padding:14px;background:var(--vscode-textCodeBlock-background);overflow:auto}
button{margin:6px 8px 0 0;padding:8px 12px;color:var(--vscode-button-foreground);background:var(--vscode-button-background);border:0;border-radius:4px;cursor:pointer}
button.secondary{color:var(--vscode-button-secondaryForeground);background:var(--vscode-button-secondaryBackground)}
@media(max-width:650px){.grid{grid-template-columns:1fr}}
</style></head><body>
<span class="badge">${Math.round(match.score * 100)}% weighted match · verification ${escapeHtml(experience.verification.status)}</span>
<h1>${escapeHtml(experience.task)}</h1>
<div class="guardrail"><strong>Guidance, not a guaranteed answer.</strong> Inspect the local code, reproduce the failure, and validate any repair with focused and regression tests.</div>
<div class="grid"><section class="card"><h2>Reusable lessons</h2><ul>${list(experience.lessons)}</ul></section><section class="card"><h2>Recommended use cases</h2><ul>${list(experience.reuse.recommendedFor)}</ul></section></div>
<div class="grid"><section class="card"><h2>Constraints</h2><ul>${list(experience.constraints)}</ul></section><section class="card"><h2>Limitations</h2><ul>${list(experience.limitations)}</ul></section></div>
<h2>Why this matched</h2><table><thead><tr><th>Field</th><th>Task phrase</th><th>Experience phrase</th><th>Lexical</th><th>Weighted</th></tr></thead><tbody>${evidence}</tbody></table>
<h2>Provenance and outcome</h2><p>Outcome: <strong>${escapeHtml(experience.outcome)}</strong>. Public source: ${escapeHtml(source.repository)} · ${escapeHtml(source.license)} · ${escapeHtml(source.benchmark)}. Experiment artifact: <code>${escapeHtml(experience.provenance.experimentEvidence.artifact)}</code>.</p>
<h2>Compact recovery capsule</h2><pre>${escapeHtml(capsule)}</pre><p><button data-command="copy">Copy capsule</button></p>
<h2>Was this useful?</h2><p><button data-rating="helpful">Helpful</button><button class="secondary" data-rating="partially-helpful">Partially helpful</button><button class="secondary" data-rating="irrelevant">Irrelevant</button><button class="secondary" data-rating="harmful">Harmful</button></p>
<p><small>Ratings are written only to this workspace under <code>.aeg/</code>. AEG v0.1.4 does not upload task text, code, capsules, or ratings.</small></p>
<script nonce="${nonce}">const vscode=acquireVsCodeApi();document.querySelector('[data-command]').addEventListener('click',()=>vscode.postMessage({command:'copy'}));document.querySelectorAll('[data-rating]').forEach(button=>button.addEventListener('click',()=>vscode.postMessage({command:'rate',rating:button.dataset.rating})));</script>
</body></html>`;
}

async function diagnosePlaywrightFailure(
  viewProvider: PlaywrightViewProvider,
  preferredArtifact?: vscode.Uri
): Promise<void> {
  const root = workspaceRoot();
  if (!root) {
    void vscode.window.showWarningMessage('Open a workspace folder before recording an AEG experience.');
    return;
  }

  const startedAt = Date.now();
  const input = await collectFailureInput(preferredArtifact);
  if (!input) return;

  const sanitized = redactSensitiveText(input.text);
  const ranked = rankPlaybooks(sanitized).slice(0, 3);
  const selected = await pickRecoveryPlaybook(ranked);
  if (!selected) return;

  const receipt = createReceipt(input, sanitized, selected, startedAt);
  const receiptUri = await writeExperienceReceipt(receipt);
  viewProvider.refresh();
  await showRecoveryPanel(receipt, selected.playbook, receiptUri);
}

async function collectFailureInput(preferredArtifact?: vscode.Uri): Promise<FailureInput | undefined> {
  if (preferredArtifact) {
    const text = await readTextFile(preferredArtifact);
    if (text) {
      return {
        source: 'artifact',
        text,
        intent: `Diagnose ${path.basename(preferredArtifact.fsPath)}`,
        artifactUri: preferredArtifact
      };
    }
  }

  const editor = vscode.window.activeTextEditor;
  const selectedText = editor && !editor.selection.isEmpty
    ? editor.document.getText(editor.selection).trim()
    : '';
  const latestArtifact = await findLatestArtifact();

  const options: Array<vscode.QuickPickItem & {inputKind: DiagnosisSource | 'clipboard'}> = [];
  if (selectedText) {
    options.push({
      label: 'Use selected text',
      description: `${selectedText.length} characters`,
      detail: 'Best for an error, stack trace, or failed assertion',
      inputKind: 'selection'
    });
  }
  if (latestArtifact) {
    options.push({
      label: 'Use latest Playwright artifact',
      description: vscode.workspace.asRelativePath(latestArtifact),
      detail: 'AEG found this in test-results, playwright-report, or JUnit output',
      inputKind: 'artifact'
    });
  }
  if (editor) {
    options.push({
      label: 'Use active file',
      description: path.basename(editor.document.uri.fsPath),
      detail: 'Reads at most 8,000 characters and redacts common secrets',
      inputKind: 'active-file'
    });
  }
  options.push(
    {
      label: 'Use clipboard',
      description: 'Paste a copied Playwright failure',
      inputKind: 'clipboard'
    },
    {
      label: 'Describe the failure',
      description: 'Enter a short error or symptom',
      inputKind: 'pasted'
    }
  );

  const choice = await vscode.window.showQuickPick(options, {
    title: 'AEG Playwright diagnosis',
    placeHolder: 'Choose the local evidence to diagnose'
  });
  if (!choice) return undefined;

  if (choice.inputKind === 'selection') {
    return {
      source: 'selection',
      text: selectedText,
      intent: 'Diagnose the selected Playwright failure'
    };
  }
  if (choice.inputKind === 'artifact' && latestArtifact) {
    const text = await readTextFile(latestArtifact);
    if (!text) return undefined;
    return {
      source: 'artifact',
      text,
      intent: `Diagnose ${path.basename(latestArtifact.fsPath)}`,
      artifactUri: latestArtifact
    };
  }
  if (choice.inputKind === 'active-file' && editor) {
    return {
      source: 'active-file',
      text: editor.document.getText(),
      intent: `Diagnose Playwright evidence in ${path.basename(editor.document.uri.fsPath)}`
    };
  }
  if (choice.inputKind === 'clipboard') {
    const text = (await vscode.env.clipboard.readText()).trim();
    if (!text) {
      void vscode.window.showInformationMessage('The clipboard is empty.');
      return undefined;
    }
    return {
      source: 'pasted',
      text,
      intent: 'Diagnose a copied Playwright failure'
    };
  }

  const text = await vscode.window.showInputBox({
    title: 'Describe the Playwright failure',
    prompt: 'Include the error and symptom; do not paste secrets.',
    placeHolder: 'Timeout 30000ms exceeded while waiting for getByRole("button", {name: "Submit"})'
  });
  if (!text?.trim()) return undefined;
  return {
    source: 'pasted',
    text,
    intent: 'Diagnose a described Playwright failure'
  };
}

async function pickRecoveryPlaybook(ranked: RankedPlaybook[]): Promise<RankedPlaybook | undefined> {
  const selected = await vscode.window.showQuickPick(
    ranked.map(item => ({
      label: item.playbook.name,
      description: `${Math.round(item.confidence * 100)}% confidence`,
      detail: item.matchedSignals.length
        ? `Matched: ${item.matchedSignals.join(', ')} · ${item.playbook.summary}`
        : `Low-confidence fallback · ${item.playbook.summary}`,
      item
    })),
    {
      title: 'Recommended Playwright recovery playbooks',
      placeHolder: 'Choose a playbook to record and try',
      matchOnDescription: true,
      matchOnDetail: true
    }
  );
  return selected?.item;
}

function createReceipt(
  input: FailureInput,
  sanitized: string,
  selected: RankedPlaybook,
  startedAt: number
): ExperienceReceipt {
  const now = new Date();
  const relativeArtifact = input.artifactUri
    ? vscode.workspace.asRelativePath(input.artifactUri, false)
    : undefined;

  return {
    schemaVersion: '0.1.1',
    id: `pw-${now.toISOString().replace(/[:.]/g, '-')}`,
    recordedAt: now.toISOString(),
    intent: {
      summary: input.intent
    },
    context: {
      framework: 'playwright',
      workspace: vscode.workspace.name ?? 'workspace',
      source: input.source,
      platform: `${process.platform}-${process.arch}`,
      artifactPath: relativeArtifact
    },
    steps: [
      {
        at: now.toISOString(),
        action: 'failure-captured',
        detail: `${input.source} evidence`
      },
      {
        at: now.toISOString(),
        action: 'playbook-recommended',
        detail: selected.playbook.id
      }
    ],
    skills: [
      {
        id: selected.playbook.id,
        name: selected.playbook.name,
        version: '0.1.1',
        confidence: selected.confidence
      }
    ],
    artifacts: relativeArtifact
      ? [{kind: artifactKind(relativeArtifact), path: relativeArtifact, redacted: true}]
      : [],
    failures: [
      {
        category: classifyFailure(sanitized),
        signature: failureSignature(sanitized),
        message: failureSignature(sanitized)
      }
    ],
    recovery: [
      {
        playbookId: selected.playbook.id,
        steps: selected.playbook.steps,
        status: 'suggested'
      }
    ],
    outcome: {
      status: 'unknown'
    },
    cost: {
      estimatedTokens: estimateTokens(sanitized + selected.playbook.summary),
      durationMs: Date.now() - startedAt,
      retries: 0
    },
    privacy: {
      localOnly: true,
      containsRawCode: false,
      shared: false
    }
  };
}

async function showRecoveryPanel(
  receipt: ExperienceReceipt,
  playbook: RecoveryPlaybook,
  receiptUri: vscode.Uri
): Promise<void> {
  const panel = vscode.window.createWebviewPanel(
    'aegPlaywrightRecovery',
    `AEG: ${playbook.name}`,
    vscode.ViewColumn.Beside,
    {enableScripts: true}
  );
  panel.webview.html = recoveryHtml(receipt, playbook, panel.webview);
  panel.webview.onDidReceiveMessage(async message => {
    if (message?.command === 'copy') {
      await vscode.env.clipboard.writeText(
        `${playbook.name}\n\n${playbook.steps.map((step, index) => `${index + 1}. ${step}`).join('\n')}`
      );
      void vscode.window.showInformationMessage('Recovery steps copied.');
    } else if (message?.command === 'outcome') {
      const status = message.status === 'resolved' ? 'resolved' : 'unresolved';
      await updateReceiptOutcome(receiptUri, status, 'Marked from the recovery view');
      void vscode.window.showInformationMessage(`AEG marked this experience ${status}.`);
      panel.dispose();
    } else if (message?.command === 'openReceipt') {
      await vscode.window.showTextDocument(receiptUri);
    }
  });
}

function recoveryHtml(
  receipt: ExperienceReceipt,
  playbook: RecoveryPlaybook,
  webview: vscode.Webview
): string {
  const nonce = `${Date.now()}`;
  const steps = playbook.steps.map(step => `<li>${escapeHtml(step)}</li>`).join('');
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { padding: 28px; max-width: 820px; margin: auto; font: 14px/1.6 var(--vscode-font-family); color: var(--vscode-foreground); }
    .badge { display:inline-block; padding:4px 9px; border-radius:999px; background:var(--vscode-badge-background); color:var(--vscode-badge-foreground); }
    .card { margin:20px 0; padding:18px; border:1px solid var(--vscode-widget-border); border-radius:10px; background:var(--vscode-editor-background); }
    h1 { line-height:1.15; }
    li { margin:10px 0; }
    button { margin:6px 8px 0 0; padding:8px 12px; color:var(--vscode-button-foreground); background:var(--vscode-button-background); border:0; border-radius:4px; cursor:pointer; }
    button.secondary { color:var(--vscode-button-secondaryForeground); background:var(--vscode-button-secondaryBackground); }
    code { color:var(--vscode-textPreformat-foreground); }
  </style>
</head>
<body>
  <span class="badge">${Math.round(receipt.skills[0].confidence * 100)}% confidence</span>
  <h1>${escapeHtml(playbook.name)}</h1>
  <p>${escapeHtml(playbook.summary)}</p>
  <div class="card">
    <strong>Failure signature</strong>
    <p><code>${escapeHtml(receipt.failures[0].signature)}</code></p>
  </div>
  <h2>Suggested recovery</h2>
  <ol>${steps}</ol>
  <p><button data-command="copy">Copy recovery steps</button><button class="secondary" data-command="openReceipt">Open local receipt</button></p>
  <h2>Verify the outcome</h2>
  <p>After trying the playbook and re-running the test, record the objective result.</p>
  <p><button data-outcome="resolved">Test passed</button><button class="secondary" data-outcome="unresolved">Still failing</button></p>
  <p><small>Local only: AEG v0.1.4 does not upload code, logs, or experience receipts.</small></p>
  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();
    document.querySelectorAll('[data-command]').forEach(button => button.addEventListener('click', () => vscode.postMessage({command: button.dataset.command})));
    document.querySelectorAll('[data-outcome]').forEach(button => button.addEventListener('click', () => vscode.postMessage({command: 'outcome', status: button.dataset.outcome})));
  </script>
</body>
</html>`;
}

async function verifyLatestExperience(viewProvider: PlaywrightViewProvider): Promise<void> {
  const latest = await latestExperienceReceipt();
  if (!latest) {
    void vscode.window.showInformationMessage('No local Playwright experience is available yet.');
    return;
  }

  const choice = await vscode.window.showQuickPick(
    [
      {label: 'Resolved — the test passed', status: 'resolved' as const},
      {label: 'Unresolved — the test is still failing', status: 'unresolved' as const}
    ],
    {title: 'Mark the latest Playwright diagnosis outcome'}
  );
  if (!choice) return;

  const note = await vscode.window.showInputBox({
    title: 'Optional verification note',
    placeHolder: 'Example: passed three times locally after replacing a fixed wait'
  });
  await updateReceiptOutcome(latest, choice.status, note || 'Marked from VS Code');
  viewProvider.refresh();
  void vscode.window.showInformationMessage(`AEG marked the latest experience ${choice.status}.`);
}

async function updateReceiptOutcome(
  uri: vscode.Uri,
  status: 'resolved' | 'unresolved',
  verification: string
): Promise<void> {
  const bytes = await vscode.workspace.fs.readFile(uri);
  const receipt = JSON.parse(Buffer.from(bytes).toString('utf8')) as ExperienceReceipt;
  receipt.outcome = {
    status,
    verification: redactSensitiveText(verification, 500),
    completedAt: new Date().toISOString()
  };
  receipt.recovery = receipt.recovery.map(item => ({...item, status: 'completed'}));
  receipt.steps.push({
    at: new Date().toISOString(),
    action: 'outcome-verified',
    detail: status
  });
  await vscode.workspace.fs.writeFile(uri, Buffer.from(JSON.stringify(receipt, null, 2), 'utf8'));
}

async function showExperiences(): Promise<void> {
  const files = await experienceReceiptFiles();
  if (files.length === 0) {
    void vscode.window.showInformationMessage('No local Playwright experiences are recorded yet.');
    return;
  }

  const rows = await Promise.all(files.slice(0, 50).map(async uri => {
    try {
      const bytes = await vscode.workspace.fs.readFile(uri);
      const receipt = JSON.parse(Buffer.from(bytes).toString('utf8')) as ExperienceReceipt;
      return {
        label: receipt.skills[0]?.name ?? 'Playwright diagnosis',
        description: `${receipt.outcome.status} · ${Math.round((receipt.skills[0]?.confidence ?? 0) * 100)}%`,
        detail: `${receipt.recordedAt} · ${receipt.failures[0]?.category ?? 'unknown'} · local only`,
        uri
      };
    } catch {
      return undefined;
    }
  }));

  const selected = await vscode.window.showQuickPick(
    rows.filter((row): row is NonNullable<typeof row> => Boolean(row)),
    {title: 'Local AEG Playwright experiences', matchOnDescription: true, matchOnDetail: true}
  );
  if (selected) await vscode.window.showTextDocument(selected.uri);
}

async function openGettingStarted(): Promise<void> {
  const document = await vscode.workspace.openTextDocument({
    language: 'markdown',
    content: `# AEG Verified Experience, Playwright Diagnosis & Public Repair Lab

AEG v0.1.4 retrieves verified debugging experience before your coding agent
starts from scratch. It also preserves the Playwright diagnosis workflow and
repeatable public repair experiments.

## Try a verified experience

1. Run **AEG: Try a Verified Experience** or select error text first.
2. Describe the task and choose a verified match.
3. Inspect the weighted match evidence, outcome, constraints, limitations, and provenance.
4. Copy the guarded capsule before the coding agent begins.
5. Validate the repair locally and rate the retrieval.

For a zero-cold-start demo, run **AEG: Open Verified Experience Challenge**.
The bundled challenge is synthetic; its prior controlled pair found the same
successful patch in both arms and higher assisted token and wall-time cost.

## Diagnose Playwright

1. Run **AEG: Diagnose Playwright Failure** or click **AEG Playwright** in the status bar.
2. Use selected error text, the latest Playwright artifact, the active file, or your clipboard.
3. Choose a recommended recovery playbook.
4. Try the steps and re-run the test.
5. Mark the outcome **resolved** or **unresolved**.

## What AEG records

Intent, Context, Steps, Skills, Artifacts, Failures, Recovery, Outcome, and Cost.

Receipts are stored under \`.aeg/experiences\`; verified-experience ratings use
\`.aeg/verified-experience-feedback.json\`. This release does not upload task
text, code, logs, capsules, ratings, or receipts.

## Public Repair Lab (v0.1.3)

Run **AEG: Run Public Repair Lab** to compare isolated Codex repairs of the same
MIT-licensed FastAPI nested response-model bug: a baseline run and an AEG-assisted
run with a compact retrieved recovery capsule. The runner keeps patches local and
writes machine-readable events, verification results, corrected cost metrics, and
a comparison report under \`.aeg/repair-lab\`.
`
  });
  await vscode.window.showTextDocument(document, {preview: true});
}

async function runPublicRepairLab(extensionUri: vscode.Uri): Promise<void> {
  const root = workspaceRoot();
  if (!root) {
    void vscode.window.showWarningMessage('Open the Agent Experience Graph repository before running the repair lab.');
    return;
  }
  const runner = vscode.Uri.joinPath(extensionUri, 'repair-lab', 'run_experiment.py');
  try {
    await vscode.workspace.fs.stat(runner);
  } catch {
    void vscode.window.showWarningMessage('The packaged AEG repair-lab runner is missing. Reinstall the extension.');
    return;
  }

  const terminal = vscode.window.createTerminal({
    name: 'AEG Public Repair Lab',
    cwd: root
  });
  terminal.show(true);
  terminal.sendText(`python3 "${runner.fsPath.replace(/"/g, '\\"')}"`, true);
  void vscode.window.showInformationMessage(
    'AEG started the isolated baseline and assisted repair runs. Results will be written under .aeg/repair-lab.'
  );
}

async function findLatestArtifact(): Promise<vscode.Uri | undefined> {
  const globs = vscode.workspace.getConfiguration('aeg').get<string[]>(
    'playwrightArtifactGlobs',
    ['**/test-results/**/error-context.md', '**/test-results/**/*.txt', '**/test-results/**/*.log', '**/playwright-report/**/*.json', '**/junit*.xml']
  );
  const files = new Map<string, vscode.Uri>();
  for (const glob of globs) {
    const matches = await vscode.workspace.findFiles(glob, '**/{node_modules,.git,out,dist}/**', 100);
    for (const uri of matches) files.set(uri.toString(), uri);
  }
  const withStats = await Promise.all([...files.values()].map(async uri => {
    try {
      const stat = await vscode.workspace.fs.stat(uri);
      return {uri, modified: stat.mtime};
    } catch {
      return {uri, modified: 0};
    }
  }));
  return withStats.sort((a, b) => b.modified - a.modified)[0]?.uri;
}

async function readTextFile(uri: vscode.Uri): Promise<string | undefined> {
  try {
    const bytes = await vscode.workspace.fs.readFile(uri);
    return Buffer.from(bytes).toString('utf8').slice(0, 64_000);
  } catch {
    void vscode.window.showWarningMessage(`AEG could not read ${path.basename(uri.fsPath)}.`);
    return undefined;
  }
}

async function writeExperienceReceipt(receipt: ExperienceReceipt): Promise<vscode.Uri> {
  const root = workspaceRoot();
  if (!root) throw new Error('Workspace required');
  const configured = vscode.workspace.getConfiguration('aeg').get<string>('experienceDirectory', '.aeg/experiences');
  const directory = vscode.Uri.joinPath(root, ...configured.split('/'));
  await vscode.workspace.fs.createDirectory(directory);
  const uri = vscode.Uri.joinPath(directory, `${receipt.id}.json`);
  await vscode.workspace.fs.writeFile(uri, Buffer.from(JSON.stringify(receipt, null, 2), 'utf8'));
  return uri;
}

async function experienceReceiptFiles(): Promise<vscode.Uri[]> {
  const configured = vscode.workspace.getConfiguration('aeg').get<string>('experienceDirectory', '.aeg/experiences');
  const files = await vscode.workspace.findFiles(`${configured}/**/*.json`, '**/{node_modules,.git,out,dist}/**', 200);
  const withStats = await Promise.all(files.map(async uri => {
    try {
      const stat = await vscode.workspace.fs.stat(uri);
      return {uri, modified: stat.mtime};
    } catch {
      return {uri, modified: 0};
    }
  }));
  return withStats.sort((a, b) => b.modified - a.modified).map(item => item.uri);
}

async function latestExperienceReceipt(): Promise<vscode.Uri | undefined> {
  return (await experienceReceiptFiles())[0];
}

async function countExperienceReceipts(): Promise<number> {
  if (!workspaceRoot()) return 0;
  return (await experienceReceiptFiles()).length;
}

function workspaceRoot(): vscode.Uri | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri;
}

function artifactKind(relativePath: string): string {
  if (relativePath.endsWith('.xml')) return 'junit';
  if (relativePath.endsWith('.json')) return 'report';
  if (relativePath.includes('error-context')) return 'error-context';
  return 'log';
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

async function discoverSkills(): Promise<void> {
  const skills = await scanWorkspaceSkills();
  if (skills.length === 0) {
    void vscode.window.showInformationMessage('AEG found no SKILL.md or capability.json files in this workspace.');
    return;
  }
  const selected = await pickSkill(skills, 'Discovered agent skills');
  if (selected) await vscode.window.showTextDocument(selected.uri);
}

async function recommendSkill(): Promise<void> {
  const skills = await scanWorkspaceSkills();
  if (skills.length === 0) {
    void vscode.window.showInformationMessage('AEG found no skills to recommend.');
    return;
  }
  const editor = vscode.window.activeTextEditor;
  const selectedText = editor && !editor.selection.isEmpty ? editor.document.getText(editor.selection) : '';
  const task = selectedText.trim() || await vscode.window.showInputBox({
    prompt: 'Describe the task that needs a skill',
    placeHolder: 'Example: diagnose a Playwright timeout in CI'
  });
  if (!task?.trim()) return;

  const ranked = skills
    .map(skill => ({skill, score: similarityScore(task, skill)}))
    .sort((a, b) => b.score - a.score);
  const selected = await vscode.window.showQuickPick(
    ranked.map(({skill, score}) => ({
      label: skill.name,
      description: `${Math.round(score * 100)}% match · ${skill.source}`,
      detail: skill.description || skill.uri.fsPath,
      skill
    })),
    {placeHolder: 'Recommended skills for the current task'}
  );
  if (!selected) return;

  const estimated = estimateTokens(task + selected.skill.description);
  await recordUse(selected.skill, estimated);
  const action = await vscode.window.showInformationMessage(
    `AEG recommends “${selected.skill.name}”. Estimated selection context: ~${estimated} tokens.`,
    'Open Skill',
    'Copy Skill Path'
  );
  if (action === 'Open Skill') {
    await vscode.window.showTextDocument(selected.skill.uri);
  } else if (action === 'Copy Skill Path') {
    await vscode.env.clipboard.writeText(selected.skill.uri.fsPath);
  }
}

async function rateSkill(): Promise<void> {
  const skills = await scanWorkspaceSkills();
  const selected = await pickSkill(skills, 'Choose a skill to rate');
  if (!selected) return;
  const rating = await vscode.window.showQuickPick(['5', '4', '3', '2', '1'], {
    placeHolder: `Rate ${selected.name} from 1 to 5`
  });
  if (!rating) return;
  const metrics = await readMetrics();
  const current = metrics[selected.id] ?? emptyMetric();
  current.ratings.push(Number(rating));
  metrics[selected.id] = current;
  await writeMetrics(metrics);
  void vscode.window.showInformationMessage(`Rated “${selected.name}” ${rating}/5.`);
}

async function showSkillMetrics(): Promise<void> {
  const skills = await scanWorkspaceSkills();
  const metrics = await readMetrics();
  const rows = skills.map(skill => {
    const metric = metrics[skill.id] ?? emptyMetric();
    const average = metric.ratings.length
      ? metric.ratings.reduce((sum, value) => sum + value, 0) / metric.ratings.length
      : 0;
    return {
      label: skill.name,
      description: `${metric.uses} uses · ${metric.totalEstimatedTokens} est. tokens · ${average.toFixed(1)}★`,
      detail: metric.lastUsed ? `Last used ${metric.lastUsed}` : 'Not used yet'
    };
  });
  if (rows.length === 0) {
    void vscode.window.showInformationMessage('No skill metrics are available yet.');
    return;
  }
  await vscode.window.showQuickPick(rows, {placeHolder: 'Local AEG skill metrics'});
}

async function scanWorkspaceSkills(): Promise<SkillRecord[]> {
  const config = vscode.workspace.getConfiguration('aeg');
  const globs = config.get<string[]>('skillGlobs', ['**/SKILL.md', '**/capability.json']);
  const files = new Map<string, vscode.Uri>();
  for (const glob of globs) {
    const matches = await vscode.workspace.findFiles(glob, '**/{node_modules,.git,out,dist}/**', 500);
    for (const uri of matches) files.set(uri.toString(), uri);
  }

  const skills: SkillRecord[] = [];
  for (const uri of files.values()) {
    try {
      const bytes = await vscode.workspace.fs.readFile(uri);
      const text = Buffer.from(bytes).toString('utf8');
      skills.push(uri.path.endsWith('capability.json')
        ? parseCapability(uri, text)
        : parseSkillMarkdown(uri, text));
    } catch (error) {
      console.warn(`AEG could not parse ${uri.fsPath}`, error);
    }
  }
  return skills.sort((a, b) => a.name.localeCompare(b.name));
}

function parseSkillMarkdown(uri: vscode.Uri, text: string): SkillRecord {
  const title = text.match(/^#\s+(.+)$/m)?.[1]?.trim();
  const description = text
    .split(/\r?\n/)
    .map(line => line.trim())
    .find(line => line && !line.startsWith('#') && !line.startsWith('---')) ?? '';
  return {
    id: workspaceRelativeId(uri),
    name: title || path.basename(path.dirname(uri.fsPath)),
    description,
    uri,
    tags: extractKeywords(`${title ?? ''} ${description} ${text.slice(0, 1800)}`),
    source: 'SKILL.md'
  };
}

function parseCapability(uri: vscode.Uri, text: string): SkillRecord {
  const raw = JSON.parse(text) as Record<string, unknown>;
  const name = stringValue(raw.name) || stringValue(raw.id) || path.basename(path.dirname(uri.fsPath));
  const description = stringValue(raw.description) || stringValue(raw.summary) || '';
  return {
    id: workspaceRelativeId(uri),
    name,
    description,
    uri,
    tags: Array.isArray(raw.tags)
      ? raw.tags.filter((value): value is string => typeof value === 'string')
      : extractKeywords(`${name} ${description}`),
    source: 'capability.json'
  };
}

function similarityScore(task: string, skill: SkillRecord): number {
  const taskTerms = new Set(extractKeywords(task));
  const skillTerms = new Set(extractKeywords(`${skill.name} ${skill.description} ${skill.tags.join(' ')}`));
  if (taskTerms.size === 0 || skillTerms.size === 0) return 0;
  let intersection = 0;
  for (const term of taskTerms) if (skillTerms.has(term)) intersection += 1;
  const union = new Set([...taskTerms, ...skillTerms]).size;
  const nameBonus = skill.name.toLowerCase().split(/[-_\s]+/).some(term => taskTerms.has(term)) ? 0.15 : 0;
  return Math.min(1, intersection / union + nameBonus);
}

function extractKeywords(value: string): string[] {
  const stopWords = new Set(['the', 'and', 'for', 'with', 'from', 'that', 'this', 'into', 'your', 'you', 'use', 'using', 'when', 'then', 'are', 'was']);
  return [...new Set(value.toLowerCase().match(/[a-z0-9][a-z0-9_-]{2,}/g) ?? [])]
    .filter(term => !stopWords.has(term))
    .slice(0, 120);
}

async function pickSkill(skills: SkillRecord[], placeHolder: string): Promise<SkillRecord | undefined> {
  const selected = await vscode.window.showQuickPick(
    skills.map(skill => ({
      label: skill.name,
      description: skill.source,
      detail: skill.description || skill.uri.fsPath,
      skill
    })),
    {placeHolder, matchOnDescription: true, matchOnDetail: true}
  );
  return selected?.skill;
}

async function recordUse(skill: SkillRecord, estimated: number): Promise<void> {
  const metrics = await readMetrics();
  const current = metrics[skill.id] ?? emptyMetric();
  current.uses += 1;
  current.totalEstimatedTokens += estimated;
  current.lastUsed = new Date().toISOString();
  metrics[skill.id] = current;
  await writeMetrics(metrics);
}

function emptyMetric(): SkillMetric {
  return {uses: 0, totalEstimatedTokens: 0, ratings: []};
}

async function readMetrics(): Promise<Metrics> {
  const uri = metricsUri();
  if (!uri) return {};
  try {
    const bytes = await vscode.workspace.fs.readFile(uri);
    return JSON.parse(Buffer.from(bytes).toString('utf8')) as Metrics;
  } catch {
    return {};
  }
}

async function writeMetrics(metrics: Metrics): Promise<void> {
  const uri = metricsUri();
  if (!uri) {
    void vscode.window.showWarningMessage('Open a workspace before writing AEG skill metrics.');
    return;
  }
  await vscode.workspace.fs.createDirectory(vscode.Uri.file(path.dirname(uri.fsPath)));
  await vscode.workspace.fs.writeFile(uri, Buffer.from(JSON.stringify(metrics, null, 2), 'utf8'));
}

function metricsUri(): vscode.Uri | undefined {
  const root = workspaceRoot();
  if (!root) return undefined;
  const configured = vscode.workspace.getConfiguration('aeg').get<string>('telemetryFile', '.aeg/skill-metrics.json');
  return vscode.Uri.joinPath(root, ...configured.split('/'));
}

function workspaceRelativeId(uri: vscode.Uri): string {
  return vscode.workspace.asRelativePath(uri, false).replace(/\\/g, '/');
}

function stringValue(value: unknown): string {
  return typeof value === 'string' ? value : '';
}
