import * as vscode from 'vscode';
import { PRReviewer } from './prReviewer';
import { ConfigManager } from './config';

export function activate(context: vscode.ExtensionContext) {
    console.log('Insightor extension is now active');

    const configManager = new ConfigManager();
    const prReviewer = new PRReviewer(configManager);

    // Command: Review PR by URL
    const reviewPRCommand = vscode.commands.registerCommand('insightor.reviewPR', async () => {
        const lastPrUrl = context.globalState.get<string>('insightor.lastPrUrl', '');
        const prUrl = await vscode.window.showInputBox({
            prompt: 'Enter GitHub PR URL',
            value: lastPrUrl,
            placeHolder: 'https://github.com/owner/repo/pull/123',
            validateInput: (value) => {
                const prUrlPattern = /^https:\/\/github\.com\/[\w-]+\/[\w.-]+\/pull\/\d+$/;
                return prUrlPattern.test(value) ? null : 'Invalid GitHub PR URL';
            }
        });

        if (!prUrl) {
            return;
        }

        await context.globalState.update('insightor.lastPrUrl', prUrl);
        await prReviewer.reviewPRByUrl(prUrl);
    });

    // Command: Review current repository PR
    const reviewCurrentPRCommand = vscode.commands.registerCommand('insightor.reviewCurrentPR', async () => {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
            vscode.window.showErrorMessage('No workspace folder open');
            return;
        }

        const prNumber = await vscode.window.showInputBox({
            prompt: 'Enter PR number',
            placeHolder: '123',
            validateInput: (value) => {
                return /^\d+$/.test(value) ? null : 'Please enter a valid PR number';
            }
        });

        if (!prNumber) {
            return;
        }

        await prReviewer.reviewCurrentRepoPR(parseInt(prNumber), workspaceFolders[0].uri.fsPath);
    });

    // Command: Configure API keys
    const configureCommand = vscode.commands.registerCommand('insightor.configure', async () => {
        const config = vscode.workspace.getConfiguration('insightor');
        const currentGithubToken = (config.get('githubToken') as string) || '';
        const currentAnthropicApiKey = (config.get('anthropicApiKey') as string) || '';
        const currentBaseUrl = (config.get('anthropicBaseUrl') as string) || 'https://cc-vibe.com';

        const githubToken = await vscode.window.showInputBox({
            prompt: 'Enter GitHub Personal Access Token',
            password: true,
            placeHolder: currentGithubToken ? 'Configured. Press Enter to keep current value.' : 'ghp_xxx'
        });
        if (githubToken === undefined) {
            return;
        }

        if (githubToken.trim()) {
            await config.update('githubToken', githubToken.trim(), vscode.ConfigurationTarget.Global);
        }

        const anthropicApiKey = await vscode.window.showInputBox({
            prompt: 'Enter Anthropic API Key',
            password: true,
            placeHolder: currentAnthropicApiKey ? 'Configured. Press Enter to keep current value.' : 'sk-ant-xxx'
        });
        if (anthropicApiKey === undefined) {
            return;
        }

        if (anthropicApiKey.trim()) {
            await config.update('anthropicApiKey', anthropicApiKey.trim(), vscode.ConfigurationTarget.Global);
        }

        const anthropicBaseUrl = await vscode.window.showInputBox({
            prompt: 'Enter Anthropic Base URL',
            value: currentBaseUrl,
            placeHolder: 'https://cc-vibe.com'
        });
        if (anthropicBaseUrl === undefined) {
            return;
        }

        if (anthropicBaseUrl.trim()) {
            await config.update('anthropicBaseUrl', anthropicBaseUrl.trim(), vscode.ConfigurationTarget.Global);
        }

        vscode.window.showInformationMessage('Insightor configuration updated');
    });

    context.subscriptions.push(reviewPRCommand, reviewCurrentPRCommand, configureCommand);
}

export function deactivate() {}
