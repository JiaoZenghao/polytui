import {Text, useApp, useInput} from 'ink';

export const banner = 'PolyTUI · TypeScript';
export const exitHint = 'Press Ctrl+C or Ctrl+D to exit';

export interface ExitKey {
  ctrl: boolean;
}

export function isExitInput(input: string, key: ExitKey): boolean {
  return key.ctrl && (input === 'c' || input === 'd');
}

export function StartupApp() {
  const {exit} = useApp();

  useInput((input, key) => {
    if (isExitInput(input, key)) {
      exit();
    }
  });

  return <Text>{`${banner}\n${exitHint}`}</Text>;
}
