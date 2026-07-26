import {render} from 'ink';

import {StartupApp} from './app.js';

const nonTtyDiagnostic = 'polytui: interactive mode requires a TTY';
const internalDiagnostic = 'polytui: interactive mode failed';

export interface InputStream {
  isTTY?: boolean;
}

export interface OutputStream {
  isTTY?: boolean;
  write(message: string): unknown;
}

export interface ErrorStream {
  write(message: string): unknown;
}

export interface TerminalStreams {
  stdin: InputStream;
  stdout: OutputStream;
  stderr: ErrorStream;
}

export interface RenderedApp {
  waitUntilExit(): Promise<unknown>;
}

export type RenderApp = (streams: TerminalStreams) => RenderedApp;

const processStreams: TerminalStreams = {
  stdin: process.stdin,
  stdout: process.stdout,
  stderr: process.stderr,
};

const renderStartupApp: RenderApp = streams =>
  render(<StartupApp />, {
    stdin: streams.stdin as NodeJS.ReadStream,
    stdout: streams.stdout as NodeJS.WriteStream,
    stderr: streams.stderr as NodeJS.WriteStream,
    exitOnCtrlC: false,
    patchConsole: false,
  });

export async function runInteractive(
  streams: TerminalStreams = processStreams,
  renderApp: RenderApp = renderStartupApp,
): Promise<number> {
  if (!streams.stdin.isTTY || !streams.stdout.isTTY) {
    streams.stderr.write(`${nonTtyDiagnostic}\n`);
    return 2;
  }

  try {
    await renderApp(streams).waitUntilExit();
    return 0;
  } catch {
    streams.stderr.write(`${internalDiagnostic}\n`);
    return 1;
  }
}
