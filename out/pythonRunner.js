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
exports.PythonRunner = void 0;
const child_process = __importStar(require("child_process"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
class PythonRunner {
    constructor() {
        // Try to find Python executable
        this.pythonPath = this.findPython();
    }
    findPython() {
        // Try common Python commands
        const pythonCommands = ['python', 'python3', 'py'];
        for (const cmd of pythonCommands) {
            try {
                const result = child_process.execSync(`${cmd} --version`, {
                    encoding: 'utf-8',
                    stdio: ['pipe', 'pipe', 'ignore']
                });
                if (result.includes('Python 3')) {
                    return cmd;
                }
            }
            catch (e) {
                // Continue to next command
            }
        }
        return 'python'; // Default fallback
    }
    async runScript(scriptPath, args, options) {
        return new Promise((resolve, reject) => {
            const fullScriptPath = path.join(options.cwd, scriptPath);
            // Check if script exists
            if (!fs.existsSync(fullScriptPath)) {
                reject(new Error(`Script not found: ${fullScriptPath}`));
                return;
            }
            const command = `${this.pythonPath} "${fullScriptPath}" ${args.join(' ')}`;
            const childProcess = child_process.exec(command, {
                cwd: options.cwd,
                env: { ...process.env, ...options.env },
                maxBuffer: 10 * 1024 * 1024 // 10MB buffer
            }, (error, stdout, stderr) => {
                const exitCode = error ? error.code || 1 : 0;
                resolve({ stdout, stderr, exitCode });
            });
        });
    }
    async checkDependencies(cwd) {
        const requirementsPath = path.join(cwd, 'requirements.txt');
        if (!fs.existsSync(requirementsPath)) {
            return { installed: true, missing: [] };
        }
        try {
            const requirements = fs.readFileSync(requirementsPath, 'utf-8')
                .split('\n')
                .map(line => line.trim())
                .filter(line => line && !line.startsWith('#'))
                .map(line => line.split('==')[0].split('>=')[0].split('<=')[0].trim());
            const missing = [];
            // Use `pip show` to check installed packages by distribution name.
            // This avoids false negatives for packages whose import name differs
            // from the distribution name (e.g. python-dotenv -> import dotenv).
            for (const pkg of requirements) {
                try {
                    child_process.execSync(`${this.pythonPath} -m pip show ${pkg}`, {
                        stdio: 'ignore'
                    });
                }
                catch (e) {
                    missing.push(pkg);
                }
            }
            return {
                installed: missing.length === 0,
                missing
            };
        }
        catch (e) {
            return { installed: false, missing: [] };
        }
    }
    async installDependencies(cwd) {
        const requirementsPath = path.join(cwd, 'requirements.txt');
        if (!fs.existsSync(requirementsPath)) {
            return true;
        }
        try {
            child_process.execSync(`${this.pythonPath} -m pip install -r "${requirementsPath}"`, {
                cwd,
                stdio: 'inherit'
            });
            return true;
        }
        catch (e) {
            return false;
        }
    }
}
exports.PythonRunner = PythonRunner;
//# sourceMappingURL=pythonRunner.js.map