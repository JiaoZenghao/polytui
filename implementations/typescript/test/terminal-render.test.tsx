import {render} from 'ink';
import {expect, it, vi} from 'vitest';

vi.mock('ink', () => ({render: vi.fn()}));

import {runInteractive} from '../src/terminal.js';

it('keeps Ink interactive when CI is set for validated TTY streams', async () => {
  const stdin = {isTTY: true};
  const stdout = {isTTY: true, write: () => true};
  const stderr = {write: () => true};
  vi.mocked(render).mockReturnValue({
    waitUntilExit: async () => undefined,
  } as never);

  const exitCode = await runInteractive({stdin, stdout, stderr});

  expect(exitCode).toBe(0);
  expect(render).toHaveBeenCalledWith(
    expect.anything(),
    expect.objectContaining({
      interactive: true,
      stdin,
      stdout,
      stderr,
      exitOnCtrlC: false,
      patchConsole: false,
    }),
  );
});
