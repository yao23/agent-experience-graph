import * as vscode from 'vscode';
import * as path from 'path';

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

export function activate(context: vscode.ExtensionContext): void {
  const status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  status.text = '$(sparkle) AEG Skills';
  status.command = 'aeg.discoverSkills';
  status.tooltip = 'Discover and recommend agent skills';
  status.show();

  context.subscriptions.push(
    status,
    vscode.commands.registerCommand('aeg.discoverSkills', discoverSkills),
    vscode.commands.registerCommand('aeg.recommendSkill', recommendSkill),
    vscode.commands.registerCommand('aeg.rateSkill', rateSkill),
    vscode.commands.registerCommand('aeg.showSkillMetrics', showSkillMetrics)
  );
}

export function deactivate(): void {
  // No background resources to dispose.
}

async function discoverSkills(): Promise<void> {
  const skills = await scanWorkspaceSkills();
  if (skills.length === 0) {
    void vscode.window.showInformationMessage('AEG found no SKILL.md or capability.json files in this workspace.');
    return;
  }

  const selected = await pickSkill(skills, 'Discovered agent skills');
  if (!selected) return;

  await vscode.window.showTextDocument(selected.uri);
}

async function recommendSkill(): Promise<void> {
  const skills = await scanWorkspaceSkills();
  if (skills.length === 0) {
    void vscode.window.showInformationMessage('AEG found no skills to recommend.');
    return;
  }

  const editor = vscode.window.activeTextEditor;
  const selectedText = editor?.selection && !editor.selection.isEmpty
    ? editor.document.getText(editor.selection)
    : '';

  const task = selectedText.trim() || await vscode.window.showInputBox({
    prompt: 'Describe the task that needs a skill',
    placeHolder: 'Example: generate a polished account plan from customer context'
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

  const estimatedTokens = estimateTokens(task + selected.skill.description);
  await recordUse(selected.skill, estimatedTokens);

  const action = await vscode.window.showInformationMessage(
    `AEG recommends “${selected.skill.name}”. Estimated selection context: ~${estimatedTokens} tokens.`,
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
    const averageRating = metric.ratings.length
      ? metric.ratings.reduce((a, b) => a + b, 0) / metric.ratings.length
      : 0;

    return {
      label: skill.name,
      description: `${metric.uses} uses · ${metric.totalEstimatedTokens} est. tokens · ${averageRating.toFixed(1)}★`,
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
  const tags = extractKeywords(`${title ?? ''} ${description} ${text.slice(0, 1800)}`);

  return {
    id: workspaceRelativeId(uri),
    name: title || path.basename(path.dirname(uri.fsPath)),
    description,
    uri,
    tags,
    source: 'SKILL.md'
  };
}

function parseCapability(uri: vscode.Uri, text: string): SkillRecord {
  const raw = JSON.parse(text) as Record<string, unknown>;
  const name = stringValue(raw.name) || stringValue(raw.id) || path.basename(path.dirname(uri.fsPath));
  const description = stringValue(raw.description) || stringValue(raw.summary) || '';
  const tags = Array.isArray(raw.tags)
    ? raw.tags.filter((value): value is string => typeof value === 'string')
    : extractKeywords(`${name} ${description}`);

  return {
    id: workspaceRelativeId(uri),
    name,
    description,
    uri,
    tags,
    source: 'capability.json'
  };
}

function similarityScore(task: string, skill: SkillRecord): number {
  const taskTerms = new Set(extractKeywords(task));
  const skillTerms = new Set(extractKeywords(`${skill.name} ${skill.description} ${skill.tags.join(' ')}`));
  if (taskTerms.size === 0 || skillTerms.size === 0) return 0;

  let intersection = 0;
  for (const term of taskTerms) {
    if (skillTerms.has(term)) intersection += 1;
  }

  const union = new Set([...taskTerms, ...skillTerms]).size;
  const jaccard = union ? intersection / union : 0;
  const nameBonus = skill.name.toLowerCase().split(/[-_\s]+/).some(term => taskTerms.has(term)) ? 0.15 : 0;
  return Math.min(1, jaccard + nameBonus);
}

function extractKeywords(value: string): string[] {
  const stopWords = new Set(['the', 'and', 'for', 'with', 'from', 'that', 'this', 'into', 'your', 'you', 'use', 'using', 'when', 'then', 'are', 'was']);
  return [...new Set(value.toLowerCase().match(/[a-z0-9][a-z0-9_-]{2,}/g) ?? [])]
    .filter(term => !stopWords.has(term))
    .slice(0, 120);
}

async function pickSkill(skills: SkillRecord[], placeHolder: string): Promise<SkillRecord | undefined> {
  if (skills.length === 0) return undefined;
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

async function recordUse(skill: SkillRecord, estimatedTokens: number): Promise<void> {
  const metrics = await readMetrics();
  const current = metrics[skill.id] ?? emptyMetric();
  current.uses += 1;
  current.totalEstimatedTokens += estimatedTokens;
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

  const directory = vscode.Uri.file(path.dirname(uri.fsPath));
  await vscode.workspace.fs.createDirectory(directory);
  await vscode.workspace.fs.writeFile(uri, Buffer.from(JSON.stringify(metrics, null, 2), 'utf8'));
}

function metricsUri(): vscode.Uri | undefined {
  const root = vscode.workspace.workspaceFolders?.[0]?.uri;
  if (!root) return undefined;
  const configured = vscode.workspace.getConfiguration('aeg').get<string>('telemetryFile', '.aeg/skill-metrics.json');
  return vscode.Uri.joinPath(root, ...configured.split('/'));
}

function workspaceRelativeId(uri: vscode.Uri): string {
  return vscode.workspace.asRelativePath(uri, false).replace(/\\/g, '/');
}

function estimateTokens(value: string): number {
  return Math.max(1, Math.ceil(value.length / 4));
}

function stringValue(value: unknown): string {
  return typeof value === 'string' ? value : '';
}
