import * as child_process from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

export interface PythonRunnerOptions {
    cwd: string;
    env?: NodeJS.ProcessEnv;
}

export class PythonRunner {
    private pythonPath: string;

    constructor() {
        // Try to find Python executable
        this.pythonPath = this.findPython();
    }

    private findPython(): string {
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
            } catch (e) {
                // Continue to next command
            }
        }

        return 'python'; // Default fallback
    }

    public async runScript(
        scriptPath: string,
        args: string[],
        options: PythonRunnerOptions
    ): Promise<{ stdout: string; stderr: string; exitCode: number }> {
        return new Promise((resolve, reject) => {
            const fullScriptPath = path.join(options.cwd, scriptPath);

            // Check if script exists
            if (!fs.existsSync(fullScriptPath)) {
                reject(new Error(`Script not found: ${fullScriptPath}`));
                return;
            }

            const command = `${this.pythonPath} "${fullScriptPath}" ${args.join(' ')}`;

            const childProcess = child_process.exec(
                command,
                {
                    cwd: options.cwd,
                    env: { ...process.env, ...options.env },
                    maxBuffer: 10 * 1024 * 1024 // 10MB buffer
                },
                (error, stdout, stderr) => {
                    const exitCode = error ? error.code || 1 : 0;
                    resolve({ stdout, stderr, exitCode });
                }
            );
        });
    }

    public async checkDependencies(cwd: string): Promise<{ installed: boolean; missing: string[] }> {
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

            const missing: string[] = [];

            // Use `pip show` to check installed packages by distribution name.
            // This avoids false negatives for packages whose import name differs
            // from the distribution name (e.g. python-dotenv -> import dotenv).
            for (const pkg of requirements) {
                try {
                    child_process.execSync(`${this.pythonPath} -m pip show ${pkg}`, {
                        stdio: 'ignore'
                    });
                } catch (e) {
                    missing.push(pkg);
                }
            }

            return {
                installed: missing.length === 0,
                missing
            };
        } catch (e) {
            return { installed: false, missing: [] };
        }
    }

    public async installDependencies(cwd: string): Promise<boolean> {
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
        } catch (e) {
            return false;
        }
    }
}
