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
exports.ConfigManager = void 0;
const vscode = __importStar(require("vscode"));
class ConfigManager {
    constructor() {
        this.config = vscode.workspace.getConfiguration('insightor');
    }
    getConfig() {
        return {
            githubToken: this.config.get('githubToken', ''),
            anthropicApiKey: this.config.get('anthropicApiKey', ''),
            anthropicBaseUrl: this.config.get('anthropicBaseUrl', 'https://cc-vibe.com'),
            reviewType: this.config.get('reviewType', 'comprehensive'),
            autoPostComment: this.config.get('autoPostComment', false),
            commentType: this.config.get('commentType', 'summary')
        };
    }
    validateConfig() {
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
    refresh() {
        this.config = vscode.workspace.getConfiguration('insightor');
    }
}
exports.ConfigManager = ConfigManager;
//# sourceMappingURL=config.js.map