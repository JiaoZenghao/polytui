import {describe, expect, it, vi} from 'vitest';

import {createProgram} from '../src/cli.js';

describe('createProgram', () => {
  it('uses the shared version text', () => {
    expect(createProgram().version()).toBe(
      'polytui 0.1.0-dev.0 (typescript)',
    );
  });

  it('runs interactive mode once and hands non-zero status to the exit setter', async () => {
    const runInteractive = vi.fn(async () => 2);
    const setExitCode = vi.fn();

    await createProgram(runInteractive, setExitCode).parseAsync([
      'node',
      'polytui',
    ]);

    expect(runInteractive).toHaveBeenCalledOnce();
    expect(setExitCode).toHaveBeenCalledWith(2);
  });

  it.each(['--version', '--help'])('%s bypasses interactive mode', async flag => {
    const runInteractive = vi.fn(async () => 0);
    const program = createProgram(runInteractive)
      .configureOutput({writeOut: () => {}, writeErr: () => {}})
      .exitOverride();

    await expect(
      program.parseAsync(['node', 'polytui', flag]),
    ).rejects.toMatchObject({code: expect.any(String)});

    expect(runInteractive).not.toHaveBeenCalled();
  });
});
