"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const prReviewer_1 = require("./prReviewer");
const config_1 = require("./config");
function activate(context) {
    console.log('Insightor extension is now active');
    const configManager = new config_1.ConfigManager();
    const prReviewer = new prReviewer_1.PRReviewer(configManager);
    // Command: Review PR by URL
    const reviewPRCommand = vscode.commands.registerCommand('insightor.reviewPR', async () => {
        const lastPrUrl = context.globalState.get('insightor.lastPrUrl', '');
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
        const currentGithubToken = config.get('githubToken') || '';
        const currentAnthropicApiKey = config.get('anthropicApiKey') || '';
        const currentBaseUrl = config.get('anthropicBaseUrl') || 'https://cc-vibe.com';
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
function deactivate() { }
//# sourceMappingURL=extension.js.map