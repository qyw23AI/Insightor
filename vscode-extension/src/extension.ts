import * as vscode from 'vscode';
import { InsightorService } from './services/insightorService';
import { ReviewTreeProvider } from './views/reviewTreeProvider';
import { CommandHandler } from './commands/commandHandler';

let insightorService: InsightorService;
let reviewTreeProvider: ReviewTreeProvider;
let commandHandler: CommandHandler;

export function activate(context: vscode.ExtensionContext) {
    console.log('=== Insightor extension activation started ===');
    console.log('Extension context:', context.extensionPath);

    // Initialize services
    insightorService = new InsightorService(context);
    reviewTreeProvider = new ReviewTreeProvider(context);
    commandHandler = new CommandHandler(context, insightorService, reviewTreeProvider);

    // Register tree view
    const treeView = vscode.window.createTreeView('insightorView', {
        treeDataProvider: reviewTreeProvider,
        showCollapseAll: true
    });
    context.subscriptions.push(treeView);

    // Register commands
    console.log('Registering commands...');
    context.subscriptions.push(
        vscode.commands.registerCommand('insightor.reviewPR', () => commandHandler.reviewPR()),
        vscode.commands.registerCommand('insightor.describePR', () => commandHandler.describePR()),
        vscode.commands.registerCommand('insightor.risksPR', () => commandHandler.risksPR()),
        vscode.commands.registerCommand('insightor.fullReview', () => commandHandler.fullReview()),
        vscode.commands.registerCommand('insightor.publishReview', () => commandHandler.publishReview()),
        vscode.commands.registerCommand('insightor.openSettings', () => commandHandler.openSettings()),
        vscode.commands.registerCommand('insightor.refreshView', () => reviewTreeProvider.refresh()),
        vscode.commands.registerCommand('insightor.viewFinding', (item) => commandHandler.viewFinding(item)),
        vscode.commands.registerCommand('insightor.applyFix', (item) => commandHandler.applyFix(item))
    );
    console.log('Commands registered successfully');

    // Check if insightor is installed
    checkInsightorInstallation();

    console.log('=== Insightor extension activation completed ===');
    vscode.window.showInformationMessage('Insightor extension activated!');
}

async function checkInsightorInstallation() {
    const isInstalled = await insightorService.checkInstallation();
    if (!isInstalled) {
        const action = await vscode.window.showWarningMessage(
            'Insightor CLI not found. Please install it first.',
            'Install Instructions',
            'Configure Python Path'
        );

        if (action === 'Install Instructions') {
            vscode.env.openExternal(vscode.Uri.parse('https://github.com/SCU-GuGuGaGa/Insightor#快速开始'));
        } else if (action === 'Configure Python Path') {
            vscode.commands.executeCommand('workbench.action.openSettings', 'insightor.pythonPath');
        }
    }
}

export function deactivate() {
    console.log('Insightor extension is now deactivated');
}
