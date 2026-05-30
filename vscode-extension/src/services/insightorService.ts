import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

export interface ReviewResult {
    meta: {
        pr_url: string;
        analysis_depth: string;
        model: string;
        duration_ms: number;
        tokens_used: number;
    };
    summary?: {
        pr_type: string;
        overview: string;
    };
    findings: Finding[];
    merge_readiness?: {
        score: number;
        recommendation: string;
        summary?: string;
    };
    file_walkthrough?: FileWalkthrough[];
}

export interface Finding {
    id: string;
    title: string;
    description: string;
    severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
    category: string;
    location: {
        path: string;
        range: {
            start: { line: number; column: number };
            end: { line: number; column: number };
        };
    };
    suggestion?: {
        current_code?: string;
        suggested_code?: string;
    };
    confidence?: number;
}

export interface FileWalkthrough {
    path: string;
    edit_type: string;
    summary: string;
}

export class InsightorService {
    private context: vscode.ExtensionContext;
    private outputChannel: vscode.OutputChannel;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        this.outputChannel = vscode.window.createOutputChannel('Insightor');
    }

    private getPythonPath(): string {
        const config = vscode.workspace.getConfiguration('insightor');
        return config.get<string>('pythonPath', 'python');
    }

    private getDefaultDepth(): string {
        const config = vscode.workspace.getConfiguration('insightor');
        return config.get<string>('defaultDepth', 'standard');
    }

    private getModel(): string | undefined {
        const config = vscode.workspace.getConfiguration('insightor');
        const model = config.get<string>('model', '');
        return model || undefined;
    }

    async checkInstallation(): Promise<boolean> {
        try {
            const result = await this.executeCommand(['--version']);
            return result.exitCode === 0;
        } catch (error) {
            return false;
        }
    }

    async reviewPR(prUrl: string, depth?: string, incremental: boolean = false): Promise<ReviewResult | null> {
        const args = ['review', prUrl, '--depth', depth || this.getDefaultDepth()];

        if (incremental) {
            args.push('--incremental');
        }

        const model = this.getModel();
        if (model) {
            args.push('--model', model);
        }

        const result = await this.executeCommand(args);

        if (result.exitCode !== 0) {
            throw new Error(`Review failed: ${result.stderr}`);
        }

        return this.loadLatestResult(prUrl);
    }

    async describePR(prUrl: string, depth?: string): Promise<ReviewResult | null> {
        const args = ['describe', prUrl, '--depth', depth || this.getDefaultDepth()];

        const model = this.getModel();
        if (model) {
            args.push('--model', model);
        }

        const result = await this.executeCommand(args);

        if (result.exitCode !== 0) {
            throw new Error(`Describe failed: ${result.stderr}`);
        }

        return this.loadLatestResult(prUrl);
    }

    async risksPR(prUrl: string, depth?: string, focus?: string): Promise<ReviewResult | null> {
        const args = ['risks', prUrl, '--depth', depth || this.getDefaultDepth()];

        if (focus) {
            args.push('--focus', focus);
        }

        const model = this.getModel();
        if (model) {
            args.push('--model', model);
        }

        const result = await this.executeCommand(args);

        if (result.exitCode !== 0) {
            throw new Error(`Risks analysis failed: ${result.stderr}`);
        }

        return this.loadLatestResult(prUrl);
    }

    async fullReview(prUrl: string, depth?: string, skip?: string[]): Promise<ReviewResult | null> {
        const args = ['full', prUrl, '--depth', depth || this.getDefaultDepth()];

        if (skip && skip.length > 0) {
            skip.forEach(s => {
                args.push('--skip', s);
            });
        }

        const model = this.getModel();
        if (model) {
            args.push('--model', model);
        }

        const result = await this.executeCommand(args);

        if (result.exitCode !== 0) {
            throw new Error(`Full review failed: ${result.stderr}`);
        }

        return this.loadLatestResult(prUrl);
    }

    async publishReview(mdPath: string, dryRun: boolean = false): Promise<void> {
        const args = ['publish', mdPath];

        if (dryRun) {
            args.push('--dry-run');
        }

        const result = await this.executeCommand(args);

        if (result.exitCode !== 0) {
            throw new Error(`Publish failed: ${result.stderr}`);
        }
    }

    private async executeCommand(args: string[]): Promise<{ exitCode: number; stdout: string; stderr: string }> {
        return new Promise((resolve, reject) => {
            const pythonPath = this.getPythonPath();
            const fullArgs = ['-m', 'insightor', ...args];

            this.outputChannel.appendLine(`Executing: ${pythonPath} ${fullArgs.join(' ')}`);

            const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
            const cwd = workspaceFolder ? workspaceFolder.uri.fsPath : undefined;

            const process = cp.spawn(pythonPath, fullArgs, {
                cwd,
                shell: true
            });

            let stdout = '';
            let stderr = '';

            process.stdout.on('data', (data) => {
                const text = data.toString();
                stdout += text;
                this.outputChannel.append(text);
            });

            process.stderr.on('data', (data) => {
                const text = data.toString();
                stderr += text;
                this.outputChannel.append(text);
            });

            process.on('close', (code) => {
                this.outputChannel.appendLine(`Process exited with code ${code}`);
                resolve({
                    exitCode: code || 0,
                    stdout,
                    stderr
                });
            });

            process.on('error', (error) => {
                this.outputChannel.appendLine(`Error: ${error.message}`);
                reject(error);
            });
        });
    }

    private async loadLatestResult(prUrl: string): Promise<ReviewResult | null> {
        try {
            const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
            if (!workspaceFolder) {
                return null;
            }

            const prNum = this.extractPRNumber(prUrl);
            const reviewsDir = path.join(workspaceFolder.uri.fsPath, '.insightor', 'reviews');

            if (!fs.existsSync(reviewsDir)) {
                return null;
            }

            const files = fs.readdirSync(reviewsDir)
                .filter(f => f.startsWith(`insightor-review-${prNum}-`) && f.endsWith('.json'))
                .sort()
                .reverse();

            if (files.length === 0) {
                return null;
            }

            const latestFile = path.join(reviewsDir, files[0]);
            const content = fs.readFileSync(latestFile, 'utf-8');
            return JSON.parse(content) as ReviewResult;
        } catch (error) {
            this.outputChannel.appendLine(`Failed to load result: ${error}`);
            return null;
        }
    }

    private extractPRNumber(prUrl: string): string {
        const parts = prUrl.split('/');
        return parts[parts.length - 1];
    }

    showOutput() {
        this.outputChannel.show();
    }
}
