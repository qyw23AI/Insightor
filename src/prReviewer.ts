import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { PythonRunner } from './pythonRunner';
import { ConfigManager } from './config';

export class PRReviewer {
    private pythonRunner: PythonRunner;
    private configManager: ConfigManager;
    private outputChannel: vscode.OutputChannel;

    constructor(configManager: ConfigManager) {
        this.pythonRunner = new PythonRunner();
        this.configManager = configManager;
        this.outputChannel = vscode.window.createOutputChannel('Insightor');
    }

    public async reviewPRByUrl(prUrl: string): Promise<void> {
        // Validate configuration
        const validation = this.configManager.validateConfig();
        if (!validation.valid) {
            vscode.window.showErrorMessage(validation.message || 'Configuration error');
            return;
        }

        const config = this.configManager.getConfig();

        // If autoPostComment is false, ask the user whether to post this time
        let postCommentFlag = config.autoPostComment;
        if (!postCommentFlag) {
            const choice = await vscode.window.showInformationMessage(
                'Auto-post to GitHub is disabled. Post the review comment to GitHub for this run?',
                'Yes',
                'No'
            );
            postCommentFlag = (choice === 'Yes');
        }

        // Show progress
        await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: 'Reviewing PR...',
                cancellable: false
            },
            async (progress) => {
                try {
                    progress.report({ message: 'Checking dependencies...' });
                    await this.ensureDependencies();

                    progress.report({ message: 'Running AI review...' });
                    const result = await this.runReview({
                        url: prUrl,
                        reviewType: config.reviewType,
                        postComment: postCommentFlag,
                        commentType: config.commentType,
                        githubToken: config.githubToken,
                        anthropicApiKey: config.anthropicApiKey,
                        anthropicBaseUrl: config.anthropicBaseUrl
                    });

                    progress.report({ message: 'Review complete!' });
                    await this.showReviewResult(result);
                } catch (error) {
                    const errorMessage = error instanceof Error ? error.message : String(error);
                    vscode.window.showErrorMessage(`Review failed: ${errorMessage}`);
                    this.outputChannel.appendLine(`Error: ${errorMessage}`);
                    this.outputChannel.show();
                }
            }
        );
    }

    public async reviewCurrentRepoPR(prNumber: number, workspacePath: string): Promise<void> {
        // Validate configuration
        const validation = this.configManager.validateConfig();
        if (!validation.valid) {
            vscode.window.showErrorMessage(validation.message || 'Configuration error');
            return;
        }

        const config = this.configManager.getConfig();

        // Get git remote info
        const gitInfo = await this.getGitInfo(workspacePath);
        if (!gitInfo) {
            vscode.window.showErrorMessage('Could not determine GitHub repository information');
            return;
        }

        const prUrl = `https://github.com/${gitInfo.owner}/${gitInfo.repo}/pull/${prNumber}`;
        await this.reviewPRByUrl(prUrl);
    }

    private async ensureDependencies(): Promise<void> {
        const extensionPath = this.getExtensionPath();
        const depCheck = await this.pythonRunner.checkDependencies(extensionPath);

        if (!depCheck.installed) {
            const install = await vscode.window.showWarningMessage(
                `Missing Python dependencies: ${depCheck.missing.join(', ')}. Install now?`,
                'Install',
                'Cancel'
            );

            if (install === 'Install') {
                const success = await this.pythonRunner.installDependencies(extensionPath);
                if (!success) {
                    throw new Error('Failed to install dependencies');
                }
            } else {
                throw new Error('Dependencies not installed');
            }
        }
    }

    private async runReview(options: {
        url: string;
        reviewType: string;
        postComment: boolean;
        commentType: string;
        githubToken: string;
        anthropicApiKey: string;
        anthropicBaseUrl: string;
    }): Promise<string> {
        const extensionPath = this.getExtensionPath();

        // Build command arguments
        const args = [
            '--url', options.url,
            '--type', options.reviewType,
            '--output', 'markdown'
        ];

        if (options.postComment) {
            // Pass the comment type as the value of --post-comment to match main.py
            args.push('--post-comment', options.commentType);
        }

        // Set environment variables
        const env = {
            GITHUB_TOKEN: options.githubToken,
            ANTHROPIC_API_KEY: options.anthropicApiKey,
            ANTHROPIC_BASE_URL: options.anthropicBaseUrl
        };

        this.outputChannel.appendLine(`Running review for: ${options.url}`);
        this.outputChannel.appendLine(`Review type: ${options.reviewType}`);
        // Log whether a GitHub token was provided (mask actual token)
        this.outputChannel.appendLine(`GITHUB_TOKEN present: ${env.GITHUB_TOKEN ? 'yes' : 'no'}`);

        const result = await this.pythonRunner.runScript('main.py', args, {
            cwd: extensionPath,
            env
        });

        // Always show stdout/stderr in the output channel for diagnosis
        if (result.stdout && result.stdout.trim()) {
            this.outputChannel.appendLine('STDOUT:');
            this.outputChannel.appendLine(result.stdout);
        }
        if (result.stderr && result.stderr.trim()) {
            this.outputChannel.appendLine('STDERR:');
            this.outputChannel.appendLine(result.stderr);
        }

        if (result.exitCode !== 0) {
            throw new Error(`Review script failed with exit code ${result.exitCode}`);
        }

        this.outputChannel.appendLine('Review completed successfully');
        return result.stdout;
    }

    private async showReviewResult(result: string): Promise<void> {
        // Create a new document to show the review
        const doc = await vscode.workspace.openTextDocument({
            content: result,
            language: 'markdown'
        });

        await vscode.window.showTextDocument(doc, {
            preview: false,
            viewColumn: vscode.ViewColumn.Beside
        });

        vscode.window.showInformationMessage('PR review completed!');
    }

    private async getGitInfo(workspacePath: string): Promise<{ owner: string; repo: string } | null> {
        try {
            const { execSync } = require('child_process');
            const remoteUrl = execSync('git config --get remote.origin.url', {
                cwd: workspacePath,
                encoding: 'utf-8'
            }).trim();

            // Parse GitHub URL
            const match = remoteUrl.match(/github\.com[:/](.+?)\/(.+?)(\.git)?$/);
            if (match) {
                return {
                    owner: match[1],
                    repo: match[2]
                };
            }
        } catch (e) {
            // Git command failed
        }

        return null;
    }

    private getExtensionPath(): string {
        // In development, this is the workspace root
        // In production, this would be the extension installation path
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (workspaceFolders && workspaceFolders.length > 0) {
            return workspaceFolders[0].uri.fsPath;
        }
        throw new Error('No workspace folder found');
    }
}
