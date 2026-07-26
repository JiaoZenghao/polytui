import {render} from 'ink-testing-library';
import {describe, expect, it} from 'vitest';

import {StartupApp, isExitInput} from '../src/app.js';

it('renders the exact startup view', () => {
  const view = render(<StartupApp />);
  expect(view.lastFrame()).toBe(
    'PolyTUI · TypeScript\nPress Ctrl+C or Ctrl+D to exit',
  );
});

it.each(['c', 'd'])('accepts ctrl+%s', input => {
  expect(isExitInput(input, {ctrl: true})).toBe(true);
});

it('ignores ordinary input', () => {
  expect(isExitInput('x', {ctrl: false})).toBe(false);
});
