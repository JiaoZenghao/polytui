import {Command} from 'commander';

import {versionText} from './build-info.js';

export function createProgram(): Command {
  return new Command()
    .name('polytui')
    .description('Learn CLI/TUI development across four languages')
    .version(versionText);
}
