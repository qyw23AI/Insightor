import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { InsightorService, ReviewResult, Finding } from '../services/insightorService';
import { ReviewTreeProvider, TreeItem } from '../views/reviewTreeProvider';

export class CommandHandler {
    constructor(
        private context: vscode.ExtensionContext,
        private insightorService: InsightorService,
        private reviewTreeProvider: ReviewTreeProvider
    ) {}

    async reviewPR(): Promise<void> {
        const prUrl = await this.promptForPRUrl();
        if (!prUrl) {
            return;
        }

        const depth = await this.promptForDepth();
        if (!depth) {
            return;
        }

        const incremental = await vscode.window.showQuickPick(
            ['No', 'Yes'],
            { placeHolder: 'Use incremental mode?' }
        );

        await this.executeWithProgress(
            'Reviewing PR...',
            async () => {
                const result = await this.insightorService.reviewPR(
                    prUrl,
                    depth,
                    incremental === 'Yes'
                );
                this.handleResult(result, 'Review');
            }
        );
    }

    async describePR(): Promise<void> {
        const prUrl = await this.promptForPRUrl();
        if (!prUrl) {
            return;
        }

        const depth = await this.promptForDepth();
        if (!depth) {
            return;
        }

        await this.executeWithProgress(
            'Describing PR...',
            async () => {
                const result = await this.insightorService.describePR(prUrl, depth);
                this.handleResult(result, 'Description');
            }
        );
    }

    async risksPR(): Promise<void> {
        const prUrl = await this.promptForPRUrl();
        if (!prUrl) {
            return;
        }

        const depth = await this.promptForDepth();
        if (!depth) {
            return;
        }

        const focus = await vscode.window.showQuickPick(
            ['None', 'security', 'performance', 'concurrency'],
            { placeHolder: 'Focus on specific category?' }
        );

        await this.executeWithProgress(
            'Analyzing risks...',
            async () => {
                const result = await this.insightorService.risksPR(
                    prUrl,
                    depth,
                    focus === 'None' ? undefined : focus
                );
                this.handleResult(result, 'Risk Analysis');
            }
        );
    }

    async fullReview(): Promise<void> {
        const prUrl = await this.promptForPRUrl();
        if (!prUrl) {
            return;
        }

        const depth = await this.promptForDepth();
        if (!depth) {
            return;
        }

        const skipOptions = await vscode.window.showQuickPick(
            ['describe', 'risks', 'review'],
            {
                placeHolder: 'Skip any tools? (optional)',
                canPickMany: true
            }
        );

        await this.executeWithProgress(
            'Running full review...',
            async () => {
                const result = await this.insightorService.fullReview(
                    prUrl,
                    depth,
                    skipOptions
                );
                this.handleResult(result, 'Full Review');

                // Open the generated markdown file
                const prNum = this.extractPRNumber(prUrl);
                const mdPath = path.join(
                    vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || '',
                    `insightor-full-review-${prNum}.md`
                );

                if (fs.existsSync(mdPath)) {
                    const doc = await vscode.workspace.openTextDocument(mdPath);
                    await vscode.window.showTextDocument(doc);
                }
            }
        );
    }

    async publishReview(): Promise<void> {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            vscode.window.showErrorMessage('No workspace folder open');
            return;
        }

        // Find markdown files
        const files = fs.readdirSync(workspaceFolder.uri.fsPath)
            .filter(f => f.startsWith('insightor-') && f.endsWith('.md'));

        if (files.length === 0) {
            vscode.window.showErrorMessage('No Insightor review files found');
            return;
        }

        const selectedFile = await vscode.window.showQuickPick(files, {
            placeHolder: 'Select review file to publish'
        });

        if (!selectedFile) {
            return;
        }

        const dryRun = await vscode.window.showQuickPick(
            ['No - Publish to GitHub', 'Yes - Dry run (preview only)'],
            { placeHolder: 'Dry run mode?' }
        );

        if (!dryRun) {
            return;
        }

