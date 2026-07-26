import {describe, expect, it, vi} from 'vitest';

import {runInteractive} from '../src/terminal.js';

function stream(isTTY: boolean) {
  const frames: string[] = [];

  return {
    isTTY,
    frames,
    write(frame: string) {
      frames.push(frame);
      return true;
    },
  };
}

describe('runInteractive', () => {
  it('returns 2 without rendering when either required stream is not a TTY', async () => {
    const stdout = stream(true);
    const stderr = stream(true);
    const renderApp = vi.fn();

    const exitCode = await runInteractive(
      {stdin: {isTTY: false}, stdout, stderr},
      renderApp,
    );

    expect(exitCode).toBe(2);
    expect(renderApp).not.toHaveBeenCalled();
    expect(stdout.frames).toEqual([]);
    expect(stderr.frames).toEqual([
      'polytui: interactive mode requires a TTY\n',
    ]);
  });

  it('returns 1 and only writes the internal diagnostic when rendering fails', async () => {
    const stdout = stream(true);
    const stderr = stream(true);
    const renderApp = vi.fn(() => {
      throw new Error('render failure');
    });

    const exitCode = await runInteractive(
      {stdin: {isTTY: true}, stdout, stderr},
      renderApp,
    );

    expect(exitCode).toBe(1);
    expect(stdout.frames).toEqual([]);
    expect(stderr.frames).toEqual(['polytui: interactive mode failed\n']);
  });

  it('returns 0 after the rendered app exits', async () => {
    const stdout = stream(true);
    const stderr = stream(true);
    const renderApp = vi.fn(() => ({waitUntilExit: async () => undefined}));

    const exitCode = await runInteractive(
      {stdin: {isTTY: true}, stdout, stderr},
      renderApp,
    );

    expect(exitCode).toBe(0);
    expect(renderApp).toHaveBeenCalledOnce();
    expect(stderr.frames).toEqual([]);
  });
});
