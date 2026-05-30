import * as vscode from 'vscode';

export interface InsightorConfig {
    githubToken: string;
    anthropicApiKey: string;
    anthropicBaseUrl: string;
    reviewType: string;
    autoPostComment: boolean;
    commentType: string;
}

export class ConfigManager {
    private config: vscode.WorkspaceConfiguration;

    constructor() {
        this.config = vscode.workspace.getConfiguration('insightor');
    }

    public getConfig(): InsightorConfig {
        return {
            githubToken: this.config.get('githubToken', ''),
            anthropicApiKey: this.config.get('anthropicApiKey', ''),
            anthropicBaseUrl: this.config.get('anthropicBaseUrl', 'https://cc-vibe.com'),
            reviewType: this.config.get('reviewType', 'comprehensive'),
            autoPostComment: this.config.get('autoPostComment', false),
            commentType: this.config.get('commentType', 'summary')
        };
    }

    public validateConfig(): { valid: boolean; message?: string } {
        const config = this.getConfig();

        if (!config.githubToken) {
            return {
                valid: false,
                message: 'GitHub token is not configured. Run "Insightor: Configure API Keys" command.'
            };
        }

        if (!config.anthropicApiKey) {
            return {
                valid: false,
                message: 'Anthropic API key is not configured. Run "Insightor: Configure API Keys" command.'
            };
        }

        return { valid: true };
    }

    public refresh() {
        this.config = vscode.workspace.getConfiguration('insightor');
    }
}