        const mdPath = path.join(workspaceFolder.uri.fsPath, selectedFile);

        await this.executeWithProgress(
            dryRun.startsWith('Yes') ? 'Running dry run...' : 'Publishing review...',
            async () => {
                await this.insightorService.publishReview(
                    mdPath,
                    dryRun.startsWith('Yes')
                );

                const message = dryRun.startsWith('Yes')
                    ? 'Dry run completed. Check output for preview.'
                    : 'Review published to GitHub successfully!';

                vscode.window.showInformationMessage(message);
                this.insightorService.showOutput();
            }
        );
    }

    async openSettings(): Promise<void> {
        vscode.commands.executeCommand('workbench.action.openSettings', 'insightor');
    }

    async viewFinding(item: TreeItem): Promise<void> {
        if (!item.data || item.contextValue !== 'finding') {
            return;
        }

        const finding = item.data as Finding;
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];

        if (!workspaceFolder) {
            return;
        }

        const filePath = path.join(workspaceFolder.uri.fsPath, finding.location.path);

        if (!fs.existsSync(filePath)) {
            vscode.window.showWarningMessage(`File not found: ${finding.location.path}`);
            return;
        }

        const doc = await vscode.workspace.openTextDocument(filePath);
        const editor = await vscode.window.showTextDocument(doc);

        // Highlight the line
        const line = finding.location.range.start.line - 1; // VSCode uses 0-based indexing
        const range = new vscode.Range(line, 0, line, 999);
        editor.selection = new vscode.Selection(range.start, range.end);
        editor.revealRange(range, vscode.TextEditorRevealType.InCenter);

        // Show finding details in a webview panel
        this.showFindingDetails(finding);
    }

    async applyFix(item: TreeItem): Promise<void> {
        if (!item.data || item.contextValue !== 'finding') {
            return;
        }

        const finding = item.data as Finding;

        if (!finding.suggestion?.suggested_code) {
            vscode.window.showInformationMessage('No fix suggestion available for this finding');
            return;
        }

        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            return;
        }

        const filePath = path.join(workspaceFolder.uri.fsPath, finding.location.path);

        if (!fs.existsSync(filePath)) {
            vscode.window.showWarningMessage(`File not found: ${finding.location.path}`);
            return;
        }

        const doc = await vscode.workspace.openTextDocument(filePath);
        const editor = await vscode.window.showTextDocument(doc);

        const startLine = finding.location.range.start.line - 1;
        const endLine = finding.location.range.end.line - 1;
        const range = new vscode.Range(startLine, 0, endLine, 999);

        await editor.edit(editBuilder => {
            editBuilder.replace(range, finding.suggestion!.suggested_code!);
        });

        vscode.window.showInformationMessage('Fix applied successfully!');
    }

    private showFindingDetails(finding: Finding): void {
        const panel = vscode.window.createWebviewPanel(
            'insightorFinding',
            `Finding: ${finding.title}`,
            vscode.ViewColumn.Two,
            { enableScripts: true }
        );

        panel.webview.html = this.getFindingDetailsHtml(finding);
    }

    private getFindingDetailsHtml(finding: Finding): string {
        const severityColor = {
            'critical': '#ff0000',
            'high': '#ff9900',
            'medium': '#3399ff',
            'low': '#cccccc',
            'info': '#00cc00'
        }[finding.severity] || '#cccccc';

        return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Finding Details</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            color: var(--vscode-foreground);
            background-color: var(--vscode-editor-background);
            padding: 20px;
            line-height: 1.6;
        }
        .header {
            border-bottom: 2px solid ${severityColor};
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        .severity {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            background-color: ${severityColor};
            color: white;
            font-weight: bold;
            text-transform: uppercase;
            font-size: 0.85em;
        }
        .section {
            margin: 20px 0;
        }
        .section-title {
            font-weight: bold;
            font-size: 1.1em;
            margin-bottom: 8px;
            color: var(--vscode-textLink-foreground);
        }
        .code-block {
            background-color: var(--vscode-textCodeBlock-background);
            border: 1px solid var(--vscode-panel-border);
            border-radius: 4px;
            padding: 12px;
            margin: 8px 0;
            overflow-x: auto;
        }
        pre {
            margin: 0;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .location {
            font-family: monospace;
            background-color: var(--vscode-badge-background);
            color: var(--vscode-badge-foreground);
            padding: 2px 6px;
            border-radius: 3px;
        }
        .confidence {
            font-weight: bold;
            color: var(--vscode-textLink-activeForeground);
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>${finding.title}</h1>
        <span class="severity">${finding.severity}</span>
        <span style="margin-left: 10px;">Category: ${finding.category}</span>
    </div>

    <div class="section">
        <div class="section-title">📍 Location</div>
        <span class="location">${finding.location.path}:${finding.location.range.start.line}</span>
    </div>

    <div class="section">
        <div class="section-title">📝 Description</div>
        <p>${finding.description}</p>
    </div>

    ${finding.confidence ? `
    <div class="section">
        <div class="section-title">🎯 Confidence</div>
        <span class="confidence">${(finding.confidence * 100).toFixed(0)}%</span>
    </div>
    ` : ''}

    ${finding.suggestion?.current_code ? `
    <div class="section">
        <div class="section-title">❌ Current Code</div>
        <div class="code-block">
            <pre>${this.escapeHtml(finding.suggestion.current_code)}</pre>
        </div>
    </div>
    ` : ''}

    ${finding.suggestion?.suggested_code ? `
    <div class="section">
        <div class="section-title">✅ Suggested Code</div>
        <div class="code-block">
            <pre>${this.escapeHtml(finding.suggestion.suggested_code)}</pre>
        </div>
    </div>
    ` : ''}
</body>
</html>
        `;
    }

    private escapeHtml(text: string): string {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    private async promptForPRUrl(): Promise<string | undefined> {
        return await vscode.window.showInputBox({
            prompt: 'Enter GitHub PR URL',
            placeHolder: 'https://github.com/owner/repo/pull/123',
            validateInput: (value) => {
                if (!value) {
                    return 'PR URL is required';
                }
                if (!value.includes('github.com') || !value.includes('/pull/')) {
                    return 'Invalid GitHub PR URL';
                }
                return null;
            }
        });
    }

    private async promptForDepth(): Promise<string | undefined> {
        const config = vscode.workspace.getConfiguration('insightor');
        const defaultDepth = config.get<string>('defaultDepth', 'standard');

        return await vscode.window.showQuickPick(
            ['quick', 'standard', 'deep'],
            {
                placeHolder: 'Select analysis depth',
                canPickMany: false
            }
        ) || defaultDepth;
    }

    private async executeWithProgress(
        title: string,
        task: () => Promise<void>
    ): Promise<void> {
        await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title,
                cancellable: false
            },
            async () => {
                try {
                    await task();
                } catch (error) {
                    const errorMessage = error instanceof Error ? error.message : String(error);
                    vscode.window.showErrorMessage(`Insightor error: ${errorMessage}`);
                    this.insightorService.showOutput();
                }
            }
        );
    }

    private handleResult(result: ReviewResult | null, operationType: string): void {
        if (!result) {
            vscode.window.showWarningMessage(`${operationType} completed but no result found`);
            return;
        }

        this.reviewTreeProvider.setResult(result);

        const config = vscode.workspace.getConfiguration('insightor');
        const showNotifications = config.get<boolean>('showNotifications', true);

        if (showNotifications) {
            const findingsCount = result.findings?.length || 0;
            const score = result.merge_readiness?.score;
            const scoreText = score !== undefined ? ` | Score: ${score}/100` : '';

            vscode.window.showInformationMessage(
                `${operationType} complete: ${findingsCount} findings${scoreText}`
            );
        }
    }

    private extractPRNumber(prUrl: string): string {
        const parts = prUrl.split('/');
        return parts[parts.length - 1];
    }
}
