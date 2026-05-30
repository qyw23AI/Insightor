import * as vscode from 'vscode';
import { ReviewResult, Finding } from '../services/insightorService';

export class ReviewTreeProvider implements vscode.TreeDataProvider<TreeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<TreeItem | undefined | null | void> = new vscode.EventEmitter<TreeItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<TreeItem | undefined | null | void> = this._onDidChangeTreeData.event;

    private currentResult: ReviewResult | null = null;
    private context: vscode.ExtensionContext;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
    }

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    setResult(result: ReviewResult | null): void {
        this.currentResult = result;
        this.refresh();
    }

    getTreeItem(element: TreeItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: TreeItem): Thenable<TreeItem[]> {
        if (!this.currentResult) {
            return Promise.resolve([]);
        }

        if (!element) {
            // Root level
            const items: TreeItem[] = [];

            // Summary section
            if (this.currentResult.summary) {
                items.push(new TreeItem(
                    `📋 ${this.currentResult.summary.pr_type || 'PR Summary'}`,
                    vscode.TreeItemCollapsibleState.Collapsed,
                    'summary'
                ));
            }

            // Merge readiness
            if (this.currentResult.merge_readiness) {
                const mr = this.currentResult.merge_readiness;
                const icon = mr.score >= 80 ? '✅' : mr.score >= 50 ? '⚠️' : '🔴';
                items.push(new TreeItem(
                    `${icon} Score: ${mr.score}/100`,
                    vscode.TreeItemCollapsibleState.None,
                    'score'
                ));
            }

            // Findings by severity
            const severities = ['critical', 'high', 'medium', 'low', 'info'];
            for (const severity of severities) {
                const findings = this.currentResult.findings.filter(f => f.severity === severity);
                if (findings.length > 0) {
                    const icon = this.getSeverityIcon(severity);
                    items.push(new TreeItem(
                        `${icon} ${severity.toUpperCase()} (${findings.length})`,
                        vscode.TreeItemCollapsibleState.Collapsed,
                        'severity',
                        { severity, findings }
                    ));
                }
            }

            // File walkthrough
            if (this.currentResult.file_walkthrough && this.currentResult.file_walkthrough.length > 0) {
                items.push(new TreeItem(
                    `📁 Files Changed (${this.currentResult.file_walkthrough.length})`,
                    vscode.TreeItemCollapsibleState.Collapsed,
                    'files'
                ));
            }

            return Promise.resolve(items);
        }

        // Child items
        if (element.contextValue === 'summary' && this.currentResult.summary) {
            return Promise.resolve([
                new TreeItem(
                    this.currentResult.summary.overview || 'No overview',
                    vscode.TreeItemCollapsibleState.None,
                    'text'
                )
            ]);
        }

        if (element.contextValue === 'severity' && element.data) {
            const findings = element.data.findings as Finding[];
            return Promise.resolve(findings.map(f => {
                const item = new TreeItem(
                    f.title,
                    vscode.TreeItemCollapsibleState.None,
                    'finding',
                    f
                );
                item.description = `${f.location.path}:${f.location.range.start.line}`;
                item.tooltip = f.description;
                item.command = {
                    command: 'insightor.viewFinding',
                    title: 'View Finding',
                    arguments: [item]
                };
                return item;
            }));
        }

        if (element.contextValue === 'files' && this.currentResult.file_walkthrough) {
            return Promise.resolve(this.currentResult.file_walkthrough.map(fw => {
                const item = new TreeItem(
                    `[${fw.edit_type}] ${fw.path}`,
                    vscode.TreeItemCollapsibleState.None,
                    'file'
                );
                item.description = fw.summary.substring(0, 50);
                item.tooltip = fw.summary;
                return item;
            }));
        }

        return Promise.resolve([]);
    }

    private getSeverityIcon(severity: string): string {
        const icons: { [key: string]: string } = {
            'critical': '🔴',
            'high': '🟡',
            'medium': '🔵',
            'low': '⚪',
            'info': 'ℹ️'
        };
        return icons[severity] || '•';
    }
}

export class TreeItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly contextValue: string,
        public readonly data?: any
    ) {
        super(label, collapsibleState);
    }
}
