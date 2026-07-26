import {Command} from 'commander';

import {versionText} from './build-info.js';
import {runInteractive} from './terminal.js';

export function createProgram(
  run: () => Promise<number> = runInteractive,
  setExitCode: (code: number) => void = code => {
    process.exitCode = code;
  },
): Command {
  return new Command()
    .name('polytui')
    .description('Learn CLI/TUI development across four languages')
    .version(versionText)
    .action(async () => {
      const exitCode = await run();

      if (exitCode !== 0) {
        setExitCode(exitCode);
      }
    });
}
